# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
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
    timestamp = now or datetime.datetime.now(datetime.UTC).isoformat()
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
            observation["relevant-evidence"] = [
                {
                    "description": item.description,
                    "props": _common.props_from(item.props),
                }
                for item in finding.evidence
            ]
        observation["collected"] = finding.observed_at
        observations.append(observation)
        risks.append(
            {
                "uuid": risk_uuid,
                "title": finding.title,
                "description": finding.risk_statement,
                "statement": finding.risk_statement,
                "status": "open",
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

    return {
        "plan-of-action-and-milestones": {
            "uuid": _det("poam", subject.id, timestamp[:10]),
            "metadata": _common.metadata(
                f"POA&M - {source} scan of {subject.id}",
                timestamp=timestamp,
            ),
            "system-id": {"identifier-type": "https://ietf.org/rfc/rfc3986", "id": subject.id},
            "local-definitions": {
                "inventory-items": [{"uuid": inventory_uuid, "description": subject.description}]
            },
            "observations": observations,
            "risks": risks,
            "poam-items": items,
        }
    }
