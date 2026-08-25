#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 BreachSAFE
#
# Run the complete local BreachSAFE Mint-OSCAL verification flow.
# This intentionally mirrors the blocking CI gates and ends with the independent
# oscal-cli/Trestle conformance gate.

set -Eeuo pipefail

MODE="clean"
case "${1:-}" in
  "") ;;
  --clean) ;;
  --in-place) MODE="in-place" ;;
  -h|--help)
    printf 'Usage: %s [--clean|--in-place]\n\n' "${BASH_SOURCE[0]}"
    printf '%s\n' \
      '--clean      (default) archive HEAD into a temporary clean directory and run there' \
      '--in-place   run against the current checkout, including uncommitted changes'
    exit 0
    ;;
  *)
    printf 'error: unknown option: %s\n' "$1" >&2
    exit 2
    ;;
esac

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$MODE" == "clean" ]]; then
  CLEAN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mint-oscal-gates.XXXXXX")"
  cleanup() {
    rm -rf -- "$CLEAN_DIR"
  }
  trap cleanup EXIT INT TERM
  git -C "$ROOT_DIR" archive --format=tar HEAD | tar -xf - -C "$CLEAN_DIR"
  bash "$CLEAN_DIR/scripts/run-all-gates.sh" --in-place
  exit $?
fi

cd "$ROOT_DIR"

ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mint-oscal-artifacts.XXXXXX")"
cleanup_artifacts() {
  rm -rf -- "$ARTIFACT_DIR"
}
trap cleanup_artifacts EXIT INT TERM

run() {
  printf '\n+==> %s\n' "$*"
  "$@"
}

printf 'Mint-OSCAL full verification\nroot: %s\nmode: %s\npython: %s\n' \
  "$ROOT_DIR" "$MODE" "$(uv run --python 3.14 --locked python --version)"

# Static quality gates (kept in the same order as .github/workflows/ci.yml).
run uv run --python 3.14 --locked ruff -v check .
run uv run --python 3.14 --locked python scripts/validate_process_contract.py
run uv run --python 3.14 --locked ruff -v format --check .
run uv run --python 3.14 --locked mypy src --strict --verbose
run uv run --python 3.14 --locked lint-imports --verbose
run uv run --python 3.14 --locked bandit -r -ll -v src
run uv run --python 3.14 --locked pip-audit -v
run uv run --python 3.14 --locked deptry . --verbose \
  --optional-dependencies-dev-groups dev \
  --known-first-party mint_oscal \
  --per-rule-ignores DEP002=compliance-trestle
run uvx --from 'reuse[charset-normalizer]' reuse lint
run uv run --python 3.14 --locked xenon \
  --max-absolute B --max-modules A --max-average A src/mint_oscal
run uv run --python 3.14 --locked refurb --verbose src/mint_oscal
run uv run --python 3.14 --locked vulture src/mint_oscal --min-confidence 80 --verbose
run uv run --python 3.14 --locked pylint \
  --disable=all --enable=duplicate-code --verbose src/mint_oscal
run npx --yes jscpd@4 --threshold 0.5 --reporters time,console src tests
run uv run --python 3.14 --locked interrogate -v src/mint_oscal

# Full tests and repository-specific integrity checks.
run uv run --python 3.14 --locked pytest -vv \
  --cov=mint_oscal --cov-report=term-missing --cov-fail-under=90
run uv run --python 3.14 --locked python scripts/check_registry_drift.py \
  --registry examples/registry

# Build and inspect distributable artifacts. The leak guard prevents internal tooling
# from accidentally entering the wheel or source distribution.
run uvx --from build pyproject-build -v --outdir "$ARTIFACT_DIR"
run uv run --python 3.14 --locked python scripts/leak_guard.py "$ARTIFACT_DIR"

# Independent standards oracle: this invokes oscal-cli 3.2.0 and Trestle 5.0.0,
# including positive and negative POA&M/Profile controls and Profile resolution.
# Keep the oracle output structured; shell tracing is intentionally not enabled here.
run bash scripts/oscal-conformance.sh

printf '\nALL GATES PASSED\n'
