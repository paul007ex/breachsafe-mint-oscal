# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Shared entry-point registry helpers for the adapter and extension ports (ADR-0004).

Both :mod:`mint_oscal.adapters` and :mod:`mint_oscal.extensions` discover plugins through an
entry-point group with a bundled built-in fallback, and the lookup/discovery logic is
identical. It lives here once so the two ports cannot drift; each port keeps only its own
type alias, group name, built-ins, and error wording.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib.metadata import entry_points
from typing import Any


def load_builtin(target: str) -> Any:  # noqa: ANN401 -- port modules cast to their concrete type
    """Import a bundled callable from its ``module:callable`` reference."""
    module_name, _, attr = target.partition(":")
    module = __import__(module_name, fromlist=[attr])
    return getattr(module, attr)


def resolve(
    group: str, builtins: dict[str, str], name: str, kind: str, available: Iterable[str]
) -> Any:  # noqa: ANN401 -- port modules cast to their concrete type
    """Return the plugin registered under ``name``: an entry point wins, then a built-in.

    Raises:
        KeyError: if no plugin is registered under ``name`` (message names ``kind`` and lists
            what is available).
    """
    for entry_point in entry_points(group=group):
        if entry_point.name == name:
            return entry_point.load()
    if name in builtins:
        return load_builtin(builtins[name])
    raise KeyError(f"unknown {kind} {name!r}; available: {', '.join(available)}")


def discover(group: str, builtins: dict[str, str]) -> set[str]:
    """All discoverable plugin names for a group (entry points plus bundled built-ins)."""
    names = {entry_point.name for entry_point in entry_points(group=group)}
    names.update(builtins)
    return names
