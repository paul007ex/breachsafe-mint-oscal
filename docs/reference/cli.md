# mint-oscal — CLI reference

Every command, flag, default, and value of the shipped `mint-oscal` command line.
This page is the exact contract; for a learning walkthrough see the
[tutorial](../tutorials/your-first-poam.md), and for goal recipes see the
[how-to guides](../how-to/mint-from-a-cbom.md).

> **Scope.** Only `poam` is implemented. `ar` and `component-definition` appear in
> `--help` as **planned** subcommands and raise a not-implemented error if invoked; they
> are documented in [oscal-shapes.md](oscal-shapes.md), not here.

## Contents

1. [Synopsis](#synopsis)
2. [Models and verbs](#models-and-verbs)
3. [`poam generate`](#poam-generate)
4. [`poam validate`](#poam-validate)
5. [Logging options](#logging-options)
6. [Exit codes](#exit-codes)
7. [Environment](#environment)
8. [Examples](#examples)

## Synopsis

```
mint-oscal [-h] [-V] <model> <verb> [options]
```

`mint-oscal` is a filter: it reads one source report and writes one OSCAL document to
STDOUT. There is no output-file flag — redirect STDOUT (`> poam.json`) or pipe onward.

| Top-level option | Effect |
| --- | --- |
| `-h`, `--help` | Show help and exit. |
| `-V`, `--version` | Print `BreachSAFE Mint-OSCAL <version> -- https://www.breachsafe.ai` and exit. |

## Models and verbs

| Model | Status | Verbs |
| --- | --- | --- |
| `poam` — Plan of Action & Milestones | **Shipped** | `generate`, `validate` |
| `ar` — Assessment Results | Planned | — |
| `component-definition` | Planned | — |

## `poam generate`

Generate an OSCAL POA&M from a source report.

```
mint-oscal poam generate --from SOURCE [--framework FRAMEWORK] [--extension NAME]
                         [--to FORMAT] [--validate] [LOGGING] REPORT
```

| Argument / flag | Effect | Required | Default |
| --- | --- | --- | --- |
| `REPORT` | Path to the source report JSON, or `-` to read STDIN. | yes | — |
| `--from SOURCE` | Source adapter that parses the report: `cbom` or `qureddy`. | yes | — |
| `--framework FRAMEWORK` | Control framework to map findings to: `scf-qts` (PQC-native SCF Quantum Security controls) or `nist` (NIST SP 800-53r5 SC-13/SC-12). | no | `scf-qts` |
| `--extension NAME` | Opt-in IR enricher, repeatable (for example `breachsafe`). Orthogonal to `--from`, which stays vendor-neutral; adds producer cross-checks. | no | none |
| `--to FORMAT` | Output encoding: `json`, `xml`, or `yaml`. `xml`/`yaml` require `oscal-cli` on `PATH`. | no | `json` |
| `--validate` | Run in-process Layer-2 semantic checks (uuid/ref/ns integrity, OSCAL structural + BreachSAFE domain vocab). Not authoritative NIST schema validation — run `oscal-cli` for that. Exit `1` on any problem. | no | off |

The output goes to STDOUT. Crypto facts ride as readable `prop` in the
`https://breachsafe.ai/ns/oscal` namespace; evidence carries hashes only, never raw
excerpts.

## `poam validate`

Validate an existing OSCAL POA&M — one that `mint-oscal` produced or one from another
tool — with pure-Python Layer-2 semantic checks. No `oscal-cli` or Trestle required;
necessary but **not** sufficient for full NIST schema conformance.

```
mint-oscal poam validate [LOGGING] DOCUMENT
```

| Argument | Effect | Required |
| --- | --- | --- |
| `DOCUMENT` | Path to the OSCAL POA&M JSON to validate, or `-` for STDIN. | yes |

## Logging options

Accepted by both verbs. Logs go to STDERR, so they never contaminate the OSCAL document
on STDOUT.

| Option | Effect |
| --- | --- |
| `-v`, `--verbose` | Increase log verbosity (`-v` INFO, `-vv` DEBUG). |
| `-q`, `--quiet` | Suppress warnings and below; only errors are logged. |
| `--json-logs` | Emit logs as newline-delimited JSON instead of console text. |

## Exit codes

`generate` and `validate` use different code sets. The full table lives in
[exit-codes.md](exit-codes.md).

## Environment

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | Disable ANSI color in `--help` output (<https://no-color.org>). |

## Examples

```bash
# Most common: a CBOM file -> POA&M JSON on stdout.
mint-oscal poam generate --from cbom scan.cbom.json > poam.json

# Read the report from stdin (the flagship pipe).
qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -

# Map to NIST SP 800-53r5 instead of the default scf-qts.
mint-oscal poam generate --from cbom scan.cbom.json --framework nist > poam.json

# Producer cross-check + in-process semantic validation.
mint-oscal poam generate --from cbom scan.cbom.json --extension breachsafe --validate

# XML output (requires oscal-cli on PATH).
mint-oscal poam generate --from cbom scan.cbom.json --to xml > poam.xml

# Validate a POA&M someone else produced.
mint-oscal poam validate their-poam.json
```

See [../contributors/cli-design.md](../contributors/cli-design.md) for the design
rationale and [../explanation/architecture.md](../explanation/architecture.md) for where
the CLI sits in the system.
