# mint-oscal CLI reference

Every command, flag, default, and accepted value of the shipped `mint-oscal` command
line. This page is the exact contract. For a first-use walkthrough see the
[tutorial](../tutorials/your-first-poam.md); for goal recipes see the
[how-to guides](../how-to/mint-from-a-cbom.md).

The banner and examples on this page were captured from `mint-oscal` version `0.2.1`.
The version string is read from installed package metadata, so `--version` reports the
version of the artifact you have installed.

## Contents

1. [Synopsis](#synopsis)
2. [Top-level options](#top-level-options)
3. [Models and verbs](#models-and-verbs)
4. [`poam generate`](#poam-generate)
5. [`poam validate`](#poam-validate)
6. [Emitted properties and namespaces](#emitted-properties-and-namespaces)
7. [Logging options](#logging-options)
8. [Exit codes](#exit-codes)
9. [Environment](#environment)
10. [Examples](#examples)

## Synopsis

```text
mint-oscal [-h] [-V] <model> <verb> [options]
```

`mint-oscal` reads one source report and writes one OSCAL document to STDOUT. There is
no output-file flag. Redirect STDOUT (`> poam.json`) or pipe the document onward.
Diagnostics and logs go to STDERR, so STDOUT stays a single parseable document.

A bare `mint-oscal`, a model with no verb (for example `mint-oscal poam`), or the word
`help` prints help and exits `0`.

## Top-level options

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Print root help to STDOUT and exit `0`. |
| `-V`, `--version` | Print the version banner and exit `0`. |

The version banner is a single line:

```text
BreachSAFE Mint-OSCAL 0.2.1 -- https://www.breachsafe.ai
```

## Models and verbs

The OSCAL model is the first token and the verb is the second, following the
`oscal-cli` command shape.

| Model | Status | Verbs | Behavior |
| --- | --- | --- | --- |
| `poam` (Plan of Action and Milestones) | Shipped | `generate`, `validate` | Emits and validates an OSCAL POA&M. |
| `ar` (Assessment Results) | Planned | `generate` | `ar generate` exits `3` (not implemented). The emitter is a stub; the OSCAL AR model requires an `import-ap` reference that is a program input. |

`ar` exposes only `generate`. The `validate` verb exists for `poam` alone.

## `poam generate`

Generate an OSCAL POA&M from a source report.

```text
mint-oscal poam generate --from SOURCE [--framework FRAMEWORK] [--extension NAME]
                         [--to FORMAT] [--validate] [LOGGING] report
```

| Argument or flag | Effect | Required | Default | Choices |
| --- | --- | --- | --- | --- |
| `report` | Path to the source report JSON, or `-` to read STDIN. | Yes | none | path or `-` |
| `--from SOURCE` | Source adapter that parses the report. | Yes | none | `cbom`, `qureddy` |
| `--framework FRAMEWORK` | Control framework the crosswalk maps findings to. `scf-qts` is SCF Quantum Security controls; `nist` is NIST SP 800-53r5 (SC-13/SC-12). | No | `scf-qts` | `scf-qts`, `nist` |
| `--extension NAME` | Opt-in IR enricher. Repeatable. Runs after the source adapter and adds producer cross-checks to the derived IR. | No | none | `breachsafe` |
| `--to FORMAT` | Output encoding. The value is lowercased before matching. Only `json` is implemented; `xml` and `yaml` exit `3` (see the note below). | No | `json` | `json`, `xml`, `yaml` |
| `--validate` | Run the in-process Layer-2 semantic checks over the minted document and exit `1` on any problem. These checks are not authoritative NIST schema validation. | No | off | flag |

The minted document goes to STDOUT. Crypto facts ride as OSCAL `prop` objects; see
[Emitted properties and namespaces](#emitted-properties-and-namespaces).

XML and YAML are not implemented in this release. `--to xml` and `--to yaml` raise a
not-implemented error and exit `3` whether or not `oscal-cli` is on `PATH`; installing
`oscal-cli` does not change this result (verified against version `0.2.1`). ADR-0005
records the design in which `oscal-cli` would perform the conversion. To obtain XML or
YAML today, mint JSON and convert it with the external tool:

```bash
mint-oscal poam generate --from cbom scan.cbom.json > poam.json
oscal-cli convert --to=xml poam.json poam.xml --overwrite
```

## `poam validate`

Validate an existing OSCAL POA&M with the pure-Python Layer-2 semantic checks. The
input can be a document that `mint-oscal` produced or one from another tool. No
`oscal-cli` or Trestle is required. These checks are necessary but not sufficient for
full NIST schema conformance.

```text
mint-oscal poam validate [LOGGING] document
```

| Argument | Effect | Required |
| --- | --- | --- |
| `document` | Path to the OSCAL POA&M JSON to validate, or `-` to read STDIN. | Yes |

The verdict and any problems are written to STDERR; STDOUT is left empty, so the exit
code is the machine signal. The Layer-2 checks cover UUID syntax and uniqueness,
cross-reference resolution (observation, risk, and inventory-item subject UUIDs),
required fields and array cardinality, the UUID and timezone-aware dateTime datatypes,
the open risk-status and observation vocabularies by token or string shape, and the
BreachSAFE property namespace and value vocabularies.

## Emitted properties and namespaces

The emitted POA&M carries `prop` objects in two namespaces.

| Namespace | URI | Property names | Owner |
| --- | --- | --- | --- |
| BreachSAFE | `https://breachsafe.ai/ns/oscal` | `readiness`, `mapping-confidence`, `severity`, `framework`, `interpretation-status`, `nistQuantumSecurityLevel`, `provenance` (with `--extension breachsafe`), and the crypto posture facts such as `kex-offered` and `cert-signature` | BreachSAFE domain vocabulary |
| Framework authority | `https://securecontrolsframework.com/ns/oscal` for `scf-qts`; `https://csrc.nist.gov/ns/oscal/800-53` for `nist` | `control-id` | The standards body that owns the control identifiers |

Control identifiers are attributed to the framework authority namespace, not the
BreachSAFE namespace. The `--framework` flag selects both the authority namespace and
the catalog link target that each POA&M item references. The metadata block reports a
fixed document `version` default of `0.1.0` and an `oscal-version` of `1.2.2`. See
[OSCAL shapes](oscal-shapes.md) for the full field table.

## Logging options

Both verbs accept the same logging flags. Logs go to STDERR only, so they never
contaminate the OSCAL document on STDOUT.

| Option | Effect |
| --- | --- |
| `-v`, `--verbose` | Increase log verbosity. `-v` selects INFO; `-vv` selects DEBUG. |
| `-q`, `--quiet` | Suppress warnings and below; only errors are logged. |
| `--json-logs` | Emit logs as newline-delimited JSON instead of console text. |

## Exit codes

`generate` and `validate` use different code sets. The full table is in
[exit-codes.md](exit-codes.md).

## Environment

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | Disable ANSI color in `--help` output. See <https://no-color.org>. |

## Examples

```bash
# A CBOM file to a POA&M JSON document on STDOUT.
mint-oscal poam generate --from cbom scan.cbom.json > poam.json

# Read the report from STDIN.
qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -

# Map to NIST SP 800-53r5 instead of the default scf-qts.
mint-oscal poam generate --from cbom scan.cbom.json --framework nist > poam.json

# Producer cross-check plus in-process semantic validation.
mint-oscal poam generate --from cbom scan.cbom.json --extension breachsafe --validate

# Validate a POA&M that another tool produced.
mint-oscal poam validate their-poam.json
```

See [../contributors/cli-design.md](../contributors/cli-design.md) for the design
rationale and [../explanation/architecture.md](../explanation/architecture.md) for where
the CLI sits in the system.
</content>
</invoke>
