# OSCAL conformance contract

This document is the conformance contract for `mint-oscal`. It separates three gates:

## Contents

1. [Profile schema contract](#profile-schema-contract)
2. [Required validation sequence](#required-validation-sequence)
3. [Gate requirements](#gate-requirements)
4. [Scope boundary](#scope-boundary)
5. [Schema compatibility matrix](#schema-compatibility-matrix)

1. Trestle validates and resolves Profile documents in a Trestle workspace.
2. The official `oscal-cli` validates the portable OSCAL document against the upstream
   OSCAL metaschema and constraints.
3. Negative controls prove that each gate rejects a deliberately broken document.

`mint-oscal` does not implement a second Profile schema or resolver. The Profile compiler
must produce the same model and workspace conventions that Compliance Trestle consumes.
See [ADR-0010](adr/0010-trestle-aligned-profile-compiler.md).

## Profile schema contract

The authoritative OSCAL 1.2.1 Profile schema is vendored by the Trestle pressure-test
toolchain and is generated from the NIST OSCAL Profile metaschema:

- `oscal_profile_schema.json`
- `reference/OSCAL/src/metaschema/oscal_profile_metaschema.xml`

At the document root, `profile` is required. Inside `profile`, these are required:

| Object | Required fields |
| --- | --- |
| `profile` | `uuid`, `metadata`, `imports` |
| `metadata` | `title`, `last-modified`, `version`, `oscal-version` |
| `imports` | At least one import object |
| Import | Exactly one of `include-all` or `include-controls` |

`merge`, `modify`, `back-matter`, `published`, `revisions`, `props`, `links`, roles,
parties, and other metadata are optional. An import may carry `href` and
`exclude-controls`; `include-controls` must contain at least one selector.

## Required validation sequence

```text
registry/objective request
        │
        ▼
Trestle Profile model + Trestle workspace artifact
        │  trestle validate --type profile
        ▼
Trestle profile resolution
        │  materialize trestle:// references for portable validation
        ▼
oscal-cli validate <portable-profile.json>
        │
        ▼
positive and negative conformance controls
```

`oscal-cli` does not know Trestle's `trestle://` URI scheme. Passing a raw Trestle Profile
to `oscal-cli` is therefore not the portable validation step. The gate must first resolve
or materialize the referenced Catalog, then validate the resulting file URI/path.

## Gate requirements

- Trestle validation exits `0` for the Profile fixture.
- Trestle resolution produces a resolved Catalog without dangling imports.
- `oscal-cli 3.2.0` reports the portable Profile as valid.
- Removing `profile.uuid`, `metadata.version`, or `imports` is rejected.
- Replacing `include-controls` with both selection modes is rejected.
- The gate records tool versions and exits non-zero on missing validators.
- The same script runs locally and in CI.

The gate currently pins Compliance Trestle `5.0.0` and `oscal-cli 3.2.0`; changing either
version is a conformance decision, not an incidental dependency update.

The gate is implemented by [`scripts/oscal-conformance.sh`](../scripts/oscal-conformance.sh)
and exercised by [`.github/workflows/conformance.yml`](../.github/workflows/conformance.yml).
The workflow remains `workflow_dispatch` while repository Actions execution is blocked by
issue #46; the local gate is authoritative until that infrastructure constraint is closed.

## Scope boundary

The existing POA&M positive/negative checks remain in the same gate. Profile checks do not
claim that a framework crosswalk is correct. Framework objective-to-control mappings still
require reviewed registry provenance; OSCAL schema validity is necessary, not proof of
policy correctness.

## Schema compatibility matrix

The Profile fixture is intentionally OSCAL `1.2.1` because Compliance Trestle `5.0.0`
currently models OSCAL 1.2.1. The independent `oscal-cli 3.2.0` validator accepts the same
Profile model and validates its required fields and constraints.

| Check | Input | Expected result | Observed result |
| --- | --- | --- | --- |
| Trestle model validation | Trestle workspace Profile | Valid | PASS |
| Trestle Profile resolution | `trestle://catalogs/fixture/catalog.json` | Resolved Catalog | PASS |
| `oscal-cli` portable validation | Same Profile with `file://` Catalog reference | Valid | PASS |
| Missing `profile.uuid` | Mutated Profile | Invalid | PASS: rejected |
| Both `include-all` and `include-controls` | Mutated import | Invalid | PASS: rejected |
| Raw `trestle://` passed directly to `oscal-cli` | Trestle workspace Profile | Not portable | Expected failure |

The last result is a boundary condition, not a schema defect: `oscal-cli` does not know the
Trestle workspace URI scheme. The gate resolves the Profile with Trestle and materializes a
portable `file://` reference before invoking `oscal-cli`.

The Profile schema contract exercised by the gate is:

```json
{
  "profile": {
    "uuid": "required UUID",
    "metadata": {
      "title": "required",
      "last-modified": "required date-time",
      "version": "required",
      "oscal-version": "required"
    },
    "imports": [
      {
        "href": "resolvable URI",
        "include-all": {},
        "exclude-controls": []
      }
    ]
  }
}
```

At least one import is required. Each import uses exactly one selection mode: `include-all`
or `include-controls`. `merge`, `modify`, `back-matter`, and extended metadata are optional.

The authoritative sources are the OSCAL Profile metaschema and generated Profile JSON
schema, not a Mint-specific schema:

- `reference/OSCAL/src/metaschema/oscal_profile_metaschema.xml`
- Trestle's generated `oscal_profile_schema.json` for the pinned toolchain
- `oscal-cli 3.2.0` for independent schema/constraint validation

Pressure-test command:

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
OSCAL_CLI=/tmp/oscal-pt/oscalcli/bin/oscal-cli \
TRESTLE=/tmp/oscal-pt/.venv-trestle/bin/trestle \
bash scripts/oscal-conformance.sh
```

The gate must exit non-zero if any positive or negative control changes result.
