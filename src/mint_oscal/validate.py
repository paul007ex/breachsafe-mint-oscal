# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Semantic (Layer-2) validation of an emitted OSCAL document.

Layer 1 -- authoritative *schema/shape* conformance -- is delegated to the NIST
``oscal-cli`` oracle (see :func:`oscal_cli_available` and ADR-0005). This module adds the
cross-cutting invariants a JSON schema cannot express, plus a native, in-process
re-derivation of the OSCAL POA&M rules that matter most (required fields, the UUID and
dateTime-with-timezone datatypes, and the risk-status / observation enums) mapped 1:1 to
``oscal_poam_schema.json``, and the BreachSAFE-namespace domain vocabularies. Running
these in-process is necessary but **not** sufficient for NIST conformance -- so callers
must not report it as such. The small Validator-registry design is borrowed from IBM
``compliance-trestle`` (pattern only, no dependency; ADR-0005).
"""

from __future__ import annotations

import re
import shutil
import uuid
from collections import Counter
from collections.abc import Iterator
from typing import Any

from mint_oscal.emitters._common import BREACHSAFE_NS
from mint_oscal.policy import READINESS_VERDICTS, get_policy

_PROP_NS_KEY = "ns"

# --- OSCAL datatype patterns (verbatim from oscal_poam_schema.json, Python-re-safe) ------
# UUIDDatatype.pattern -- RFC-4122 v4/v5 shape (version nibble in [45], variant in [89ABab]);
# a nil or otherwise non-conformant uuid is flagged. mint's uuid5 output passes.
_UUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[45][0-9A-Fa-f]{3}-[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}$"
)
# DateTimeWithTimezoneDatatype.pattern -- the FULL leap-year-aware pattern, verbatim: it
# validates real calendar dates AND requires a mandatory timezone (Z or a legal offset), so
# both a naive tz-less timestamp (#18) and an impossible date (e.g. 2026-02-30) are caught.
_DT_TZ_RE = re.compile(
    r"^(((2000|2400|2800|(19|2[0-9](0[48]|[2468][048]|[13579][26])))-02-29)"
    r"|(((19|2[0-9])[0-9]{2})-02-(0[1-9]|1[0-9]|2[0-8]))"
    r"|(((19|2[0-9])[0-9]{2})-(0[13578]|10|12)-(0[1-9]|[12][0-9]|3[01]))"
    r"|(((19|2[0-9])[0-9]{2})-(0[469]|11)-(0[1-9]|[12][0-9]|30)))"
    r"T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?"
    r"(Z|(-((0[0-9]|1[0-2]):00|0[39]:30)|\+((0[0-9]|1[0-4]):00|(0[34569]|10):30|(0[58]|12):45)))$"
)

# --- Controlled vocabularies (verbatim allowed-values) -----------------------------------
# OSCAL risk-status allowed-values (POA&M metaschema).
_RISK_STATUS = frozenset(
    {
        "open",
        "investigating",
        "remediating",
        "deviation-requested",
        "deviation-approved",
        "closed",
    }
)
# OSCAL observation.methods / observation.types allowed-values.
_OBS_METHODS = frozenset({"EXAMINE", "INTERVIEW", "TEST", "UNKNOWN"})
_OBS_TYPES = frozenset(
    {"ssp-statement-issue", "control-objective", "mitigation", "finding", "discovery", "historic"}
)
# BreachSAFE mapping-confidence vocabulary.
_CONFIDENCE = frozenset({"high", "partial", "not-applicable"})
# BreachSAFE provenance grammar (see extensions.breachsafe).
_PROV_RE = re.compile(r"^(derived|producer-confirmed|conflict:producer=.+,derived=.+)$")
# NIST control identifier shape, e.g. SC-13.
_CONTROL_RE = re.compile(r"^[A-Z]{2}-\d+$")


def _find(obj: object, key: str) -> list[Any]:
    """Collect every value of ``key`` anywhere in a nested dict/list (reflective walk)."""
    out: list[Any] = []
    if isinstance(obj, dict):
        if key in obj:
            out.append(obj[key])
        for value in obj.values():
            out.extend(_find(value, key))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_find(item, key))
    return out


def _poam(document: dict[str, Any]) -> dict[str, Any]:
    """Return the POA&M root, or raise if the document is not a POA&M."""
    body = document.get("plan-of-action-and-milestones") if isinstance(document, dict) else None
    if not isinstance(body, dict):
        raise KeyError("missing plan-of-action-and-milestones root")
    return body


def _as_list(value: object) -> list[Any]:
    """Return ``value`` if it is a list, else ``[]`` -- so a malformed scalar is never iterated.

    A field the schema declares as an array (observations, risks, poam-items, methods) may
    arrive as a scalar in hand-malformed input; iterating that directly would raise a bare
    ``TypeError``/``AttributeError`` and break the never-raises contract. Callers flag the
    non-list container separately; this only makes the loop safe.
    """
    return value if isinstance(value, list) else []


def _is_uuid(value: object) -> bool:
    """Return True if ``value`` is a syntactically valid uuid string."""
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return False
    return True


def uuid_syntax(document: dict[str, Any]) -> list[str]:
    """Every uuid is a syntactically valid UUID."""
    return [f"invalid uuid: {value!r}" for value in _find(document, "uuid") if not _is_uuid(value)]


def unique_uuids(document: dict[str, Any]) -> list[str]:
    """Every uuid in the document is unique."""
    counts = Counter(_find(document, "uuid"))
    return [f"duplicate uuid: {value}" for value, n in sorted(counts.items()) if n > 1]


def observation_refs(document: dict[str, Any]) -> list[str]:
    """Every related-observation uuid resolves to a declared observation."""
    poam = _poam(document)
    declared = {o.get("uuid") for o in _as_list(poam.get("observations")) if isinstance(o, dict)}
    used = _find(poam.get("poam-items", []), "observation-uuid")
    return [f"unresolved observation-uuid: {u}" for u in used if u not in declared]


def risk_refs(document: dict[str, Any]) -> list[str]:
    """Every related-risk uuid resolves to a declared risk."""
    poam = _poam(document)
    declared = {r.get("uuid") for r in _as_list(poam.get("risks")) if isinstance(r, dict)}
    used = _find(poam.get("poam-items", []), "risk-uuid")
    return [f"unresolved risk-uuid: {u}" for u in used if u not in declared]


def subject_refs(document: dict[str, Any]) -> list[str]:
    """Every observation subject-uuid resolves to a declared inventory-item."""
    poam = _poam(document)
    ld = poam.get("local-definitions")
    inventory = ld.get("inventory-items", []) if isinstance(ld, dict) else []
    declared = {i.get("uuid") for i in _as_list(inventory) if isinstance(i, dict)}
    used = _find(poam.get("observations", []), "subject-uuid")
    return [f"unresolved subject-uuid: {u}" for u in used if u not in declared]


def props_namespaced(document: dict[str, Any]) -> list[str]:
    """Every props group is an array and every custom prop carries an ns."""
    out: list[str] = []
    for group in _find(document, "props"):
        if not isinstance(group, list):
            out.append(f"props must be an array, got {type(group).__name__}")
            continue
        out += [
            f"prop without ns: {prop.get('name')!r}"
            for prop in group
            if isinstance(prop, dict) and _PROP_NS_KEY not in prop
        ]
    return out


# --- A: OSCAL POA&M structural validators (1:1 with oscal_poam_schema.json) ---------------


def required_fields(document: dict[str, Any]) -> list[str]:
    """Required OSCAL POA&M fields are present."""
    p = _poam(document)
    out: list[str] = []

    def need(obj: object, fields: list[str], where: str) -> None:
        out.extend(
            f"{where} missing required '{f}'"
            for f in fields
            if not isinstance(obj, dict) or f not in obj
        )

    need(p, ["uuid", "metadata", "poam-items"], "poam")
    need(p.get("metadata", {}), ["title", "last-modified", "version", "oscal-version"], "metadata")
    for key in ("observations", "risks", "poam-items"):
        if key in p and not isinstance(p[key], list):
            out.append(f"poam '{key}' must be an array, got {type(p[key]).__name__}")
    for o in _as_list(p.get("observations")):
        need(o, ["uuid", "methods"], "observation")
    for r in _as_list(p.get("risks")):
        need(r, ["uuid", "title", "description", "statement", "status"], "risk")
    for it in _as_list(p.get("poam-items")):
        need(it, ["title", "description"], "poam-item")
    if "system-id" in p:
        need(p["system-id"], ["id"], "system-id")
    return out


def datatypes(document: dict[str, Any]) -> list[str]:
    """Every uuid matches the UUID datatype; last-modified/collected are dateTime-with-timezone."""
    out = [
        f"invalid uuid datatype: {u!r}"
        for u in _find(document, "uuid")
        if isinstance(u, str) and not _UUID_RE.match(u)
    ]
    p = _poam(document)
    metadata = p.get("metadata", {})
    lm = metadata.get("last-modified") if isinstance(metadata, dict) else None
    if isinstance(lm, str) and not _DT_TZ_RE.match(lm):
        out.append(f"last-modified not dateTime-with-timezone: {lm}")
    out += [
        f"collected not dateTime-with-timezone: {c}"
        for c in _find(p.get("observations", []), "collected")
        if isinstance(c, str) and not _DT_TZ_RE.match(c)
    ]
    return out


def risk_status_enum(document: dict[str, Any]) -> list[str]:
    """Every risk.status is an OSCAL risk-status token."""
    return [
        f"invalid risk status: {r.get('status')!r}"
        for r in _as_list(_poam(document).get("risks"))
        if isinstance(r, dict) and r.get("status") not in _RISK_STATUS
    ]


def observation_enums(document: dict[str, Any]) -> list[str]:
    """observation.methods and .types use OSCAL-allowed tokens."""
    out: list[str] = []
    for o in _as_list(_poam(document).get("observations")):
        if not isinstance(o, dict):
            continue
        if not (isinstance(o.get("methods"), list) and o["methods"]):
            out.append(f"observation methods must be a non-empty array: {o.get('methods')!r}")
        out += [
            f"invalid observation method: {m!r}"
            for m in _as_list(o.get("methods"))
            if m not in _OBS_METHODS
        ]
        out += [
            f"invalid observation type: {t!r}"
            for t in _as_list(o.get("types"))
            if t not in _OBS_TYPES
        ]
    return out


# --- B: BreachSAFE domain validator (single-source vocabularies; BreachSAFE ns only) ------


def _bs_props(document: dict[str, Any]) -> Iterator[tuple[Any, Any]]:
    """Yield (name, value) for every prop in the BreachSAFE namespace (ignore foreign ns)."""
    for group in _find(document, "props"):
        if isinstance(group, list):
            for pr in group:
                if isinstance(pr, dict) and pr.get(_PROP_NS_KEY) == BREACHSAFE_NS:
                    yield pr.get("name"), pr.get("value")


def domain_vocabulary(document: dict[str, Any]) -> list[str]:
    """Every BreachSAFE prop value is within its declared vocabulary."""
    severities = set(get_policy().severity.values())
    out: list[str] = []
    for name, val in _bs_props(document):
        v = val or ""
        if name == "readiness" and val not in READINESS_VERDICTS:
            out.append(f"readiness not in vocabulary: {val!r}")
        elif name == "mapping-confidence" and val not in _CONFIDENCE:
            out.append(f"mapping-confidence invalid: {val!r}")
        elif name == "severity" and val not in severities:
            out.append(f"severity invalid: {val!r}")
        elif name == "provenance" and not _PROV_RE.match(v):
            out.append(f"provenance malformed: {val!r}")
        elif name == "nistQuantumSecurityLevel" and not v.isdigit():
            out.append(f"nistQuantumSecurityLevel not a non-neg int: {val!r}")
        elif name == "control-id" and not _CONTROL_RE.match(v):
            out.append(f"control-id malformed: {val!r}")
    return out


_VALIDATORS = (
    uuid_syntax,
    unique_uuids,
    observation_refs,
    risk_refs,
    subject_refs,
    props_namespaced,
    # A -- OSCAL POA&M structural (1:1 with the schema)
    required_fields,
    datatypes,
    risk_status_enum,
    observation_enums,
    # B -- BreachSAFE domain
    domain_vocabulary,
)


def semantic_errors(document: dict[str, Any]) -> list[str]:
    """Return Layer-2 semantic problems in an OSCAL POA&M, empty if sound.

    Each validator's docstring states the invariant it enforces. This is necessary but
    **not** sufficient for NIST schema conformance -- run ``oscal-cli`` for that.

    Never raises: a document that is not a POA&M (no ``plan-of-action-and-milestones``
    root, which the per-validator ``_poam`` helper would otherwise surface as a bare
    ``KeyError``) is reported as a single problem string, so callers always get a list.
    """
    try:
        _poam(document)
    except KeyError as exc:
        return [f"not a POA&M document: {exc.args[0]}"]
    return [problem for check in _VALIDATORS for problem in check(document)]


def oscal_cli_available() -> str | None:
    """Return the path to the NIST ``oscal-cli`` validator if installed, else None."""
    return shutil.which("oscal-cli")
