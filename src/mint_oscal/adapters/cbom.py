# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
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

import datetime
import functools
import uuid
from dataclasses import dataclass
from importlib import resources
from typing import Any, cast

import yaml
from cyclonedx.model.bom import Bom

from mint_oscal.controls.nist import controls_for, risk_statement
from mint_oscal.ir import Finding, Subject

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://breachsafe.ai/ns/oscal/cbom")
_DATA_PACKAGE = "mint_oscal.adapters.cbom_data"
_KEX_PRIMITIVES = frozenset({"key-agree", "kem"})

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
    """Load and cache the crypto registry and readiness rules from bundled data."""
    data = resources.files(_DATA_PACKAGE)
    registry = yaml.safe_load((data / "crypto-registry.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((data / "readiness-rules.yaml").read_text(encoding="utf-8"))["rules"]
    return cast("dict[str, Any]", registry), cast("list[dict[str, Any]]", rules)


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
                refs = list(suite.algorithms or []) + list(getattr(suite, "tls_groups", None) or [])
                for ref in refs:
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
    when the CBOM omits them. An algorithm known to neither is left ``unclassified``
    rather than assumed classical. The declarative rules then pick the verdict; an
    omitted quantifier means "any".
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
        if entry is None and declared_primitive is None and declared_level is None:
            unclassified.append(name)
        if is_kex:
            kex_names.append(name)
            kex_safe.append(bool(safe))
            if safe and level:
                levels.append(level)

    readiness = "unknown"
    if kex_names:
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
    try:
        bom = Bom.from_json(document)  # type: ignore[attr-defined]  # lib parses + validates shape
    except MalformedCbomError:
        raise
    except Exception as exc:  # any parse failure is one domain error, not a leak
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
    timestamp = (bom.metadata.timestamp or datetime.datetime.now(datetime.UTC)).isoformat()

    posture = {
        "readiness": readiness,
        "kex-offered": ", ".join(facts.kex) or "none-observed",
        "cert-signature": ", ".join(sorted(sigs)) or "none-observed",
        "nistQuantumSecurityLevel": facts.level,
        "mapping-confidence": "partial" if facts.unclassified else "high",
    }
    if facts.unclassified:
        posture["unclassified-algorithms"] = ", ".join(facts.unclassified)

    finding = Finding(
        id=_det("cbom-finding", subject_id, readiness),
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
