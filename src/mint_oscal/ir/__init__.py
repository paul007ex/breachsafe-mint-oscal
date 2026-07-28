# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Source-neutral intermediate representation (IR) for mint-oscal.

Re-exports the IR dataclasses so callers can ``from mint_oscal.ir import Finding``.
"""

from __future__ import annotations

from mint_oscal.ir.model import IR, Evidence, Finding, Subject

__all__ = ["IR", "Evidence", "Finding", "Subject"]
