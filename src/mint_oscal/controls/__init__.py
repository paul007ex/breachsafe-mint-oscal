# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Control mappings: from a source's finding vocabulary to NIST controls.

These are per-source, auditable, swappable tables (never emitter-invented). See
``nist`` for the SP 800-53 mapping; the reviewable readiness->control data lives in
the versioned policy pack (:mod:`mint_oscal.policy`, ``default`` pack).
"""

from __future__ import annotations

from mint_oscal.controls.nist import controls_for, risk_statement

__all__ = ["controls_for", "risk_statement"]
