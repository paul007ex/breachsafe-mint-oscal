# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Shared OSCAL building blocks used by more than one emitter.

Metadata, party, and property constructs recur across every OSCAL model
(POA&M, Assessment Results, Component Definition). Centralizing them here keeps
those shapes identical across emitters and gives one place to adjust when the
target ``oscal-version`` moves.
"""

from __future__ import annotations

from typing import Any

OSCAL_VERSION = "1.1.2"


def prop(name: str, value: str, *, ns: str | None = None) -> dict[str, Any]:
    """Build one OSCAL ``prop`` object."""
    out: dict[str, Any] = {"name": name, "value": value}
    if ns is not None:
        out["ns"] = ns
    return out


def props_from(mapping: dict[str, str]) -> list[dict[str, Any]]:
    """Build a list of OSCAL ``prop`` objects from a name->value mapping."""
    return [prop(name, value) for name, value in mapping.items()]


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


def party(uuid: str, name: str, *, party_type: str = "organization") -> dict[str, Any]:
    """Build an OSCAL ``party`` object (for metadata ``parties``)."""
    return {"uuid": uuid, "type": party_type, "name": name}
