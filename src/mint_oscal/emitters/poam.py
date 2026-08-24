# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Emitter: IR findings -> an OSCAL 1.2.2 plan-of-action-and-milestones (POA&M).

Each finding becomes one poam-item tied to an evidence-backed observation and a
risk. Remediation milestones/dates, system-id, and party/role context are program
inputs and are left as caller-supplied fields, not fabricated here.
"""

from __future__ import annotations

import datetime
import uuid
from collections import Counter
from collections.abc import Iterable
from typing import Any

from mint_oscal.emitters import _common
from mint_oscal.ir import IR, Finding, Subject
from mint_oscal.policy import Policy, active_policy

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


def _emit_observation(finding: Finding, inventory_uuid: str, key: str) -> dict[str, Any]:
    """Build the OSCAL observation for one finding."""
    observation: dict[str, Any] = {"uuid": _det("observation", key), "description": finding.title}
    if finding.posture:
        observation["props"] = _common.props_from(finding.posture)
    observation.update(
        {
            "methods": ["TEST"],
            "types": ["finding"],
            "subjects": [{"subject-uuid": inventory_uuid, "type": "inventory-item"}],
            "collected": _aware(finding.observed_at),
        }
    )
    if finding.evidence:
        observation["relevant-evidence"] = _relevant_evidence(finding.evidence)
    return observation


def _emit_risk(finding: Finding, key: str) -> dict[str, Any]:
    """Build the OSCAL risk for one finding."""
    return {
        "uuid": _det("risk", key),
        "title": finding.title,
        "description": finding.risk_statement,
        "statement": finding.risk_statement,
        "status": finding.status,
    }


def _emit_item(
    finding: Finding, policy: Policy, key: str, observation: dict[str, Any], risk: dict[str, Any]
) -> dict[str, Any]:
    """Build the OSCAL POA&M item linking its observation and risk."""
    props = [
        *(
            _common.prop("control-id", c, ns=policy.authority_ns or None)
            for c in finding.control_ids
        ),
        _common.prop("severity", finding.severity),
    ]
    if policy.framework:
        props.append(_common.prop("framework", policy.framework))
    if not policy.reviewed:
        props.append(_common.prop("interpretation-status", "provisional"))
    item: dict[str, Any] = {
        "uuid": _det("poam-item", key),
        "title": finding.title,
        "description": finding.description,
        "props": props,
        "related-observations": [{"observation-uuid": observation["uuid"]}],
        "related-risks": [{"risk-uuid": risk["uuid"]}],
    }
    if policy.catalog_href and finding.control_ids:
        item["links"] = [
            {"href": f"{policy.catalog_href}#{control}", "rel": "reference"}
            for control in finding.control_ids
        ]
    return item


def _emit_finding(
    finding: Finding, inventory_uuid: str, policy: Policy, *, uuid_key: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build the observation, risk, and POA&M item for one finding."""
    key = uuid_key or finding.id
    observation = _emit_observation(finding, inventory_uuid, key)
    risk = _emit_risk(finding, key)
    item = _emit_item(finding, policy, key, observation, risk)
    return observation, risk, item


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
    # Framework attribution + governance for this run (scf-qts by default). Control ids belong
    # to the framework authority (SCF/NIST); framework + provisional status are BreachSAFE facts.
    pol = active_policy()

    observations: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    id_counts = Counter(finding.id for finding in findings)
    seen_ids: Counter[str] = Counter()
    for finding in findings:
        seen_ids[finding.id] += 1
        # Preserve existing UUIDs for the normal case. If an upstream producer repeats an id,
        # add a stable ordinal rather than silently emitting duplicate OSCAL UUIDs (#168).
        uuid_key = (
            f"{finding.id}|duplicate-{seen_ids[finding.id]}" if id_counts[finding.id] > 1 else None
        )
        observation, risk, item = _emit_finding(finding, inventory_uuid, pol, uuid_key=uuid_key)
        observations.append(observation)
        risks.append(risk)
        items.append(item)

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
