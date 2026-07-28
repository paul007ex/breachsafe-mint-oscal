# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Structural validation of an emitted OSCAL document.

This checks internal integrity (valid uuids, no dangling cross-references) without
a network or the NIST toolchain. It is NOT a substitute for full OSCAL schema
conformance: run the NIST ``oscal-cli`` validator (see ``oscal_cli_available``) for
that. Structural validity is necessary but not sufficient.
"""

from __future__ import annotations

import shutil
import uuid
from typing import Any


def structural_errors(poam: dict[str, Any]) -> list[str]:
    """Return internal-integrity problems in an OSCAL POA&M, empty if sound."""
    root = poam.get("plan-of-action-and-milestones")
    if root is None:
        return ["missing plan-of-action-and-milestones root"]

    problems: list[str] = []
    observation_uuids = {o["uuid"] for o in root.get("observations", [])}
    risk_uuids = {r["uuid"] for r in root.get("risks", [])}

    for collection in ("observations", "risks", "poam-items"):
        for entry in root.get(collection, []):
            if not _is_uuid(entry.get("uuid", "")):
                problems.append(f"{collection}: invalid or missing uuid {entry.get('uuid')!r}")

    for item in root.get("poam-items", []):
        for ref in item.get("related-observations", []):
            if ref.get("observation-uuid") not in observation_uuids:
                problems.append(f"poam-item {item.get('uuid')}: dangling observation ref")
        for ref in item.get("related-risks", []):
            if ref.get("risk-uuid") not in risk_uuids:
                problems.append(f"poam-item {item.get('uuid')}: dangling risk ref")
    return problems


def _is_uuid(value: str) -> bool:
    """Return True if ``value`` is a syntactically valid uuid string."""
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def oscal_cli_available() -> str | None:
    """Return the path to the NIST ``oscal-cli`` validator if installed, else None."""
    return shutil.which("oscal-cli")
