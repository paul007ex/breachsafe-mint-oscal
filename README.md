# mint-oscal

Mint NIST OSCAL documents from security-tool findings.

[![License: PolyForm-Noncommercial-1.0.0](https://img.shields.io/badge/License-PolyForm--Noncommercial--1.0.0-blue.svg)](LICENSE)
![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)

`mint-oscal` converts security-tool findings into NIST
[OSCAL](https://pages.nist.gov/OSCAL/) documents. Its first source is post-quantum crypto
posture from QuReddy. It is a composable filter: findings in, OSCAL out, ready to validate
with `oscal-cli` or commit for review.

> **Status: pre-alpha.** The POA&M path is prototyped and validated against NIST
> `oscal-cli`. The `ar` (Assessment Results) emitter is a stub that exits `3`. Not yet
> published to PyPI. Claim classes below: **Shipped** = in the artifact; **Designed** =
> specified, not built.

## Contents

1. [Why](#why)
2. [Install](#install)
3. [Quickstart](#quickstart)
4. [Registry CLI](#registry-cli)
5. [Supported OSCAL models](#supported-oscal-models)
6. [Supported formats](#supported-formats)
7. [Library API](#library-api)
8. [Determinism and git](#determinism-and-git)
9. [What "valid" does and does not mean](#what-valid-does-and-does-not-mean)
10. [Versioning](#versioning)
11. [Documentation](#documentation)
12. [Contributing, security, license](#contributing-security-license)
13. [Relationship to prior work](#relationship-to-prior-work)

## Why

No open tool converts scanner findings, including post-quantum crypto posture, *into*
OSCAL. `oscal-cli` and `oscalkit` transform existing OSCAL; Trestle authors and manages it.
`mint-oscal` fills the producer gap: it turns a scan into a Plan of Action & Milestones (or
Assessment Results) an assessor can consume.

The design is an **agnostic core**: `N sources → neutral IR → M OSCAL shapes`. The core
knows only the IR and OSCAL; source formats are handled by optional edge adapters, or
sources emit the published `mint.ir.v1` contract directly.

## Install

Requires Python 3.14+. Not yet on PyPI; install from source:

```bash
pip install .
```

XML and YAML output additionally require an external [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli)
on `PATH`; JSON output has no external dependency.

## Quickstart

```bash
# mint a POA&M from a CycloneDX CBOM (JSON to stdout)
# findings map to PQC-native SCF Quantum Security (QTS) controls by default
mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json

# map to NIST SP 800-53r5 instead of the default scf-qts
mint-oscal poam generate --from cbom examples/example.cbom.json --framework nist > poam.json

# validate with the NIST validator (oscal-cli reads a file; it has no stdin)
oscal-cli validate poam.json

# run in-process semantic checks while minting, then convert JSON to XML (ADR-0005)
mint-oscal poam generate --from cbom examples/example.cbom.json --validate > poam.json
oscal-cli convert --to=xml poam.json poam.xml --overwrite
```

Findings map to a control framework selected with `--framework`: **`scf-qts`** (default,
PQC-native SCF Quantum Security controls) or **`nist`** (SP 800-53r5). Control ids are
attributed to the framework's own namespace and linked to its catalog. Full flag reference:
[docs/reference/cli.md](docs/reference/cli.md).

## Supported OSCAL models

| Model | Role | Status |
| --- | --- | --- |
| `poam` (Plan of Action & Milestones) | emit | **Shipped** (prototype, `oscal-cli`-validated) |
| `ar` (Assessment Results) | emit | Designed (requires `import-ap`; the emitter exits `3`) |
| `profile`, `catalog` | consume (the ODP bar / control text) | Designed |

Crypto facts ride as readable `prop` in the `https://breachsafe.ai/ns/oscal` namespace
(readiness, algorithm, `nistQuantumSecurityLevel`, certificate signature, evidence hashes).
OSCAL has no native crypto model; these props pass through validators unchanged.

## Supported formats

JSON is the only shipped native encoding: deterministic, no external dependency. Native
`--to yaml` is supported natively. XML is not a supported output format.
To get XML or YAML now, mint JSON and convert it with `oscal-cli`:

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json
oscal-cli convert --to=xml poam.json poam.xml --overwrite
```

See [docs/how-to/emit-xml-or-yaml.md](docs/how-to/emit-xml-or-yaml.md).

## Registry CLI

The governed registry keeps Catalog pins, framework packs, Profiles, objectives, and
crosswalk metadata versioned and reviewable in Git. These registry commands are shipped:

```bash
# Create a bootstrap registry workspace.
mint-oscal registry init --output policy

# Add and pin a local OSCAL Catalog.
mint-oscal registry add-catalog --registry policy --id nist-800-53r5 \
  --file reference/nist/catalog.json \
  --source-uri https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final \
  --release rev5 --license "NIST public domain" --authority NIST

# Inspect and verify the registry.
mint-oscal registry list --registry policy
mint-oscal registry show nist-800-53r5 --registry policy
mint-oscal registry validate --registry policy
mint-oscal registry lock --registry policy
mint-oscal registry verify --registry policy
```

Use `mint-oscal registry --help` for the authoritative grammar. The complete contract,
registry layout, lock format, and provenance rules are in
[docs/reference/registry.md](docs/reference/registry.md).

## Library API

Embedded callers build an `IR` and call `convert` instead of shelling out to the CLI:

```python
from mint_oscal import IR, Finding, Subject, convert

subject = Subject(id="example.com:443", kind="endpoint", description="TLS endpoint")
finding = Finding(
    id="rsa-2048-in-use",
    title="RSA-2048 key exchange is not quantum-safe",
    description="Endpoint negotiates RSA-2048, which CNSA 2.0 deprecates.",
    severity="high",
    status="open",
    subject=subject,
    observed_at="2026-07-28T15:00:12+00:00",
    control_ids=("QTS-01",),
    risk_statement="Harvest-now-decrypt-later exposure.",
)
ir = IR(findings=(finding,), subject=subject, source="cbom")
poam = convert(ir, shape="poam")  # returns a dict; metadata.oscal-version == "1.2.2"
```

The CLI is a thin wrapper over `convert`.

## Determinism and git

UUIDs are `uuid5` over a fixed namespace and `last-modified` is derived from the scan's
observation time (not wall-clock), so the same scan produces byte-identical output. A
re-scan yields a clean `git diff`: you review what changed in posture, without churn.

## What "valid" does and does not mean

`oscal-cli` validation confirms schema and constraint conformance. It does **not** bless the
finding→control mapping or the compliance verdict. That verdict depends on an
organization-defined parameter (for example, whether the ODP requires CNSA 2.0 PQC) and is
*asserted*, not scanner-derived. The default `scf-qts` crosswalk (and the opt-in `nist` one)
ship as **drafts pending conformance sign-off**, so every finding carries an
`interpretation-status: provisional` prop until then. Valid OSCAL is not the same as compliant.

## Versioning

Documents declare `oscal-version` **1.2.2** (the current NIST OSCAL release). Validated with
`oscal-cli` 3.2.0 and the NIST v1.2.2 JSON schema.

## Documentation

The docs follow [Diátaxis](https://diataxis.fr). Start at the [docs index](docs/README.md).

- **Learn:** [Your first POA&M](docs/tutorials/your-first-poam.md)
- **Do:** [Mint from a CBOM](docs/how-to/mint-from-a-cbom.md) ·
  [Choose a framework](docs/how-to/choose-a-control-framework.md) ·
  [Validate with oscal-cli](docs/how-to/validate-with-oscal-cli.md) ·
  [Emit XML or YAML](docs/how-to/emit-xml-or-yaml.md)
- **Look up:** [CLI reference](docs/reference/cli.md) · [Exit codes](docs/reference/exit-codes.md) ·
  [OSCAL shapes](docs/reference/oscal-shapes.md) · [Requirements](docs/reference/requirements.md)
- **Understand:** [Agnostic core](docs/explanation/agnostic-core.md) ·
  [Valid vs compliant](docs/explanation/valid-vs-compliant.md) ·
  [Honest state & frameworks](docs/explanation/honest-state-and-frameworks.md) ·
  [Architecture](docs/explanation/architecture.md)
- [ADRs](docs/adr/) · [Roadmap](ROADMAP.md)

## Contributing, security, license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Source-available under
[PolyForm-Noncommercial-1.0.0](LICENSE).

## Relationship to prior work

Built on the OSCAL standard and validated with NIST's
[`oscal-cli`](https://github.com/metaschema-framework/oscal-cli). It complements, rather than
duplicates, [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli) (validate/convert)
and [Compliance Trestle](https://github.com/oscal-compass/compliance-trestle) (authoring).
**mint-oscal is an independent project and is not affiliated with or endorsed by NIST.**
