# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Emitter: IR findings -> an OSCAL 1.1.2 plan-of-action-and-milestones (POA&M).

Each finding becomes one poam-item tied to an evidence-backed observation and a
risk. Remediation milestones/dates, system-id, and party/role context are program
inputs and are left as caller-supplied fields, not fabricated here.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Iterable
from typing import Any

from mint_oscal.emitters import _common
from mint_oscal.ir import IR, Finding, Subject

OSCAL_VERSION = _common.OSCAL_VERSION
# Fixed namespace so the same scan produces the same OSCAL uuids (content-addressable).
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _det(*parts: str) -> str:
    """Deterministic uuid from stable inputs (reproducible OSCAL output)."""
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))


def _aware(timestamp: str) -> str:
    """Return an ISO-8601 timestamp guaranteed to carry a UTC (``+00:00``) offset.

    OSCAL's ``dateTime-with-timezone`` datatype (which oscal-cli enforces at parse time)
    rejects a naive timestamp, so a timezone-less input is interpreted as UTC. Every input
    is then converted to UTC so that a lexical string compare is a chronological compare
    (see :func:`_stamp`): a mixed-offset set like ``+05:30`` and ``-08:00`` would otherwise
    sort by wall-clock text, not by instant. Unparseable strings are returned unchanged for
    the semantic layer / oscal-cli to flag.
    """
    try:
        parsed = datetime.datetime.fromisoformat(timestamp)
    except ValueError:
        return timestamp
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed.astimezone(datetime.UTC).isoformat()


def _stamp(findings: list[Finding]) -> str:
    """Deterministic document timestamp: the latest observation time.

    Using the findings' own ``observed_at`` (rather than wall-clock ``now()``) makes the
    same input produce a byte-identical POA&M; each is normalised to a timezone-aware
    isoformat (OSCAL requires it), so the lexical max is the chronological max. Falls back
    to the Unix epoch when no finding carries an observation time.
    """
    stamps = sorted(_aware(f.observed_at) for f in findings if f.observed_at)
    return stamps[-1] if stamps else "1970-01-01T00:00:00+00:00"


def _relevant_evidence(evidence: Iterable[Any]) -> list[dict[str, Any]]:
    """Build relevant-evidence entries, omitting ``props`` when empty.

    OSCAL's ``props`` is optional but requires >=1 item when present, so an evidence entry with
    no props must omit the key rather than emit ``[]`` (which is schema-invalid; #65).
    """
    entries: list[dict[str, Any]] = []
    for item in evidence:
        entry: dict[str, Any] = {"description": item.description}
        if item.props:
            entry["props"] = _common.props_from(item.props)
        entries.append(entry)
    return entries


def _no_findings_item(subject: Subject) -> dict[str, Any]:
    """A single, honest poam-item for a scan that produced no findings.

    OSCAL requires >=1 ``poam-item``, so an empty scan (e.g. a fully PQ-ready endpoint) is
    reported as one truthful summary item -- never fabricated findings, observations, or risks
    (#64). Deterministic uuid so the same empty scan mints byte-identical output.
    """
    return {
        "uuid": _det("poam-item", "no-findings", subject.id),
        "title": "No findings",
        "description": f"No post-quantum cryptographic findings were identified for {subject.id}.",
    }


def emit(ir: IR, *, source: str | None = None, now: str | None = None) -> dict[str, Any]:
    """Emit an OSCAL POA&M from an IR bundle (registry entry point)."""
    return to_poam(
        ir.findings,
        ir.subject,
        source=source or ir.source.capitalize(),
        now=now,
    )


def to_poam(
    findings: Iterable[Finding],
    subject: Subject,
    *,
    source: str,
    now: str | None = None,
) -> dict[str, Any]:
    """Emit an OSCAL POA&M document from IR findings for one subject."""
    findings = list(findings)
    timestamp = now or _stamp(findings)
    inventory_uuid = _det("inventory-item", subject.id)

    observations: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for finding in findings:
        observation_uuid = _det("observation", finding.id)
        risk_uuid = _det("risk", finding.id)
        # OSCAL metaschema observation child order:
        # description -> props -> methods -> types -> subjects -> relevant-evidence -> collected.
        observation: dict[str, Any] = {
            "uuid": observation_uuid,
            "description": finding.title,
        }
        if finding.posture:
            observation["props"] = _common.props_from(finding.posture)
        observation.update(
            {
                "methods": ["TEST"],
                "types": ["finding"],
                "subjects": [{"subject-uuid": inventory_uuid, "type": "inventory-item"}],
            }
        )
        # relevant-evidence is optional and OSCAL requires >=1 item when present, so omit
        # it for an evidence-less finding (e.g. a CBOM carries posture but no probe output).
        if finding.evidence:
            observation["relevant-evidence"] = _relevant_evidence(finding.evidence)
        observation["collected"] = _aware(finding.observed_at)
        observations.append(observation)
        risks.append(
            {
                "uuid": risk_uuid,
                "title": finding.title,
                "description": finding.risk_statement,
                "statement": finding.risk_statement,
                # Reflect the finding's own status (open|closed), not a hardcoded "open", so a
                # remediated finding is not minted as an open risk (#66). Both IR values are
                # valid OSCAL risk-status tokens.
                "status": finding.status,
            }
        )
        items.append(
            {
                "uuid": _det("poam-item", finding.id),
                "title": finding.title,
                "description": finding.description,
                "props": [
                    *(_common.prop("control-id", control) for control in finding.control_ids),
                    _common.prop("severity", finding.severity),
                ],
                "related-observations": [{"observation-uuid": observation_uuid}],
                "related-risks": [{"risk-uuid": risk_uuid}],
            }
        )

    # OSCAL requires observations/risks to have >=1 item when present, so omit an empty array
    # rather than emit a schema-invalid `[]`; poam-items is required (>=1), so an empty scan
    # gets one honest "no findings" item (#64). Key order follows the metaschema child order.
    body: dict[str, Any] = {
        "uuid": _det("poam", subject.id, timestamp[:10]),
        "metadata": _common.metadata(
            f"POA&M - {source} scan of {subject.id}",
            timestamp=timestamp,
        ),
        "system-id": {"identifier-type": "https://ietf.org/rfc/rfc3986", "id": subject.id},
        "local-definitions": {
            "inventory-items": [{"uuid": inventory_uuid, "description": subject.description}]
        },
    }
    if observations:
        body["observations"] = observations
    if risks:
        body["risks"] = risks
    body["poam-items"] = items or [_no_findings_item(subject)]
    return {"plan-of-action-and-milestones": body}
