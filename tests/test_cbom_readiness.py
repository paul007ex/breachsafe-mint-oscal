# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Focused tests for CBOM readiness classification helpers."""

from __future__ import annotations

from mint_oscal.ingestion.cbom_readiness import classify_algorithm, derive_readiness


def test_classify_algorithm_prefers_declared_level() -> None:
    assert classify_algorithm("ML-KEM", "kem", 3, {}) == (True, True, 3, False)


def test_classify_algorithm_uses_registry_fallback() -> None:
    registry = {"X25519": {"kind": "kex", "quantum_safe": False, "nistLevel": 0}}
    assert classify_algorithm("x25519", None, None, registry) == (True, False, 0, False)


def test_classify_algorithm_marks_unknown_non_kex_unclassified() -> None:
    assert classify_algorithm("mystery", "unknown", None, {}) == (False, None, 0, True)


def test_derive_readiness_handles_all_some_none_and_unknown() -> None:
    rules = [
        {"readiness": "quantum_ready", "kex_quantum_safe": "all", "kex_classical": "none"},
        {"readiness": "quantum_vulnerable", "kex_quantum_safe": "none", "kex_classical": "all"},
    ]
    assert derive_readiness([True], [], rules) == "quantum_ready"
    assert derive_readiness([False], [], rules) == "quantum_vulnerable"
    assert derive_readiness([], [], rules) == "unknown"
