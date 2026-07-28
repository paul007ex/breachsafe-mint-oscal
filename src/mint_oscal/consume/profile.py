# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Consume an OSCAL profile: read its operational-defined parameters (ODPs).

A profile's ``set-parameters`` bind the tailorable values (organization-defined
parameters) a control baseline leaves open. Emitters that need those bindings read
them here rather than hard-coding program-specific values.
"""

from __future__ import annotations

from typing import Any


def set_parameters(profile: dict[str, Any]) -> dict[str, str]:
    """Return the ODP bindings (``param-id`` -> value) declared by a profile.

    Not yet implemented. Part of the profile-consume path (P1). See ADR-0004 and
    UC-TAILOR.

    Raises:
        NotImplementedError: always, until profile consumption lands.
    """
    raise NotImplementedError(
        "profile.set_parameters: reading OSCAL profile set-parameters (ODPs) is "
        "not implemented yet (ADR-0004, UC-TAILOR, P1)"
    )
