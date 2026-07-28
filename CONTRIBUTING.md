# Contributing to breachsafe-mint-oscal

Thanks for your interest in contributing. This project mints NIST OSCAL documents
from a source-neutral intermediate representation (IR); correctness and auditability
matter more than speed here.

## Ground rules

- By contributing you agree your work is licensed under [Apache-2.0](LICENSE).
- Be excellent to each other; see our [Code of Conduct](CODE_OF_CONDUCT.md).
- Every source file carries the SPDX header:

  ```python
  # SPDX-FileCopyrightText: 2026 BreachSAFE
  # SPDX-License-Identifier: Apache-2.0
  ```

## Architecture (read first)

The core is agnostic (ADR-0004: ports & adapters):

- **Adapters** (`mint_oscal.adapters`) normalize a source report into the IR.
- **Emitters** (`mint_oscal.emitters`) turn the IR into an OSCAL model.
- Neither knows the other. Adding a source is one adapter; adding a target is one
  emitter. Do not couple them.

Control mappings live in `mint_oscal.controls` and are **auditable, swappable data** --
never invented inside an emitter. Crosswalk tables are DRAFT until they carry a
recorded conformance sign-off (R-CTRL-01).

## Development setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before you open a PR

Run the same checks CI runs:

```bash
ruff check src
ruff format --check
mypy src
pytest
```

- Keep IR dataclasses **frozen**.
- Stubs raise `NotImplementedError` naming *what* and *which ADR/use case*.
- Update `CHANGELOG.md` under `## [Unreleased]`.
- Tests are owned by the project's tester; coordinate before adding test files.

## Reporting security issues

Do **not** open a public issue for vulnerabilities. See [SECURITY.md](SECURITY.md).
