# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
