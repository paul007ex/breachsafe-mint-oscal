# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Adapter discovery: source name -> callable building IR from a source document.

Adapters are discovered through the ``mint_oscal.adapters`` entry-point group, so
a third party ships an adapter as its own distribution without editing this
package (ADR-0004: agnostic core, ports & adapters). ``qureddy`` (native scan JSON)
and ``cbom`` (generic CycloneDX CBOM, ADR-0006) are bundled here as a convenience
and are always available even from a source checkout.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any, cast

from mint_oscal.ir import Finding, Subject

Adapter = Callable[[dict[str, Any]], tuple[list[Finding], Subject]]

_ENTRY_POINT_GROUP = "mint_oscal.adapters"
# Bundled fallbacks: name -> "module:callable". Entry-point adapters still win.
_BUILTINS = {
    "qureddy": "mint_oscal.adapters.qureddy:from_scan_v1",
    "cbom": "mint_oscal.adapters.cbom:from_cbom",
}


def _load_builtin(target: str) -> Adapter:
    """Import a bundled adapter from its ``module:callable`` reference."""
    module_name, _, attr = target.partition(":")
    module = __import__(module_name, fromlist=[attr])
    return cast("Adapter", getattr(module, attr))


def get_adapter(name: str) -> Adapter:
    """Return the adapter registered under ``name``.

    Entry-point adapters win; the bundled ``qureddy``/``cbom`` adapters are the
    fallback so they resolve even before the package is installed.

    Raises:
        KeyError: if no adapter is registered under ``name``.
    """
    for entry_point in entry_points(group=_ENTRY_POINT_GROUP):
        if entry_point.name == name:
            return cast("Adapter", entry_point.load())
    if name in _BUILTINS:
        return _load_builtin(_BUILTINS[name])
    raise KeyError(f"unknown source adapter {name!r}; available: {', '.join(available_adapters())}")


def available_adapters() -> list[str]:
    """Return the sorted names of all discoverable source adapters."""
    names = {entry_point.name for entry_point in entry_points(group=_ENTRY_POINT_GROUP)}
    names.update(_BUILTINS)
    return sorted(names)


__all__ = ["Adapter", "available_adapters", "get_adapter"]
