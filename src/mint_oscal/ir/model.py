# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""The source-neutral intermediate representation (IR).

Every source adapter (QuReddy JSON, Prowler, OCSF, ...) normalizes into these
types; every emitter (OSCAL POA&M, OSCAL Assessment Results, ...) reads them. That
keeps the mapping N + M instead of N x M: a new source is one adapter, a new target
is one emitter, and neither touches the other (ADR-0004: agnostic core).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Subject:
    """The thing a finding is about (a scanned endpoint, a cloud resource, ...)."""

    id: str
    kind: str  # OSCAL inventory-item / component / location
    description: str


@dataclass(frozen=True)
class Evidence:
    """A single piece of provenance backing an observation.

    Carries hashes and small facts, never raw secret-bearing output.
    """

    description: str
    props: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Risk:
    """The compliance risk framing an emitter needs for a finding.

    Supplied by a per-source control map (see ``mint_oscal.controls``), never
    invented by the emitter. Kept separate from :class:`Finding` so that a target
    emitter that models risk differently (Assessment Results vs POA&M) can reuse it.
    """

    statement: str
    control_ids: tuple[str, ...]
    severity: str  # critical|high|medium|low|info


@dataclass(frozen=True)
class Finding:
    """A normalized finding: what was concluded, about what, backed by what.

    ``control_ids`` and ``risk_statement`` are the compliance framing a target
    emitter needs; they are supplied by a per-source control map, not invented by
    the emitter. Remediation milestones and system/party context are deliberately
    absent here: they are program inputs, not scanner outputs.
    """

    id: str
    title: str
    description: str
    severity: str  # critical|high|medium|low|info
    status: str  # open|closed|...
    subject: Subject
    observed_at: str  # RFC 3339
    control_ids: tuple[str, ...]
    risk_statement: str
    evidence: tuple[Evidence, ...] = ()
    posture: dict[str, str] = field(default_factory=dict)
    """structured crypto-posture facts (readiness, algorithm, nistQuantumSecurityLevel,
    cert-signature) for observation props; supplied by the adapter, never invented by
    the emitter."""


@dataclass(frozen=True)
class IR:
    """A source-neutral bundle: the findings for one subject and their origin.

    This is the single value passed to :func:`mint_oscal.convert`; adapters build
    it, emitters consume it. ``source`` names the adapter that produced the bundle
    (for provenance in emitted metadata), not a program-level system identity.
    """

    findings: tuple[Finding, ...]
    subject: Subject
    source: str = "unknown"
