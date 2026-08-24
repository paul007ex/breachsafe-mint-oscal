# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Shared OSCAL building blocks used by more than one emitter.

Metadata and property constructs recur across every OSCAL model
(POA&M, Assessment Results, Component Definition). Centralizing them here keeps
those shapes identical across emitters and gives one place to adjust when the
target ``oscal-version`` moves.
"""

from __future__ import annotations

from itertools import starmap
from typing import Any

OSCAL_VERSION = "1.2.2"

# Custom (non-core) props MUST carry this namespace. OSCAL constrains prop names in
# the default core namespace (http://csrc.nist.gov/ns/oscal) to an allowed set, so an
# unnamespaced custom prop like "severity" fails oscal-cli validation. Everything mint
# emits that is not a core OSCAL prop rides in this namespace.
BREACHSAFE_NS = "https://breachsafe.ai/ns/oscal"


def prop(name: str, value: str, *, ns: str | None = BREACHSAFE_NS) -> dict[str, Any]:
    """Build one OSCAL ``prop`` object.

    Defaults to the BreachSAFE namespace; pass ``ns=None`` only for a genuine core
    OSCAL prop whose name is in the allowed core set.
    """
    out: dict[str, Any] = {"name": name, "value": value}
    if ns is not None:
        out["ns"] = ns
    return out


def props_from(mapping: dict[str, str]) -> list[dict[str, Any]]:
    """Build a list of custom (BreachSAFE-namespaced) OSCAL ``prop`` objects."""
    return list(starmap(prop, mapping.items()))


def metadata(
    title: str,
    *,
    timestamp: str,
    version: str = "0.1.0",
    oscal_version: str = OSCAL_VERSION,
) -> dict[str, Any]:
    """Build an OSCAL ``metadata`` block."""
    return {
        "title": title,
        "last-modified": timestamp,
        "version": version,
        "oscal-version": oscal_version,
    }
