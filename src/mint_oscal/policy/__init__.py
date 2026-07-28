# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Versioned policy pack: the *policy* tables the engine consults, as data.

Three tables are genuine policy decisions (which controls a verdict implicates,
how severe it is, and how to phrase its risk) rather than mechanism, so they live
in reviewable, promotable YAML under :mod:`mint_oscal.policy.<name>` and are read
(not imported) via :mod:`importlib.resources`. ``default`` is the bundled pack.

Fail-loud (ADR-0006): every readiness verdict the engine can emit must have an
entry in each of the three tables, or :func:`get_policy` raises at load naming the
missing keys — an incomplete pack never silently mis-maps a finding.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from importlib import resources
from typing import cast

import yaml

# The canonical readiness vocabulary — the single source of truth shared by the policy
# loader (a pack omitting any of these for any table is rejected at load) and the
# breachsafe extension (which recognises a producer-declared verdict only if it is one
# of these). Keep this the ONLY definition so the two cannot drift (issue #47).
READINESS_VERDICTS = frozenset(
    {
        "quantum_vulnerable",
        "transitional_hybrid",
        "quantum_ready",
        "unknown",
        "classically_weak",
    }
)


@dataclass(frozen=True)
class Policy:
    """A loaded policy pack: readiness verdict -> control ids, severity, and risk prose."""

    severity: dict[str, str]
    crosswalk: dict[str, list[str]]
    risk: dict[str, str]


@functools.cache
def get_policy(name: str = "default") -> Policy:
    """Load, validate, and cache the named policy pack.

    Raises:
        ValueError: if any of the three tables is missing a readiness key the
            engine can emit (fail-loud; never silently mis-map a finding).
    """
    pkg = resources.files(f"mint_oscal.policy.{name}")

    def load(filename: str) -> dict[str, object]:
        return cast(
            "dict[str, object]",
            yaml.safe_load((pkg / filename).read_text(encoding="utf-8")),
        )

    policy = Policy(
        severity=cast("dict[str, str]", load("severity.yaml")),
        crosswalk=cast("dict[str, list[str]]", load("control-crosswalk.yaml")),
        risk=cast("dict[str, str]", load("risk-statements.yaml")),
    )
    for table, data in (
        ("severity", policy.severity),
        ("control-crosswalk", policy.crosswalk),
        ("risk-statements", policy.risk),
    ):
        # An empty or non-mapping YAML (yaml.safe_load -> None / list) would otherwise reach
        # ``data.keys()`` and raise a bare AttributeError; fail loud with a clear message so the
        # invited "copy the pack and swap" path never crashes opaquely.
        if not isinstance(data, dict):
            msg = f"policy '{name}' {table}.yaml is not a mapping (got {type(data).__name__})"
            raise ValueError(msg)
        missing = READINESS_VERDICTS - data.keys()
        if missing:
            msg = f"policy '{name}' {table}.yaml missing readiness keys: {sorted(missing)}"
            raise ValueError(msg)
    return policy
