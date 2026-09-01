# BreachSAFE Mint-OSCAL contributor instructions

Repository policy for `breachsafe-mint-oscal` (`paul007ex/breachsafe-mint-oscal`). Read this
first. The executable agent card is [AGENTS.md](AGENTS.md): it carries the numbered ten-step
loop and the handoff format. Read it before any non-trivial change. The parent-checkout
platform policy (`~/claude/CLAUDE.md`) remains authoritative for cross-repo and safety rules;
record any deliberate repo exception here.

## Contents

1. [What mint-oscal is](#what-mint-oscal-is)
2. [Source layout](#source-layout)
3. [CLI entry point](#cli-entry-point)
4. [Fast gates](#fast-gates)
5. [Runtime and licence](#runtime-and-licence)
6. [Review and merge discipline](#review-and-merge-discipline)
7. [Verification](#verification)

## What mint-oscal is

`mint-oscal` converts security-tool findings into NIST OSCAL documents. It is a producer, not
a validator: findings in, OSCAL out, ready to hand to `oscal-cli`. The design is an agnostic
core, `N sources → neutral IR (mint.ir.v1) → M OSCAL shapes`. The core knows only the IR and
OSCAL. Source formats are handled by optional edge adapters registered as entry points, or a
source emits the published `mint.ir.v1` contract directly. POA&M is the shipped emitter
(prototype, `oscal-cli`-validated); the `ar` (Assessment Results) emitter is a stub that exits
`3`. Documents declare `oscal-version` 1.2.2.

## Source layout

`src/mint_oscal/` holds the package. `cli.py` is a thin wrapper over the library `convert`;
the `import-linter` contract in `pyproject.toml` forbids `cli` from leaking into the domain
core (`ir`, `adapters`, `emitters`, `policy`).

| Path | Holds |
| --- | --- |
| `ir/` | Neutral IR: `model.py` plus `mint.ir.v1.schema.json`, the published contract |
| `adapters/` | Edge source adapters. `qureddy.py`, `cbom.py`. Plugin surface, see below |
| `extensions/` | Opt-in enrichers that refine the IR from producer facts (`breachsafe`). Not a `--from` source |
| `emitters/` | OSCAL shape emitters: `poam.py` (shipped), `ar.py` (stub, exit 3) |
| `policy/` | Control frameworks and crosswalks: `default`, `scf_qts` |
| `registry.py`, `_registry.py`, `governance/` | Governed registry: Catalog pins, packs, Profiles, lock/verify |
| `controls/`, `ingestion/`, `validate.py`, `validation/`, `render.py`, `schemas/` | Control text, source ingestion, in-process Layer-2 checks, JSON rendering, bundled schemas |

Adapters and extensions are registered plugins, wired in `pyproject.toml`:

- `[project.entry-points."mint_oscal.adapters"]`: `qureddy`, `cbom` (selected with `--from`).
- `[project.entry-points."mint_oscal.extensions"]`: `breachsafe` (bundled cross-check, ADR-0008).

## CLI entry point

`mint-oscal = mint_oscal.cli:main` (from `pyproject.toml` `[project.scripts]`). Run it through
`uv`:

```bash
uv run --python 3.14 --locked mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json
uv run --python 3.14 --locked mint-oscal registry --help
```

`--framework` selects the crosswalk: `scf-qts` (default, PQC-native SCF Quantum Security) or
`nist` (SP 800-53r5). Full flag reference: [docs/reference/cli.md](docs/reference/cli.md).

## Fast gates

No `Justfile`. The gate scripts live in `scripts/`; the individual gate commands are:

```bash
uv run --python 3.14 --locked pytest -q
uv run --python 3.14 --locked ruff check .
uv run --python 3.14 --locked ruff format --check .
uv run --python 3.14 --locked mypy src --strict
uv run --python 3.14 --locked bandit -c pyproject.toml -r src
uv run --python 3.14 --locked pip-audit
bash scripts/oscal-conformance.sh
uv run --python 3.14 --locked python scripts/check_registry_drift.py --registry examples/registry
```

`bash scripts/run-all-gates.sh` runs the complete local flow (it archives HEAD into a clean
temporary directory by default; `--in-place` runs against the working tree). Other scripts:
`regression.sh`, `check_docs.py`, `leak_guard.py`, `validate_process_contract.py`. The CI
workflows are authoritative for the full MAX gate set: `.github/workflows/ci.yml`,
`conformance.yml`, `codeql.yml`. A green command that did not execute the required scope is not
evidence.

## Runtime and licence

- **Runtime:** Python 3.14+ (`requires-python = ">=3.14"`, `.python-version` is `3.14`). Do not
  add a fallback below 3.14.
- **Licence:** PolyForm-Noncommercial-1.0.0. This is the platform default, not a carve-out.
  The full text is `LICENSES/PolyForm-Noncommercial-1.0.0.txt`; `LICENSE` is the root copy.
  Markdown and other non-code files are licensed in bulk by `REUSE.toml` (`**/*.md`), so
  no per-file SPDX header is added to prose. Source files carry per-file headers. Run
  `reuse lint` after any licensing change. `AGENTS.md` and `CLAUDE.md` are repository
  governance and are excluded from the sdist.

## Review and merge discipline

Review pull requests one at a time against the current `main` branch. Do not stack PRs,
merge a dependent branch, or review an old branch against another feature branch. Before each
decision, refresh `main`, inspect the PR diff against `main`, and merge or reject that PR before
starting the next one. If a PR is stale or conflicts, update that PR branch or close it; do not
hide the conflict by stacking another PR on top.

## Verification

For each PR, record the exact PR number, base/head, mergeability, changed files, required checks,
and local quality-gate results. A green check run is evidence for that PR only; it does not
transfer to another PR. After merging, refresh `main` and verify the merged tree before reviewing
the next PR.
