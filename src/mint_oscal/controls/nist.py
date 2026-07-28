# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Map a cryptographic-posture finding to NIST SP 800-53 controls.

REVIEW REQUIRED: these mappings are a defensible starting point, not an authored
compliance decision, and await conformance sign-off (see the crosswalk-authoring
reference in the breachsafe-oscal-conformance skill). SC-13 (Cryptographic
Protection) is the anchor; SC-12 (Cryptographic Key Establishment/Management) is
supporting when key establishment is classical. SC-8 (Transmission
Confidentiality/Integrity) is intentionally EXCLUDED as overreach: the finding is
about the cryptographic primitive's quantum readiness, not transmission integrity.

The verdict->control, ->severity, and ->risk tables are *policy*, not mechanism, so
they live in the versioned policy pack (:mod:`mint_oscal.policy`, ``default`` pack)
as reviewable YAML rather than hardcoded here. A program targeting CNSA 2.0 or NIST
SP 1800-38 (PQC migration) may prefer a different frame: copy the pack and swap the
table per program.
"""

from __future__ import annotations

from mint_oscal.policy import get_policy


def controls_for(readiness: str) -> tuple[str, ...]:
    """Return the NIST 800-53 control ids a readiness verdict implicates."""
    return tuple(get_policy().crosswalk.get(readiness, ["SC-13"]))


def risk_statement(readiness: str) -> str:
    """Return a plain-language risk statement for a readiness verdict."""
    return get_policy().risk.get(readiness, f"Cryptographic posture: {readiness}.")
