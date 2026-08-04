# CLI Design

Source: [`requirements.xlsx`](../requirements.xlsx) → *CLI-Design* sheet (R-CLI-D01..D12).
See the [docs index](../README.md). The CLI-shape decision is recorded in
[ADR-0002](../adr/0002-cli-shape.md).

> **This is a design record, not the shipped contract.** For the exact command surface as
> built, read [reference/cli.md](../reference/cli.md). Some names evolved after this record:
> the encoding flag shipped as `--to` (not `--format`), output goes to STDOUT with no
> `-o/--output` flag, and the `sources`/`shapes` introspection commands are not implemented.
> The `Status` column below tracks what actually landed.

## Contents

1. [Prior art](#prior-art)
2. [Decision](#decision)
3. [Synopsis](#synopsis)
4. [Design requirements (R-CLI-D01..D12)](#design-requirements-r-cli-d01d12)
5. [Exit codes (R-CLI-D08)](#exit-codes-r-cli-d08)

## Prior art

| Tool | Shape | Model |
| --- | --- | --- |
| **IBM Compliance Trestle** | verb/task subcommands (`trestle author`, `trestle task ...`) | a **stateful, git-workflow platform** that owns an OSCAL working directory and edits it in place. |
| **NIST oscal-cli** | model-first (`oscal-cli poam validate`, `... convert`) | operates on a model, then an action. |
| **GoComply oscalkit** | flat verbs (`oscalkit convert`, `... sign`) | one-shot transforms. |

## Decision

**Model-first subcommands + composable stdin→stdout filter.**

`mint-oscal` reads as the brand verb — "mint a `<shape>`" — matching NIST oscal-cli's
model-first ergonomics, and behaves as a pure Unix filter that chains cleanly. It is
explicitly **not** a Trestle-style stateful repo tool: it never edits an OSCAL working
directory in place. Trestle owns that lane; `mint` is a *producing* filter (R-CLI-D12).

## Synopsis

```
mint-oscal <shape> --from <source> [--format json|xml|yaml] [-o FILE] [--validate]

  <shape>     poam | sar | component        (model-first subcommand)
  --from      required adapter; no auto-detection (e.g. qureddy)
  input       stdin by default, or a path argument
  --format    OSCAL encoding; default json
  -o/--output output file; default stdout
  --validate  shell to oscal-cli if present, else internal structural check
```

Introspection: `mint-oscal sources`, `mint-oscal shapes`, `mint-oscal --version`.

### Pipeline example

```
qureddy scan | mint-oscal poam --from qureddy | oscal-cli validate -
```

Output is deterministic (stable uuid5), so generated OSCAL is meaningful to diff in git
and safe to review as a pipeline artifact.

## Design requirements (R-CLI-D01..D12)

| ID | Requirement | Rationale / prior art | Priority | Status |
| --- | --- | --- | --- | --- |
| R-CLI-D01 | Model-first subcommands: `mint-oscal <shape>` where shape in {poam, sar, component}. | Matches NIST oscal-cli (model-first); reads as the brand verb "mint <shape>". | Must | Designed |
| R-CLI-D02 | Source selected explicitly via `--from <adapter>` (required; no auto-detection). | Explicit beats magic; already built in v1. | Must | Built |
| R-CLI-D03 | Composable filter: read stdin or a path arg; write OSCAL to stdout by default. | Chains: `qureddy scan \| mint-oscal poam --from qureddy \| oscal-cli validate -` | Must | Designed |
| R-CLI-D04 | `--format json\|xml\|yaml` (OSCAL's three encodings); default json. | OSCAL is multi-encoding; downstream tools vary. | Should | Designed |
| R-CLI-D05 | `-o/--output FILE` optional (default stdout). | Pipeline + file both first-class. | Should | Designed |
| R-CLI-D06 | `--validate`: shell to oscal-cli when present, else run internal structural check. | Reuse the NIST validator; never reinvent schema validation. | Should | Partial |
| R-CLI-D07 | Introspection: `mint-oscal sources`, `mint-oscal shapes`, `--version`. | Discoverability of adapters/targets. | Should | Open |
| R-CLI-D08 | Exit codes: 0 ok; 1 validation/structural failure; 2 usage error. | Scriptable / CI-friendly. | Must | Open |
| R-CLI-D09 | Deterministic output (stable uuid5) so pipeline diffs are meaningful. | Enables git review of generated OSCAL. | Must | Built |
| R-CLI-D10 | No side effects beyond the declared output; safe to run in CI. | Pure filter contract. | Should | Designed |
| R-CLI-D11 | Library API mirrors the CLI: `convert(source, shape, doc)` facade + public adapters/emitters. | API parity so callers (QuReddy) use the lib, not the CLI. | Could | Partial |
| R-CLI-D12 | NOT a Trestle-style stateful repo tool; no in-place editing of an OSCAL working dir. | Trestle owns that lane; mint is a producing filter. | Must | Decided |

## Exit codes (R-CLI-D08)

| Code | Meaning |
| --- | --- |
| `0` | OK — document produced (and validated clean if `--validate`). |
| `1` | Validation / structural failure. |
| `2` | Usage error (bad args, unknown `--from`, unknown shape). |
