# mint-oscal — CLI reference

> **Status: designed, not yet shipped.** The command surface below is the accepted
> design (NIST-aligned). The POA&M path is prototyped; other models raise
> `NotImplementedError`. Claim classes: **Shipped** = in the artifact; **Designed** = in
> this spec, not built.

## Contents

1. [Synopsis](#synopsis)
2. [Models](#models)
3. [Operation](#operation)
4. [Global options](#global-options)
5. [`poam generate` parameters](#poam-generate-parameters)
6. [Exit codes](#exit-codes)
7. [Examples](#examples)
8. [NIST alignment](#nist-alignment)

## Synopsis

```
mint-oscal <model> generate --from <source> [SRC|-] [DEST] [options]
```

`SRC` is a source-report file or `-`/omitted for stdin. `DEST` is a file or omitted for
stdout. The command is a filter: it reads one report and writes one OSCAL document.

## Models

| Model | OSCAL document | Role |
| --- | --- | --- |
| `poam` | Plan of Action & Milestones | emit (flagship) |
| `ar` | Assessment Results | emit |
| `component-definition` | Component Definition | emit |
| `profile` | Profile | consume (the ODP bar) |
| `catalog` | Catalog | consume (control text) |

## Operation

| Operation | Effect |
| --- | --- |
| `generate` | Build the model from a source report through the IR. |
| `validate`, `convert` | Delegated to `oscal-cli`; not re-implemented. |

## Global options

Adopted verbatim from `oscal-cli`:

| Option | Effect |
| --- | --- |
| `-q`, `--quiet` | Errors only. |
| `--no-color` | Disable ANSI color. |
| `--show-stack-trace` | Full trace on error. |
| `--version` | Tool version and supported OSCAL version. |
| `-h`, `--help` | Help. |

## `poam generate` parameters

Each flag maps to the OSCAL field it populates. POA&M requires `system-id` **or**
`import-ssp` — supply exactly one.

| Flag | OSCAL field / effect | Required | Default |
| --- | --- | --- | --- |
| `--from SOURCE` | source adapter (installed: `qureddy`) | yes | — |
| `SRC` / `-` | source report | yes | stdin |
| `-o`, `--output DEST` | output destination | no | stdout |
| `--to FORMAT` | encoding `JSON`\|`XML`\|`YAML` | no | `JSON` |
| `--overwrite` | overwrite `DEST` | no | off |
| `--system-id VALUE` | `system-id` (XOR `--import-ssp`) | one of | subject locator |
| `--system-id-type URI` | `system-id/@identifier-type` | no | `https://ietf.org/rfc/rfc3986` |
| `--import-ssp HREF` | `import-ssp` (XOR `--system-id`) | one of | — |
| `--title TEXT` | `metadata/title` | no | derived |
| `--doc-version VER` | `metadata/version` | no | `0.1.0` |
| `--oscal-version VER` | `metadata/oscal-version` | no | `1.2.2` |
| `--now TS` | `metadata/last-modified` (determinism) | no | scan completion time |
| `--published TS` | `metadata/published` | no | omitted |
| `--prepared-by NAME` | `responsible-party` | no | omitted |
| `--cbom HREF` | `relevant-evidence` (CycloneDX CBOM) | no | omitted |
| `--profile PATH` | consume Profile for the ODP bar | no | omitted |
| `--framework ID` | control framework: `scf-qts` (SCF Quantum Security) or `nist` (SP 800-53r5) | no | `scf-qts` |
| `--validate` | validate output via `oscal-cli` or structural | no | off |

Evidence carries hashes only (`command-sha256`, `stdout-sha256`), never raw excerpts.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Validation or structural failure. |
| `2` | Usage error (bad flag, unknown source or model). |

## Examples

```bash
# minimal: stdin to stdout, JSON
qureddy scan example.com:443 | mint-oscal poam generate --from qureddy

# full: XML, pinned timestamp, validated
mint-oscal poam generate --from qureddy scan.json --to XML \
  --system-id "tls://example.com:443" --prepared-by "BreachSAFE" \
  --now 2026-07-27T03:21:54Z --validate -o example.poam.xml

# chain into the NIST validator
mint-oscal poam generate --from qureddy scan.json | oscal-cli poam validate -
```

## NIST alignment

The grammar mirrors `oscal-cli`: model-first groups (`poam`, `ar`, `component-definition`,
`profile`, `catalog`), the `--to`/`--overwrite`/global flags verbatim, and `<source>
[dest]` positionals. Flags with no NIST analog (`--from`, `--now`, `--system-id`, …) exist
because mint-oscal *produces* OSCAL from a foreign source, which `oscal-cli` never does.
See [cli-design.md](cli-design.md) for the rationale and [architecture.md](architecture.md)
for where the CLI sits in the system.
