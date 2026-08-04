# mint-oscal — exit codes

`mint-oscal` uses distinct exit codes so scripts and CI can branch on the outcome without
parsing text. `generate` and `validate` have different code sets. Errors are reported on
STDERR; the OSCAL document, when produced, is the only thing on STDOUT.

## Contents

1. [`poam generate`](#poam-generate)
2. [`poam validate`](#poam-validate)
3. [Scripting notes](#scripting-notes)

## `poam generate`

| Code | Meaning |
| --- | --- |
| `0` | OSCAL document minted. |
| `1` | `--validate` found a semantic problem. |
| `2` | Input error, or a malformed / unrecognized source report. |
| `3` | Requested output needs a local dependency (`oscal-cli` for `xml`/`yaml`). |
| `4` | Usage error (bad flag, argument, or choice). |
| `70` | Internal error — `mint-oscal` itself failed, not your input. |

## `poam validate`

| Code | Meaning |
| --- | --- |
| `0` | Valid: no semantic problems found. |
| `1` | Invalid: one or more semantic problems (reported on STDERR). |
| `2` | Input error: not valid JSON, or not a POA&M document. |

## Scripting notes

- A `0` from `generate` means a document was produced (and passed the in-process checks if
  `--validate` was given). It does **not** assert NIST schema conformance — run `oscal-cli`
  for that (see [../how-to/validate-with-oscal-cli.md](../how-to/validate-with-oscal-cli.md)).
- Code `3` is recoverable: install `oscal-cli`, or drop `--to xml`/`--to yaml` and keep the
  default JSON, which has no external dependency.
- Code `70` is a defect in `mint-oscal`; re-run with `-vv` and report the trace.
