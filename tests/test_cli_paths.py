# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Exercise the CLI boundary in-process so coverage includes its error contracts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mint_oscal.cli import main

ROOT = Path(__file__).parents[1]
CBOM = str(ROOT / "examples/example.cbom.json")


def _invoke(argv: list[str]) -> int:
    """Call argparse-backed main and normalize its documented SystemExit paths."""
    try:
        return main(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 70


@pytest.mark.parametrize(
    "argv",
    [
        ["--version"],
        ["-V"],
        ["--help"],
        ["help"],
        ["poam", "--help"],
        ["poam", "generate", "--help"],
        ["poam", "validate", "--help"],
        ["registry", "--help"],
    ],
)
def test_help_paths(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert _invoke(argv) == 0
    captured = capsys.readouterr()
    assert captured.out or captured.err


def test_no_args_and_incomplete_model(capsys: pytest.CaptureFixture[str]) -> None:
    assert _invoke([]) == 0
    assert _invoke(["poam"]) == 0
    assert "usage" in capsys.readouterr().err.lower()


@pytest.mark.parametrize(
    "argv",
    [
        ["poam", "generate", "--from", "cbom", CBOM],
        ["poam", "generate", "--from", "cbom", CBOM, "--validate"],
        ["poam", "generate", "--from", "cbom", CBOM, "--extension", "breachsafe"],
        ["poam", "generate", "--from", "cbom", CBOM, "--verbose"],
        ["poam", "generate", "--from", "cbom", CBOM, "--quiet"],
        ["poam", "generate", "--from", "cbom", CBOM, "--json-logs"],
    ],
)
def test_generate_paths(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["plan-of-action-and-milestones"]


@pytest.mark.parametrize(
    "argv",
    [
        ["poam", "generate", "--from", "nope", CBOM],
        ["poam", "generate", "--from", "cbom"],
        ["poam", "generate", "--from", "cbom", CBOM, "--to", "toml"],
        ["poam", "generate", "--from", "cbom", CBOM, "--extension", "nope"],
        ["poam", "generate", "--from", "cbom", "/missing/input.json"],
    ],
)
def test_usage_and_input_errors(argv: list[str]) -> None:
    assert _invoke(argv) in {2, 4}


def test_render_and_planned_model_paths() -> None:
    assert _invoke(["poam", "generate", "--from", "cbom", CBOM, "--to", "xml"]) == 4
    assert _invoke(["poam", "generate", "--from", "cbom", CBOM, "--to", "yaml"]) == 0
    assert _invoke(["ar", "generate", "--from", "cbom", CBOM]) == 3


def test_validate_paths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(
        json.dumps(json.loads(Path(CBOM).read_text(encoding="utf-8"))), encoding="utf-8"
    )
    # A CBOM is input, not an OSCAL POA&M, so this exercises the input boundary.
    assert main(["poam", "validate", str(valid)]) == 2
    broken = tmp_path / "broken.json"
    broken.write_text("not-json", encoding="utf-8")
    assert main(["poam", "validate", str(broken)]) == 2
    assert capsys.readouterr().err


def test_registry_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path = tmp_path / "registry"
    shutil.copytree(ROOT / "examples/registry", registry_path)
    registry = str(registry_path)
    assert main(["registry", "validate", "--registry", registry]) == 0
    assert main(["registry", "list", "--registry", registry, "--json"]) == 0
    assert main(["registry", "show", "nist-800-53r5", "--registry", registry]) == 0
    assert main(["registry", "lock", "--registry", registry]) == 0
    assert main(["registry", "verify", "--registry", registry]) == 0
    assert main(["registry", "show", "missing", "--registry", registry]) == 2
    assert "unknown Catalog" in capsys.readouterr().err


def test_registry_verbose_logging_reports_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_path = tmp_path / "registry"
    shutil.copytree(ROOT / "examples/registry", registry_path)

    assert main(["registry", "validate", "--registry", str(registry_path), "--verbose"]) == 0
    assert "registry_loaded" in capsys.readouterr().err
