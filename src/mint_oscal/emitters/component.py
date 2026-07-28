# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Emitter (stub): IR findings -> an OSCAL Component Definition document.

A component-definition describes the assessed components and the controls they
satisfy, independent of any one assessment. Authoring it needs control-text from
a consumed catalog/profile (``mint_oscal.consume``), which is a P2 item.
"""

from __future__ import annotations

from typing import Any

from mint_oscal.ir import IR


def emit(ir: IR, **params: Any) -> dict[str, Any]:  # noqa: ANN401
    """Emit an OSCAL Component Definition document from an IR bundle.

    Not yet implemented. Depends on the catalog/profile consume path to resolve
    control text and implemented-requirements. See ADR-0004 and the P2 tier
    (UC-3).

    Raises:
        NotImplementedError: always, until the component emitter lands.
    """
    raise NotImplementedError(
        "component.emit: Component Definition emitter depends on catalog/profile "
        "consume (ADR-0004, UC-3, P2)"
    )
