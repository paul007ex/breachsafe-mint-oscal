# mint-oscal

Mint NIST OSCAL documents from security-tool findings.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)

`mint-oscal` converts security-tool findings — starting with post-quantum crypto
posture from QuReddy — into NIST [OSCAL](https://pages.nist.gov/OSCAL/) documents. It is
a composable filter: findings in, OSCAL out, ready to pipe into `oscal-cli` or commit for
review.

> **Status: pre-alpha.** The POA&M path is prototyped and validated against NIST
> `oscal-cli`. `ar` and `component-definition` emitters are stubs. Not yet published to
> PyPI. Claim classes below: **Shipped** = in the artifact; **Designed** = specified, not
> built.

## Contents

1. [Why](#why)
2. [Install](#install)
3. [Quickstart](#quickstart)
4. [Supported OSCAL models](#supported-oscal-models)
5. [Supported formats](#supported-formats)
6. [Library API](#library-api)
7. [Determinism and git](#determinism-and-git)
8. [What "valid" does and does not mean](#what-valid-does-and-does-not-mean)
9. [Versioning](#versioning)
10. [Documentation](#documentation)
11. [Contributing, security, license](#contributing-security-license)
12. [Relationship to prior work](#relationship-to-prior-work)

## Why

No open tool converts scanner findings — least of all post-quantum crypto posture — *into*
OSCAL. `oscal-cli` and `oscalkit` transform existing OSCAL; Trestle authors and manages it.
`mint-oscal` fills the producer gap: it turns a scan into a Plan of Action & Milestones (or
Assessment Results) an assessor can consume.

The design is an **agnostic core**: `N sources → neutral IR → M OSCAL shapes`. The core
knows only the IR and OSCAL; source formats are handled by optional edge adapters, or
sources emit the published `mint.ir.v1` contract directly.

## Install

Requires Python 3.11+. Not yet on PyPI; install from source:

```bash
pip install .
```

XML and YAML output additionally require an external [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli)
on `PATH` (or the Docker image); JSON output has no external dependency.

## Quickstart

```bash
# mint a POA&M from a QuReddy scan (JSON to stdout)
mint-oscal poam generate --from qureddy scan.json

# chain straight into the NIST validator
mint-oscal poam generate --from qureddy scan.json | oscal-cli poam validate -

# XML, pinned timestamp, validated, to a file
mint-oscal poam generate --from qureddy scan.json --to XML \
  --system-id "tls://example.com:443" --prepared-by "BreachSAFE" \
  --now 2026-07-27T03:21:54Z --validate -o example.poam.xml
```

Full flag reference: [docs/cli.md](docs/cli.md).

## Supported OSCAL models

| Model | Role | Status |
| --- | --- | --- |
| `poam` — Plan of Action & Milestones | emit | **Shipped** (prototype, `oscal-cli`-validated) |
| `ar` — Assessment Results | emit | Designed (requires `import-ap`) |
| `component-definition` | emit | Designed |
| `profile`, `catalog` | consume (the ODP bar / control text) | Designed |

Crypto facts ride as readable `prop` in the `https://breachsafe.ai/ns/oscal` namespace
(readiness, algorithm, `nistQuantumSecurityLevel`, certificate signature, evidence hashes).
OSCAL has no native crypto model; these props pass through validators unchanged.

## Supported formats

OSCAL's three native encodings, matching `oscal-cli`: **JSON** (native, deterministic, no
dependency), **XML**, and **YAML** (both via `oscal-cli`). Select with `--to`.

## Library API

Embedded callers use the library directly instead of the CLI:

```python
import mint_oscal
poam = mint_oscal.convert(ir, shape="poam", system_id="tls://example.com:443")
```

The CLI is a thin wrapper over `convert`; parameters map 1:1.

## Determinism and git

UUIDs are `uuid5` over a fixed namespace and `last-modified` is pinnable with `--now`, so
the same scan produces byte-identical output. A re-scan yields a clean `git diff` — you
review what changed in posture, not churn.

## What "valid" does and does not mean

`oscal-cli` validation confirms schema and constraint conformance. It does **not** bless the
finding→control mapping or the compliance verdict. That verdict depends on an
organization-defined parameter (for example, whether the ODP requires CNSA 2.0 PQC) and is
*asserted*, not scanner-derived. The `sp800-53r5` crosswalk ships as a **draft pending
conformance sign-off**. Valid OSCAL is not the same as compliant.

## Versioning

Documents declare `oscal-version` **1.1.2** for maximum validator interop and record the
internal target **1.2.2** as a prop. Validated with `oscal-cli` 3.2.0.

## Documentation

- [Architecture](docs/architecture.md) — components, data flow, trust boundaries, decisions
- [CLI reference](docs/cli.md) · [CLI design](docs/cli-design.md)
- [Use cases](docs/use-cases.md) · [OSCAL shapes](docs/oscal-shapes.md) · [Requirements](docs/requirements.md)
- [ADRs](docs/adr/) · [Roadmap](ROADMAP.md)

## Contributing, security, license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Licensed under [Apache-2.0](LICENSE).

## Relationship to prior work

Built on the OSCAL standard and validated with NIST's
[`oscal-cli`](https://github.com/metaschema-framework/oscal-cli). It complements, rather than
duplicates, [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli) (validate/convert)
and [Compliance Trestle](https://github.com/oscal-compass/compliance-trestle) (authoring).
**mint-oscal is an independent project and is not affiliated with or endorsed by NIST.**
