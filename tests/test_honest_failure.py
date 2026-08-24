# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Regression tests for malformed-input and missing-link-href boundaries."""

from __future__ import annotations

from mint_oscal.cli import main
from mint_oscal.validation.engine import semantic_errors


def _base() -> dict[str, object]:
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


def test_link_without_href_is_rejected() -> None:
    document = _base()
    item = document["plan-of-action-and-milestones"]["poam-items"][0]  # type: ignore[index]
    item["links"] = [{"rel": "reference"}]  # type: ignore[index]
    assert any("link" in error and "href" in error for error in semantic_errors(document))


def test_non_utf8_generate_exits_as_input_error(tmp_path) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\x00\xff garbage")
    assert main(["poam", "generate", "--from", "cbom", str(bad)]) == 2
    assert main(["poam", "generate", "--from", "qureddy", str(bad)]) == 2


def test_non_utf8_validate_exits_as_input_error(tmp_path) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\x00\xff garbage")
    assert main(["poam", "validate", str(bad)]) == 2
