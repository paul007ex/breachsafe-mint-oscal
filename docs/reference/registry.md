# Registry reference

The registry is the governed control-plane source of truth. It is independent from the
evidence-plane policy tables under `src/mint_oscal/policy/`.

## Contents

1. [Responsibilities](#responsibilities)
2. [Layout](#layout)
3. [Contract](#contract)
4. [Commands](#commands)
5. [Initial catalog options](#initial-catalog-options)
6. [Source authority and drift](#source-authority-and-drift)
7. [Milestone and issues](#milestone-and-issues)

## Responsibilities

The registry owns Catalog pins, framework packs, objectives, control crosswalks, review
status, source digests, and the deterministic lockfile. It does not emit Profiles or inspect
scanner findings.

## Layout

```text
policy/
├── registry.yaml
├── catalogs/<catalog-id>/catalog.json
├── packs/<pack-id>/pack.yaml
├── packs/<pack-id>/objectives/<objective-id>.yaml
├── registry.lock.json
└── generated/
```

Source YAML is reviewed. Generated OSCAL and lock artifacts are reproducible outputs.

## Contract

Every Catalog has an ID, UUID, OSCAL version, source URI, local path, document version, and
SHA-256. Every objective has a framework, Catalog, version, selected control IDs, rationale,
evidence requirements, and review metadata.

The loader rejects unknown fields, duplicate IDs, missing Catalogs, invalid control IDs,
framework/catalog mismatches, unresolved dependencies, and unapproved release content.

The lock records the source Git revision, resolver version, Catalog UUID/digest, objective
source digest, and canonical selected-control arrays. `source_sha256` is computed over RFC 8785
canonical JSON of the parsed registry document, not raw YAML bytes; comments and formatting do
not change identity. The lock records the canonicalization method explicitly.

## Initial catalog options

The registry is catalog-agnostic. It does not contain NIST-specific branches. Each option
is a pinned Catalog or Profile entry with its own source, digest, OSCAL version, license,
and validation state.

| Registry ID | Content | Role | State |
| --- | --- | --- | --- |
| `nist-800-53r5` | NIST SP 800-53 Rev. 5 Catalog | Detailed security-control source | P0 active lane |
| `scf-qts-2026-2` | SCF 2026.2 Quantum Security Catalog/Profile | PQC and crypto-agility controls | P0 local fixture |
| `scf-universal-2026-2` | SCF 2026.2 universal control catalog | Cross-framework control layer | P1, pending same-version OSCAL export |
| `nist-csf-2` | NIST CSF 2.0 Catalog | Broad framework view | P1 |
| `fedramp-20x` | FedRAMP 20x Catalog/Profile | Federal authorization baseline | P1 |
| `cis-controls-8-1` | CIS Controls 8.1 community Catalog | Community framework | P2 |
| `bsi-grundschutz` | BSI Grundschutz++ community Catalog | German control framework | P2 |

PCI DSS, NCUA, FFIEC, CMMC, and similar frameworks are not registered as native Catalogs
until an authoritative OSCAL artifact is found and its license and provenance are verified.
SCF STRM mappings may represent those frameworks without fabricating Catalogs.

The first registry proof must expose at least:

```text
mint-oscal registry list
mint-oscal registry show nist-800-53r5
mint-oscal registry show scf-qts-2026-2
mint-oscal registry validate --registry policy
mint-oscal registry lock --registry policy
mint-oscal registry verify --registry policy
```

## Source authority and drift

The SCF workbook and QTS artifacts are pinned locally at:

```text
../breachsafe-common/standards/scf/2026.2/
```

The official SCF 2026.2 workbook digest is:

```text
9e0a4df4993726c95e636f04b3028d8b5edeba2bda45d16ed6722b13540e6835
```

The QTS Catalog and Profile declare OSCAL 1.1.2. The active Trestle compiler lane is
OSCAL 1.2.1. A QTS entry must therefore carry an explicit compatibility state and cannot
be treated as Trestle-ready until conversion, schema validation, profile resolution, and
downstream validation pass.

The SCF OSCAL exporter currently reports an older published export than the SCF 2026.2
GitHub workbook. Never combine exporter output with the 2026.2 workbook without recording
the mismatch and blocking the import.

## Commands

```bash
mint-oscal registry init --output policy
mint-oscal registry add-catalog \\
  --registry policy \\
  --id nist-800-53r5 \\
  --file /path/to/catalog.json \\
  --source-uri https://github.com/usnistgov/oscal-content \\
  --release v1.5.0 \\
  --license NIST \\
  --authority NIST
mint-oscal registry list
mint-oscal registry show nist-800-53r5:pqc-readiness
mint-oscal registry validate --registry policy
mint-oscal registry lock --registry policy
mint-oscal registry verify --registry policy
```

`registry init` creates a valid `bootstrap` registry and the directory layout. It does not
fabricate a Catalog, Profile, Pack, or review decision. A bootstrap registry may have empty
collections and no defaults. `registry add-catalog` copies a local OSCAL Catalog, records its
UUID, version, provenance, retrieval date, and SHA-256, then validates and locks the existing
registry. Imported sources are marked `source.verified: false`: remote URLs are provenance
metadata, not proof of origin, and acquisition/digest verification remains a separate audited
step. The CLI has no offline-safe way to assert that a remote URI matches the local bytes.
Registries written before this field existed are normalized to `verified: false` when loaded.

An `active` registry requires defaults that resolve to registered Catalog, Profile, and Pack
entries. Registries created before the lifecycle field existed are treated as `active` for
backward compatibility.

## Milestone and issues

Milestone `0.4.1 - Registry foundation`:

- #147 governed registry
- #148 Catalog import and pinning
- #149 strict schema and loader
- #150 registry CLI
- #151 review workflow
- #152 determinism and fail-closed tests
- #164 source/generated/release separation
- #165 signed lock and release verification
- #137 Catalog authoring governance

The enterprise projection is deferred to `0.6.0` (#160, #161, #163). Git remains the
authoritative source even when those projections exist.
