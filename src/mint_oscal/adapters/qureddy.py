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


def _list(value: Any, where: str) -> list[Any]:  # noqa: ANN401
    """Return ``value`` if it is a list, else raise a typed error naming the field."""
    if not isinstance(value, list):
        raise MalformedScanError(
            f"malformed qureddy.scan.v1: {where} must be a list, got {type(value).__name__}"
        )
    return value


def _dict(value: Any, where: str) -> dict[str, Any]:  # noqa: ANN401
    """Return ``value`` if it is an object, else raise a typed error naming the field."""
    if not isinstance(value, dict):
        raise MalformedScanError(
            f"malformed qureddy.scan.v1: {where} must be an object, got {type(value).__name__}"
        )
    return value


def _str(value: Any, where: str) -> str:  # noqa: ANN401
    """Return ``value`` if it is a string, else raise a typed error naming the field.

    Guards untrusted values before they are used as mapping keys (``by_id``,
    ``crosswalk``): a list/dict there would leak a bare ``TypeError: unhashable type``.
    """
    if not isinstance(value, str):
        raise MalformedScanError(
            f"malformed qureddy.scan.v1: {where} must be a string, got {type(value).__name__}"
        )
    return value


def _index_evidence(evidence: Any) -> dict[str, Any]:  # noqa: ANN401
    """Index evidence records by ``id``, asserting the shape of untrusted input.

    ``evidence`` must be a list of objects, each carrying an ``id``; anything else
    fails with one typed :class:`MalformedScanError` naming the offending field,
    never a bare ``KeyError``/``TypeError`` leaking through the CLI boundary.
    """
    if not isinstance(evidence, list):
        raise MalformedScanError(
            f"malformed qureddy.scan.v1: 'evidence' must be a list, got {type(evidence).__name__}"
        )
    by_id: dict[str, Any] = {}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise MalformedScanError(
                f"malformed qureddy.scan.v1: evidence[{index}] must be an object, "
                f"got {type(item).__name__}"
            )
        item_id = _require(item, "id", f"evidence[{index}].id")
        # ``id`` becomes a dict key below, so it must be a hashable scalar: a list/dict here
        # would otherwise leak a bare ``TypeError: unhashable type`` (the #48 guard only
        # asserts the item is an object, not that its ``id`` is usable as a key).
        by_id[_str(item_id, f"evidence[{index}].id")] = item
    return by_id


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
        # id flows into the emitter's uuid5 "|".join(...); a non-str would leak a bare
        # TypeError there, so type-guard it here (like ``readiness`` below) into a typed error.
        id=_str(_require(target, "locator", "target.locator"), "target.locator"),
        kind="inventory-item",
        description=(
            f"{target.get('scheme', 'tls')} endpoint "
            f"{_require(target, 'host', 'target.host')}:{_require(target, 'port', 'target.port')}"
        ),
    )
    scan = _require(document, "scan", "scan")
    if not isinstance(scan, dict):
        raise MalformedScanError("malformed qureddy.scan.v1: 'scan' must be an object")
    # Type-guard like its siblings: a non-string completed_at flows into Finding.observed_at
    # then datetime.fromisoformat(), whose TypeError (not a ValueError) escapes the adapter's
    # domain-error boundary and is mislabeled exit 70 internal_error instead of exit 2
    # malformed_input -- the exit code would lie about whose fault the bad input is (#82).
    collected = _str(_require(scan, "completed_at", "scan.completed_at"), "scan.completed_at")
    evidence_by_id = _index_evidence(document.get("evidence", []))

    findings: list[Finding] = []
    for finding in _list(document.get("findings", []), "findings"):
        if not isinstance(finding, dict):
            raise MalformedScanError("malformed qureddy.scan.v1: each finding must be an object")
        # ``readiness`` flows into controls_for/risk_statement, which use it as a crosswalk
        # key; a dict there would leak a bare ``TypeError: unhashable type``.
        readiness = _str(finding.get("readiness", ""), "findings[].readiness")
        title = _require(finding, "title", "findings[].title")
        findings.append(
            Finding(
                # id flows into the emitter's uuid5 "|".join(...); guard it to a typed error.
                id=_str(_require(finding, "id", "findings[].id"), "findings[].id"),
                title=title,
                description=finding.get("description", title),
                severity=_require(finding, "severity", "findings[].severity"),
                status=_status(finding),
                subject=subject,
                observed_at=collected,
                control_ids=controls_for(readiness),
                risk_statement=risk_statement(readiness),
                evidence=tuple(_evidence(evidence_by_id, finding.get("evidence_ids", []))),
                posture=_posture(finding),
            )
        )
    return findings, subject


def _status(finding: dict[str, Any]) -> str:
    """Derive the OSCAL risk status (``open``|``closed``) the scan reports for a finding.

    A finding the scanner marks remediated/closed mints a CLOSED risk, not a hardcoded open
    one, so a resolved finding is no longer published as an open POA&M risk (#83). This is what
    makes the emitter's status pass-through (poam.py) live. Any other/absent/non-string value
    falls back to ``open`` -- the honest default (an unresolved finding), never a crash.
    """
    if finding.get("remediated") is True or finding.get("status") == "closed":
        return "closed"
    return "open"


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


def _evidence(by_id: dict[str, Any], evidence_ids: Any) -> list[Evidence]:  # noqa: ANN401
    """Build IR evidence from the referenced probe results (hashes only, never excerpts).

    ``evidence_ids`` is untrusted: a scalar there (instead of a list) or an unhashable
    element (list/dict) would leak a bare ``TypeError``, and a non-object ``probe_result``
    a bare ``AttributeError`` -- each becomes one typed :class:`MalformedScanError` instead.
    """
    out: list[Evidence] = []
    for evidence_id in _list(evidence_ids, "findings[].evidence_ids"):
        record = by_id.get(_str(evidence_id, "findings[].evidence_ids[]"), {})
        probe = _dict(record.get("probe_result") or {}, "evidence[].probe_result")
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
