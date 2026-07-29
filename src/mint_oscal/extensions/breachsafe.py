# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Extension: the BreachSAFE producer cross-check + evidence enricher (ADR-0008).

Runs *after* a source adapter has derived the neutral IR and reconciles the producer's
declared facts against what mint derived from the crypto inventory itself. Two facts:

- **Aggregate readiness** -> stamped onto ``finding.posture['provenance']`` as
  ``derived`` (no usable producer claim), ``producer-confirmed`` (producer's declared
  readiness matches the derived verdict), or ``conflict:producer=X,derived=Y`` (they
  differ; ``Y`` -- the derived verdict -- is kept, honest-failure). mint's own verdict
  always wins on conflict; the producer claim is *recorded*, not obeyed.
- **Evidence chain** -> the producer's per-probe evidence (sha256 hashes, probe results,
  timestamps) becomes OSCAL ``relevant-evidence`` on the observation, so the minted POA&M
  carries the chain of custody, not just the verdict.

Producer facts are read from the standard ``breachsafe:v1:*`` extension namespace when
present. As a **for-now bridge**, the native ``qureddy:*`` namespace is also read, because
QuReddy does not yet emit ``breachsafe:v1:*`` (tracked upstream; long-term QuReddy emits the
standard namespace and this bridge is removed). ``breachsafe:v1:*`` takes precedence. This
qureddy-awareness lives only in this *opt-in* enricher; the neutral ``--from cbom`` path
stays vendor-neutral.

The enricher is pure: it never logs, prints, or raises. A malformed or unknown declared
value is ignored (treated as absent), not an error.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from mint_oscal.ir import Evidence, Finding, Subject
from mint_oscal.policy import READINESS_VERDICTS

_EXT_PREFIX = "breachsafe:v1:"
# For-now bridge: QuReddy still emits its native namespace, not breachsafe:v1. Read it so the
# cross-check + evidence chain work today; remove when QuReddy emits breachsafe:v1 (upstream).
_QUREDDY_PREFIX = "qureddy:"
_EVIDENCE_INFIX = "evidence."


def _producer_props(document: dict[str, Any]) -> dict[str, str]:
    """Collect every string producer prop (``breachsafe:v1:*`` and ``qureddy:*``), keyed by name.

    Scans ``properties[]`` on ``metadata`` (where QuReddy places scan facts), on
    ``metadata.component`` and every component (where ``breachsafe:v1`` facts ride). Anything
    shapeless is skipped -- a facts extension never fails the pipeline over a stray property.
    """
    out: dict[str, str] = {}

    def scan(holder: object) -> None:
        if not isinstance(holder, dict):
            return
        for prop in holder.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            name, value = prop.get("name"), prop.get("value")
            if (
                isinstance(name, str)
                and isinstance(value, str)
                and (name.startswith(_EXT_PREFIX) or name.startswith(_QUREDDY_PREFIX))
            ):
                out[name] = value

    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        scan(metadata)
        scan(metadata.get("component"))
    for component in document.get("components") or []:
        scan(component)
    return out


def _declared_readiness(props: dict[str, str]) -> str | None:
    """The producer's declared aggregate readiness (breachsafe:v1 preferred, qureddy fallback).

    Returns it only if it is a recognized readiness verdict; an unknown/out-of-vocab value is
    treated as absent (``None``) so a garbage producer claim can never taint the cross-check.
    """
    declared = props.get(f"{_EXT_PREFIX}readiness") or props.get(f"{_QUREDDY_PREFIX}scan.readiness")
    return declared if declared in READINESS_VERDICTS else None


def _evidence_records(props: dict[str, str]) -> tuple[Evidence, ...]:
    """Build IR ``Evidence`` (-> OSCAL relevant-evidence) from producer evidence facts.

    QuReddy emits ``qureddy:evidence.<NN>.<key>`` grouped by index; each group becomes one
    ``Evidence`` whose props are its facts (sha256 hashes, probe results, ...). A single
    ``breachsafe:v1:evidence-sha256`` fact, if present, is carried as one more record.
    Deterministic: groups and their keys are sorted.
    """
    groups: dict[str, dict[str, str]] = {}
    for name, value in props.items():
        if name.startswith(f"{_QUREDDY_PREFIX}{_EVIDENCE_INFIX}"):
            index, _, key = name[len(f"{_QUREDDY_PREFIX}{_EVIDENCE_INFIX}") :].partition(".")
            if key:
                groups.setdefault(index, {})[key] = value
    records: list[Evidence] = []
    for index in sorted(groups):
        facts = dict(sorted(groups[index].items()))
        description = facts.get("type") or facts.get("source") or f"probe evidence {index}"
        records.append(Evidence(description=description, props=facts))
    sha = props.get(f"{_EXT_PREFIX}evidence-sha256")
    if sha:
        records.append(Evidence(description="producer evidence", props={"sha256": sha}))
    return tuple(records)


def _crosscheck(derived: str, declared: str | None) -> str:
    """Return the provenance verdict for a derived readiness against the producer's declared one.

    On conflict the derived verdict is authoritative; the producer's claim is only recorded.
    ``derived`` is guarded to a recognized verdict so the delimited ``conflict:producer=X,
    derived=Y`` string can never be corrupted by an unexpected value bearing a ``,``/``=`` (#63).
    """
    if derived not in READINESS_VERDICTS:
        return "derived"
    if declared and declared != derived:
        return f"conflict:producer={declared},derived={derived}"
    if declared:
        return "producer-confirmed"
    return "derived"


def enrich(
    findings: list[Finding],
    subject: Subject,
    *,
    document: dict[str, Any],
) -> tuple[list[Finding], Subject]:
    """Enrich IR findings with the producer provenance cross-check and evidence chain.

    Stamps each finding's ``posture`` with a ``provenance`` verdict and attaches the producer's
    evidence records (-> OSCAL relevant-evidence). Pure: returns new ``Finding`` objects via
    :func:`dataclasses.replace` and never mutates its inputs, logs, or raises.
    """
    props = _producer_props(document)
    declared = _declared_readiness(props)
    evidence = _evidence_records(props)

    enriched: list[Finding] = []
    for finding in findings:
        derived = finding.posture.get("readiness", "unknown")
        posture = {**finding.posture, "provenance": _crosscheck(derived, declared)}
        enriched.append(
            replace(finding, posture=posture, evidence=(*finding.evidence, *evidence))
        )
    return enriched, subject


__all__ = ["enrich"]
