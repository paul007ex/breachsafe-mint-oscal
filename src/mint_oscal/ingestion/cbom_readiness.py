# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Pure readiness classification helpers for the CycloneDX CBOM adapter."""

from __future__ import annotations

from typing import Any

_KEX_PRIMITIVES = frozenset({"key-agree", "kem", "pke"})
_INDETERMINATE_PRIMITIVES = frozenset({"unknown", "other"})


def _declared_result(level: int, registry_classical: bool) -> tuple[bool, int]:
    """Evaluate a producer-declared security level."""
    return level > 0 and not registry_classical, level


def _registry_result(entry: dict[str, Any]) -> tuple[bool, int]:
    """Evaluate the bundled registry fallback."""
    return bool(entry.get("quantum_safe")), int(entry.get("nistLevel", 0))


def classify_algorithm(
    name: str,
    declared_primitive: str | None,
    declared_level: int | None,
    registry: dict[str, dict[str, Any]],
) -> tuple[bool, bool | None, int, bool]:
    """Classify one algorithm without turning missing evidence into a safe verdict."""
    entry = registry.get(name.upper())
    is_kex = declared_primitive in _KEX_PRIMITIVES or (entry or {}).get("kind") == "kex"
    registry_classical = entry is not None and not entry.get("quantum_safe", False)
    if declared_level is not None:
        safe, level = _declared_result(declared_level, registry_classical)
    elif entry is not None:
        safe, level = _registry_result(entry)
    else:
        safe, level = None, 0
    indeterminate = (
        not is_kex
        and entry is None
        and (declared_primitive is None or declared_primitive in _INDETERMINATE_PRIMITIVES)
    )
    return is_kex, safe, level, indeterminate


def _matches_rule(
    rule: dict[str, Any], quantum_safe: dict[str, bool], classical: dict[str, bool]
) -> bool:
    """Return whether one declarative readiness rule matches the inventory."""
    return quantum_safe.get(rule.get("kex_quantum_safe", ""), True) and classical.get(
        rule.get("kex_classical", ""), True
    )


def derive_readiness(
    kex_safe: list[bool], unclassified: list[str], rules: list[dict[str, Any]]
) -> str:
    """Apply declarative readiness rules to the KEX evidence we could classify."""
    if not kex_safe:
        return "unknown"
    total, safe_count = len(kex_safe), sum(kex_safe)
    quantum_safe = {"all": safe_count == total, "some": safe_count > 0, "none": safe_count == 0}
    classical = {"all": safe_count == 0, "some": safe_count < total, "none": safe_count == total}
    readiness = next(
        (str(rule["readiness"]) for rule in rules if _matches_rule(rule, quantum_safe, classical)),
        "unknown",
    )
    return "unknown" if readiness == "quantum_ready" and unclassified else readiness
