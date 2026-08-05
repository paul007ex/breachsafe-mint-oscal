# mint-oscal exit codes

`mint-oscal` uses distinct exit codes so scripts and CI can branch on the outcome
without parsing text. `generate` and `validate` have different code sets. Diagnostics
are written to STDERR; the OSCAL document, when produced, is the only content on STDOUT.

The codes are defined in `src/mint_oscal/cli.py` as the `_EXIT_*` constants. Every code
in the tables below was triggered against version `0.2.1`.

## Contents

1. [`poam generate`](#poam-generate)
2. [`poam validate`](#poam-validate)
3. [Scripting notes](#scripting-notes)

## `poam generate`

| Code | Constant | Meaning | Example trigger |
| --- | --- | --- | --- |
| `0` | `_EXIT_OK` | OSCAL document minted to STDOUT. | `poam generate --from cbom scan.cbom.json` |
| `1` | `_EXIT_VALIDATION` | `--validate` found a semantic problem in the minted document. | Reachable only when the minted document fails the Layer-2 checks; mint's own output passes them, so this code is defensive. |
| `2` | `_EXIT_INPUT` | Input or OS error, or a malformed or unrecognized source report. | Missing file, non-JSON input, or a document that is not a CycloneDX BOM. |
| `3` | `_EXIT_NOT_IMPLEMENTED` | A not-implemented path was requested: `--to xml`, `--to yaml`, or a planned model (`ar generate`). | `poam generate --from cbom scan.cbom.json --to xml`; `ar generate --from cbom scan.cbom.json` |
| `4` | `_EXIT_USAGE` | Usage error: an unknown flag, a missing argument, or an invalid choice. | `--from bogus`; `--to toml` |
| `70` | `_EXIT_INTERNAL` | Internal error inside `mint-oscal`, distinct from bad input. `70` is BSD `sysexits.h` `EX_SOFTWARE`. | An unexpected fault; not deliberately reachable through documented input. |

Code `3` is not recoverable by installing a dependency in this release. XML and YAML
output is not implemented, so `--to xml` and `--to yaml` exit `3` whether or not
`oscal-cli` is on `PATH`. The only way to avoid code `3` for encoding is to keep the
default `json`. `ar generate` exits `3` because the Assessment Results emitter is a stub.

## `poam validate`

| Code | Constant | Meaning | Example trigger |
| --- | --- | --- | --- |
| `0` | `_EXIT_OK` | Valid: no semantic problems found. | Validate a document that passes the Layer-2 checks. |
| `1` | `_EXIT_VALIDATION` | Invalid: one or more semantic problems, each reported on STDERR. | Validate a POA&M that is missing a required field. |
| `2` | `_EXIT_INPUT` | Input error: not valid JSON, or not a POA&M document (no `plan-of-action-and-milestones` root). | Non-JSON input; a document whose root is not a POA&M. |

## Scripting notes

- A `0` from `generate` means a document was produced, and that it passed the in-process
  Layer-2 checks when `--validate` was given. It does not assert NIST schema conformance.
  Run `oscal-cli` for authoritative validation; see
  [../how-to/validate-with-oscal-cli.md](../how-to/validate-with-oscal-cli.md).
- To avoid code `3`, keep the default JSON encoding and do not invoke the planned `ar`
  model. Convert JSON to XML or YAML with the external `oscal-cli convert` command.
- Code `70` is a defect in `mint-oscal`. Re-run with `-vv` and report the diagnostic.
</content>
