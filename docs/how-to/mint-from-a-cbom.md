# Mint a POA&M from a CBOM

Goal: turn a CycloneDX CBOM into an OSCAL POA&M. This is the most common `mint-oscal` path.

## Contents

1. [Prerequisites](#prerequisites)
2. [From a file](#from-a-file)
3. [Add producer cross-checks](#add-producer-cross-checks)
4. [Straight from a QuReddy scan (planned)](#straight-from-a-qureddy-scan-planned)
5. [What the CBOM adapter reads](#what-the-cbom-adapter-reads)
6. [Related](#related)

## Prerequisites

- `mint-oscal` installed (Python 3.14+).
- A CBOM file. A CBOM (Cryptographic Bill of Materials) is a CycloneDX document that lists the
  cryptographic assets observed on a target. The repository ships one at
  `examples/example.cbom.json`; a scanner such as QuReddy will produce one per scan once CBOM
  emission ships (see [below](#straight-from-a-qureddy-scan-planned)).

## From a file

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json
```

`--from cbom` selects the CycloneDX CBOM adapter. Output is JSON on STDOUT; redirect it to a
file or pipe it onward. The command exits `0` on success. Findings map to the default `scf-qts`
framework unless you pass `--framework` (see
[choose-a-control-framework.md](choose-a-control-framework.md)).

## Add producer cross-checks

`--from` stays vendor-neutral. To layer in producer-specific enrichment, add one or more
`--extension` flags (repeatable):

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json --extension breachsafe > poam.json
```

The extension is orthogonal to the source: it adds cross-checks on the intermediate
representation without coupling the adapter to a producer.

## Straight from a QuReddy scan (planned)

The target pipeline pipes a QuReddy scan straight into `mint-oscal` with no temporary file:

```bash
# planned: QuReddy CBOM emission is tracked in QuReddy #61 and is not shipped
qureddy scan tls example.com --format cbom | mint-oscal poam generate --from cbom -
```

`qureddy scan ... --format cbom` is not implemented yet (QuReddy #61), so this pipe does not run
today. The `mint-oscal` side already reads a CBOM from STDIN with `-`, so any tool that writes a
CycloneDX CBOM to STDOUT composes the same way:

```bash
cat examples/example.cbom.json | mint-oscal poam generate --from cbom -
```

## What the CBOM adapter reads

The adapter maps CBOM crypto assets into the neutral intermediate representation, from which the
POA&M emitter builds the document. Crypto facts are carried as namespaced props and evidence as
hashes. The design rationale is in
[../explanation/agnostic-core.md](../explanation/agnostic-core.md), and the CBOM-first ingestion
decision is [ADR-0006](../adr/0006-cbom-first-ingestion.md).

## Related

- [Choose a control framework](choose-a-control-framework.md)
- [Validate with oscal-cli](validate-with-oscal-cli.md)
- [Emit XML or YAML](emit-xml-or-yaml.md)
- [CLI reference](../reference/cli.md) · [Exit codes](../reference/exit-codes.md)
