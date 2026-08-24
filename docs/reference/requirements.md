# Requirements (RTM)

Requirements Traceability Matrix for `mint-oscal`. It lists 44 requirements across 11
categories (ARCH, SRC, OUT, OSC, DET, EVID, CTRL, VAL, CLI, PKG, NG). Source of truth:
[`requirements.xlsx`](../requirements.xlsx) → *Requirements* sheet.

See the [docs index](../README.md) for the honest-verdict caveat that governs all
control-mapping requirements below.

## Contents

1. [Legend](#legend)
2. [ARCH: Architecture (N sources → neutral IR → M targets)](#arch-architecture-n-sources--neutral-ir--m-targets)
3. [SRC: Sources (input adapters)](#src-sources-input-adapters)
4. [OUT: Targets (output emitters)](#out-targets-output-emitters)
5. [OSC: OSCAL Conformance (schema + version)](#osc-oscal-conformance-schema--version)
6. [DET: Determinism (reproducibility)](#det-determinism-reproducibility)
7. [EVID: Evidence integrity (privacy of evidence)](#evid-evidence-integrity-privacy-of-evidence)
8. [CTRL: Control mapping (finding → control crosswalk)](#ctrl-control-mapping-finding--control-crosswalk)
9. [VAL: Validation (checking output)](#val-validation-checking-output)
10. [CLI: CLI (command surface)](#cli-cli-command-surface)
11. [PKG: Packaging / NFR (ship the library)](#pkg-packaging--nfr-ship-the-library)
12. [NG: Non-goals (explicitly out of scope)](#ng-non-goals-explicitly-out-of-scope)

## Legend

- **Priority**: Must (release blocked without it) · Should (ship without only with a
  reason) · Could (roadmap) · Won't (explicit non-goal).
- **Type**: Functional (what it does) · Non-functional (quality attribute) · Constraint
  (a boundary that must hold).
- **Verify**: Test (automated, tester-owned) · Demo (run and observe) · Inspection (read
  code/doc) · Analysis (reason from spec).
- **Status**: Built / Met / PASS (implemented / evidenced) · Designed / Partial
  (decided or partially done) · Open / Backlog / Deferred (not started / later) · Held
  (a constraint currently being honored).

## ARCH: Architecture (N sources → neutral IR → M targets)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-ARCH-01 | Sources and targets are decoupled through a neutral intermediate representation (IR). | Constraint | Must | N→IR→M design | New source needs no emitter change and vice-versa. | Inspection | Designed |
| R-ARCH-02 | Adding a source = one new adapter, discovered without a CLI edit. | Functional | Must | `mint_oscal.adapters` entry-point group; `_BUILTINS` fallback; [ADR-0004](../adr/0004-agnostic-core.md) | Register via the entry-point group (or `_BUILTINS`); emitters and CLI untouched. | Inspection | Built |
| R-ARCH-03 | Adding a target = one new emitter; adapters untouched. | Functional | Must | `emitters/` package | New emitter consumes IR only. | Inspection | Designed |
| R-ARCH-04 | IR is frozen, source/target-agnostic (Finding/Subject/Evidence). | Constraint | Must | `ir.py` frozen dataclasses | Dataclasses frozen; no source field names leak past adapter. | Inspection | Built |

## SRC: Sources (input adapters)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-SRC-01 | QuReddy `qureddy.scan.v1` JSON adapter. | Functional | Must | `adapters/qureddy.py` | Live example.com scan → IR findings + subject. | Demo | Built |
| R-SRC-02 | Prowler adapter. | Functional | Should | roadmap | Prowler OCSF/native output → IR. | Test | Backlog |
| R-SRC-03 | OCSF adapter. | Functional | Could | roadmap | OCSF finding → IR. | Test | Backlog |
| R-SRC-04 | CycloneDX CBOM adapter (default source). | Functional | Must | `adapters/cbom.py`; entry-point `cbom`; `cyclonedx-python-lib` dep; [ADR-0006](../adr/0006-cbom-first-ingestion.md) | `--from cbom` parses CBOM crypto-assets → IR findings + subject; CBOM → POA&M runs end to end. | Demo | Built |
| R-SRC-05 | OpenTelemetry adapter. | Functional | Won't | roadmap | Deferred beyond this release. | n/a | Deferred |
| R-SRC-06 | Adapter fails loudly on unknown/unsupported schema version. | Non-functional | Should | n/a | Unsupported version raises, never silently maps. | Test | Open |

## OUT: Targets (output emitters)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-OUT-01 | OSCAL POA&M emitter (first target). | Functional | Must | `emitters/poam.py` | Emits plan-of-action-and-milestones with all required fields. | Demo | Built |
| R-OUT-02 | Output is standalone + human-readable (no base64, no mandatory external fetch). | Constraint | Must | Option A decision | Reader understands posture from the doc alone. | Inspection | Met (v2) |
| R-OUT-03 | Crypto facts carried as readable namespaced props (`ns=https://breachsafe.ai/ns/oscal`). | Functional | Must | v2 observation props | readiness/algorithm/level/cert-sig/hashes present as props. | Inspection | Met (v2) |
| R-OUT-04 | Optional CBOM companion via `relevant-evidence` href; POA&M valid without it. | Functional | Should | v2 relevant-evidence | Remove the link → still validates. | Demo | Met (v2) |
| R-OUT-05 | Provenance in metadata (generator + responsible-party). | Functional | Should | v2 metadata | generator/version props + Prepared By party present. | Inspection | Met (v2) |

## OSC: OSCAL Conformance (schema + version)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-OSC-01 | Declared `oscal-version = 1.2.2` (current NIST OSCAL release). | Constraint | Must | oscal-cli 3.2.0; NIST v1.2.2 JSON schema | Declared 1.2.2; no `oscal-target-version` prop. | Inspection | Met (v3) |
| R-OSC-02 | All required POA&M fields present (uuid, metadata{title,last-modified,version,oscal-version}, system-id\|import-ssp, ≥1 poam-item{title,description}). | Constraint | Must | `oscal_poam_metaschema.xml` | Validator reports required fields satisfied. | Demo | Met (v2) |
| R-OSC-03 | Output validates clean against NIST oscal-cli. | Non-functional | Must | ghcr.io oscal-cli:latest (3.2.0) | "The file is valid." exit clean. | Demo | PASS (v2) |
| R-OSC-04 | Element ordering conforms to the metaschema. | Constraint | Must | metaschema | No ordering errors from validator. | Demo | PASS (v2) |
| R-OSC-05 | All cross-references resolve (obs↔risk↔poam-item, subject↔inventory-item). | Constraint | Must | `validate.semantic_errors` (Layer-2 checks) | No dangling refs. | Test | PASS (v2) |

## PROF: OSCAL Profile conformance

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-PROF-01 | Profile uses the OSCAL Profile model and Trestle workspace conventions. | Constraint | Must | ADR-0010; OSCAL Profile metaschema | Trestle validates the Profile fixture. | Test | PASS |
| R-PROF-02 | Profile contains required `uuid`, metadata, and imports fields. | Constraint | Must | OSCAL Profile schema 1.2.1 | Required-field negative control is rejected. | Test | PASS |
| R-PROF-03 | Each import has one selection mode: `include-all` or `include-controls`. | Constraint | Must | OSCAL Profile metaschema | Invalid dual-selection fixture is rejected. | Test | Planned (#156) |
| R-PROF-04 | Profile imports resolve before portable validation. | Functional | Must | Trestle profile resolver | Trestle produces a resolved Catalog with no dangling imports. | Test | PASS |
| R-PROF-05 | Portable Profile validates with the official `oscal-cli` validator. | Non-functional | Must | oscal-cli 3.2.0 | `oscal-cli validate` exits valid after `trestle://` materialization. | Test | PASS |
| R-PROF-06 | Profile conformance runs locally and in CI with positive and negative controls. | Non-functional | Must | `scripts/oscal-conformance.sh` | Gate exits non-zero when a required field is removed. | Test | PASS |

## DET: Determinism (reproducibility)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-DET-01 | Same scan → same OSCAL uuids (uuid5 over fixed namespace). | Non-functional | Must | `poam._det` | Re-run yields identical uuids. | Test | Built |
| R-DET-02 | Output byte-stable for same input + timestamp. | Non-functional | Should | n/a | diff of two runs is empty. | Test | Open |

## EVID: Evidence integrity (privacy of evidence)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-EVID-01 | Evidence carries hashes (command-sha256, stdout-sha256), never raw excerpts. | Constraint | Must | `adapters/qureddy._evidence` | No stdout/plaintext bodies in output. | Inspection | Built |
| R-EVID-02 | No live scan-target data committed to repo artifacts. | Constraint | Must | session rule | example.com samples only in /tmp + examples, not product code. | Inspection | Held |

## CTRL: Control mapping (finding → control crosswalk)

> The finding→control→ODP judgment is an **organization-policy assertion**, not a
> scanner-derived truth. Every row of the crosswalk must cite a control statement and
> carry reviewer sign-off; see [oscal-shapes.md](oscal-shapes.md) and the DRAFT crosswalk
> in the workbook. `R-CTRL-01` is **OPEN**.

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-CTRL-01 | finding→control crosswalk is authored, cited, human-reviewed; NOT LLM/scanner-guessed. | Constraint | Must | conformance lane; rev5 catalog | Every row cites a control statement; reviewer sign-off. | Inspection | OPEN |
| R-CTRL-02 | Mapping is framework-scoped (SP 800-53 rev5) and ODP-aware. | Functional | Must | rev5 catalog ODPs | Row records ODP id + org-set value. | Inspection | OPEN |
| R-CTRL-03 | POA&M states the verdict as an assertion tied to org ODP, not scanner truth. | Constraint | Must | v2 poam-item remarks | remarks makes the ODP dependency explicit. | Inspection | Met (v2) |
| R-CTRL-04 | Under `--framework nist`: SC-13 primary, SC-12 supporting for classical key-establishment findings; SC-8 excluded (overreach). | Functional | Should | `policy/default/control-crosswalk.yaml` | With `--framework nist`, SC-8 is not emitted; SC-13 present, SC-12 added for `quantum_vulnerable`/`classically_weak`. | Inspection | Met (v2) |
| R-CTRL-05 | No PQC/CNSA catalog exists; ODP bar is org-supplied, not shipped as fact. | Constraint | Must | reference tree has no PQC catalog | ODP value is caller/policy input. | Inspection | Held |
| R-CTRL-06 | Control mapping is framework-selectable at run time via `--framework`: `scf-qts` (default, SCF Quantum Security controls) or `nist` (SP 800-53r5). | Functional | Should | `policy.FRAMEWORK_PACKS`; `policy.set_active_framework`; [ADR-0004](../adr/0004-agnostic-core.md) | `--framework` default is `scf-qts` (qts-* controls); `nist` selects the SC-13/SC-12 pack. | Demo | Built |

## VAL: Validation (checking output)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-VAL-01 | In-process Layer-2 semantic validator (uuid/ref/ns integrity, OSCAL structural, datatypes, BreachSAFE domain vocab) with no network or external toolchain. | Functional | Must | `validate.semantic_errors` | Returns `[]` for a sound doc; lists problems otherwise. | Test | Built |
| R-VAL-02 | External oscal-cli is the authoritative NIST schema check; detected when available (local or docker). | Functional | Should | `validate.oscal_cli_available` | Detects oscal-cli; the Layer-2 check is necessary but not sufficient for NIST conformance. | Demo | Partial |
| R-VAL-03 | `generate --validate` runs the in-process Layer-2 semantic checks before writing output. | Functional | Must | `cli._run`; `validate.semantic_errors` | `--validate` reports problems on STDERR; exit 1 on any problem, else 0. | Test | Built |
| R-VAL-04 | Standalone `poam validate <document>` verb checks an existing POA&M (the caller's or another tool's) with the same Layer-2 checks. | Functional | Should | `cli._validate` | Exit 0 clean, 1 on a semantic problem, 2 when the input is not a POA&M. | Demo | Built |

## CLI: CLI (command surface)

> See [cli-design.md](../contributors/cli-design.md) for the full design set (R-CLI-D01..D12) and
> [reference/cli.md](cli.md) for the shipped command surface. The binary is `mint-oscal` and the
> shipped invocation is `mint-oscal <model> <verb>` per [ADR-0003](../adr/0003-naming.md), not the
> pre-naming `breachsafe-oscal` wording.

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-CLI-01 | `mint-oscal poam generate --from <source> report.json` (`<model> <verb>` shape; `-` reads STDIN). | Functional | Must | `cli.py`; [ADR-0003](../adr/0003-naming.md) | Emits POA&M JSON to STDOUT; exit 0. | Demo | Built |
| R-CLI-02 | Adapters resolve through discovery (entry-points + bundled fallback); no runtime-mutable source registry. | Non-functional | Should | `adapters.get_adapter`; `_registry.resolve` | No mutable global adapter dict exists to mutate at runtime. | Inspection | Built |
| R-CLI-03 | Explicit `--from` selection; no source auto-detection. | Constraint | Should | cli argparse choices | Unknown source rejected with choices. | Test | Built |

## PKG: Packaging / NFR (ship the library)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-PKG-01 | Installable: pyproject.toml, `__init__` files, README, LICENSE (PolyForm-Noncommercial-1.0.0). | Non-functional | Must | package skeleton | `pip install .` succeeds; entry point runs. | Demo | Built |
| R-PKG-02 | Python 3.12+ (matches type-hint syntax used). | Constraint | Should | `from __future__` / `X|None` | CI runs on 3.12. | Test | Built |
| R-PKG-03 | No runtime dependency on the NIST toolchain (validation is optional/external). | Constraint | Must | `validate.py shutil.which` | Library imports + emits with zero external tools. | Test | Built |
| R-PKG-04 | Deterministic, side-effect-free core; I/O only at the CLI edge. | Non-functional | Should | emitters/adapters pure | Core functions do no I/O. | Inspection | Built |

## NG: Non-goals (explicitly out of scope)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-NG-01 | Does NOT assert an authoritative compliance pass/fail. | Constraint | Won't | CTRL-03 | Verdict is always ODP-conditioned. | Inspection | Held |
| R-NG-02 | Does NOT fabricate remediation milestones/dates. | Constraint | Won't | poam emitter | No invented deadlines. | Inspection | Held |
| R-NG-03 | Does NOT embed/transmit raw evidence excerpts. | Constraint | Won't | EVID-01 | Hashes only. | Inspection | Held |
