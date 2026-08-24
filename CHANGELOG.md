# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Contents

1. [Unreleased](#unreleased)
2. [0.2.2 - 2026-08-04](#022---2026-08-04)
3. [0.2.1 - 2026-08-04](#021---2026-08-04)
4. [0.2.0 - 2026-08-04](#020---2026-08-04)
5. [0.1.13 - 2026-07-28](#0113---2026-07-28)
6. [0.1.12 - 2026-07-28](#0112---2026-07-28)
7. [0.1.11 - 2026-07-28](#0111---2026-07-28)
8. [0.1.10 - 2026-07-28](#0110---2026-07-28)
9. [0.1.9 - 2026-07-28](#019---2026-07-28)
10. [0.1.8 - 2026-07-28](#018---2026-07-28)
11. [0.1.7 - 2026-07-28](#017---2026-07-28)
12. [0.1.6 - 2026-07-28](#016---2026-07-28)
13. [0.1.5 - 2026-07-28](#015---2026-07-28)
14. [0.1.4 - 2026-07-28](#014---2026-07-28)
15. [0.1.3 - 2026-07-28](#013---2026-07-28)
16. [0.1.2 - 2026-07-28](#012---2026-07-28)
17. [0.1.1 - 2026-07-28](#011---2026-07-28)
18. [0.1.0 - 2026-07-28](#010---2026-07-28)

## [Unreleased]

### Fixed

- Malformed non-UTF-8 source files now exit as input errors rather than internal failures.
- Layer-2 POA&M validation now rejects OSCAL links missing the required `href` field.

## [0.2.2] - 2026-08-04

### Removed

- **Speculative model stubs** (#96): deleted the advertised-but-hollow `component-definition`
  emitter, the `consume/` catalog and profile readers, and `ir/schema.py`. The CLI no longer lists
  `component-definition`; the only planned model surfaced is `ar` (Assessment Results).

### Fixed

- **Validator false-greens** (#105): `--validate` / `poam validate` no longer pass POA&M documents
  that NIST oscal-cli rejects. `required_fields` now checks every sub-object oscal-cli requires:
  observation `description`/`collected`, observation subject `type`/`subject-uuid`, poam-item
  `related-observation`/`related-risk` uuids, and `inventory-item` `description`. Proven with an
  oscal-cli 3.2.0 differential harness.
- **Invalid output at exit 0** (#106, #107): the QuReddy adapter now rejects a non-ISO-8601
  `completed_at` (empty or malformed) and a non-string `title`/`severity`/`description` at the
  parse boundary (exit 2, `malformed_input`) instead of shipping a schema-invalid POA&M at exit 0.
- **CBOM honest-failure hole, control-id validation, finding status, type-guard** (#98, #94, #83,
  #82): an indeterminate primitive with a producer security level and a registry miss no longer
  rides a favorable verdict; control-id shape is validated in the authority namespace; CBOM finding
  status stays `open` (a point-in-time inventory carries no remediation evidence) while QuReddy
  carries a real status; a non-string `scan.completed_at` exits 2 (`malformed_input`), not 70.

### Documentation

- **All 17 user-facing docs raised to a 9-10 quality bar** and restructured into Diátaxis
  (tutorials / how-to / reference / explanation) (#104). Every command is verified against the
  shipped CLI and oscal-cli 3.2.0: the broken `oscal-cli ... -` stdin pipes are replaced with
  file-based validation, native `--to xml/yaml` is documented as planned (the working path is
  `oscal-cli convert`), and stale references (`component-definition`, a phantom `--now` flag, the
  `from_qureddy` adapter name) are corrected.

## [0.2.1] - 2026-08-04

### Changed

- **Build/quality hardening** (#71, #87): REUSE/SPDX compliance (`LICENSES/` + `REUSE.toml`;
  normalized `Dockerfile` and `CONTRIBUTING.md` from `Apache-2.0` to `PolyForm-Noncommercial-1.0.0`),
  bandit + CodeQL SAST, and a numbered-`## Contents` documentation-contract check (ported
  `scripts/check_docs.py`). All enforced via pre-commit (GitHub Actions are billing-blocked on the
  private repo, #46). No runtime behavior change.

### Documentation

- README trued up against the shipped product: the Quickstart now shows `--framework`
  (`scf-qts` default, `nist` opt-in), the stale `sp800-53r5` crosswalk description is corrected,
  and the dangling "Docker image" claim is removed (no image is published; #100). Every
  first-party doc gained a numbered `## Contents` table of contents.

## [0.2.0] - 2026-08-04

### Added

- **SCF-QTS as the default control framework + `--framework` selector** (#88): findings map to
  PQC-native SCF Quantum Security controls (qts-04.3 Exposure, qts-06.5 Deprecated, qts-06.9
  Hybrid, qts-06.3 Approved-PQC, qts-04 Discovery) instead of a single generic SC-13. NIST SP
  800-53r5 (SC-13/SC-12) is retained as `--framework nist`. Control ids are attributed to the
  framework authority namespace (SCF/NIST) and linked to its OSCAL catalog; only BreachSAFE
  concepts (`severity`, `framework`, `interpretation-status`) ride the BreachSAFE namespace.
- **`not_applicable` readiness verdict** (#86): a producer's out-of-scope state (e.g. a
  certificate signature algorithm) maps to no control and is no longer coerced into SC-13, so
  the `qureddy | mint-oscal` pipe no longer emits a self-invalid POA&M.
- **`interpretation-status: provisional` marker** (#84): a finding built from an unreviewed
  policy pack is marked provisional, so an ungoverned mapping is never read as authoritative.
- **NIST OSCAL conformance gate** (#71, #93): `scripts/oscal-conformance.sh` (and a
  `workflow_dispatch` CI workflow) validate every minted POA&M against the upstream reference
  validator **oscal-cli 3.2.0** — positive + negative controls, fail-closed. Requires Python
  3.14+ (older versions are rejected).

### Changed

- **Pinned OSCAL to 1.2.2** (#85), the current NIST release; removed the redundant
  `oscal-target-version` prop and the `oscal-version 1.1.2` declaration. Validated against
  oscal-cli 3.2.0 and the NIST v1.2.2 JSON schema.
- `controls_for` no longer defaults an unrecognized verdict to `SC-13`; an unmapped verdict
  implicates no control (#86).
- `validate.py` control-id checks are framework-agnostic: a control id may be a non-NIST id
  (e.g. `qts-04.3`) attributed to its framework authority, not the BreachSAFE namespace (#88).

### Fixed

- **breachsafe enricher never-raises contract** (#76): `_producer_props` iterated
  `properties`/`components` with `... or []`, so a truthy non-list (e.g. `components: 5`) raised
  `TypeError` and a non-dict document raised `AttributeError` -- reachable via
  `--from qureddy --extension breachsafe` (a stray CBOM-shaped field rides through the qureddy
  adapter to the enricher), surfacing as exit 70 instead of being ignored. All three containers
  are now type-guarded, so a shapeless field is ignored per the documented contract.
- **CBOM crypto-scoring correctness** (#78, #79, #80): canonical FIPS-203 `ML-KEM-768`/
  `ML-KEM-1024` hyphenated names now resolve in the registry, so a real hybrid no longer
  mis-scores as `quantum_vulnerable` (#80); a producer `nistQuantumSecurityLevel` can no longer
  upgrade a registry-classical algorithm to `quantum_ready` (#79); an indeterminate `primitive`
  (`unknown`/`other`) is routed to unclassified instead of silently dropped, so a hidden KEX can
  no longer ride a favorable verdict (#78).

## [0.1.13] - 2026-07-28

### Added

- **`--extension breachsafe` now carries the producer cross-check + evidence chain** (#75):
  a live end-to-end demo (qureddy scan -> CBOM -> POA&M) showed the minted POA&M asserted a
  verdict but dropped its proof. The opt-in `breachsafe` extension now (a) records
  `provenance=producer-confirmed` / `conflict:producer=X,derived=Y` by reading the producer's
  declared readiness from `breachsafe:v1:readiness` (preferred) or the native `qureddy:scan.readiness`
  as a for-now bridge (breachsafe-qureddy-v2#14 tracks qureddy emitting the standard namespace);
  and (b) maps the producer evidence (`qureddy:evidence.<NN>.*` sha256 hashes / probe facts) into
  OSCAL `relevant-evidence`, so the POA&M carries the chain of custody. Honest-failure preserved
  (a producer over-claim never overrides the derived verdict). The neutral `--from cbom` path is
  unchanged and vendor-neutral. oscal-cli reports the evidence-bearing POA&M valid.

## [0.1.12] - 2026-07-28

### Fixed

- **`validate` now catches empty required arrays** (#73): differential-testing `semantic_errors`
  against **trestle** (`PlanOfActionAndMilestones.parse_obj`) surfaced that `required_fields`
  checked *presence*, not `minItems`, so an empty `poam-items: []` (schema `minItems: 1`, and
  `poam-items` is required) passed. A new `cardinality` validator flags an empty `poam-items`
  and empty-when-present `observations`/`risks`. (trestle's own structural parse *misses* this,
  so mint is now stronger here; the differential also confirmed mint already catches several
  things trestle-parse misses -- timezone-required datetimes, cross-ref resolution, uuid
  uniqueness, the BreachSAFE domain layer -- and that the #62 open-vocab decision matches
  trestle + the schema `anyOf`.) Exhaustive `additionalProperties`/unknown-field detection is a
  documented deliberate non-goal (version-brittle; Layer-1, owned by oscal-cli).
- **`poam validate` exit code for a non-POA&M input** (#72): a document that is not a POA&M at
  all (no `plan-of-action-and-milestones` root) is the wrong *input*, so it now exits `2` (input
  error) -- consistent with `generate` -- rather than `1` (a POA&M with a semantic problem).
  `1` is reserved for an actual POA&M that fails validation.

## [0.1.11] - 2026-07-28

### Added

- **`mint-oscal poam validate <file>`** — a standalone, pure-Python POA&M validator. It takes in
  an *existing* OSCAL POA&M (a file, or `-` for STDIN) -- yours or another tool's -- and runs the
  Layer-2 semantic checks (uuid/ref/ns integrity, OSCAL structural + datatypes, BreachSAFE domain
  vocab), reporting each problem on STDERR and exiting `1` on any problem, `0` if clean. **No
  oscal-cli or trestle required**, so anyone can lint a POA&M without the Java toolchain (still
  necessary-but-not-sufficient for full NIST schema conformance). Composes with the pipe:
  `mint-oscal poam generate --from cbom scan.cbom.json | mint-oscal poam validate -`. The existing
  `generate --validate` flag (validate-what-you-just-minted) is unchanged.

## [0.1.10] - 2026-07-28

### Fixed

- **Usage errors are distinct from bad input** (error-surface parity with BreachSAFE QuReddy):
  argparse's default `error()` exits `2` -- the same code mint uses for a malformed source
  report -- so a CLI mistake (an invalid `--from`/`--to`/`--extension` choice, a missing
  argument, an unknown flag) was indistinguishable from "your file was bad". A `_UsageParser`
  now routes every usage error to a distinct **exit 4** with a clean one-line
  `mint-oscal ...: usage error: <detail>` diagnostic on STDERR (STDOUT stays pure). The exit
  surface is now `0` ok / `1` validate-fail / `2` input / `3` local-dependency / `4` usage /
  `70` internal, documented in `--help` and covered by `scripts/regression.sh` (41 checks).

## [0.1.9] - 2026-07-28

### Fixed

- **Internal errors are no longer mislabeled as bad input** (#70): the CLI boundary caught every
  exception as `malformed_input`/exit 2, so a genuine internal fault (an unexpected `TypeError`,
  `KeyError`, …) was indistinguishable from a malformed source report. The adapter boundary now
  catches only the typed domain error (`MalformedCbomError`/`MalformedScanError`, both
  `ValueError`) → exit 2; any other fault propagates to a new top-level boundary that reports it
  as `internal_error` with a distinct **exit 70** (BSD `sysexits.h` EX_SOFTWARE) — never a leaked
  traceback, never mislabeled as input. The over-broad `except KeyError` → `unknown_selector`
  mapping (unreachable for its stated purpose; it only ever caught internal `KeyError`s) is
  removed. The exit-code surface (`0`/`1`/`2`/`3`/`70`) is now named constants and documented in
  `--help`.
- **No-args help no longer pollutes the STDOUT data channel** (#70): an *incomplete* invocation
  (no command, or a model with no verb) writes its help to **STDERR** (still exit 0), keeping
  STDOUT a pure OSCAL channel; an *explicit* `help` / `--help` request still writes to STDOUT
  (it is the requested output).

### Added

- **Black-box CLI regression harness** (`scripts/regression.sh`): drives the real console entry
  point across every parameter and exit path (help/version/no-args, all sources, `--extension`,
  `--validate`, `--to`, stdin, the 0/1/2/3 error paths) plus a **guard for every bug fixed to
  date** — #67 legacy-TLS-string cap, #68 RSA key transport, #64 zero-finding, #62 open-vocab,
  never-raises (no traceback on malformed input), and byte-determinism. Self-contained
  (generates its adversarial fixtures inline), no pytest/mocks, and runs the optional NIST
  `oscal-cli` Layer-1 check when present. Wired into CI as the `regression` job; 36 checks.

## [0.1.8] - 2026-07-28

Internal hardening — behavior-identical (every CLI exit path 0/1/2/3 and all source/format
paths verified unchanged), no user-facing change.

### Changed

- **Lint ruleset aligned with (and a superset of) BreachSAFE QuReddy**: added `N` (naming),
  `TCH`, `PL` (pylint incl. complexity ceilings), `PT`, `RET`, `ARG`, `DTZ` (timezone-aware
  datetime), `ERA` (no commented-out code), `INP`, **`BLE` (blind-except)**, and `SLF`. This
  makes the anti-pattern discipline lint-*enforced* rather than review-enforced — in particular
  `BLE` now requires every `except Exception` to be a deliberate, justified boundary. The two
  fail-closed boundaries (`semantic_errors`, the CLI adapter/enricher boundary) carry an
  explicit `# noqa: BLE001` documenting why. `ruff` + `mypy --strict` are green across all 29
  modules under the stricter rules.
- **`cli.main` split into `main` + `_run`**: the pipeline (read → adapt → enrich → mint →
  validate → render) moved into `_run`, leaving `main` as the thin error boundary that maps
  domain errors to exit codes. Improves cohesion and drops the function under the complexity
  ceilings.
- Named the internal-exit-code magic value in `_help`; `__version__` re-export no longer trips
  the naming rule; added a `BoundLog` logger-type alias so the CLI annotates against
  `mint_oscal.logging` rather than structlog internals.

## [0.1.7] - 2026-07-28

Closes the never-raises boundary gap (#69): the honest-failure contract now holds by
construction, not by remembering to guard each new site.

### Fixed

- **`semantic_errors()` never raises, enforced at the boundary** (#69): the #62 pass guarded
  some validators but missed the three reference validators and `props_namespaced`, so an
  unhashable id/ref/prop-name (a `list`/`dict`) still raised a bare `TypeError`. Those sites are
  now guarded (string-id sets, type-checked membership), **and** `semantic_errors` runs every
  validator under a fail-closed boundary so any escaping exception on hostile input degrades to
  a problem string rather than propagating — the contract holds even if a future validator
  misses a guard.
- **Typed error on a non-string qureddy id** (#69): `target.locator` and `findings[].id` used a
  presence-only `_require` while sibling fields used `_str`; a non-string value flowed into the
  emitter's uuid5 `"|".join(...)` and leaked a bare `TypeError`. Both are now `_str`-guarded, so
  malformed input raises the typed `MalformedScanError` (clean exit 2).

### Changed

- **Deduplicated the plugin registry**: the entry-point lookup/discovery logic was copy-pasted
  between `adapters/__init__.py` and `extensions/__init__.py`; it now lives once in
  `mint_oscal._registry` (the two ports keep only their type alias, group, built-ins, and error
  wording). Behavior-identical.
- **`-v`/`-vv` are no longer no-ops**: the CLI now logs a `minted_document` run summary at INFO,
  so raising verbosity surfaces real output (STDOUT stays a pure OSCAL channel).
- Removed a dead `SOURCE_URL` constant from `_branding`.

### Notes

- Two items in #69 were **not** defects and were left unchanged after verification: `_tail`
  (`str()` handles non-string scalars/lists without raising) and adding `start`/`end` to the
  dateTime fields (`start`/`end` are `port-range` **integers** in the schema, not
  dateTime-with-timezone). The two false-greens it listed (zero-finding, empty evidence props)
  shipped in 0.1.6 (#64/#65).

## [0.1.6] - 2026-07-28

Multi-agent adversarial review of the modules not touched by 0.1.5 (CBOM adapter, emitters,
extensions, policy) surfaced two HIGH honest-failure violations and several correctness gaps.

### Fixed

- **Legacy-protocol cap bypassed by non-numeric TLS version strings** (#67, HIGH, honest-failure):
  `_is_legacy_protocol` compared the version with a bare `float()`, so a producer rendering
  TLS 1.0 as `"TLSv1.0"`, `"v1.0"`, `"1.0.0"`, `"1.0 (deprecated)"` or `"TLSv1"` raised a
  `ValueError` that was swallowed as *not weak* — minting the most-favorable `quantum_ready`
  for a deprecated transport. #53's real case was literally `TLSv1`. The version number is now
  extracted from the version field or the name, so every encoding of TLS < 1.2 (and SSL, by
  name) caps at `classically_weak`; modern TLS 1.2/1.3 is unaffected.
- **RSA key transport silently dropped** (#68, HIGH, honest-failure): `_KEX_PRIMITIVES` was
  `{key-agree, kem}`, so an algorithm with the `pke` primitive (RSA key transport) was neither
  scored as key exchange nor caught by the unclassified safety-net — an RSA-key-transport +
  ML-KEM offering read as `quantum_ready`/high-confidence with RSA absent from the inventory.
  `pke` is now scored as key establishment: RSA alone → `quantum_vulnerable`, RSA + ML-KEM →
  `transitional_hybrid`, and RSA appears in `kex-offered`.
- **Zero-finding POA&M was schema-invalid** (#64): the emitter always wrote
  `observations`/`risks`/`poam-items`, so an empty scan (e.g. a fully PQ-ready endpoint)
  emitted `[]` for all three — violating OSCAL's `minItems: 1` (and `poam-items` is required),
  which `--validate` false-greened. Empty `observations`/`risks` are now omitted, and an empty
  scan yields one honest "No findings" `poam-item` (never fabricated findings).
- **`relevant-evidence` props emitted empty** (#65): an evidence entry with no props wrote
  `props: []`, violating the schema's `minItems: 1`; the key is now omitted when empty (matching
  the omit-when-empty the emitter already did for `relevant-evidence` itself).
- **Risk status hardcoded `open`** (#66): the emitter ignored the IR's first-class
  `Finding.status`, minting a `closed`/remediated finding as an `open` risk. It now reflects
  `finding.status`.
- **Provenance string parseability** (#63, defensive): `_crosscheck` embedded the derived
  verdict raw into the delimited `conflict:producer=X,derived=Y` provenance; `derived` is now
  guarded to a recognized verdict (a no-op for every real finding) so the string can't be
  corrupted by an unexpected value bearing `,`/`=`.
- **Policy pack fails loud on a non-mapping table**: an empty or non-mapping custom-pack YAML
  (`yaml.safe_load` → `None`/list) reached `data.keys()` and raised a bare `AttributeError`,
  contradicting the loader's "raises naming the missing keys" contract on the "copy the pack and
  swap" path it invites. It now raises a clear `ValueError`.

## [0.1.5] - 2026-07-28

### Fixed

- **`--validate` no longer diverges from `oscal_poam_schema.json`** (#62): an adversarial
  review found the native validator was both too strict and too loose. Corrected against the
  schema:
  - **Open vocabularies are no longer closed** (false-red): `risk-status`, `observation.methods`
    and `observation.types` are `anyOf[token/string, enum]` — any well-formed token/string is
    schema-legal and the enum is a suggestion. They are now validated by token/string *shape*,
    not closed-enum membership, so a conformant value like `status: under-review` is accepted
    (as `oscal-cli` accepts it) while empty/whitespace/non-token junk is still caught.
  - **`ns`-less standard props are no longer flagged** (false-red): OSCAL's `ns` is optional
    (absent ⇒ core namespace). `props_namespaced` now only flags a prop that reuses a
    BreachSAFE-reserved name *outside* the BreachSAFE namespace, not every core `ns`-less prop.
  - **Every dateTime-with-timezone field is checked** (false-green): `datatypes` previously only
    validated `metadata.last-modified` and observation `collected`, so a naive `metadata.published`
    (or `expires`/`deadline`) passed. It now validates all five dateTime-tz fields wherever they
    appear.
  - **`semantic_errors()` never raises on malformed input**: an unhashable value (e.g.
    `risk.status: []`) flowing into a set-membership test raised a bare `TypeError`; all
    membership/`Counter` sites now guard type first and report a problem string.
- **`severity` prop validated against the finding-severity vocabulary** (found while fixing #62):
  the `severity` domain check compared against `policy.severity.values()` (the readiness→severity
  lookup table, only `{info, low, medium}`), false-rejecting a legitimate `high`/`critical`. It now
  validates against the canonical IR `finding.severity` enum `{info, low, medium, high, critical}`,
  so a real `qureddy … --extension breachsafe --validate` run passes.

## [0.1.4] - 2026-07-28

### Added

- **Branded `--help`, consistent with BreachSAFE QuReddy** (CLI): the help output now leads
  with a `BreachSAFE Mint-OSCAL <version> -- <description>` header and carries UPPERCASE
  section blocks in the epilog (`QUICK START:` / `MORE HELP:` on the root; `EXAMPLES:` /
  `EXIT CODES:` / `ENVIRONMENT:` / `Project:` on `generate`), colorized by line shape
  (bold-cyan sections, dim `#` comments, green command lines, severity-colored exit codes,
  magenta env vars) and `NO_COLOR`-aware. Every command level has its own help; stub models
  are labelled `(planned)`; `--from` is documented and `--validate` reworded honestly
  (Layer-2, not authoritative NIST). New `mint_oscal._branding` and `mint_oscal._help`
  mirror QuReddy's module structure without taking its click/typer dependency.
- **`--version` / `-V`** print a single-line branded banner
  (`BreachSAFE Mint-OSCAL <version> -- https://www.breachsafe.ai`).
- **No-args, `mint-oscal help`, and a model with no verb** print the relevant help to STDOUT
  and exit 0 (discovery UX, not an error).

### Fixed

- **Version drift** (`__version__`): `mint_oscal.__version__` was hardcoded `"0.0.1"` while the
  packaged metadata read `0.1.x`. It now derives from installed package metadata via the new
  `_branding` module, so a release bump can't drift from the banner.

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
- Require **Python 3.14**.
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

[Unreleased]: https://github.com/paul007ex/breachsafe-mint-oscal/compare/v0.1.13...HEAD
[0.1.13]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.13
[0.1.12]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.12
[0.1.11]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.11
[0.1.10]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.10
[0.1.9]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.9
[0.1.8]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.8
[0.1.7]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.7
[0.1.6]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.6
[0.1.5]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.5
[0.1.4]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.4
[0.1.3]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.3
[0.1.2]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.2
[0.1.1]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.1
[0.1.0]: https://github.com/paul007ex/breachsafe-mint-oscal/releases/tag/v0.1.0
