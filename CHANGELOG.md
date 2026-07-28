# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **UTC timestamp normalization** (#39): the POA&M emitter now converts every observation
  timestamp to UTC (`+00:00`), so the document timestamp (lexical max of ISO strings) is the
  true chronological latest even across mixed-offset inputs.
- **CycloneDX specVersion validation** (#38): the CBOM adapter rejects an unsupported
  `specVersion` with `MalformedCbomError` (supported set derived from
  `cyclonedx.schema.SchemaVersion`) instead of attempting to parse it.
- **QuReddy typed error** (#21): the `qureddy.scan.v1` adapter validates the envelope shape
  and raises a new `MalformedScanError` on malformed input, mirroring the CBOM adapter, rather
  than leaking a bare `KeyError`/`TypeError`.

### Changed

- **POA&M title casing** (#13): source display names in the title now read `CBOM`/`QuReddy`
  via a display-name map instead of `str.capitalize()` (`Cbom`/`Qureddy`).

## [0.1.0] - 2026-07-28

First tagged release. Validated end-to-end against live infrastructure — qureddy 0.2.12
CBOMs of cloudflare.com, www.google.com, github.com, and pecutx.org — with output confirmed
by NIST `oscal-cli` and IBM `trestle`.

### Added

- **Agnostic core** (ADR-0004): `convert(ir, *, shape, **params)` over registries of
  entry-point-discovered source adapters and OSCAL emitters, fed by a source-neutral
  intermediate representation (`mint_oscal.ir`, `mint.ir.v1` JSON Schema).
- **CBOM ingestion** (ADR-0006): file-driven CycloneDX-CBOM → IR with data-driven
  algorithm classification (`crypto-registry.yaml`) and readiness rules
  (`readiness-rules.yaml`); shape-validated, honest confidence, secret material skipped.
- **`--extension` model** (ADR-0008): source × extension orthogonality. `--extension
  breachsafe` runs a `breachsafe:v1` producer-observation enricher that cross-checks
  producer-declared readiness against the derived verdict (ours authoritative) and records
  provenance (`derived | producer-confirmed | conflict:*`).
- OSCAL **POA&M emitter**; QuReddy `qureddy.scan.v1` adapter; NIST SP 800-53 control
  mapping. `ar` and `component-definition` emitters stubbed.
- **CLI** `mint-oscal <model> generate --from <source>`: reads a file or STDIN (`-`, the
  flagship pipe), structured logging to STDERR (structlog; `-v/-q/--json-logs`) keeping
  STDOUT a pure OSCAL channel, and a source-agnostic error boundary (clean one-line
  diagnostics + non-zero exit, never a traceback).
- **Semantic `--validate`** (ADR-0005, Layer 2): uuid uniqueness, observation/risk/subject
  reference resolution, prop namespacing; NIST `oscal-cli` is the authoritative Layer-1
  schema oracle.

### Changed

- **License: Apache-2.0 → PolyForm Noncommercial 1.0.0** (ADR-0007): source-available,
  not open source; commercial use requires a separate license (see `NOTICE`).
- Require **Python 3.12**.
- Render/validation boundary hand-rolled with `oscal-cli` as the oracle — **no `trestle`
  dependency** (version sovereignty + minimal supply chain; ADR-0005).

### Fixed

- Deterministic output: `last-modified`/uuids derived from the source, not wall-clock
  (#4, #33); timestamps normalised to timezone-aware, which oscal-cli requires (#18).
- `--validate` no longer false-greens (#3); custom props are always namespaced (#2).
- CBOM fail-open hardening — malformed/under-declared input can no longer mint a
  confident-but-wrong POA&M (#9); an unclassified KEX never reads as the most-favorable
  posture (#24); finding id content-addressed over the crypto inventory (#26); CLI never
  leaks a traceback on bad input (#20).

### Known limitations

- No automated test suite yet (#6) — 0.1.0 is validated manually, against live
  infrastructure, and by independent review; a CI test suite is the immediate follow-on.
- `ar`/`component-definition` emitters and the `consume` side are stubs.

[Unreleased]: https://github.com/paul007ex/breachsafe-mint-oscal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.0
