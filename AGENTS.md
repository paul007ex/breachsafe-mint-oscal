# BreachSAFE Mint-OSCAL agent card

## Contents

1. [Authority](#authority)
2. [Ten-step loop](#ten-step-loop)
3. [Fast gates](#fast-gates)
4. [Handoff](#handoff)

## Authority

Read [CLAUDE.md](CLAUDE.md) first. It is the repository policy and points to the parent
checkout policy in `~/claude/AGENTS.md`. Use the applicable BreachSAFE skills from
`breachsafe-common`:

- `breachsafe-quality-review` for diff, issue-resolution, documentation-drift, and
  anti-pattern review.
- `breachsafe-oscal-conformance` for OSCAL/Trestle/oscal-cli validation.
- `breachsafe-release` for supply-chain and package/release readiness.
- `breachsafe-implement` (when available) for implementation sequencing and tests.

The repository's Python baseline is 3.14. Do not bypass a failing gate or treat a skipped
command as evidence.

## Ten-step loop

1. **Inventory:** Read repository/parent policy, issue, tree, and applicable skills.
2. **Steelman:** State the strongest case and smallest defensible fix.
3. **Isolated reproduction:** Reproduce in a fresh temporary workstream before editing.
4. **Pressure test:** Exercise alternatives, malformed input, compatibility, failure paths, and regressions.
5. **Surgical implementation:** Make the smallest contract-preserving change.
6. **Regression tests:** Add tests that fail before the fix and cover acceptance criteria.
7. **Quality gates:** Run build, lint, type, security, test, and release gates with real exit codes.
8. **Architecture review:** Inspect ownership, dependencies, duplication, size, logging, errors, and extensibility.
9. **Issue/Git workflow:** Refresh `main`, use one PR at a time, record evidence, and verify after merge.
10. **Release verification:** Independently validate package, provenance/signatures when applicable, and real CLI smoke paths.

If a step is not applicable or cannot run, report it exactly as `NOT RUN — <reason>` in the
handoff. A green command that did not execute the required scope is not evidence.

## Fast gates

```bash
uv run --python 3.14 --locked pytest -q
uv run --python 3.14 --locked ruff check .
uv run --python 3.14 --locked ruff format --check .
uv run --python 3.14 --locked mypy src --strict
uv run --python 3.14 --locked bandit -r -ll src
uv run --python 3.14 --locked pip-audit
bash scripts/oscal-conformance.sh
uv run --python 3.14 --locked python scripts/check_registry_drift.py --registry examples/registry
```

The CI workflow is authoritative for the complete MAX gate set, including dependency hygiene,
duplication, complexity, REUSE, and changed-line coverage.

## Handoff

Report: issue and PR numbers; base/head and mergeability; changed files; reproduction; tests
and exact gate commands; architecture/anti-pattern findings; release/provenance status; every
`NOT RUN` item; merged commit and post-merge `main` verification.
