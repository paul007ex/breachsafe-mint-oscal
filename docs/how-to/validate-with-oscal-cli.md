# Validate with oscal-cli

Goal: run the authoritative NIST schema-and-constraint check on a POA&M with `oscal-cli`.
`mint-oscal`'s in-process checks catch semantic problems but do not cover full NIST
conformance; this guide covers the authoritative step and how it relates to the in-process
check.

## Contents

1. [Two levels of validation](#two-levels-of-validation)
2. [In-process check (no external tool)](#in-process-check-no-external-tool)
3. [Authoritative check with oscal-cli](#authoritative-check-with-oscal-cli)
4. [Related](#related)

## Two levels of validation

| Level | Command | Needs | Confirms |
| --- | --- | --- | --- |
| Layer-2 in-process | `mint-oscal poam generate --validate` or `mint-oscal poam validate` | nothing | uuid/ref/ns integrity, OSCAL structure and datatypes, BreachSAFE vocab |
| Authoritative | `oscal-cli validate` | `oscal-cli` on `PATH` | NIST OSCAL schema and constraints |

Neither level rules on the finding-to-control mapping or a compliance verdict. That is a
policy judgment; see [../explanation/valid-vs-compliant.md](../explanation/valid-vs-compliant.md).

## In-process check (no external tool)

The Layer-2 check is pure Python and needs no external tool. Fold it into generation, or run
it on an existing document:

```bash
# fail generation (exit 1) if the output has a semantic problem
mint-oscal poam generate --from cbom examples/example.cbom.json --validate > poam.json

# check a document produced anywhere (yours or another tool's)
mint-oscal poam validate poam.json
```

`mint-oscal poam validate` accepts `-` to read from STDIN, so you can generate and check in one
chain:

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json | mint-oscal poam validate -
```

A valid document exits `0`. The tool logs a reminder on STDERR that this is not NIST schema
validation and that you should run `oscal-cli` for that.

## Authoritative check with oscal-cli

`oscal-cli` reads a file, not STDIN. Mint to a file first, then validate the file:

1. Mint the POA&M:

   ```bash
   mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json
   ```

2. Validate the file:

   ```bash
   oscal-cli validate poam.json
   ```

A valid document prints `The file 'file:.../poam.json' is valid.` and exits `0`.

Install NIST [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli) (it needs a Java
17 runtime) if it is not on `PATH`. `mint-oscal` documents declare `oscal-version` `1.2.2` and
were validated against `oscal-cli` 3.2.0.

Do not pass `-` to `oscal-cli`; it has no STDIN mode and treats `-` as a filename, which fails
with `The provided source 'file:.../-' does not exist.` The older `oscal-cli poam validate`
form still works but prints a deprecation warning; use `oscal-cli validate`.

## Related

- [Exit codes](../reference/exit-codes.md): how the two checks signal success and failure
- [Emit XML or YAML](emit-xml-or-yaml.md): the other `oscal-cli`-backed step
- [CLI reference](../reference/cli.md)
