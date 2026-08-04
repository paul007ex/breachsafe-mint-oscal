# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Versioned policy packs: the *policy* tables the engine consults, as data.

Three tables are genuine policy decisions (which controls a verdict implicates, how
severe it is, and how to phrase its risk) rather than mechanism, so they live in
reviewable YAML under :mod:`mint_oscal.policy.<pack>` and are read (not imported) via
:mod:`importlib.resources`. Each pack targets one control FRAMEWORK:

- ``scf-qts`` (package ``scf_qts``) -- SCF Quantum Security controls; the DEFAULT frame,
  PQC-native (qts-04 Discovery, qts-04.3 Exposure, ...) where NIST SC-13 is generic (#88).
- ``nist`` (package ``default``) -- NIST SP 800-53r5 (SC-13/SC-12); opt-in secondary.

The framework is selected per run via :func:`set_active_framework` (contextvar-scoped), so
the CLI's ``--framework`` flag reaches the adapter's crosswalk without threading a parameter
through the vendor-neutral adapter port (ADR-0004).

Fail-loud (ADR-0006): every readiness verdict the engine can emit must have an entry in each
of the three tables, or :func:`get_policy` raises at load naming the missing keys.
"""

from __future__ import annotations

import contextvars
import functools
from dataclasses import dataclass
from importlib import resources
from typing import Any, cast

import yaml

# The canonical readiness vocabulary -- the single source of truth shared by the policy loader
# (a pack omitting any of these for any table is rejected at load) and the breachsafe extension.
# Keep this the ONLY definition so the two cannot drift (issue #47). ``not_applicable`` is a real
# honest-state a producer (QuReddy) emits for an out-of-scope asset, e.g. a cert signature (#86).
READINESS_VERDICTS = frozenset(
    {
        "quantum_vulnerable",
        "transitional_hybrid",
        "quantum_ready",
        "unknown",
        "classically_weak",
        "not_applicable",
    }
)

# Friendly framework name (CLI/user-facing) -> policy PACKAGE (module names cannot hyphenate).
# SCF-QTS is the default frame; NIST is opt-in. Add a framework by adding a pack + one entry.
FRAMEWORK_PACKS = {"scf-qts": "scf_qts", "nist": "default"}
DEFAULT_FRAMEWORK = "scf-qts"
_active_framework: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mint_oscal_framework", default=DEFAULT_FRAMEWORK
)


def set_active_framework(name: str) -> None:
    """Select the control framework for this run (contextvar-scoped, thread/async-safe)."""
    if name not in FRAMEWORK_PACKS:
        available = ", ".join(sorted(FRAMEWORK_PACKS))
        raise ValueError(f"unknown framework {name!r}; choose from: {available}")
    _active_framework.set(name)


def active_framework() -> str:
    """The friendly name of the framework selected for this run (default: scf-qts)."""
    return _active_framework.get()


@dataclass(frozen=True)
class Policy:
    """A loaded policy pack: verdict->control/severity/risk plus framework authority metadata."""

    severity: dict[str, str]
    crosswalk: dict[str, list[str]]
    risk: dict[str, str]
    reviewed: bool = False
    """Whether this pack's mappings passed conformance sign-off. False (the default, and the
    state of both bundled packs) means every finding's compliance framing is PROVISIONAL and
    is marked as such in emitted OSCAL -- a fact is not an authoritative finding without a
    governed interpretation (#84)."""
    framework: str = ""
    """Framework version id, e.g. ``scf-qts-2026.2`` -- emitted as a BreachSAFE prop so the
    output records which frame we assessed against (that IS a BreachSAFE fact)."""
    authority_ns: str = ""
    """The URI namespace of the body that OWNS these control ids (SCF, NIST) -- control ids are
    attributed here, NEVER the BreachSAFE ns, so the output is clear about what is standard."""
    catalog_href: str = ""
    """The OSCAL catalog that DEFINES these control ids -- emitted as a link target so a control
    reference resolves to its authoritative source rather than a bare string."""


@functools.cache
def get_policy(pack: str) -> Policy:
    """Load, validate, and cache a policy pack by its PACKAGE name (e.g. ``scf_qts``).

    Prefer :func:`active_policy` in engine code; this is the low-level loader keyed on the
    package so framework switching within a process never returns a stale cache.

    Raises:
        ValueError: if any of the three tables is missing a readiness key the engine can emit
            (fail-loud; never silently mis-map a finding).
    """
    pkg = resources.files(f"mint_oscal.policy.{pack}")

    def load(filename: str) -> dict[str, object]:
        return cast(
            "dict[str, object]",
            yaml.safe_load((pkg / filename).read_text(encoding="utf-8")),
        )

    # Governance + authority metadata (issue #84/#88). Absent or non-true meta -> reviewed=False
    # (safe default: an ungoverned interpretation is marked provisional, not authoritative).
    reviewed = False
    meta: dict[str, Any] = {}
    meta_file = pkg / "meta.yaml"
    if meta_file.is_file():
        loaded = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            meta = loaded
            reviewed = meta.get("reviewed") is True

    policy = Policy(
        severity=cast("dict[str, str]", load("severity.yaml")),
        crosswalk=cast("dict[str, list[str]]", load("control-crosswalk.yaml")),
        risk=cast("dict[str, str]", load("risk-statements.yaml")),
        reviewed=reviewed,
        framework=str(meta.get("framework") or ""),
        authority_ns=str(meta.get("authority_ns") or ""),
        catalog_href=str(meta.get("catalog_href") or ""),
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
            msg = f"policy '{pack}' {table}.yaml is not a mapping (got {type(data).__name__})"
            raise ValueError(msg)
        missing = READINESS_VERDICTS - data.keys()
        if missing:
            msg = f"policy '{pack}' {table}.yaml missing readiness keys: {sorted(missing)}"
            raise ValueError(msg)
    return policy


def active_policy() -> Policy:
    """The :class:`Policy` for the framework selected this run (resolves the contextvar)."""
    return get_policy(FRAMEWORK_PACKS[active_framework()])
