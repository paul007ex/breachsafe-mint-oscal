# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Semantic (Layer-2) validation of an emitted OSCAL document.

Layer 1 -- authoritative *schema/shape* conformance -- is delegated to the NIST
``oscal-cli`` oracle (see :func:`oscal_cli_available` and ADR-0005). This module adds the
cross-cutting invariants a JSON schema cannot express, plus a native, in-process
re-derivation of the OSCAL POA&M rules that matter most (required fields, the UUID and
dateTime-with-timezone datatypes, and the *shape* of the open risk-status / observation
vocabularies) grounded in ``oscal_poam_schema.json``, and the BreachSAFE-namespace domain
vocabularies. The open ``anyOf[token/string, enum]`` vocabularies are validated by token/
string shape, not closed enum membership, so a conformant out-of-enum value is not
false-rejected. Running these in-process is necessary but **not** sufficient for NIST
conformance -- so callers must not report it as such. The small Validator-registry design is
borrowed from IBM ``compliance-trestle`` (pattern only, no dependency; ADR-0005).

Deliberate non-goal: exhaustive ``additionalProperties: false`` / unknown-field detection.
A hardcoded per-object allow-list would be version-brittle -- a field valid in a newer OSCAL
minor would be false-rejected, which violates the honest-failure principle (better to miss an
unknown field than to reject a conformant document). Unknown-field conformance is Layer 1,
owned by ``oscal-cli`` (differential-tested vs trestle, #73). What this module *does* add over
trestle's structural parse: timezone-required datetimes, cross-reference resolution, global
uuid uniqueness, and the BreachSAFE domain layer.
"""

from __future__ import annotations

import re
import shutil
import uuid
from collections import Counter
from collections.abc import Iterator
from typing import Any

from mint_oscal.emitters._common import BREACHSAFE_NS
from mint_oscal.policy import READINESS_VERDICTS

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

# --- Open-vocabulary shape checks --------------------------------------------------------
# risk-status, observation.methods and observation.types are OPEN vocabularies in the schema
# (anyOf[TokenDatatype|StringDatatype, enum]): any well-formed token/string is schema-legal and
# the listed enum is a *suggested*, not closed, set. We validate the value's SHAPE -- rejecting
# empty/whitespace/non-token junk -- instead of closing the set, which would false-reject
# conformant documents that oscal-cli accepts. These are Python-re-safe approximations of the
# metaschema patterns (which use \p{} classes `re` cannot compile).
_TOKEN_RE = re.compile(r"^[^\W\d][\w.\-]*$")  # NCName-ish: starts with a letter/_, no colon/space
_STRING_RE = re.compile(r"^\S(.*\S)?$")  # non-empty, no leading/trailing whitespace
# POA&M fields typed DateTimeWithTimezoneDatatype; validated wherever they appear. (The generic
# `date` field -- only under the rare metadata `action` -- is omitted to avoid false-reds on
# unrelated `date` keys.)
_DATETIME_TZ_FIELDS = ("last-modified", "published", "collected", "expires", "deadline")
# BreachSAFE severity vocabulary: the IR ``finding.severity`` enum (mint.ir.v1.schema.json),
# which is what the emitter writes into the ``severity`` prop. NOT ``policy.severity.values()``
# -- that is the readiness->severity lookup table, whose value set is only a subset (info/low/
# medium) and would false-reject a legitimate ``high``/``critical`` finding severity.
_SEVERITY = frozenset({"critical", "high", "medium", "low", "info"})
# BreachSAFE mapping-confidence vocabulary.
_CONFIDENCE = frozenset({"high", "partial", "not-applicable"})
# BreachSAFE provenance grammar (see extensions.breachsafe).
_PROV_RE = re.compile(r"^(derived|producer-confirmed|conflict:producer=.+,derived=.+)$")
# Control identifier shape, framework-agnostic: NIST ``SC-13`` and SCF ``qts-04.3`` alike
# (2-5 letters, a number, optional dotted sub-parts). Control ids belong to the framework
# authority, not BreachSAFE (#88), so control-id is no longer a BreachSAFE-namespaced prop.
_CONTROL_RE = re.compile(r"^[A-Za-z]{2,5}-\d+(?:\.\d+)*$")
# BreachSAFE custom prop names -- these carry our domain vocabulary and must live in the
# BreachSAFE ns, never the core OSCAL namespace (`ns` itself is optional in OSCAL).
_BREACHSAFE_PROP_NAMES = frozenset(
    {
        "readiness",
        "mapping-confidence",
        "severity",
        "provenance",
        "framework",
        "interpretation-status",
        "nistQuantumSecurityLevel",
    }
)


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


def _is_token(value: object) -> bool:
    """Return True if ``value`` is a well-formed OSCAL TokenDatatype (NCName-ish string)."""
    return isinstance(value, str) and _TOKEN_RE.match(value) is not None


def _is_string(value: object) -> bool:
    """Return True if ``value`` is a well-formed OSCAL StringDatatype (non-empty, no edge space)."""
    return isinstance(value, str) and _STRING_RE.match(value) is not None


def uuid_syntax(document: dict[str, Any]) -> list[str]:
    """Every uuid is a syntactically valid UUID."""
    return [f"invalid uuid: {value!r}" for value in _find(document, "uuid") if not _is_uuid(value)]


def unique_uuids(document: dict[str, Any]) -> list[str]:
    """Every uuid in the document is unique."""
    # Only count string uuids -- a malformed (unhashable) uuid value would blow up ``Counter``
    # and is already reported by :func:`uuid_syntax`.
    counts = Counter(u for u in _find(document, "uuid") if isinstance(u, str))
    return [f"duplicate uuid: {value}" for value, n in sorted(counts.items()) if n > 1]


def _string_ids(items: list[Any], key: str) -> set[str]:
    """Collect the string ``key`` values from a list of dicts.

    Skips missing and non-string ids so an unhashable value (list/dict) can never blow up the
    set build -- a non-string id cannot be a resolvable OSCAL uuid anyway.
    """
    out: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
            if isinstance(value, str):
                out.add(value)
    return out


def _unresolved(used: list[Any], declared: set[str], label: str) -> list[str]:
    """Flag every used ref that is not a declared string id (a non-string ref never resolves)."""
    return [
        f"unresolved {label}: {ref}"
        for ref in used
        if not (isinstance(ref, str) and ref in declared)
    ]


def _imports_ssp(poam: dict[str, Any]) -> bool:
    """True if the POA&M imports an external SSP (``import-ssp``), which mint cannot resolve.

    An ``import-ssp`` pulls in a System Security Plan (and, transitively, its assessment
    context) that lives *outside* the POA&M document. Cross-references such as a risk-uuid or a
    subject-uuid may legitimately resolve into that imported context rather than into the
    POA&M's own ``risks``/``local-definitions`` -- and mint cannot follow the ``href`` to check.
    Per the honest-failure principle (#74), mint must therefore NOT assert those refs are
    *dangling* when an SSP is imported: doing so false-reds the canonical NIST POA&M, which the
    trestle/oscal-cli oracles accept. A self-contained POA&M (no ``import-ssp``) is still fully
    cross-checked, so a genuinely dangling ref is caught.
    """
    return isinstance(poam.get("import-ssp"), dict)


def observation_refs(document: dict[str, Any]) -> list[str]:
    """Every related-observation uuid resolves to a declared observation."""
    poam = _poam(document)
    declared = _string_ids(_as_list(poam.get("observations")), "uuid")
    used = _find(poam.get("poam-items", []), "observation-uuid")
    return _unresolved(used, declared, "observation-uuid")


def risk_refs(document: dict[str, Any]) -> list[str]:
    """Every related-risk uuid resolves to a declared risk (self-contained POA&M only).

    A poam-item's ``related-risk`` may reference a risk declared in an imported SSP's assessment
    context, not the POA&M's own ``risks`` list; mint cannot follow ``import-ssp``, so when one
    is present it does not assert the ref is dangling (#74). Without ``import-ssp`` the risk
    universe is fully local, so a genuinely dangling risk-uuid is still caught.
    """
    poam = _poam(document)
    if _imports_ssp(poam):
        return []
    declared = _string_ids(_as_list(poam.get("risks")), "uuid")
    used = _find(poam.get("poam-items", []), "risk-uuid")
    return _unresolved(used, declared, "risk-uuid")


def subject_refs(document: dict[str, Any]) -> list[str]:
    """Every locally-resolvable observation subject resolves to a declared inventory-item.

    A subject resolves *locally* only when (a) the POA&M is self-contained (no ``import-ssp``,
    which mint cannot follow) AND (b) its ``type`` is ``inventory-item`` (the sole subject kind
    declared in ``local-definitions.inventory-items``). Subjects of any other type -- component,
    party, location, user -- are declared in the imported SSP or a component-definition mint
    cannot see, and when an SSP is imported even an inventory-item subject may live there. In
    both cases mint must not assert the ref is dangling, or it false-reds the canonical NIST
    POA&M (#74). A dangling inventory-item subject in a self-contained POA&M is still caught.
    """
    poam = _poam(document)
    if _imports_ssp(poam):
        return []
    ld = poam.get("local-definitions")
    inventory = ld.get("inventory-items", []) if isinstance(ld, dict) else []
    declared = _string_ids(_as_list(inventory), "uuid")
    used = [
        subject.get("subject-uuid")
        for observation in _as_list(poam.get("observations"))
        if isinstance(observation, dict)
        for subject in _as_list(observation.get("subjects"))
        if isinstance(subject, dict) and subject.get("type") == "inventory-item"
    ]
    return _unresolved(used, declared, "subject-uuid")


def props_namespaced(document: dict[str, Any]) -> list[str]:
    """Props groups are arrays; BreachSAFE custom props live in the BreachSAFE namespace.

    OSCAL's ``ns`` is optional -- an absent ``ns`` means the core OSCAL namespace, which is
    valid -- so a standard ns-less prop (e.g. ``marking``) is NOT flagged. Only a prop that
    reuses a BreachSAFE-reserved name outside the BreachSAFE namespace is a problem: that would
    smuggle our domain vocabulary into the core namespace.
    """
    out: list[str] = []
    for group in _find(document, "props"):
        if not isinstance(group, list):
            out.append(f"props must be an array, got {type(group).__name__}")
            continue
        out += [
            f"BreachSAFE prop {prop.get('name')!r} not in the BreachSAFE namespace"
            for prop in group
            if isinstance(prop, dict)
            and isinstance(prop.get("name"), str)
            and prop.get("name") in _BREACHSAFE_PROP_NAMES
            and prop.get(_PROP_NS_KEY) != BREACHSAFE_NS
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


def cardinality(document: dict[str, Any]) -> list[str]:
    """OSCAL arrays that require >=1 item are non-empty (schema ``minItems: 1``).

    ``required_fields`` only checks *presence*; an empty ``poam-items: []`` (required, minItems 1)
    or an empty ``observations``/``risks`` (minItems 1 when present) would otherwise pass. The
    #64 emitter fix stops *mint* producing these, but the ``validate`` verb runs on external
    documents that can. (Differential-tested vs trestle, #73.)
    """
    p = _poam(document)
    out: list[str] = []
    if isinstance(p.get("poam-items"), list) and not p["poam-items"]:
        out.append("poam-items must have at least one item (minItems 1)")
    for key in ("observations", "risks"):
        if isinstance(p.get(key), list) and not p[key]:
            out.append(f"{key} must have at least one item when present (minItems 1)")
    return out


def datatypes(document: dict[str, Any]) -> list[str]:
    """Every uuid matches the UUID datatype; every dateTime-with-timezone field is tz-aware/real."""
    out = [
        f"invalid uuid datatype: {u!r}"
        for u in _find(document, "uuid")
        if isinstance(u, str) and not _UUID_RE.match(u)
    ]
    for field in _DATETIME_TZ_FIELDS:
        out += [
            f"{field} not dateTime-with-timezone: {v}"
            for v in _find(document, field)
            if isinstance(v, str) and not _DT_TZ_RE.match(v)
        ]
    return out


def risk_status(document: dict[str, Any]) -> list[str]:
    """Every risk.status is a well-formed token (risk-status is an OPEN anyOf vocabulary)."""
    return [
        f"risk status not a valid token: {r.get('status')!r}"
        for r in _as_list(_poam(document).get("risks"))
        if isinstance(r, dict) and not _is_token(r.get("status"))
    ]


def observation_enums(document: dict[str, Any]) -> list[str]:
    """observation.methods (StringDatatype) and .types (TokenDatatype) are OPEN anyOf vocabularies.

    Any well-formed string/token is schema-legal (the OSCAL enum is a suggestion, not a closed
    set), so we validate shape, not enum membership -- closing them would reject documents
    oscal-cli accepts. The non-string guard also keeps a malformed value from crashing.
    """
    out: list[str] = []
    for o in _as_list(_poam(document).get("observations")):
        if not isinstance(o, dict):
            continue
        if not (isinstance(o.get("methods"), list) and o["methods"]):
            out.append(f"observation methods must be a non-empty array: {o.get('methods')!r}")
        out += [
            f"observation method not a valid string: {m!r}"
            for m in _as_list(o.get("methods"))
            if not _is_string(m)
        ]
        out += [
            f"observation type not a valid token: {t!r}"
            for t in _as_list(o.get("types"))
            if not _is_token(t)
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
    out: list[str] = []
    for name, val in _bs_props(document):
        # A non-string value (incl. an unhashable list/dict) fails every check below and is
        # reported, never crashes a set-membership test or a regex match.
        s = val if isinstance(val, str) else None
        if name == "readiness" and not (s is not None and s in READINESS_VERDICTS):
            out.append(f"readiness not in vocabulary: {val!r}")
        elif name == "mapping-confidence" and not (s is not None and s in _CONFIDENCE):
            out.append(f"mapping-confidence invalid: {val!r}")
        elif name == "severity" and not (s is not None and s in _SEVERITY):
            out.append(f"severity invalid: {val!r}")
        elif name == "provenance" and not (s is not None and _PROV_RE.match(s)):
            out.append(f"provenance malformed: {val!r}")
        elif name == "nistQuantumSecurityLevel" and not (s is not None and s.isdigit()):
            out.append(f"nistQuantumSecurityLevel not a non-neg int: {val!r}")
    return out


def control_id_shape(document: dict[str, Any]) -> list[str]:
    """Every control-id prop value is a well-formed control identifier (any namespace).

    control-id belongs to the framework authority, so #88/#91 moved it out of the BreachSAFE
    namespace into the authority ns (SCF/NIST). That left the shape check dead: it only ran over
    BreachSAFE-namespaced props, a namespace the emitter never writes control-id into, so a
    malformed control-id went unvalidated (#94). Validate it wherever it now lives -- walking all
    props, not only BreachSAFE ones -- so the framework-agnostic ``_CONTROL_RE`` is live again.
    """
    out: list[str] = []
    for group in _find(document, "props"):
        if isinstance(group, list):
            for pr in group:
                if isinstance(pr, dict) and pr.get("name") == "control-id":
                    v = pr.get("value")
                    if not (isinstance(v, str) and _CONTROL_RE.match(v)):
                        out.append(f"control-id malformed: {v!r}")
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
    cardinality,
    datatypes,
    risk_status,
    observation_enums,
    # B -- BreachSAFE domain
    domain_vocabulary,
    control_id_shape,
)


def semantic_errors(document: dict[str, Any]) -> list[str]:
    """Return Layer-2 semantic problems in an OSCAL POA&M, empty if sound.

    Each validator's docstring states the invariant it enforces. This is necessary but
    **not** sufficient for NIST schema conformance -- run ``oscal-cli`` for that.

    Never raises. This is enforced at the boundary, not just per validator: a non-POA&M
    document is reported as one problem string, and each validator runs under a fail-closed
    guard so that any escaping exception on hostile input degrades to a problem string rather
    than propagating. The individual validators guard their own inputs too (defense in depth);
    this guarantee holds even if a future validator misses a guard.
    """
    try:
        _poam(document)
    except KeyError as exc:
        return [f"not a POA&M document: {exc.args[0]}"]
    problems: list[str] = []
    for check in _VALIDATORS:
        try:
            problems.extend(check(document))
        except Exception as exc:  # noqa: BLE001 -- deliberate fail-closed boundary (see below)
            # A validator fault on hostile input is a reported problem, not a propagated crash:
            # this is what makes the never-raises contract hold even if an inner guard is ever
            # missed. The blind catch is intentional and scoped to one validator call.
            problems.append(f"validator {check.__name__} failed on malformed input: {exc}")
    return problems


def oscal_cli_available() -> str | None:
    """Return the path to the NIST ``oscal-cli`` validator if installed, else None."""
    return shutil.which("oscal-cli")
