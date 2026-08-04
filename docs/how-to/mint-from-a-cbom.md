# Mint a POA&M from a CBOM

Goal: turn a CycloneDX CBOM into an OSCAL POA&M. This is the most common `mint-oscal` path.
Assumes `mint-oscal` is installed (Python 3.12+).

## Contents

1. [From a file](#from-a-file)
2. [Straight from a QuReddy scan](#straight-from-a-qureddy-scan)
3. [Add producer cross-checks](#add-producer-cross-checks)
4. [What the CBOM adapter reads](#what-the-cbom-adapter-reads)
5. [Related](#related)

## From a file

```bash
mint-oscal poam generate --from cbom scan.cbom.json > poam.json
```

`--from cbom` selects the CycloneDX CBOM adapter. Output is JSON on STDOUT; redirect it to a
file or pipe it onward. Findings map to the default `scf-qts` framework unless you pass
`--framework` (see [choose-a-control-framework.md](choose-a-control-framework.md)).

## Straight from a QuReddy scan

QuReddy can emit a CBOM on STDOUT, so the two tools compose without a temporary file:

```bash
qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -
```

The `-` tells `mint-oscal` to read the report from STDIN.

## Add producer cross-checks

`--from` stays vendor-neutral. To layer in producer-specific enrichment, add one or more
`--extension` flags (repeatable):

```bash
mint-oscal poam generate --from cbom scan.cbom.json --extension breachsafe > poam.json
```

The extension is orthogonal to the source: it adds cross-checks on the IR without coupling the
adapter to a producer.

## What the CBOM adapter reads

The adapter maps CBOM crypto assets into the neutral IR (`Finding`/`Subject`), from which the
POA&M emitter builds the document. Crypto facts are carried as readable namespaced props;
evidence is carried as hashes, never raw excerpts. The design rationale is in
[../explanation/agnostic-core.md](../explanation/agnostic-core.md), and the CBOM-first
ingestion decision is [ADR-0006](../adr/0006-cbom-first-ingestion.md).

## Related

- [Choose a control framework](choose-a-control-framework.md)
- [Emit XML or YAML](emit-xml-or-yaml.md)
- [Validate with oscal-cli](validate-with-oscal-cli.md)
- [CLI reference](../reference/cli.md) · [Exit codes](../reference/exit-codes.md)
