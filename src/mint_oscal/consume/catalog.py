# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Consume an OSCAL catalog: read control text keyed by control id.

Component definitions and human-readable POA&M annotations need the prose of a
control (its statement/guidance). That text lives in an OSCAL catalog and is read
here so emitters never transcribe control language by hand.
"""

from __future__ import annotations

from typing import Any


def control_text(catalog: dict[str, Any], control_id: str) -> str:
    """Return the prose statement for ``control_id`` from an OSCAL catalog.

    Not yet implemented. Part of the catalog-consume path (P2). See ADR-0004 and
    UC-COMPONENT.

    Raises:
        NotImplementedError: always, until catalog consumption lands.
    """
    raise NotImplementedError(
        "catalog.control_text: reading OSCAL catalog control prose is not "
        "implemented yet (ADR-0004, UC-COMPONENT, P2)"
    )
