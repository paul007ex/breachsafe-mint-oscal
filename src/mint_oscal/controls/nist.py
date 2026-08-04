# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Map a cryptographic-posture readiness verdict to control ids under the ACTIVE framework.

Framework-neutral despite the module name (kept for import stability; a rename to
``controls/crosswalk.py`` is a follow-up). The verdict->control, ->severity, and ->risk
tables are *policy*, not mechanism, so they live in the versioned policy pack for the
selected framework (:mod:`mint_oscal.policy`; ``scf-qts`` by default, ``nist`` opt-in) as
reviewable YAML rather than hardcoded here. Select the frame with ``--framework`` /
:func:`mint_oscal.policy.set_active_framework`.
"""

from __future__ import annotations

from mint_oscal.policy import active_policy


def controls_for(readiness: str) -> tuple[str, ...]:
    """Return the control ids a readiness verdict implicates under the active framework.

    An unrecognized verdict implicates NO control rather than defaulting to a catch-all: a
    verdict the pack does not map must not silently fabricate an authoritative control (that
    coerced ``not_applicable`` into SC-13 before #86).
    """
    return tuple(active_policy().crosswalk.get(readiness, ()))


def risk_statement(readiness: str) -> str:
    """Return a plain-language risk statement for a readiness verdict (active framework)."""
    return active_policy().risk.get(readiness, f"Cryptographic posture: {readiness}.")
