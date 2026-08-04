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
import re
import uuid
from dataclasses import dataclass
from importlib import resources
from typing import Any, cast

import yaml
from cyclonedx.model.bom import Bom
from cyclonedx.schema import SchemaVersion

from mint_oscal.controls.nist import controls_for, risk_statement
from mint_oscal.ir import Finding, Subject
from mint_oscal.policy import active_policy

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://breachsafe.ai/ns/oscal/cbom")
_DATA_PACKAGE = "mint_oscal.adapters.cbom_data"
# CycloneDX spec versions the parser understands ("1.0".."1.7"); an out-of-range
# specVersion is rejected up front rather than silently mis-parsed.
_SUPPORTED_SPEC_VERSIONS = frozenset(v.to_version() for v in SchemaVersion)
# Primitives that establish a shared/transported key -- the quantum-relevant exchange.
# key-agree (DH/ECDH) and kem (ML-KEM), plus pke: RSA-encrypted **key transport** is classical
# key establishment and must be scored, not silently dropped as a non-KEX primitive (#68).
_KEX_PRIMITIVES = frozenset({"key-agree", "kem", "pke"})
# CycloneDX's indeterminate `primitive` enum values: the producer is explicitly telling us
# it could not determine the primitive. An indeterminate algorithm that also misses the
# registry must surface as `unclassified` (it could be a hidden classical KEX), never be
# silently dropped into the most-favorable verdict -- same as a no-primitive unknown (#78).
_INDETERMINATE_PRIMITIVES = frozenset({"unknown", "other"})
_QUANTIFIERS = frozenset({"all", "some", "none"})
# Transport protocols that carry a numeric TLS-style version; SSL is handled by name.
_TLS_LIKE = frozenset({"tls", "dtls"})
# The floor at or above which a TLS/DTLS version is not, by itself, a weak offering.
# TLS 1.0/1.1 (< 1.2) are deprecated (RFC 8996); any SSL version is weaker still.
_WEAK_TLS_FLOOR = 1.2
# Extracts an embedded major(.minor) version from a protocol string, so a non-bare-decimal
# encoding ("TLSv1.0", "v1.0", "1.0.0", "1.0 (deprecated)") is still compared against the floor.
_VER_RE = re.compile(r"\d+(?:\.\d+)?")
# Readiness verdicts that a weak-protocol offering downgrades to ``classically_weak``.
# ``quantum_vulnerable`` is already unfavorable and is left as-is (honest-failure, #24/#53).
_WEAK_DOWNGRADE_FROM = frozenset({"transitional_hybrid", "quantum_ready", "unknown"})
# Readiness verdicts that carry no open PQC gap: an already-PQC-ready subject (or one out of
# scope for PQC readiness) is a resolved posture, so its risk is minted ``closed``, not open --
# A CBOM is a point-in-time inventory with no remediation evidence, so mint never claims a risk is
# "closed" from it: asserting a resolution it cannot prove is the unsafe/non-conformant direction.
# CBOM findings stay "open" (an assessor closes with evidence); QuReddy carries real status (#83).


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
    legacy_protocols: list[str]


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
    """Deterministic id from stable inputs (reproducible IR, and thus OSCAL uuids).

    Every caller passes only strings that have been shape-guarded upstream (subject id,
    readiness, inventory fingerprint), so an untrusted non-str never reaches the ``join``
    here -- it is rejected as a typed :class:`MalformedCbomError` at its source instead.
    """
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))


def _tail(ref: object) -> str:
    """Return the last path segment of a bom-ref (``crypto/algorithm/x25519`` -> ``x25519``)."""
    return str(ref).rsplit("/", 1)[-1]


def _protocol_version(*candidates: str | None) -> float | None:
    """Return the first embedded major(.minor) version number found in any candidate string."""
    for candidate in candidates:
        if isinstance(candidate, str):
            match = _VER_RE.search(candidate)
            if match:
                return float(match.group(0))
    return None


def _is_legacy_protocol(name: str | None, ptype: str | None, version: str | None) -> bool:
    """True if a ``protocol`` component offers a weak/deprecated transport.

    Weak means any SSL (all versions are deprecated) or a TLS/DTLS version below 1.2
    (TLS 1.0/1.1, deprecated by RFC 8996). SSL is matched by name because CycloneDX has
    no ``ssl`` protocol type. The version number is *extracted* from the version field or
    the name rather than parsed with a bare ``float`` -- a producer may render TLS 1.0 as
    ``"TLSv1.0"``, ``"v1.0"``, ``"1.0.0"`` or ``"1.0 (deprecated)"``, none of which
    ``float`` accepts; before this fix a ``ValueError`` was swallowed as *not weak*,
    reintroducing #53's false-favorable (its real case was literally ``TLSv1``). An SSLv3
    version (``3.0``) is caught by the SSL name match, not the numeric compare.
    """
    if (name or "").upper().replace(" ", "").startswith("SSL") or ptype == "ssl":
        return True
    if ptype in _TLS_LIKE:
        version_num = _protocol_version(version, name)
        if version_num is not None:
            return version_num < _WEAK_TLS_FLOOR
    return False


def _inventory(
    bom: Bom,
) -> tuple[dict[str, tuple[str | None, int | None]], set[str], list[str]]:
    """Collect the crypto inventory from the typed CBOM.

    Returns a mapping of algorithm name -> (producer-declared ``primitive``,
    producer-declared ``nistQuantumSecurityLevel``), the set of certificate signature
    names, and the sorted display names of any weak/legacy transport protocols offered
    (see :func:`_is_legacy_protocol`). Names are deduped case-insensitively: a cipher-suite
    bom-ref (``crypto/algorithm/x25519``) and a standalone algorithm asset (``X25519``)
    name the same algorithm, so they are folded together, preferring the proper-case
    display and keeping any producer declaration. ``related-crypto-material`` is skipped
    explicitly — its key/secret values must never reach emitted output.
    """
    canon: dict[str, tuple[str, str | None, int | None]] = {}
    sigs: set[str] = set()
    weak_protocols: set[str] = set()

    def add(name: str, primitive: str | None = None, level: int | None = None) -> None:
        # ``name`` may come straight from an untrusted component name (typed str, but the
        # parser will surface whatever JSON supplied); a non-str would leak a bare
        # ``AttributeError`` from ``.upper()``.
        if not isinstance(name, str):
            raise MalformedCbomError(f"component name must be a string, got {type(name).__name__}")
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
        # assetType is what selects the branch below; a null one would leak a bare
        # ``AttributeError`` from ``.value``. Guard it as a typed malformation.
        if cp.asset_type is None:
            raise MalformedCbomError(
                f"assetType must be present on crypto component {comp.name!r}, got null"
            )
        kind = cp.asset_type.value
        if kind == "algorithm" and comp.name:
            ap = cp.algorithm_properties
            add(
                comp.name,
                ap.primitive.value if ap and ap.primitive else None,
                ap.nist_quantum_security_level if ap else None,
            )
        elif kind == "protocol" and cp.protocol_properties:
            pp = cp.protocol_properties
            for suite in pp.cipher_suites or []:
                for ref in suite.algorithms or []:
                    add(_tail(ref))
            ptype = pp.type.value if pp.type else None
            if _is_legacy_protocol(comp.name, ptype, pp.version):
                # a plain protocol-version component (no cipherSuites) still scores the
                # verdict: a legacy TLS/SSL offering is a weak posture on its own (#53).
                weak_protocols.add(comp.name or f"{ptype or 'protocol'} {pp.version or '?'}")
        elif kind == "certificate" and cp.certificate_properties:
            ref = cp.certificate_properties.signature_algorithm_ref
            if ref:
                sigs.add(_tail(ref))
        elif kind == "related-crypto-material":
            continue  # never read key/secret material into an emitted document
    algos = {display: (primitive, level) for display, primitive, level in canon.values()}
    return algos, sigs, sorted(weak_protocols)


def _readiness(
    algos: dict[str, tuple[str | None, int | None]], weak_protocols: list[str]
) -> _Readiness:
    """Classify the inventory (producer-declared first, registry fallback) and derive readiness.

    ``primitive`` decides whether an algorithm is key exchange (``key-agree``/``kem``)
    and ``nistQuantumSecurityLevel`` decides quantum-safety; the registry supplies both
    when the CBOM omits them. A key exchange whose quantum-safety cannot be established
    (and any wholly unrecognised algorithm) is left ``unclassified`` rather than assumed
    classical, and the verdict is only computed over the KEX we could classify. The
    declarative rules then pick the verdict; an omitted quantifier means "any". The KEX
    picture is the primary signal (certificate signatures are inventoried but do not score
    it), but a weak transport offering (legacy TLS/SSL) caps the verdict: honest-failure
    means a favorable KEX cannot excuse a deprecated protocol still on the wire (#53).
    """
    registry, rules = _config()
    kex_names: list[str] = []
    kex_safe: list[bool] = []
    unclassified: list[str] = []
    levels: list[int] = []
    for name, (declared_primitive, declared_level) in algos.items():
        entry = registry.get(name.upper())
        is_kex = declared_primitive in _KEX_PRIMITIVES or (entry or {}).get("kind") == "kex"
        # A producer's nistQuantumSecurityLevel is a *classical-equivalent* strength
        # (category 1 ~ AES-128 ... 5 ~ AES-256), NOT a PQC-readiness claim. A positive
        # level must never UPGRADE an algorithm the registry authoritatively records as
        # classical (quantum_safe: false) -- otherwise a producer stamping level 1 on a
        # purely classical X25519 would read as the most-favorable posture (#79).
        # Downgrades (level 0) and registry misses stay producer-first.
        registry_classical = entry is not None and not entry.get("quantum_safe", False)
        if declared_level is not None:
            safe: bool | None = declared_level > 0 and not registry_classical
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
        elif entry is None and (
            declared_primitive is None or declared_primitive in _INDETERMINATE_PRIMITIVES
        ):
            # a registry-miss we cannot classify: either no primitive at all, or one the
            # producer explicitly flagged indeterminate (`unknown`/`other`). Surface it as
            # unclassified so a hidden classical KEX cannot ride a favorable verdict (#78).
            # A producer-declared `nistQuantumSecurityLevel` does NOT license classifying it:
            # the level is a classical-equivalent *strength*, not a primitive determination, so
            # a level-stamped indeterminate/no-primitive registry-miss is still unclassified --
            # otherwise it is silently dropped and a hidden KEX rides a favorable verdict (#98).
            unclassified.append(name)

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
    # honest-failure cap: a legacy TLS/SSL offering means the posture cannot be more
    # favorable than classically_weak, regardless of how strong the KEX looks. Applied
    # last so it also covers the not-yet-scored `unknown` case; an already-unfavorable
    # `quantum_vulnerable` is left alone (it outranks classically_weak).
    if weak_protocols and readiness in _WEAK_DOWNGRADE_FROM:
        readiness = "classically_weak"
    return _Readiness(
        readiness=readiness,
        kex=sorted(kex_names),
        unclassified=sorted(unclassified),
        level=str(min(levels)) if levels else "0",
        legacy_protocols=weak_protocols,
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
    # An unhashable specVersion (e.g. a list) would leak a bare ``TypeError`` from the
    # ``in`` membership test below; assert it is a string first.
    if not isinstance(spec_version, str):
        raise MalformedCbomError(f"specVersion must be a string, got {type(spec_version).__name__}")
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
    # subject_id is a _det part here and, via Subject.id, a _det part in the emitter too; a
    # non-str metadata component name would leak a bare TypeError from str.join. Guard it as
    # a typed malformation (contained honestly at the adapter, not silently coerced into a
    # nonsense subject id that would mint a confident-but-wrong POA&M).
    if not isinstance(subject_id, str):
        raise MalformedCbomError(
            f"metadata.component.name must be a string, got {type(subject_id).__name__}"
        )
    subject = Subject(
        id=subject_id,
        kind="inventory-item",
        description=f"cryptographic subject {subject_id}",
    )

    algos, sigs, weak_protocols = _inventory(bom)
    facts = _readiness(algos, weak_protocols)
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
    if facts.legacy_protocols:
        posture["legacy-protocols"] = ", ".join(facts.legacy_protocols)

    inventory_fp = (
        ";".join(sorted(algos))
        + "|"
        + ";".join(sorted(sigs))
        + "|"
        + ";".join(facts.legacy_protocols)
    )
    finding = Finding(
        id=_det("cbom-finding", subject_id, readiness, inventory_fp),
        title=f"Cryptographic posture: {readiness}",
        description=(
            f"KEX offered: {posture['kex-offered']}; cert signature: {posture['cert-signature']}."
        ),
        severity=active_policy().severity.get(readiness, "info"),
        status="open",
        subject=subject,
        observed_at=timestamp,
        control_ids=controls_for(readiness),
        risk_statement=risk_statement(readiness),
        posture=posture,
    )
    return [finding], subject
