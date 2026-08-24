# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Executable coverage for the public conversion and validation paths."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mint_oscal import convert
from mint_oscal.adapters.cbom import MalformedCbomError, from_cbom
from mint_oscal.adapters.qureddy import MalformedScanError, from_scan_v1
from mint_oscal.emitters.poam import to_poam
from mint_oscal.extensions.breachsafe import enrich
from mint_oscal.ir import IR, Evidence, Finding, Subject
from mint_oscal.policy import active_policy, get_policy, set_active_framework
from mint_oscal.render import render
from mint_oscal.validate import semantic_errors

ROOT = Path(__file__).parents[1]


def _cbom() -> dict[str, object]:
    return json.loads((ROOT / "examples/example.cbom.json").read_text(encoding="utf-8"))


def _finding(status: str = "open") -> Finding:
    subject = Subject("example.com:443", "inventory-item", "example endpoint")
    return Finding(
        id="finding-1",
        title="PQC posture",
        description="fixture finding",
        severity="high",
        status=status,
        subject=subject,
        observed_at="2026-08-24T12:00:00+00:00",
        control_ids=("qts-04",),
        risk_statement="migration required",
        evidence=(Evidence("TLS probe", {"sha256": "a" * 64}),),
        posture={"readiness": "quantum_vulnerable", "mapping-confidence": "high"},
    )


def test_cbom_adapter_and_poam_round_trip() -> None:
    findings, subject = from_cbom(_cbom())
    document = to_poam(findings, subject, source="CBOM")
    assert document["plan-of-action-and-milestones"]["poam-items"]
    assert semantic_errors(document) == []
    assert json.loads(render(document, fmt="json")) == document


def test_cbom_rejects_bad_envelopes() -> None:
    with pytest.raises(MalformedCbomError):
        from_cbom({})
    bad = copy.deepcopy(_cbom())
    bad["specVersion"] = "0.1"
    with pytest.raises(MalformedCbomError):
        from_cbom(bad)


def test_qureddy_adapter_rejects_bad_input() -> None:
    with pytest.raises(MalformedScanError):
        from_scan_v1({})
    with pytest.raises(MalformedScanError):
        from_scan_v1({"target": {"locator": "x", "host": "x", "port": 443}})


def test_emitter_handles_empty_and_closed_findings() -> None:
    subject = Subject("ready.example", "inventory-item", "ready endpoint")
    empty = to_poam([], subject, source="CBOM", now="2026-08-24T00:00:00Z")
    assert empty["plan-of-action-and-milestones"]["poam-items"][0]["title"] == "No findings"
    closed = to_poam([_finding("closed")], subject, source="CBOM")
    assert closed["plan-of-action-and-milestones"]["risks"][0]["status"] == "closed"


def test_extension_provenance_and_evidence() -> None:
    finding = _finding()
    document = {
        "metadata": {
            "properties": [{"name": "qureddy:scan.readiness", "value": "quantum_vulnerable"}]
        }
    }
    findings, _ = enrich([finding], finding.subject, document=document)
    assert findings[0].posture["provenance"] == "producer-confirmed"
    assert findings[0].evidence == finding.evidence


def test_policy_switch_and_convert() -> None:
    set_active_framework("nist")
    assert active_policy().framework
    assert get_policy("default").severity
    ir = IR((_finding(),), _finding().subject, "cbom")
    assert "plan-of-action-and-milestones" in convert(ir, shape="poam")
    set_active_framework("scf-qts")


def test_semantic_errors_are_fail_closed() -> None:
    document = to_poam([_finding()], _finding().subject, source="CBOM")
    body = document["plan-of-action-and-milestones"]
    body["poam-items"][0]["related-risks"][0]["risk-uuid"] = "missing"
    assert any("unresolved risk-uuid" in error for error in semantic_errors(document))
