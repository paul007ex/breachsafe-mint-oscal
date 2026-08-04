# Emit XML or YAML

Goal: produce a POA&M in XML or YAML. Mint JSON with `mint-oscal`, then convert the JSON
with `oscal-cli`.

JSON is the only encoding `mint-oscal` writes natively today. Native `--to xml` and
`--to yaml` are planned (ADR-0005) and currently exit `3`; see
[Native XML/YAML output is planned](#native-xmlyaml-output-is-planned). The recipe below is
the working path and uses only commands that run today.

## Contents

1. [Prerequisites](#prerequisites)
2. [Convert to XML](#convert-to-xml)
3. [Convert to YAML](#convert-to-yaml)
4. [Native XML/YAML output is planned](#native-xmlyaml-output-is-planned)
5. [Related](#related)

## Prerequisites

- `mint-oscal` installed (Python 3.12+).
- `oscal-cli` 3.2.0 on `PATH`. Install NIST
  [`oscal-cli`](https://github.com/metaschema-framework/oscal-cli); it needs a Java 17 runtime.
- A CBOM to mint from. The repository ships `examples/example.cbom.json`.

## Convert to XML

1. Mint the POA&M as JSON:

   ```bash
   mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json
   ```

2. Convert the JSON to XML with `oscal-cli`:

   ```bash
   oscal-cli convert --to=xml poam.json poam.xml --overwrite
   ```

`oscal-cli` exits `0` and writes `poam.xml`. The document opens with the OSCAL root element:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plan-of-action-and-milestones xmlns="http://csrc.nist.gov/ns/oscal/1.0" uuid="4f13bddd-95ce-5673-90dd-6d3b40af1025">
  <metadata>
    <title>POA&amp;M - CBOM scan of example.com:443</title>
    <oscal-version>1.2.2</oscal-version>
```

## Convert to YAML

Reuse the `poam.json` from the previous step and change the target format:

```bash
oscal-cli convert --to=yaml poam.json poam.yaml --overwrite
```

`oscal-cli` exits `0` and writes `poam.yaml`:

```yaml
---
plan-of-action-and-milestones:
  metadata:
    title: POA&M - CBOM scan of example.com:443
    oscal-version: 1.2.2
```

`--overwrite` replaces an existing target file. Omit it to make `oscal-cli` refuse to clobber
an existing path.

## Native XML/YAML output is planned

`mint-oscal poam generate --to xml` and `--to yaml` are recorded in
[ADR-0005](../adr/0005-render-and-validation-boundary.md) and are not implemented. Requesting
either exits `3` with a `not_implemented` diagnostic on STDERR, even when `oscal-cli` is on
`PATH`:

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json --to xml
# exit 3; STDERR: not_implemented ... render(fmt='xml') ... not wired in yet (ADR-0005)
```

Until that lands, mint JSON and convert with `oscal-cli` as shown above. See
[Exit codes](../reference/exit-codes.md) for exit `3`.

## Related

- [Validate with oscal-cli](validate-with-oscal-cli.md)
- [Mint from a CBOM](mint-from-a-cbom.md)
- [CLI reference](../reference/cli.md)
