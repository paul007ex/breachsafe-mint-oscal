<!-- SPDX-FileCopyrightText: 2026 BreachSAFE -->
<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# ADR-0010: Registry source, generated, and release boundary

## Contents

1. [Status](#status)
2. [Decision](#decision)
3. [Layout](#layout)
4. [Reproducibility](#reproducibility)
5. [Consequences](#consequences)

## Status

Accepted for registry foundation work in milestone `0.4.1` (#164).

## Decision

The editable registry YAML and pinned source Catalogs are authoritative. Generated OSCAL
documents and distributable release artifacts are separate projections and must never become a
second source of truth. The current repository reserves explicit directories for those
projections without pretending that the Profile compiler is complete.

## Layout

```text
examples/registry/
├── registry.yaml                 # editable governed source
├── catalogs/<id>/catalog.json    # pinned source inputs
├── registry.lock.json             # generated integrity projection
├── generated/                    # generated OSCAL, not hand-edited
└── release/                      # reviewed distributable outputs
```

`registry.lock.json` is generated from the parsed registry and pinned Catalog bytes. It is
checked for canonical byte stability in CI. `generated/` and `release/` remain empty until the
Profile compiler and release receipt contracts land.

## Reproducibility

Every generation command must be deterministic for the same source revision and tool versions.
The drift gate regenerates the lock into a temporary directory and compares bytes with the
committed lock. Future OSCAL generators must extend the same gate with generated-artifact
comparisons and a receipt containing source revision, generator version, and validator results.

## Consequences

- Reviewers can distinguish authored policy from generated output.
- CI catches stale lock projections before merge.
- No framework-specific command tree or speculative compiler is introduced by this ADR.
- A later compiler can add generated Profiles without migrating the registry source format.
