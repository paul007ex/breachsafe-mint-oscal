# Profile compiler reference

The Profile compiler consumes the Registry contract and emits an OSCAL Profile through
Compliance Trestle. It does not own framework mappings or Catalog storage.

## Contents

1. [Responsibilities](#responsibilities)
2. [CLI contract](#cli-contract)
3. [Compilation sequence](#compilation-sequence)
4. [Forbidden behavior](#forbidden-behavior)
5. [Milestone and issues](#milestone-and-issues)
6. [Schema compatibility](#schema-compatibility)

## Responsibilities

The compiler loads one governed objective, verifies its selected controls against the pinned
Catalog, constructs a Trestle Profile, validates/resolves it, and emits a Profile plus a
provenance receipt.

## CLI contract

```bash
mint-oscal profile create \
  --framework nist-800-53r5 \
  --objective pqc-readiness \
  --catalog nist-800-53r5 \
  --registry policy \
  [destination]

mint-oscal profile validate <file-or-URI>
mint-oscal profile convert --to FORMAT <source> [destination]
mint-oscal profile resolve --to FORMAT <profile-URI> [destination]
mint-oscal profile explain <file-or-URI>
```

`validate`, `convert`, and `resolve` preserve the official `oscal-cli` meanings. `create`
and `explain` are BreachSAFE additions.

## Compilation sequence

```text
Registry
  → strict load and semantic validation
  → objective resolution
  → Trestle Profile model/workspace
  → trestle validate
  → trestle profile-resolve
  → portable file:// references
  → oscal-cli validate
  → Profile + provenance receipt
```

Profiles contain control-selection intent. Targets and evidence enter through Assessment
Plans and Assessment Results, not Profile creation.

## Forbidden behavior

The compiler must not accept arbitrary control IDs, infer mappings from natural language or
scanner output, download unpinned Catalogs, create a second OSCAL schema, mutate the Registry,
or mix evidence into a Profile.

## Milestone and issues

Milestone `0.4.2 - Profile compiler`:

- #153 Profile CLI grammar
- #166 dependency-cycle detection
- #133 Catalog/Profile consumption and resolution
- #134 governed Profile emission
- #154 objective compilation
- #155 provenance receipts
- #156 conformance and negative tests

The compiler cannot start its production path until the Registry foundation reaches its
`0.4.1` exit gate.

## Schema compatibility

The emitted object must be an OSCAL Profile, not a BreachSAFE wrapper around one. Its
required fields are `profile.uuid`, `profile.metadata`, and `profile.imports`; metadata
requires `title`, `last-modified`, `version`, and `oscal-version`. Each import must select
controls using exactly one of `include-all` or `include-controls`.

The compatibility sequence is:

```text
Trestle 5.0.0 model validation
  → Trestle Profile resolution
  → materialize trestle:// as file://
  → oscal-cli 3.2.0 validation
```

The compiler must not call `oscal-cli` on a raw `trestle://` Profile. That URI is meaningful
inside a Trestle workspace, while `oscal-cli` requires a resolvable portable URI or path.
The complete positive/negative matrix is in [the conformance contract](../conformance.md).
