# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Semantic (Layer-2) validation of an emitted OSCAL document.

Layer 1 -- authoritative *schema/shape* conformance -- is delegated to the NIST
``oscal-cli`` oracle (see :func:`oscal_cli_available` and ADR-0005). This module adds the
cross-cutting invariants a JSON schema cannot express: uuid syntax + uniqueness, internal
reference resolution (observation / risk / subject), and prop namespacing. Running these
in-process is necessary but **not** sufficient for NIST conformance -- so callers must not
report it as such. The small Validator-registry design is borrowed from IBM
``compliance-trestle`` (pattern only, no dependency; ADR-0005).
"""

from __future__ import annotations

import shutil
import uuid
from collections import Counter
from typing import Any

_PROP_NS_KEY = "ns"


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
    body = document.get("plan-of-action-and-milestones")
    if not isinstance(body, dict):
        raise KeyError("missing plan-of-action-and-milestones root")
    return body


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
    declared = {o.get("uuid") for o in poam.get("observations", [])}
    used = _find(poam.get("poam-items", []), "observation-uuid")
    return [f"unresolved observation-uuid: {u}" for u in used if u not in declared]


def risk_refs(document: dict[str, Any]) -> list[str]:
    """Every related-risk uuid resolves to a declared risk."""
    poam = _poam(document)
    declared = {r.get("uuid") for r in poam.get("risks", [])}
    used = _find(poam.get("poam-items", []), "risk-uuid")
    return [f"unresolved risk-uuid: {u}" for u in used if u not in declared]


def subject_refs(document: dict[str, Any]) -> list[str]:
    """Every observation subject-uuid resolves to a declared inventory-item."""
    poam = _poam(document)
    inventory = poam.get("local-definitions", {}).get("inventory-items", [])
    declared = {i.get("uuid") for i in inventory}
    used = _find(poam.get("observations", []), "subject-uuid")
    return [f"unresolved subject-uuid: {u}" for u in used if u not in declared]


def props_namespaced(document: dict[str, Any]) -> list[str]:
    """Every custom prop carries an ns."""
    return [
        f"prop without ns: {prop.get('name')!r}"
        for group in _find(document, "props")
        if isinstance(group, list)
        for prop in group
        if isinstance(prop, dict) and _PROP_NS_KEY not in prop
    ]


_VALIDATORS = (
    uuid_syntax,
    unique_uuids,
    observation_refs,
    risk_refs,
    subject_refs,
    props_namespaced,
)


def semantic_errors(document: dict[str, Any]) -> list[str]:
    """Return Layer-2 semantic problems in an OSCAL POA&M, empty if sound.

    Each validator's docstring states the invariant it enforces. This is necessary but
    **not** sufficient for NIST schema conformance -- run ``oscal-cli`` for that.
    """
    return [problem for check in _VALIDATORS for problem in check(document)]


def oscal_cli_available() -> str | None:
    """Return the path to the NIST ``oscal-cli`` validator if installed, else None."""
    return shutil.which("oscal-cli")
