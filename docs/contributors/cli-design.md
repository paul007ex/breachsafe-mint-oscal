# CLI Design

Source: [`requirements.xlsx`](../requirements.xlsx) → *CLI-Design* sheet (R-CLI-D01..D12).
See the [docs index](../README.md). The CLI-shape decision is recorded in
[ADR-0002](../adr/0002-cli-shape.md).

> **This is a design record. It is not the shipped contract.** For the exact command surface
> as built, read [reference/cli.md](../reference/cli.md). Several details evolved after this
> record; the `Status` column below tracks what landed:
>
> - The invocation gained a verb level. The shipped shape is `mint-oscal <model> <verb>`
>   (`poam generate`, `poam validate`), replacing the bare `mint-oscal <shape>` used here.
> - The Assessment Results shape shipped under the model name `ar`; this record calls it
>   `sar`. It is registered but planned (the emitter raises `NotImplementedError`).
> - The `component` shape was dropped. The shipped models are `poam` and `ar`.
> - The encoding flag shipped as `--to`, and output goes to STDOUT with no `-o/--output` flag.
> - The `sources`/`shapes` introspection commands are not implemented.
> - Exit codes expanded from the 0/1/2 design below to the shipped 0/1/2/3/4/70 scheme.

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

`mint-oscal` reads as the brand verb "mint a `<shape>`", matching NIST oscal-cli's
model-first ergonomics, and behaves as a pure Unix filter that chains cleanly. It is not a
Trestle-style stateful repo tool: it never edits an OSCAL working directory in place.
Trestle owns that lane; `mint` is a producing filter (R-CLI-D12).

## Synopsis

```
mint-oscal <shape> --from <source> [--format json|xml|yaml] [-o FILE] [--validate]

  <shape>     poam | sar                     (model-first subcommand)
  --from      required adapter; no auto-detection (e.g. qureddy)
  input       stdin by default, or a path argument
  --format    OSCAL encoding; default json
  -o/--output output file; default stdout
  --validate  in-process semantic check; oscal-cli is authoritative, run separately
```

Introspection: `mint-oscal sources`, `mint-oscal shapes`, `mint-oscal --version`.

### Pipeline example

```
qureddy scan | mint-oscal poam generate --from qureddy - | oscal-cli validate -
```

Output is deterministic (stable uuid5), so generated OSCAL is meaningful to diff in git
and safe to review as a pipeline artifact.

## Design requirements (R-CLI-D01..D12)

| ID | Requirement | Rationale / prior art | Priority | Status |
| --- | --- | --- | --- | --- |
| R-CLI-D01 | Model-first subcommands: `mint-oscal <shape>` where shape in {poam, sar}. | Matches NIST oscal-cli (model-first); reads as the brand verb "mint <shape>". | Must | Built (shipped as `<model> <verb>`; `sar`→`ar`) |
| R-CLI-D02 | Source selected explicitly via `--from <adapter>` (required; no auto-detection). | Explicit beats magic; already built in v1. | Must | Built |
| R-CLI-D03 | Composable filter: read stdin or a path arg; write OSCAL to stdout by default. | Chains: `qureddy scan \| mint-oscal poam generate --from qureddy - \| oscal-cli validate -` | Must | Built |
| R-CLI-D04 | `--format json\|xml\|yaml` (OSCAL's three encodings); default json. | OSCAL is multi-encoding; downstream tools vary. | Should | Designed |
| R-CLI-D05 | `-o/--output FILE` optional (default stdout). | Pipeline + file both first-class. | Should | Designed |
| R-CLI-D06 | `--validate`: run the in-process semantic check; oscal-cli stays the authoritative NIST validator. | Reuse the NIST validator; never reinvent schema validation. | Should | Built (in-process semantic check; oscal-cli not auto-shelled) |
| R-CLI-D07 | Introspection: `mint-oscal sources`, `mint-oscal shapes`, `--version`. | Discoverability of adapters/targets. | Should | Open |
| R-CLI-D08 | Exit codes: 0 ok; 1 validation/semantic failure; 2 usage error. | Scriptable / CI-friendly. | Must | Built (expanded to 0/1/2/3/4/70) |
| R-CLI-D09 | Deterministic output (stable uuid5) so pipeline diffs are meaningful. | Enables git review of generated OSCAL. | Must | Built |
| R-CLI-D10 | No side effects beyond the declared output; safe to run in CI. | Pure filter contract. | Should | Designed |
| R-CLI-D11 | Library API mirrors the CLI: `convert(source, shape, doc)` facade + public adapters/emitters. | API parity so callers (QuReddy) use the lib, not the CLI. | Could | Partial |
| R-CLI-D12 | NOT a Trestle-style stateful repo tool; no in-place editing of an OSCAL working dir. | Trestle owns that lane; mint is a producing filter. | Must | Decided |

## Exit codes (R-CLI-D08)

This record proposed 0/1/2. The shipped surface expanded it to separate a usage mistake
from bad input and to flag output formats that are not wired yet. The authoritative table
is in [reference/cli.md](../reference/cli.md); the shipped scheme is reproduced here.

Shipped `poam generate`:

| Code | Meaning |
| --- | --- |
| `0` | OSCAL document minted (semantic checks passed if `--validate`). |
| `1` | `--validate` found a semantic problem. |
| `2` | Input error, or malformed / unrecognized source report. |
| `3` | Requested output needs a local dependency (oscal-cli for `--to xml`/`yaml`). |
| `4` | Usage error (bad flag, argument, or `--from`/model choice). |
| `70` | Internal error (mint-oscal itself failed). |

Shipped `poam validate`:

| Code | Meaning |
| --- | --- |
| `0` | Valid: no semantic problems found. |
| `1` | Invalid: one or more semantic problems (reported on STDERR). |
| `2` | Input error: not valid JSON, or not a POA&M document. |

## P0 Profile CLI contract (OSCAL-compatible extension)

The Profile command surface must mirror the official `oscal-cli` model-first grammar. The
official tool uses `oscal-cli profile <command> [<options>]` with `validate`, `convert`, and
`resolve`; Mint-OSCAL must preserve those meanings and help conventions. BreachSAFE adds
`create` and `explain` for the registry-backed resolver moat.

```text
mint-oscal profile <command> [<options>]

  create       BreachSAFE registry-backed Profile compiler (designed P0)
  validate     OSCAL Profile validation boundary (designed P0)
  convert      JSON/XML/YAML conversion boundary (designed P0)
  resolve      OSCAL Profile resolution boundary (designed P0)
  explain      BreachSAFE selection/provenance explanation (designed P0)
```

The help cascade is part of the contract:

```bash
mint-oscal --help
mint-oscal profile --help
mint-oscal profile create --help
mint-oscal profile validate --help
mint-oscal profile convert --help
mint-oscal profile resolve --help
mint-oscal profile explain --help
```

P0 command shapes:

```bash
mint-oscal profile create \
  --framework <framework-pack> \
  --objective <objective-id> \
  --catalog <catalog-id> \
  --registry default \
  [destination]

mint-oscal profile validate <file-or-URI>
mint-oscal profile convert --to FORMAT <source> [destination]
mint-oscal profile resolve --to FORMAT <profile-URI> [destination]
mint-oscal profile explain <file-or-URI>
```

`create` and `explain` are BreachSAFE additions. `validate`, `convert`, and `resolve` must
not be renamed or given semantics that conflict with `oscal-cli`. The framework is an option
to Profile creation; `mint-oscal nist profile ...` is not the contract. The objective is a
governed registry key, not an arbitrary control expression. NIST SP 800-53 is the first
fixture, not a product limitation. The same contract must support governed packs for NIST
CSF, PCI-DSS, FFIEC, NCUA, EU frameworks, SCF, and future frameworks only when their
Catalogs and crosswalks are reviewed and available. Names alone do not imply that a mapping
exists.

The parser implementation should retain Mint-OSCAL's existing nested-subparser pattern:
top-level parser → model parser → verb parser → command-specific options. Keep one central
error boundary, structured STDERR logging, pure OSCAL STDOUT/output behavior, and explicit
exit codes. Do not add a second parser or a framework-specific command tree.

This is a designed P0 contract, not shipped behavior. The shipped contract remains the
`poam` and planned `ar` surface documented above until implementation lands.
