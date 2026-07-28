# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Adapter: CycloneDX CBOM + the optional ``breachsafe:v1`` overlay -> the neutral IR.

This is the BreachSAFE overlay over the vendor-neutral CBOM path (ADR-0008). It
*composes* :func:`mint_oscal.adapters.cbom.from_cbom` (its only import from the core,
which already validates the CycloneDX shape and derives every crypto fact from
``cryptoProperties``) and then reads the optional producer-facts extension carried in
CycloneDX ``properties[]`` under the ``breachsafe:v1:`` prefix.

Facts-only, native-first: crypto facts are always DERIVED by ``from_cbom`` and are
NEVER read from the extension, so there is no duplication and no path by which a
producer's self-report replaces measured fact. The extension only annotates. The one
adjudicated value is the AGGREGATE readiness verdict: the producer's declaration is
cross-checked against ours and recorded as ``provenance``, but on conflict OUR verdict
stays authoritative — the disagreement is surfaced as posture *data*, never logged,
printed, or raised (adapter purity).
"""

from __future__ import annotations

import dataclasses
from typing import Any

from mint_oscal.adapters.cbom import from_cbom
from mint_oscal.ir import Finding, Subject

_EXT_PREFIX = "breachsafe:v1:"
# A producer may *declare* one of these readiness verdicts; anything else is ignored
# (treated as absent) rather than trusted, so a malformed value can never weaken the
# derived verdict or fabricate a false confirmation.
_READINESS_VALUES = frozenset(
    {"quantum_vulnerable", "transitional_hybrid", "quantum_ready", "unknown"}
)


def _producer_observations(document: dict[str, Any]) -> dict[str, str]:
    """Collect ``breachsafe:v1:*`` producer facts from the raw document's ``properties[]``.

    Walks ``metadata.component`` and every ``components[]`` entry via plain dict access
    (``from_cbom`` already validated the shape), keeping every property whose name
    carries the ``breachsafe:v1:`` prefix, keyed by the unprefixed field name
    (``breachsafe:v1:readiness`` -> ``readiness``). Non-string / empty values are
    dropped.
    """
    metadata_component = document.get("metadata", {}).get("component")
    holders = [metadata_component, *document.get("components", [])]
    out: dict[str, str] = {}
    for holder in holders:
        if not isinstance(holder, dict):
            continue
        for prop in holder.get("properties", []):
            name = prop.get("name")
            value = prop.get("value")
            if isinstance(name, str) and name.startswith(_EXT_PREFIX) and isinstance(value, str):
                out[name[len(_EXT_PREFIX) :]] = value
    return out


def _provenance(derived: str, observations: dict[str, str]) -> str:
    """Cross-check the derived readiness against the producer's declaration.

    Returns one of the stable provenance vocabulary values: ``producer-confirmed`` when
    the producer independently declares the same verdict we derived,
    ``conflict:producer=<p>,derived=<d>`` when it declares a different (valid) verdict —
    OUR derivation remains authoritative — and ``derived`` when the producer declares
    nothing usable.
    """
    declared: str | None = observations.get("readiness")
    if declared not in _READINESS_VALUES:
        declared = None  # ignore an absent or malformed declaration
    if declared and declared != derived:
        return f"conflict:producer={declared},derived={derived}"
    if declared:
        return "producer-confirmed"
    return "derived"


def _with_provenance(finding: Finding, observations: dict[str, str]) -> Finding:
    """Return a copy of ``finding`` carrying provenance (and evidence hash) posture props."""
    derived = finding.posture.get("readiness", "unknown")
    posture = {**finding.posture, "provenance": _provenance(derived, observations)}
    evidence_hash = observations.get("evidence-sha256")
    if evidence_hash:
        posture["evidence-sha256"] = evidence_hash
    return dataclasses.replace(finding, posture=posture)


def from_breachsafe_cbom(document: dict[str, Any]) -> tuple[list[Finding], Subject]:
    """Convert a CycloneDX CBOM into IR, overlaying the optional ``breachsafe:v1`` facts.

    The vendor-neutral adapter derives the crypto posture; this overlay only adds
    provenance from the producer's declarations. A document with no ``breachsafe:v1:*``
    properties yields exactly the standard result plus a ``provenance=derived`` marker.

    Raises:
        MalformedCbomError: if ``document`` is not a parseable CycloneDX BOM.
    """
    findings, subject = from_cbom(document)
    observations = _producer_observations(document)
    enriched = [_with_provenance(finding, observations) for finding in findings]
    return enriched, subject
