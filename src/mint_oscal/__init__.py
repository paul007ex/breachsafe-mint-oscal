# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""breachsafe-mint-oscal: mint OSCAL documents from a source-neutral IR.

Public API::

    from mint_oscal import convert
    from mint_oscal.adapters import get_adapter

    ir = build_ir(...)                       # an adapter builds the IR
    poam = convert(ir, shape="poam", source="QuReddy")

``convert`` is the agnostic core (ADR-0004): adapters normalize any source into the
IR, emitters turn the IR into any OSCAL model, and neither knows the other.
"""

from __future__ import annotations

from typing import Any

from mint_oscal.emitters import get_emitter
from mint_oscal.ir import IR, Evidence, Finding, Risk, Subject

__version__ = "0.0.1"

__all__ = [
    "IR",
    "Evidence",
    "Finding",
    "Risk",
    "Subject",
    "__version__",
    "convert",
]


def convert(ir: IR, *, shape: str, **params: Any) -> dict[str, Any]:  # noqa: ANN401
    """Convert a neutral :class:`IR` into an OSCAL document of the given ``shape``.

    ``shape`` is an OSCAL model name registered in ``mint_oscal.emitters``
    (``poam``, ``ar``, ``component-definition``). Extra keyword ``params`` are
    forwarded to the selected emitter.

    Raises:
        KeyError: if ``shape`` is not a registered OSCAL model.
        NotImplementedError: if the selected emitter is still a stub.
    """
    return get_emitter(shape)(ir, **params)
