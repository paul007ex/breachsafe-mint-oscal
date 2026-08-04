# Emit XML or YAML

Goal: produce a POA&M in XML or YAML instead of the default JSON.

## Contents

1. [Select the encoding](#select-the-encoding)
2. [Why oscal-cli is required](#why-oscal-cli-is-required)
3. [If oscal-cli is missing](#if-oscal-cli-is-missing)
4. [Related](#related)

## Select the encoding

Pass `--to` with `json` (default), `xml`, or `yaml`:

```bash
# XML
mint-oscal poam generate --from cbom scan.cbom.json --to xml > poam.xml

# YAML
mint-oscal poam generate --from cbom scan.cbom.json --to yaml > poam.yaml
```

Output still goes to STDOUT; redirect it to the file extension you want.

## Why oscal-cli is required

JSON is `mint-oscal`'s native, dependency-free encoding. XML and YAML are produced by shelling
out to NIST [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli), which must be on
your `PATH`. This keeps a single, standard converter responsible for the alternate encodings
rather than re-implementing them. The decision is recorded in
[ADR-0005](../adr/0005-render-and-validation-boundary.md).

## If oscal-cli is missing

Requesting `--to xml` or `--to yaml` without `oscal-cli` installed exits with code `3`
(output needs a local dependency). Two fixes:

- install `oscal-cli` and re-run; or
- keep the default JSON (drop `--to`) — JSON has no external dependency.

See [../reference/exit-codes.md](../reference/exit-codes.md).

## Related

- [Validate with oscal-cli](validate-with-oscal-cli.md)
- [CLI reference](../reference/cli.md)
