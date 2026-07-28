# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`breachsafe` overlay adapter** (`--from breachsafe`, ADR-0008): an opt-in
  progressive enhancement over the vendor-neutral `cbom` flagship. It composes
  `from_cbom` and, when a producer declares the optional `breachsafe:v1:*` facts in
  CycloneDX `properties[]`, records a `provenance` posture prop
  (`derived | producer-confirmed | conflict:producer=X,derived=Y`) and carries an
  `evidence-sha256`. Crypto facts stay derived from `cryptoProperties`; on a readiness
  conflict our derivation stays authoritative. `cbom` and `qureddy` are unchanged (#28).

### Changed

- **License: Apache-2.0 → PolyForm Noncommercial 1.0.0** (ADR-0007). The project is now
  **source-available, not open source**: read/run/evaluate/self-host/modify for any
  noncommercial purpose; commercial use requires a separate license (see `NOTICE`).
- Require Python 3.12 (was 3.11); CI runs on 3.12 only.

### Fixed

- Deterministic `metadata.last-modified` derived from the source observation time, not
  wall-clock — same input now yields a byte-identical POA&M (#4).
- `--validate` no longer false-greens: replaced the shallow structural check with a
  Layer-2 semantic validator registry (uuid uniqueness, observation/risk/subject
  reference resolution, prop namespacing) and honest messaging that points at `oscal-cli`
  as the authoritative schema oracle (#3, ADR-0005).

## [0.0.1] - Unreleased

### Added

- Agnostic core (ADR-0004): `convert(ir, *, shape, **params)` dispatching to a
  registry of OSCAL emitters, fed by entry-point-discovered source adapters.
- Source-neutral intermediate representation (`mint_oscal.ir`) with a
  `mint.ir.v1` JSON Schema.
- OSCAL POA&M emitter (`poam`); `ar` and `component-definition` emitters stubbed.
- QuReddy `qureddy.scan.v1` adapter (bundled convenience).
- NIST SP 800-53 control mapping and a draft, unreviewed r5 crosswalk.
- `mint-oscal <model> generate --from <source>` CLI, structural POA&M validation,
  and JSON rendering (XML/YAML via external `oscal-cli`, ADR-0005).

[Unreleased]: https://github.com/breachsafe/breachsafe-mint-oscal/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/breachsafe/breachsafe-mint-oscal/releases/tag/v0.0.1
