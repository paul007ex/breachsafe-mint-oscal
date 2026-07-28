# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-07-28

### Added

- **Native OSCAL-structural + BreachSAFE-domain `--validate`** (#59): the Layer-2 validator
  registry grows from 6 to 11 checks, re-deriving in-process the OSCAL POA&M rules that matter
  most — required fields, the UUID and (full leap-year-aware, timezone-mandatory)
  dateTime-with-timezone datatypes, and the risk-status / observation-method / observation-type
  enums — mapped 1:1 to `oscal_poam_schema.json`, plus the BreachSAFE-namespace domain
  vocabularies (readiness, mapping-confidence, severity, provenance, control-id,
  nistQuantumSecurityLevel) sourced from the single-source policy pack. NIST `oscal-cli` remains
  the authoritative Layer-1 oracle; these run in-process and are necessary but **not** sufficient
  for schema conformance (callers must not report them as such). The impossible date `2026-02-30`
  and a naive tz-less timestamp are both caught by the verbatim datatype pattern.

### Fixed

- **`semantic_errors()` never raises on malformed input** (#60): a document that is not a POA&M
  (or whose `observations`/`risks`/`poam-items`/`methods`/`props` arrive as a scalar, or whose
  root is `None`/a list) is now reported as a problem string rather than surfacing a bare
  `KeyError`/`TypeError`/`AttributeError`. Non-list containers are flagged structurally. The
  validator always returns a `list[str]`.
- **`--validate` result visible at default verbosity** (#55): the semantic-check summary logs at
  `WARNING`, not `INFO`, so a `--validate` run's outcome is no longer silently suppressed at the
  default log level.
- **Legacy/weak protocols downgrade readiness** (#53): the CBOM adapter now scores plain
  `protocol` components (not just key exchange). A weak transport offering — any SSL, or a
  TLS/DTLS version below 1.2 (TLS 1.0/1.1, RFC 8996) — caps the verdict at `classically_weak`
  and is surfaced as `legacy-protocols` in `posture`, mirroring the #24 honest-failure
  downgrade. Previously a live cloudflare.com CBOM offering TLSv1/TLSv1.1 minted the favorable
  `transitional_hybrid`/`low` despite the producer's own `classically_weak`; it now reads
  `classically_weak`/`medium` (SC-13, SC-12). Modern-only CBOMs are unchanged.
- **Typed errors on all nested-shape malformations** (#54): the CBOM adapter raises
  `MalformedCbomError` (not a bare `KeyError`/`TypeError`) when a nested component/property is
  the wrong shape, so malformed input yields a clean one-line diagnostic + non-zero exit.

### Changed

- **CI automatic triggers disabled** (#46): GitHub Actions execution is blocked on this repo by
  billing, so `push`/`pull_request` runs only produced noise; the pipeline is retained and
  runnable on demand (`workflow_dispatch`), re-enabled in one edit once billing is restored.

## [0.1.2] - 2026-07-28

### Fixed

- **Single-source readiness vocabulary** (#47): the `breachsafe` provenance extension now
  reads the canonical readiness set from `mint_oscal.policy.READINESS_VERDICTS` instead of a
  private copy, so a producer-declared `classically_weak` is recorded as a `conflict:*`
  (honest attribution) rather than silently dropped. The two vocabularies can no longer drift.

## [0.1.1] - 2026-07-28

### Added

- **Versioned policy pack** (#10, closes #5): severity, the SP 800-53 control crosswalk, and
  risk statements now live as loadable YAML under `mint_oscal/policy/default/` (replacing the
  hardcoded tables and the dead, never-loaded `sp800-53r5.yaml`). The loader fails loudly if a
  pack omits any emittable readiness verdict. Behavior-preserving for all current outputs.
- **NIST oscal-cli conformance CI gate** (#17): CI mints a POA&M and asserts oscal-cli reports
  it `is valid` (with a negative-control fixture), asserting on the verdict string since
  oscal-cli exits 0 even on invalid input. (Test-count/coverage + golden gates remain deferred
  to the test suite, #6/#41.)

### Fixed

- **UTC timestamp normalization** (#39): the emitter converts every observation timestamp to
  UTC (`+00:00`), so the document timestamp (lexical max) is the true chronological latest even
  across mixed-offset inputs.
- **CycloneDX specVersion validation** (#38): the CBOM adapter rejects an unsupported
  `specVersion` with `MalformedCbomError` (supported set from `cyclonedx.schema.SchemaVersion`).
- **QuReddy typed errors** (#21, #44): the `qureddy.scan.v1` adapter validates its envelope —
  including the evidence list — and raises `MalformedScanError` on malformed input instead of
  leaking a bare `KeyError`/`TypeError`.
- **CI pipeline** (#43): tolerate `pytest`'s exit-5 on an empty suite until it lands (#6); run
  gitleaks via the pinned release binary + a build/clean-install leak-guard. (Actions execution
  itself is blocked by repo billing — #46 — not the workflow.)

### Changed

- **POA&M title casing** (#13): title source names read `CBOM`/`QuReddy` via a display map
  instead of `str.capitalize()`.

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

[Unreleased]: https://github.com/paul007ex/breachsafe-mint-oscal/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.3
[0.1.2]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.2
[0.1.1]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.1
[0.1.0]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.0
