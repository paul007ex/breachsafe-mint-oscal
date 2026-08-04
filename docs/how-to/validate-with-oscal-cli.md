# Validate with oscal-cli

Goal: run the authoritative NIST schema-and-constraint check on a POA&M. `mint-oscal`'s
built-in `--validate` / `poam validate` are pure-Python semantic checks — necessary but not
sufficient for full NIST conformance. This guide covers the authoritative step.

## Contents

1. [Two levels of validation](#two-levels-of-validation)
2. [In-process check (no external tool)](#in-process-check-no-external-tool)
3. [Authoritative check with oscal-cli](#authoritative-check-with-oscal-cli)
4. [Validate in a pipeline](#validate-in-a-pipeline)
5. [Related](#related)

## Two levels of validation

| Level | Command | Needs | Confirms |
| --- | --- | --- | --- |
| In-process | `--validate` or `mint-oscal poam validate` | nothing | uuid/ref/ns integrity, OSCAL structure + datatypes, BreachSAFE vocab |
| Authoritative | `oscal-cli poam validate` | `oscal-cli` on `PATH` | NIST OSCAL schema + constraints |

Neither blesses the finding→control mapping or the compliance verdict — that is a policy
judgment, not a validation result. See
[../explanation/valid-vs-compliant.md](../explanation/valid-vs-compliant.md).

## In-process check (no external tool)

Fold the check into generation, or run it on an existing document:

```bash
# fail generation (exit 1) if the output has a semantic problem
mint-oscal poam generate --from cbom scan.cbom.json --validate > poam.json

# check a document produced anywhere (yours or another tool's)
mint-oscal poam validate poam.json
```

## Authoritative check with oscal-cli

Install NIST [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli), then:

```bash
oscal-cli poam validate poam.json
```

`mint-oscal` was validated against `oscal-cli` 3.2.0 and the NIST v1.2.2 JSON schema; documents
declare `oscal-version` `1.2.2`.

## Validate in a pipeline

Because `mint-oscal` writes to STDOUT, you can generate and validate in one chain:

```bash
mint-oscal poam generate --from cbom scan.cbom.json | mint-oscal poam validate -
```

Or hand the same stream to `oscal-cli`:

```bash
mint-oscal poam generate --from cbom scan.cbom.json | oscal-cli poam validate -
```

## Related

- [Exit codes](../reference/exit-codes.md) — how the two checks signal success and failure
- [Emit XML or YAML](emit-xml-or-yaml.md) — the other `oscal-cli`-backed feature
- [CLI reference](../reference/cli.md)
