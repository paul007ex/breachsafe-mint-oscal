# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Tests for shared CLI presentation and plugin discovery helpers."""

from __future__ import annotations

import pytest

from mint_oscal._help import colorize_help
from mint_oscal._registry import discover, load_builtin, resolve


def test_colorize_help_covers_line_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    text = "HEADER:\n  # note\n  mint-oscal poam\n0  ok\n70  internal\nVAR_NAME  value\nplain"
    colored = colorize_help(text)
    assert "\033[1;36mHEADER:" in colored
    assert "\033[2m# note" in colored
    assert "\033[1;32mmint-oscal" in colored
    assert "\033[1;32m0" in colored
    assert "\033[1;31m70" in colored
    assert "\033[1;35mVAR_NAME" in colored


def test_colorize_help_honors_no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert colorize_help("HEADER:\n") == "HEADER:\n"
    monkeypatch.delenv("NO_COLOR")
    assert "\033[" in colorize_help("HEADER:\n")


def test_plugin_registry_builtin_and_unknown_paths() -> None:
    builtin = {"demo": "mint_oscal.render:render"}
    assert load_builtin(builtin["demo"]).__name__ == "render"
    assert resolve("missing-group", builtin, "demo", "adapter", ["demo"]).__name__ == "render"
    with pytest.raises(KeyError, match="unknown adapter"):
        resolve("missing-group", builtin, "nope", "adapter", ["demo"])
    assert "demo" in discover("missing-group", builtin)
