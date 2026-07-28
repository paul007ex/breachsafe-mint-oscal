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
from typing import Any, cast

from mint_oscal._registry import discover, resolve
from mint_oscal.ir import Finding, Subject

Adapter = Callable[[dict[str, Any]], tuple[list[Finding], Subject]]

_ENTRY_POINT_GROUP = "mint_oscal.adapters"
# Bundled fallbacks: name -> "module:callable". Entry-point adapters still win.
_BUILTINS = {
    "qureddy": "mint_oscal.adapters.qureddy:from_scan_v1",
    "cbom": "mint_oscal.adapters.cbom:from_cbom",
}


def get_adapter(name: str) -> Adapter:
    """Return the adapter registered under ``name``.

    Entry-point adapters win; the bundled ``qureddy``/``cbom`` adapters are the
    fallback so they resolve even before the package is installed.

    Raises:
        KeyError: if no adapter is registered under ``name``.
    """
    return cast(
        "Adapter",
        resolve(_ENTRY_POINT_GROUP, _BUILTINS, name, "source adapter", available_adapters()),
    )


def available_adapters() -> list[str]:
    """Return the sorted names of all discoverable source adapters."""
    return sorted(discover(_ENTRY_POINT_GROUP, _BUILTINS))


__all__ = ["Adapter", "available_adapters", "get_adapter"]
