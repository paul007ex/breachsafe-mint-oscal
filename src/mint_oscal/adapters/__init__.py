# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Adapter discovery: source name -> callable building IR from a source document.

Adapters are discovered through the ``mint_oscal.adapters`` entry-point group, so
a third party ships an adapter as its own distribution without editing this
package (ADR-0004: agnostic core, ports & adapters). ``qureddy`` is bundled here
as an optional convenience and is always available even from a source checkout.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any, cast

from mint_oscal.ir import Finding, Subject

Adapter = Callable[[dict[str, Any]], tuple[list[Finding], Subject]]

_ENTRY_POINT_GROUP = "mint_oscal.adapters"
_BUILTIN = "qureddy"


def get_adapter(name: str) -> Adapter:
    """Return the adapter registered under ``name``.

    Entry-point adapters win; the bundled ``qureddy`` adapter is the fallback so it
    resolves even before the package is installed.

    Raises:
        KeyError: if no adapter is registered under ``name``.
    """
    for entry_point in entry_points(group=_ENTRY_POINT_GROUP):
        if entry_point.name == name:
            return cast("Adapter", entry_point.load())
    if name == _BUILTIN:
        from mint_oscal.adapters.qureddy import from_scan_v1

        return from_scan_v1
    raise KeyError(f"unknown source adapter {name!r}; available: {', '.join(available_adapters())}")


def available_adapters() -> list[str]:
    """Return the sorted names of all discoverable source adapters."""
    names = {entry_point.name for entry_point in entry_points(group=_ENTRY_POINT_GROUP)}
    names.add(_BUILTIN)
    return sorted(names)


__all__ = ["Adapter", "available_adapters", "get_adapter"]
