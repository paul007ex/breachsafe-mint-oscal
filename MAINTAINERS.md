# Maintainers

This file lists the people responsible for reviewing and merging changes to
`breachsafe-mint-oscal`, in the style used by the NIST OSCAL tooling projects.

## Current maintainers

| Name      | GitHub      | Area                                   |
| --------- | ----------- | -------------------------------------- |
| BreachSAFE | @breachsafe | Overall project, releases, OSCAL emitters |

## Responsibilities

- Triage issues and review pull requests.
- Guard the agnostic-core boundary (ADR-0004): keep adapters and emitters decoupled.
- Own release cuts and the `CHANGELOG.md`.
- Record control-crosswalk conformance sign-offs (R-CTRL-01) before any emitter
  is driven by a crosswalk table.

## Decision making

Substantive design decisions are recorded as ADRs under `docs/adr/`. A change that
alters a public interface, the IR wire format, or a control mapping requires
maintainer review and, where relevant, an ADR.

## Becoming a maintainer

Sustained, high-quality contributions and review participation are the path to
maintainership. Existing maintainers nominate and confirm new maintainers by
consensus.
