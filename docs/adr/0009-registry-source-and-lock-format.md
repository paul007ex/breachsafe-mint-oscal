# ADR-0009: Registry source and lock format

## Status

Accepted (P0 control-plane design)

## Context

Mint-OSCAL needs a governed registry that maps a framework and objective such as
`nist-800-53r5` + `pqc-readiness` to approved control IDs, evidence capabilities, and
provenance. The registry is BreachSAFE policy, not an OSCAL Catalog replacement. It must be
reviewable in Git for OSS use, deterministic in CI, and projectable into an Enterprise API
or database later without making that projection authoritative.

The existing Mint-OSCAL policy packs are YAML. OSCAL artifacts and the imported NIST Catalog
are JSON. OSCAL CLI and Trestle support JSON, YAML, and XML, but neither requires the
registry to be an OSCAL model.

## Decision

Use one human-authored YAML registry source and a generated canonical JSON lock:

```text
YAML policy packs  ->  strict loader/schema validation  ->  registry.lock.json
                                                          |
                                                          v
                                               Profile compiler / API projection
```

Use JSON for generated OSCAL Profiles, resolved Catalogs, and downstream OSCAL artifacts.
Preserve upstream Catalog files unchanged and record their source URL, version, and
SHA-256 in the registry/lock.

The registry loader must:

- use YAML 1.2-compatible strict parsing;
- reject duplicate keys and unknown fields where the schema forbids them;
- validate the registry and objective schemas before resolution;
- canonicalize data before calculating digests;
- generate `registry.lock.json`; and
- treat the lock as generated, never hand-edited.

The initial layout is:

```text
policy/
├── registry.yaml
├── packs/nist-800-53r5/
│   ├── meta.yaml
│   ├── objectives/pqc-readiness.yaml
│   └── control-crosswalk.yaml
├── catalogs/NIST_SP-800-53_rev5_catalog.json
└── registry.lock.json
```

## Automation boundary

Catalog mechanics are automatable: download, digest verification, import, validation,
control indexing, and candidate generation from titles/groups/explicit query terms. The
upstream Catalog cannot determine BreachSAFE's objective meanings or evidence sufficiency.
Final objective-to-control selection, control-to-capability mapping, and evidence
sufficiency therefore remain reviewed policy.

A future `mint-oscal registry scaffold` may emit a `draft` objective, but draft output
cannot be locked or compiled until a reviewer approves it. Heuristic or natural-language
candidate generation must never silently become policy authority.

## Consequences

Positive:

- Human governance and Git review remain first-class.
- JSON consumers receive deterministic, hashable input.
- OSS works offline without a registry service.
- Enterprise can add an API/database projection that is rebuildable from Git.
- OSCAL output remains standards-native JSON.

Costs:

- We must implement strict YAML loading and canonical locking.
- YAML and generated lock drift must be CI-detected.
- Service/API work is deferred until the local registry contract is stable.

## Rejected alternatives

- **JSON-only source:** simpler parser, but less consistent with current policy packs and
  less reviewable for governed mappings.
- **Database as authority:** weak Git review/provenance and poor offline OSS behavior.
- **Service as authority:** introduces availability, tenancy, and version drift before the
  local compiler contract exists.
- **Editable YAML and JSON copies:** creates two sources of truth and is rejected.

## Verification

- Registry schema and objective fixture validate in CI.
- Same YAML source produces byte-identical canonical lock output.
- Missing Catalogs, unknown controls, duplicate keys, and stale digests fail closed.
- Profile creation records policy/catalog/resolver digests and passes independent OSCAL
  validation.
