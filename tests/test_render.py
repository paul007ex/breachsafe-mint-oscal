# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Tests for the output serializer (:mod:`mint_oscal.render`).

JSON and YAML are native; XML is delegated to oscal-cli. The YAML cases guard the traps that
make a naive dump wrong: shared child mappings (which must not become anchors/aliases) and
YAML 1.1 scalar ambiguities (``no``/``yes``/``007``/timestamp-like strings must stay strings).
"""

from __future__ import annotations

import json

import pytest
import yaml

from mint_oscal.render import render

# A shared child mapping reused by two observations: the default dumper would emit it as a YAML
# anchor/alias, so this is the alias trap.
_SHARED_SUBJECT = {"subject-uuid": "11111111-1111-5111-8111-111111111111", "type": "inventory-item"}

# A document whose string values hit YAML 1.1 resolver traps: ``no`` (bool), ``007`` (int/octal),
# a timestamp-like scalar, unicode, embedded newline/colon, and a long scalar (line-wrap trap).
_DOC = {
    "plan-of-action-and-milestones": {
        "uuid": "00000000-0000-5000-8000-000000000000",
        "metadata": {
            "title": "no",
            "last-modified": "2026-07-28T15:00:12+00:00",
            "version": "007",
            "oscal-version": "1.2.2",
        },
        "observations": [
            {
                "uuid": "22222222-2222-5222-8222-222222222222",
                "description": "line1\nline2 café ✅ key: value # not-a-comment",
                "methods": ["TEST"],
                "collected": "2026-07-28T15:00:12+00:00",
                "subjects": [_SHARED_SUBJECT],
            },
            {
                "uuid": "33333333-3333-5333-8333-333333333333",
                "description": "x" * 5000,
                "methods": ["TEST"],
                "collected": "2026-07-28T15:00:12+00:00",
                "subjects": [_SHARED_SUBJECT],
            },
        ],
    }
}


def test_json_is_native() -> None:
    assert json.loads(render(_DOC, fmt="json")) == _DOC


def test_yaml_round_trips_to_the_same_document() -> None:
    # OSCAL YAML is the JSON data model in YAML syntax: reloading must reproduce the document.
    assert yaml.safe_load(render(_DOC, fmt="yaml")) == _DOC


def test_yaml_is_deterministic() -> None:
    assert render(_DOC, fmt="yaml") == render(_DOC, fmt="yaml")


def test_yaml_emits_no_anchors_or_aliases_for_shared_mappings() -> None:
    out = render(_DOC, fmt="yaml")
    assert "&id" not in out
    assert " *id" not in out


def test_yaml_keeps_scalar_traps_as_strings() -> None:
    md = yaml.safe_load(render(_DOC, fmt="yaml"))["plan-of-action-and-milestones"]["metadata"]
    assert md["title"] == "no"
    assert md["version"] == "007"
    assert md["last-modified"] == "2026-07-28T15:00:12+00:00"


def test_yaml_does_not_wrap_long_scalars() -> None:
    # A wrapped scalar would fold to a different value; a long line must survive intact.
    out = render(_DOC, fmt="yaml")
    assert "x" * 5000 in out


@pytest.mark.parametrize("fmt", ["xml", "toml", ""])
def test_unsupported_format_raises_value_error(fmt: str) -> None:
    # Only json and yaml are supported; anything else (xml included) is not a format mint emits.
    with pytest.raises(ValueError, match="unknown output format"):
        render(_DOC, fmt=fmt)
