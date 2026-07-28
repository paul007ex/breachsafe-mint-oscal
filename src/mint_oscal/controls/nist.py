# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Map a cryptographic-posture finding to NIST SP 800-53 controls.

REVIEW REQUIRED: these mappings are a defensible starting point, not an authored
compliance decision. SC-13 (Cryptographic Protection) is the anchor; SC-8
(Transmission Confidentiality/Integrity) and SC-12 (Cryptographic Key
Establishment/Management) apply when key establishment is classical. A program
targeting CNSA 2.0 or NIST SP 1800-38 (PQC migration) may prefer a different or
additional control frame; keep this table auditable and swappable per program.
"""

from __future__ import annotations

_CRYPTO_PROTECTION = "SC-13"
_TRANSMISSION_CONFIDENTIALITY = "SC-8"
_KEY_ESTABLISHMENT = "SC-12"

_CLASSICAL_READINESS = frozenset({"quantum_vulnerable", "classically_weak"})

_RISK_STATEMENTS = {
    "quantum_vulnerable": (
        "Classical key establishment exposes captured traffic to "
        "harvest-now-decrypt-later once a cryptographically relevant quantum "
        "computer exists."
    ),
    "classically_weak": "A weak or deprecated cryptographic primitive is offered.",
    "transitional_hybrid": (
        "PQ-hybrid key exchange is negotiated; residual classical elements remain "
        "(for example a classical certificate signature)."
    ),
}


def controls_for(readiness: str) -> tuple[str, ...]:
    """Return the NIST 800-53 control ids a readiness verdict implicates."""
    if readiness in _CLASSICAL_READINESS:
        return (_CRYPTO_PROTECTION, _TRANSMISSION_CONFIDENTIALITY, _KEY_ESTABLISHMENT)
    return (_CRYPTO_PROTECTION,)


def risk_statement(readiness: str) -> str:
    """Return a plain-language risk statement for a readiness verdict."""
    return _RISK_STATEMENTS.get(readiness, f"Cryptographic posture: {readiness}.")
