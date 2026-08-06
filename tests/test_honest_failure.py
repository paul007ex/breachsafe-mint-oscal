# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Honest-failure boundary regression guards (real-data pressure-test findings).

- #121: a non-UTF-8 (binary) input is malformed *input* (exit 2), not an internal fault (70).
- #118: the Layer-2 validator requires ``href`` on every OSCAL ``link``.
"""

from __future__ import annotations

from mint_oscal.cli import main
from mint_oscal.validate import semantic_errors

_EXIT_INPUT = 2


def _base() -> dict:
    """A minimal POA&M that passes every Layer-2 check, carrying one link."""
    return {
        "plan-of-action-and-milestones": {
            "uuid": "00000000-0000-5000-8000-000000000001",
            "metadata": {
                "title": "t",
                "last-modified": "2026-01-01T00:00:00+00:00",
                "version": "0.1.0",
                "oscal-version": "1.2.2",
            },
            "poam-items": [
                {
                    "uuid": "00000000-0000-5000-8000-000000000002",
                    "title": "i",
                    "description": "d",
                    "links": [{"href": "catalog.json#x", "rel": "reference"}],
                }
            ],
        }
    }


def test_base_poam_passes_layer2() -> None:
    assert semantic_errors(_base()) == []


def test_link_missing_href_is_caught() -> None:
    d = _base()
    d["plan-of-action-and-milestones"]["poam-items"][0]["links"][0].pop("href")
    errs = semantic_errors(d)
    assert any("link" in e and "href" in e for e in errs), errs


def test_non_utf8_generate_exits_2(tmp_path) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\x00\xff garbage")
    assert main(["poam", "generate", "--from", "cbom", str(bad)]) == _EXIT_INPUT
    assert main(["poam", "generate", "--from", "qureddy", str(bad)]) == _EXIT_INPUT


def test_non_utf8_validate_exits_2(tmp_path) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\x00\xff garbage")
    assert main(["poam", "validate", str(bad)]) == _EXIT_INPUT
