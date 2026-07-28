# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Emitter registry: OSCAL model name -> emitter callable.

Every emitter exposes ``emit(ir, **params) -> dict``. Register a new OSCAL target
here and nowhere else; the CLI and :func:`mint_oscal.convert` discover models
through this registry.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType
from typing import Any

from mint_oscal.emitters import ar, component, poam

Emitter = Callable[..., dict[str, Any]]

# MappingProxyType so the registry can't be mutated at runtime (breachsafe-implement).
_EMITTERS: MappingProxyType[str, Emitter] = MappingProxyType(
    {
        "poam": poam.emit,
        "ar": ar.emit,
        "component-definition": component.emit,
    }
)


def get_emitter(model: str) -> Emitter:
    """Return the emitter registered for an OSCAL model name.

    Raises:
        KeyError: if ``model`` is not a registered OSCAL model.
    """
    try:
        return _EMITTERS[model]
    except KeyError:
        raise KeyError(
            f"unknown OSCAL model {model!r}; known models: {', '.join(available_models())}"
        ) from None


def available_models() -> list[str]:
    """Return the sorted list of registered OSCAL model names."""
    return sorted(_EMITTERS)


__all__ = ["Emitter", "available_models", "get_emitter"]
