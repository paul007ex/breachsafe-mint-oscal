# Registry and Profile compiler plan

This is the implementation plan for taking the registry/Profile control plane from the
current 8/10 design to a production-ready 10/10 boundary. It is deliberately separate from
the evidence plane (`CBOM -> IR -> Assessment Results/POA&M`).

## Contents

1. [Current state](#current-state)
2. [Target architecture](#target-architecture)
3. [Registry contract](#registry-contract)
4. [Profile compiler contract](#profile-compiler-contract)
5. [Execution plan](#execution-plan)
6. [Quality and conformance gates](#quality-and-conformance-gates)
7. [Definition of done](#definition-of-done)
8. [Known non-goals](#known-non-goals)

## Current state

The shipped policy packs under `src/mint_oscal/policy/` answer a different question:

```text
finding readiness verdict -> control IDs + severity + risk text
```

They are useful evidence-plane policy tables, but they are not yet a registry for Profile
creation. A Profile registry must answer:

```text
framework + catalog + governed objective -> reviewed control selection
```

The distinction is mandatory. The Profile compiler must not infer control mappings from a
scanner finding or silently reinterpret the existing POA&M crosswalk.

Current implementation status:

| Capability | State |
| --- | --- |
| OSCAL Profile schema contract | Documented |
| Trestle Profile validation/resolution gate | Implemented in fixture gate |
| `oscal-cli` portable Profile validation | Implemented in fixture gate |
| Git registry layout decision | Documented |
| Strict registry loader | Implemented in `mint_oscal.registry` |
| Deterministic registry lock compiler | Implemented and tested |
| `mint-oscal registry` CLI | Implemented: list/show/validate/lock/verify |
| `mint-oscal profile create` | Not implemented |
| Generated Profile provenance receipt | Not implemented |

## Target architecture

```text
                         CONTROL PLANE

  Git policy source
       │
       ├── Catalog pins (URI, UUID, version, SHA-256)
       ├── Framework packs
       └── Reviewed objectives/crosswalks
       │
       ▼
  strict registry loader
       │
       ▼
  deterministic registry.lock.json
       │
       ▼
  objective resolver
       │
       ▼
  Compliance Trestle Profile model/workspace
       │
       ├── trestle validate
       ├── trestle profile-resolve
       └── portable file:// materialization
       │
       ▼
  oscal-cli validate
       │
       ├── Profile JSON
       └── resolution/provenance receipt

                         EVIDENCE PLANE

  CBOM / QuReddy / Prowler
       → adapters → mint.ir.v1 → Qurum/analysis
       → Assessment Results / POA&M
```

The control plane produces assessment intent. The evidence plane supplies observed facts. A
Profile does not contain scan findings or target endpoints; those enter through an Assessment
Plan and later Assessment Results.

## Registry contract

### Source layout

```text
policy/
├── registry.yaml
├── catalogs/
│   └── nist-800-53r5/
│       ├── catalog.json
│       └── metadata.yaml
├── packs/
│   └── nist-800-53r5/
│       ├── pack.yaml
│       ├── objectives/
│       │   └── pqc-readiness.yaml
│       └── control-crosswalk.yaml
├── registry.lock.json
└── generated/
    └── profiles/
```

Source files are reviewed. Generated OSCAL and lock artifacts are reproducible outputs. A
generated file must never become a second hand-edited source of truth.

### Registry top-level object

```yaml
schema: breachsafe.registry/v1
catalogs:
  - id: nist-800-53r5
    title: NIST SP 800-53 Revision 5
    oscal-version: 1.2.1
    document-version: 5.0.0
    source-uri: https://github.com/usnistgov/oscal-content/...
    local-path: catalogs/nist-800-53r5/catalog.json
    sha256: <sha256>
  - id: scf-qts-2026-2
    title: SCF 2026.2 Quantum Security
    oscal-version: 1.1.2
    document-version: SCF 2026.2
    source-uri: https://github.com/securecontrolsframework/securecontrolsframework/releases/tag/2026.2
    local-path: catalogs/scf-qts-2026-2/catalog.json
    sha256: 9e0a4df4993726c95e636f04b3028d8b5edeba2bda45d16ed6722b13540e6835
    compatibility: requires-oscal-1.2.1-conversion-test
packs:
  - id: nist-800-53r5
    framework: nist-800-53r5
    catalog: nist-800-53r5
    version: 1.0.0
    objectives:
      - pqc-readiness
  - id: scf-qts-2026-2
    framework: scf
    catalog: scf-qts-2026-2
    version: 0.1.0
    objectives:
      - pqc-readiness
```

### Objective object

```yaml
schema: breachsafe.objective/v1
id: pqc-readiness
title: Post-quantum cryptography readiness
framework: nist-800-53r5
catalog: nist-800-53r5
version: 1.0.0
controls:
  - id: sc-12
    rationale: Cryptographic key establishment and management
  - id: sc-13
    rationale: Cryptographic protection
review:
  status: approved
  reviewer: security-architecture
  reviewed-at: 2026-08-24
evidence-requirements:
  - cbom
  - tls-scan
```

The loader must reject unknown fields, duplicate IDs, missing Catalogs, invalid control IDs,
unreviewed objectives used in release mode, and framework/catalog mismatches.

### Lock contract

The lock is canonical JSON with sorted keys and stable arrays:

```json
{
  "schema": "breachsafe.registry.lock/v1",
  "source_revision": "<git-sha>",
  "resolver_version": "mint-oscal/<version>",
  "catalogs": {
    "nist-800-53r5": {
      "uuid": "<catalog-uuid>",
      "sha256": "<sha256>",
      "oscal_version": "1.2.1"
    }
  },
  "objectives": {
    "nist-800-53r5:pqc-readiness": {
      "source_sha256": "<sha256>",
      "control_ids": ["sc-12", "sc-13"]
    }
  }
}
```

The lock is an integrity and reproducibility artifact. It does not replace human review or
claim that an objective is legally or regulatorily sufficient.

## Profile compiler contract

```bash
mint-oscal profile create \
  --framework nist-800-53r5 \
  --objective pqc-readiness \
  --catalog nist-800-53r5 \
  --registry policy \
  [destination]
```

The same contract must work for SCF QTS without a second command family:

```bash
mint-oscal profile create \
  --framework scf \
  --catalog scf-qts-2026-2 \
  --objective pqc-readiness \
  --registry policy \
  [destination]
```

The command selects registry data. It does not infer controls from the framework name,
download an unpinned catalog, or copy NIST control IDs into an SCF objective.

The compiler must:

1. Load and validate the registry.
2. Verify the requested framework, Catalog, and objective exist.
3. Verify every selected control exists in the pinned Catalog.
4. Build the Profile through the Trestle model/workspace boundary.
5. Validate and resolve with Trestle.
6. Materialize portable references for `oscal-cli`.
7. Validate with `oscal-cli`.
8. Emit the Profile and a provenance receipt.

The compiler must not:

- accept arbitrary control IDs without registry provenance;
- infer controls from natural language or scan output;
- create a custom OSCAL Profile schema;
- add endpoints or evidence to the Profile;
- silently fetch unpinned remote Catalogs;
- mutate the source registry during compilation.

## Execution plan

### 0.4.0 — contract freeze

Issue [#142](https://github.com/paul007ex/breachsafe-mint-oscal/issues/142).

Exit gate: ADRs, CLI grammar, registry schema, lock format, provenance fields, and
Trestle/oscal-cli boundaries are documented and reviewed.

### 0.4.1 — registry foundation

Issues [#147](https://github.com/paul007ex/breachsafe-mint-oscal/issues/147),
[#148](https://github.com/paul007ex/breachsafe-mint-oscal/issues/148),
[#149](https://github.com/paul007ex/breachsafe-mint-oscal/issues/149),
[#150](https://github.com/paul007ex/breachsafe-mint-oscal/issues/150),
[#151](https://github.com/paul007ex/breachsafe-mint-oscal/issues/151),
[#152](https://github.com/paul007ex/breachsafe-mint-oscal/issues/152),
[#164](https://github.com/paul007ex/breachsafe-mint-oscal/issues/164),
[#165](https://github.com/paul007ex/breachsafe-mint-oscal/issues/165), and
[#137](https://github.com/paul007ex/breachsafe-mint-oscal/issues/137).

Implementation order: freeze schemas; import and digest-pin one real Catalog; implement
strict loading; generate the lock; add registry commands; then add review, provenance, and
generated-artifact drift checks.

Exit gate: a clean checkout produces the same lock and generated artifacts, and every
negative fixture fails closed.

### 0.4.2 — Profile compiler

Issues [#153](https://github.com/paul007ex/breachsafe-mint-oscal/issues/153),
[#154](https://github.com/paul007ex/breachsafe-mint-oscal/issues/154),
[#155](https://github.com/paul007ex/breachsafe-mint-oscal/issues/155),
[#156](https://github.com/paul007ex/breachsafe-mint-oscal/issues/156),
[#133](https://github.com/paul007ex/breachsafe-mint-oscal/issues/133),
[#134](https://github.com/paul007ex/breachsafe-mint-oscal/issues/134), and
[#166](https://github.com/paul007ex/breachsafe-mint-oscal/issues/166).

Exit gate: `profile create` emits a governed Profile that passes Trestle validation,
resolution, portable `oscal-cli` validation, deterministic-output tests, and provenance
checks.

### 0.6.0 — enterprise projection

Issues [#160](https://github.com/paul007ex/breachsafe-mint-oscal/issues/160),
[#161](https://github.com/paul007ex/breachsafe-mint-oscal/issues/161), and
[#163](https://github.com/paul007ex/breachsafe-mint-oscal/issues/163).

The API, PostgreSQL database, and external OSCAL Content Registry are rebuildable
projections. They never replace Git as the policy authority.

### 0.6.1 — additional framework packs

Issues [#167](https://github.com/paul007ex/breachsafe-mint-oscal/issues/167) and
[#162](https://github.com/paul007ex/breachsafe-mint-oscal/issues/162).

Although scheduled here, #167's identity rules are a prerequisite for adding multiple
frameworks. The framework-pack harness remains blocked until those rules are accepted.

## Quality and conformance gates

Every registry/Profile change must pass:

| Gate | Purpose |
| --- | --- |
| YAML/schema validation | Reject malformed or unknown registry fields |
| Semantic registry validation | Reject missing Catalogs, bad control IDs, duplicates, cycles |
| Determinism | Same source revision produces byte-identical lock/output |
| Digest verification | Detect modified Catalogs, objectives, and generated artifacts |
| Trestle validation | Confirm Profile model/workspace correctness |
| Trestle resolution | Confirm imports resolve to a usable Catalog |
| oscal-cli validation | Independent OSCAL schema/constraint authority |
| Negative controls | Prove required fields and invalid selection modes are rejected |
| Documentation contract | Numbered contents, valid local links, no stale CLI claims |
| Review gate | Confirm issue acceptance criteria are actually met |

## Definition of done

The registry/Profile lane reaches 10/10 when:

- a new reviewer can add an objective without editing Python;
- malformed, ambiguous, or unreviewed release content is rejected;
- the lock identifies every input by digest and source revision;
- Profile output is produced through Trestle conventions;
- `oscal-cli` validates the portable result;
- every generated Profile has a resolution receipt;
- repeated builds are byte-identical;
- no database or external registry is required for OSS operation;
- enterprise projections can be rebuilt from Git;
- adding a framework does not change the CLI grammar or OSCAL engine.

## Known non-goals

- Automatically deciding which controls a regulator requires.
- Treating natural-language prompts as authoritative control mappings.
- Replacing Trestle or `oscal-cli` with a Mint-specific OSCAL implementation.
- Mixing scan evidence into Profiles.
- Building the enterprise registry before the Git registry is deterministic.
