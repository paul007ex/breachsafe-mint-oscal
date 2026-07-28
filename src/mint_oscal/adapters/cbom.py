# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Adapter: CycloneDX CBOM JSON -> the neutral IR.

CBOM is the vendor-independent ingestion path (ADR-0006): any producer that emits
CycloneDX cryptography assets flows through the same engine. Parsing and the typed
model come from the official ``cyclonedx-python-lib``; classification and the
readiness verdict are *data* (``cbom_data/*.yaml``), so adding a PQC algorithm or a
rule is a config edit, not a code change. This module only walks the typed
inventory, classifies each algorithm, applies the rules, and builds IR.

The adapter is a pure library function: it never logs, prints, or exits. A document
that is not a parseable CycloneDX BOM raises :class:`MalformedCbomError`.
"""

from __future__ import annotations

import functools
import uuid
from dataclasses import dataclass
from importlib import resources
from typing import Any, cast

import yaml
from cyclonedx.model.bom import Bom
from cyclonedx.schema import SchemaVersion

from mint_oscal.controls.nist import controls_for, risk_statement
from mint_oscal.ir import Finding, Subject

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://breachsafe.ai/ns/oscal/cbom")
_DATA_PACKAGE = "mint_oscal.adapters.cbom_data"
# CycloneDX spec versions the parser understands ("1.0".."1.7"); an out-of-range
# specVersion is rejected up front rather than silently mis-parsed.
_SUPPORTED_SPEC_VERSIONS = frozenset(v.to_version() for v in SchemaVersion)
_KEX_PRIMITIVES = frozenset({"key-agree", "kem"})
_QUANTIFIERS = frozenset({"all", "some", "none"})

# Readiness -> POA&M severity. The CBOM finding is about quantum readiness of the key
# establishment, so a still-classical exchange is a real, but not urgent, exposure.
_SEVERITY = {
    "quantum_vulnerable": "medium",
    "transitional_hybrid": "low",
    "quantum_ready": "info",
    "unknown": "info",
}


class MalformedCbomError(ValueError):
    """The input is not a parseable CycloneDX BOM.

    A domain error (not ``SystemExit``): the caller decides how to surface it.
    """


@dataclass(frozen=True)
class _Readiness:
    """The classified key-exchange picture derived from a CBOM inventory."""

    readiness: str
    kex: list[str]
    unclassified: list[str]
    level: str


@functools.lru_cache(maxsize=1)
def _config() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load, validate, and cache the crypto registry and readiness rules from bundled data.

    Rules are evaluated first-match-wins (order is significant), so a malformed rule must
    fail loudly at load rather than silently mis-map: an unknown quantifier is rejected
    here instead of being treated as "any" at match time.

    Raises:
        ValueError: if a readiness rule uses an unknown quantifier.
    """
    data = resources.files(_DATA_PACKAGE)
    registry = yaml.safe_load((data / "crypto-registry.yaml").read_text(encoding="utf-8"))
    rules = cast(
        "list[dict[str, Any]]",
        yaml.safe_load((data / "readiness-rules.yaml").read_text(encoding="utf-8"))["rules"],
    )
    for rule in rules:
        for field in ("kex_quantum_safe", "kex_classical"):
            value = rule.get(field)
            if value is not None and value not in _QUANTIFIERS:
                allowed = sorted(_QUANTIFIERS)
                msg = (
                    f"readiness rule has invalid {field}={value!r}; "
                    f"expected one of {allowed} or omit it"
                )
                raise ValueError(msg)
    return cast("dict[str, Any]", registry), rules


def _det(*parts: str) -> str:
    """Deterministic id from stable inputs (reproducible IR, and thus OSCAL uuids)."""
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))


def _tail(ref: object) -> str:
    """Return the last path segment of a bom-ref (``crypto/algorithm/x25519`` -> ``x25519``)."""
    return str(ref).rsplit("/", 1)[-1]


def _inventory(bom: Bom) -> tuple[dict[str, tuple[str | None, int | None]], set[str]]:
    """Collect the crypto inventory from the typed CBOM.

    Returns a mapping of algorithm name -> (producer-declared ``primitive``,
    producer-declared ``nistQuantumSecurityLevel``) and the set of certificate
    signature names. Names are deduped case-insensitively: a cipher-suite bom-ref
    (``crypto/algorithm/x25519``) and a standalone algorithm asset (``X25519``) name
    the same algorithm, so they are folded together, preferring the proper-case
    display and keeping any producer declaration. ``related-crypto-material`` is
    skipped explicitly — its key/secret values must never reach emitted output.
    """
    canon: dict[str, tuple[str, str | None, int | None]] = {}
    sigs: set[str] = set()

    def add(name: str, primitive: str | None = None, level: int | None = None) -> None:
        key = name.upper()
        prev = canon.get(key)
        if prev is None:
            canon[key] = (name, primitive, level)
        else:
            display = name if prev[0].islower() and not name.islower() else prev[0]
            canon[key] = (display, prev[1] or primitive, prev[2] if prev[2] is not None else level)

    for comp in bom.components:
        cp = comp.crypto_properties
        if cp is None:
            continue
        kind = cp.asset_type.value
        if kind == "algorithm" and comp.name:
            ap = cp.algorithm_properties
            add(
                comp.name,
                ap.primitive.value if ap and ap.primitive else None,
                ap.nist_quantum_security_level if ap else None,
            )
        elif kind == "protocol" and cp.protocol_properties:
            for suite in cp.protocol_properties.cipher_suites or []:
                for ref in suite.algorithms or []:
                    add(_tail(ref))
        elif kind == "certificate" and cp.certificate_properties:
            ref = cp.certificate_properties.signature_algorithm_ref
            if ref:
                sigs.add(_tail(ref))
        elif kind == "related-crypto-material":
            continue  # never read key/secret material into an emitted document
    algos = {display: (primitive, level) for display, primitive, level in canon.values()}
    return algos, sigs


def _readiness(algos: dict[str, tuple[str | None, int | None]]) -> _Readiness:
    """Classify the inventory (producer-declared first, registry fallback) and derive readiness.

    ``primitive`` decides whether an algorithm is key exchange (``key-agree``/``kem``)
    and ``nistQuantumSecurityLevel`` decides quantum-safety; the registry supplies both
    when the CBOM omits them. A key exchange whose quantum-safety cannot be established
    (and any wholly unrecognised algorithm) is left ``unclassified`` rather than assumed
    classical, and the verdict is only computed over the KEX we could classify. The
    declarative rules then pick the verdict; an omitted quantifier means "any". The
    verdict is KEX-centric: certificate signatures are inventoried but do not score it.
    """
    registry, rules = _config()
    kex_names: list[str] = []
    kex_safe: list[bool] = []
    unclassified: list[str] = []
    levels: list[int] = []
    for name, (declared_primitive, declared_level) in algos.items():
        entry = registry.get(name.upper())
        is_kex = declared_primitive in _KEX_PRIMITIVES or (entry or {}).get("kind") == "kex"
        if declared_level is not None:
            safe: bool | None = declared_level > 0
            level = declared_level
        elif entry is not None:
            safe = bool(entry.get("quantum_safe"))
            level = int(entry.get("nistLevel", 0))
        else:
            safe = None
            level = 0
        if is_kex:
            kex_names.append(name)
            if safe is None:
                # a key exchange whose quantum-safety we cannot establish: report it
                # honestly as unclassified (partial confidence), never assume classical.
                unclassified.append(name)
            else:
                kex_safe.append(safe)
                if safe and level:
                    levels.append(level)
        elif entry is None and declared_primitive is None and declared_level is None:
            unclassified.append(name)  # a non-KEX algorithm we do not recognize at all

    readiness = "unknown"
    if kex_safe:  # only judge over the KEX we could actually classify
        total, safe_count = len(kex_safe), sum(kex_safe)
        quantum_safe = {"all": safe_count == total, "some": safe_count > 0, "none": safe_count == 0}
        classical = {
            "all": safe_count == 0,
            "some": safe_count < total,
            "none": safe_count == total,
        }
        readiness = next(
            (
                str(rule["readiness"])
                for rule in rules
                if quantum_safe.get(rule.get("kex_quantum_safe", ""), True)
                and classical.get(rule.get("kex_classical", ""), True)
            ),
            "unknown",
        )
        # honest-failure invariant: an unclassified algorithm means we cannot claim the
        # most-favorable posture (a hidden KEX could be classical) -- never read unknown as ready.
        if readiness == "quantum_ready" and unclassified:
            readiness = "unknown"
    return _Readiness(
        readiness=readiness,
        kex=sorted(kex_names),
        unclassified=sorted(unclassified),
        level=str(min(levels)) if levels else "0",
    )


def from_cbom(document: dict[str, Any]) -> tuple[list[Finding], Subject]:
    """Convert one CycloneDX CBOM document into IR findings and their subject.

    Raises:
        MalformedCbomError: if ``document`` is not a parseable CycloneDX BOM.
    """
    # cyclonedx-python-lib parses permissively — it does NOT reject a non-CycloneDX or
    # shapeless dict — so assert the shape ourselves first, or a garbage document would
    # mint a confident-but-wrong POA&M instead of failing loudly.
    if (
        not isinstance(document, dict)
        or document.get("bomFormat") != "CycloneDX"
        or "specVersion" not in document
    ):
        raise MalformedCbomError(
            "not a CycloneDX BOM (expected bomFormat=CycloneDX and specVersion)"
        )
    spec_version = document["specVersion"]
    if spec_version not in _SUPPORTED_SPEC_VERSIONS:
        supported = ", ".join(sorted(_SUPPORTED_SPEC_VERSIONS))
        raise MalformedCbomError(
            f"unsupported CycloneDX specVersion {spec_version}; supported: {supported}"
        )
    try:
        bom = Bom.from_json(document)  # type: ignore[attr-defined]  # shape asserted above
    except Exception as exc:  # any parse failure becomes one domain error, never a leak
        raise MalformedCbomError(str(exc)) from exc

    component = bom.metadata.component
    name = (component.name if component else None) or (
        str(bom.serial_number) if bom.serial_number else None
    )
    subject_id = name or "unknown-subject"
    subject = Subject(
        id=subject_id,
        kind="inventory-item",
        description=f"cryptographic subject {subject_id}",
    )

    algos, sigs = _inventory(bom)
    facts = _readiness(algos)
    readiness = facts.readiness
    # Read the timestamp from the RAW document: cyclonedx-python-lib auto-fills
    # bom.metadata.timestamp with wall-clock now() when the CBOM omits it, which would make
    # output non-deterministic. Absent -> a deterministic epoch; the emitter makes it
    # timezone-aware (OSCAL requires it).
    timestamp = (document.get("metadata") or {}).get("timestamp") or "1970-01-01T00:00:00+00:00"

    if facts.unclassified:
        confidence = "partial"  # something crypto-relevant we could not classify
    elif readiness == "unknown":
        confidence = "not-applicable"  # no key exchange was observed to assess
    else:
        confidence = "high"
    posture = {
        "readiness": readiness,
        "kex-offered": ", ".join(facts.kex) or "none-observed",
        "cert-signature": ", ".join(sorted(sigs)) or "none-observed",
        "nistQuantumSecurityLevel": facts.level,
        "mapping-confidence": confidence,
    }
    if facts.unclassified:
        posture["unclassified-algorithms"] = ", ".join(facts.unclassified)

    inventory_fp = ";".join(sorted(algos)) + "|" + ";".join(sorted(sigs))
    finding = Finding(
        id=_det("cbom-finding", subject_id, readiness, inventory_fp),
        title=f"Cryptographic posture: {readiness}",
        description=(
            f"KEX offered: {posture['kex-offered']}; cert signature: {posture['cert-signature']}."
        ),
        severity=_SEVERITY.get(readiness, "info"),
        status="open",
        subject=subject,
        observed_at=timestamp,
        control_ids=controls_for(readiness),
        risk_statement=risk_statement(readiness),
        posture=posture,
    )
    return [finding], subject
