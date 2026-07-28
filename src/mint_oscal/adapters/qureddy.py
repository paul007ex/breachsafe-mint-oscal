# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Adapter: QuReddy ``qureddy.scan.v1`` JSON -> the neutral IR.

QuReddy's JSON is the richest source for findings (the CBOM carries the same
posture but hashes rather than raw evidence). This adapter is the only place that
knows QuReddy's field names; everything downstream sees only the IR.
"""

from __future__ import annotations

from typing import Any

from mint_oscal.controls.nist import controls_for, risk_statement
from mint_oscal.ir import Evidence, Finding, Subject


class MalformedScanError(ValueError):
    """The input is not a well-shaped ``qureddy.scan.v1`` document.

    A domain error (not ``SystemExit``): the caller decides how to surface it. Mirrors
    :class:`mint_oscal.adapters.cbom.MalformedCbomError` so a shapeless scan fails loudly
    with a clear message instead of leaking a bare ``KeyError``/``TypeError``.
    """


def _require(container: dict[str, Any], key: str, where: str) -> Any:  # noqa: ANN401
    """Return ``container[key]`` or raise a typed error naming the missing field."""
    if key not in container:
        raise MalformedScanError(f"malformed qureddy.scan.v1: missing {where!r}")
    return container[key]


def from_scan_v1(document: dict[str, Any]) -> tuple[list[Finding], Subject]:
    """Convert one ``qureddy.scan.v1`` document into IR findings and their subject.

    Raises:
        MalformedScanError: if ``document`` is not a well-shaped scan envelope.
    """
    # qureddy JSON is untrusted input, so assert the envelope shape ourselves: a shapeless
    # dict (or a list/scalar) must fail with one typed domain error, never a bare
    # KeyError/TypeError that would leak through the CLI boundary as a traceback.
    if not isinstance(document, dict):
        raise MalformedScanError(
            f"malformed qureddy.scan.v1: expected a JSON object, got {type(document).__name__}"
        )
    target = _require(document, "target", "target")
    if not isinstance(target, dict):
        raise MalformedScanError("malformed qureddy.scan.v1: 'target' must be an object")
    subject = Subject(
        id=_require(target, "locator", "target.locator"),
        kind="inventory-item",
        description=(
            f"{target.get('scheme', 'tls')} endpoint "
            f"{_require(target, 'host', 'target.host')}:{_require(target, 'port', 'target.port')}"
        ),
    )
    scan = _require(document, "scan", "scan")
    if not isinstance(scan, dict):
        raise MalformedScanError("malformed qureddy.scan.v1: 'scan' must be an object")
    collected = _require(scan, "completed_at", "scan.completed_at")
    evidence_by_id = {item["id"]: item for item in document.get("evidence", [])}

    findings: list[Finding] = []
    for finding in document.get("findings", []):
        if not isinstance(finding, dict):
            raise MalformedScanError("malformed qureddy.scan.v1: each finding must be an object")
        readiness = finding.get("readiness", "")
        title = _require(finding, "title", "findings[].title")
        findings.append(
            Finding(
                id=_require(finding, "id", "findings[].id"),
                title=title,
                description=finding.get("description", title),
                severity=_require(finding, "severity", "findings[].severity"),
                status="open",
                subject=subject,
                observed_at=collected,
                control_ids=controls_for(readiness),
                risk_statement=risk_statement(readiness),
                evidence=tuple(_evidence(evidence_by_id, finding.get("evidence_ids", ()))),
                posture=_posture(finding),
            )
        )
    return findings, subject


def _posture(finding: dict[str, Any]) -> dict[str, str]:
    """Extract structured crypto-posture facts a scan finding may carry.

    Every field is optional; only non-empty values are kept. Scan key names are
    mapped to their OSCAL prop names (``cert_signature`` -> ``cert-signature``).
    """
    facts = {
        "readiness": finding.get("readiness", ""),
        "algorithm": finding.get("algorithm", ""),
        "nistQuantumSecurityLevel": finding.get("nistQuantumSecurityLevel", ""),
        "cert-signature": finding.get("cert_signature", ""),
    }
    return {name: str(value) for name, value in facts.items() if value}


def _evidence(by_id: dict[str, Any], evidence_ids: tuple[str, ...]) -> list[Evidence]:
    """Build IR evidence from the referenced probe results (hashes only, never excerpts)."""
    out: list[Evidence] = []
    for evidence_id in evidence_ids:
        record = by_id.get(evidence_id, {})
        probe = record.get("probe_result") or {}
        props = {
            "observation_type": record.get("observation_type", ""),
            "stdout_sha256": probe.get("stdout_sha256", ""),
            "return_code": str(probe.get("return_code", "")),
        }
        out.append(
            Evidence(
                description=(
                    f"{record.get('source', 'probe')} ({record.get('observation_type', '')})"
                ),
                props={key: value for key, value in props.items() if value},
            )
        )
    return out
