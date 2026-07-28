# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Emitter (stub): IR findings -> an OSCAL Assessment Results (AR) document.

The AR metaschema REQUIRES an ``import-ap`` (a reference to the Assessment Plan
this result answers to). That reference is a program input, not a scanner output,
so wiring it is deferred until the profile/plan consume path (P1) lands.
"""

from __future__ import annotations

from typing import Any

from mint_oscal.ir import IR


def emit(ir: IR, **params: Any) -> dict[str, Any]:  # noqa: ANN401
    """Emit an OSCAL Assessment Results document from an IR bundle.

    Not yet implemented. AR requires a REQUIRED ``import-ap`` per the OSCAL AR
    metaschema; that assessment-plan reference is a program input. See ADR-0004
    and the P1 tier (UC-2).

    Raises:
        NotImplementedError: always, until the AR emitter lands.
    """
    raise NotImplementedError(
        "ar.emit: Assessment Results emitter needs a REQUIRED import-ap "
        "(program input) before it can be authored (ADR-0004, UC-2, P1)"
    )
