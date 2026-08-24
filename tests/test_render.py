# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Tests for native JSON/YAML serialization."""

from __future__ import annotations

import json

import pytest
import yaml

from mint_oscal.render import render

DOCUMENT = {
    "plan-of-action-and-milestones": {
        "uuid": "00000000-0000-5000-8000-000000000000",
        "metadata": {
            "title": "no",
            "last-modified": "2026-07-28T15:00:12+00:00",
            "version": "007",
            "oscal-version": "1.2.2",
        },
        "observations": [
            {"description": "line1\nline2 café ✅ key: value # text"},
            {"description": "x" * 5000},
        ],
    }
}


def test_json_round_trips() -> None:
    assert json.loads(render(DOCUMENT, fmt="json")) == DOCUMENT


def test_yaml_round_trips() -> None:
    assert yaml.safe_load(render(DOCUMENT, fmt="yaml")) == DOCUMENT


def test_yaml_is_deterministic_and_alias_free() -> None:
    first = render(DOCUMENT, fmt="yaml")
    assert first == render(DOCUMENT, fmt="yaml")
    assert "&id" not in first
    assert " *id" not in first


def test_yaml_preserves_scalar_traps_and_long_values() -> None:
    loaded = yaml.safe_load(render(DOCUMENT, fmt="yaml"))
    metadata = loaded["plan-of-action-and-milestones"]["metadata"]
    assert metadata["title"] == "no"
    assert metadata["version"] == "007"
    assert metadata["last-modified"] == "2026-07-28T15:00:12+00:00"
    assert "x" * 5000 in render(DOCUMENT, fmt="yaml")


def test_xml_is_a_usage_error() -> None:
    with pytest.raises(ValueError, match="json, yaml"):
        render(DOCUMENT, fmt="xml")
