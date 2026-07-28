# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Extension: the BreachSAFE ``breachsafe:v1`` cross-check enricher (ADR-0008).

``breachsafe:v1`` is a facts-only CycloneDX extension: a producer declares small,
native-first, string-valued facts as ``properties[]`` (``breachsafe:v1:readiness``,
``breachsafe:v1:evidence-sha256``) on ``metadata.component`` or on any component. This
enricher runs *after* a source adapter has already derived the neutral IR and reconciles
the producer's *declared aggregate readiness* against the verdict mint derived from the
inventory itself.

Trust is scoped honestly (ADR-0008). Native atomic facts (e.g. ``nistQuantumSecurityLevel``
on an algorithm) are trusted-by-design and consumed by ``adapters/cbom.py`` directly; this
enricher does *not* re-adjudicate them. Only the *aggregate* readiness verdict is compared,
and mint's own derived verdict always wins on conflict — the producer claim is recorded, not
obeyed. The outcome is stamped onto ``finding.posture['provenance']``:

- ``derived`` — no usable producer claim; the verdict is mint's own.
- ``producer-confirmed`` — the producer's declared readiness matches the derived verdict.
- ``conflict:producer=X,derived=Y`` — they differ; ``Y`` (the derived verdict) is kept.

The enricher is pure: it never logs, prints, or raises. A malformed or unknown declared
value is ignored (treated as absent), not an error.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from mint_oscal.ir import Finding, Subject
from mint_oscal.policy import READINESS_VERDICTS

_EXT_PREFIX = "breachsafe:v1:"


def _observations(document: dict[str, Any]) -> dict[str, str]:
    """Collect ``breachsafe:v1:*`` facts from the raw CBOM document.

    Reads ``properties[]`` on ``metadata.component`` and on every component, keyed by the
    suffix after ``breachsafe:v1:``. Later occurrences win (components override metadata),
    which is fine for the single-subject flow. Anything shapeless is skipped silently — a
    facts extension never fails the pipeline over a stray property.
    """
    observations: dict[str, str] = {}

    def scan(holder: object) -> None:
        if not isinstance(holder, dict):
            return
        for prop in holder.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            name, value = prop.get("name"), prop.get("value")
            if isinstance(name, str) and name.startswith(_EXT_PREFIX) and isinstance(value, str):
                observations[name[len(_EXT_PREFIX) :]] = value

    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        scan(metadata.get("component"))
    for component in document.get("components") or []:
        scan(component)
    return observations


def _crosscheck(derived: str, observations: dict[str, str]) -> str:
    """Return the provenance verdict for a derived readiness against producer observations.

    A declared readiness outside the recognized vocabulary is ignored (treated as absent).
    On conflict the derived verdict is authoritative; the producer's claim is only recorded.
    """
    declared = observations.get("readiness")
    if declared not in READINESS_VERDICTS:
        declared = None
    # ``derived`` is mint's own verdict and is always a recognized token in practice; guard it
    # too so the delimited ``conflict:producer=X,derived=Y`` provenance can never be corrupted
    # by an unexpected value bearing a ``,`` or ``=`` (keeps the string round-trip-parseable).
    # A no-op for every real finding; only a would-be junk derived verdict falls back to
    # ``derived`` rather than emitting a malformed conflict token (#63).
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
    """Enrich IR findings with a ``breachsafe:v1`` provenance cross-check.

    Reads producer-declared facts from the raw ``document`` and stamps each finding's
    ``posture`` with a ``provenance`` verdict (and ``evidence-sha256`` when the producer
    supplies one). Pure: returns new ``Finding`` objects via :func:`dataclasses.replace`
    and never mutates its inputs, logs, or raises.
    """
    observations = _observations(document)
    evidence = observations.get("evidence-sha256")

    enriched: list[Finding] = []
    for finding in findings:
        derived = finding.posture.get("readiness", "unknown")
        posture = {**finding.posture, "provenance": _crosscheck(derived, observations)}
        if evidence:
            posture["evidence-sha256"] = evidence
        enriched.append(replace(finding, posture=posture))
    return enriched, subject


__all__ = ["enrich"]
