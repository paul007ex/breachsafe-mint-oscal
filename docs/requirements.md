# Requirements (RTM)

Requirements Traceability Matrix for `mint-oscal` — 42 requirements across 11 categories
(ARCH, SRC, OUT, OSC, DET, EVID, CTRL, VAL, CLI, PKG, NG). Source of truth:
[`requirements.xlsx`](requirements.xlsx) → *Requirements* sheet.

See [README](README.md) for the index and the honest-verdict caveat that governs all
control-mapping requirements below.

## Contents

1. [Legend](#legend)
2. [ARCH — Architecture (N sources → neutral IR → M targets)](#arch--architecture-n-sources--neutral-ir--m-targets)
3. [SRC — Sources (input adapters)](#src--sources-input-adapters)
4. [OUT — Targets (output emitters)](#out--targets-output-emitters)
5. [OSC — OSCAL Conformance (schema + version)](#osc--oscal-conformance-schema--version)
6. [DET — Determinism (reproducibility)](#det--determinism-reproducibility)
7. [EVID — Evidence integrity (privacy of evidence)](#evid--evidence-integrity-privacy-of-evidence)
8. [CTRL — Control mapping (finding → control crosswalk)](#ctrl--control-mapping-finding--control-crosswalk)
9. [VAL — Validation (checking output)](#val--validation-checking-output)
10. [CLI — CLI (command surface)](#cli--cli-command-surface)
11. [PKG — Packaging / NFR (ship the library)](#pkg--packaging--nfr-ship-the-library)
12. [NG — Non-goals (explicitly out of scope)](#ng--non-goals-explicitly-out-of-scope)

## Legend

- **Priority** — Must (release blocked without it) · Should (ship without only with a
  reason) · Could (roadmap) · Won't (explicit non-goal).
- **Type** — Functional (what it does) · Non-functional (quality attribute) · Constraint
  (a boundary that must hold).
- **Verify** — Test (automated, tester-owned) · Demo (run and observe) · Inspection (read
  code/doc) · Analysis (reason from spec).
- **Status** — Built / Met / PASS (implemented / evidenced) · Designed / Partial
  (decided or partially done) · Open / Backlog / Deferred (not started / later) · Held
  (a constraint currently being honored).

## ARCH — Architecture (N sources → neutral IR → M targets)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-ARCH-01 | Sources and targets are decoupled through a neutral intermediate representation (IR). | Constraint | Must | N→IR→M design | New source needs no emitter change and vice-versa. | Inspection | Designed |
| R-ARCH-02 | Adding a source = one new adapter registered in a single place. | Functional | Must | `cli._ADAPTERS` registry | Register in `_ADAPTERS` only; emitters untouched. | Inspection | Designed |
| R-ARCH-03 | Adding a target = one new emitter; adapters untouched. | Functional | Must | `emitters/` package | New emitter consumes IR only. | Inspection | Designed |
| R-ARCH-04 | IR is frozen, source/target-agnostic (Finding/Subject/Evidence). | Constraint | Must | `ir.py` frozen dataclasses | Dataclasses frozen; no source field names leak past adapter. | Inspection | Built |

## SRC — Sources (input adapters)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-SRC-01 | QuReddy `qureddy.scan.v1` JSON adapter. | Functional | Must | `adapters/qureddy.py` | Live example.com scan → IR findings + subject. | Demo | Built |
| R-SRC-02 | Prowler adapter. | Functional | Should | roadmap | Prowler OCSF/native output → IR. | Test | Backlog |
| R-SRC-03 | OCSF adapter. | Functional | Could | roadmap | OCSF finding → IR. | Test | Backlog |
| R-SRC-04 | CycloneDX CBOM adapter. | Functional | Could | roadmap; qureddy CBOM | CBOM crypto-assets → IR. | Test | Backlog |
| R-SRC-05 | OpenTelemetry adapter. | Functional | Won't | roadmap | Deferred beyond this release. | – | Deferred |
| R-SRC-06 | Adapter fails loudly on unknown/unsupported schema version. | Non-functional | Should | – | Unsupported version raises, never silently maps. | Test | Open |

## OUT — Targets (output emitters)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-OUT-01 | OSCAL POA&M emitter (first target). | Functional | Must | `emitters/poam.py` | Emits plan-of-action-and-milestones with all required fields. | Demo | Built |
| R-OUT-02 | Output is standalone + human-readable (no base64, no mandatory external fetch). | Constraint | Must | Option A decision | Reader understands posture from the doc alone. | Inspection | Met (v2) |
| R-OUT-03 | Crypto facts carried as readable namespaced props (`ns=https://breachsafe.ai/ns/oscal`). | Functional | Must | v2 observation props | readiness/algorithm/level/cert-sig/hashes present as props. | Inspection | Met (v2) |
| R-OUT-04 | Optional CBOM companion via `relevant-evidence` href; POA&M valid without it. | Functional | Should | v2 relevant-evidence | Remove the link → still validates. | Demo | Met (v2) |
| R-OUT-05 | Provenance in metadata (generator + responsible-party). | Functional | Should | v2 metadata | generator/version props + Prepared By party present. | Inspection | Met (v2) |

## OSC — OSCAL Conformance (schema + version)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-OSC-01 | Declared `oscal-version = 1.2.2` (current NIST OSCAL release). | Constraint | Must | oscal-cli 3.2.0; NIST v1.2.2 JSON schema | Declared 1.2.2; no `oscal-target-version` prop. | Inspection | Met (v3) |
| R-OSC-02 | All required POA&M fields present (uuid, metadata{title,last-modified,version,oscal-version}, system-id\|import-ssp, ≥1 poam-item{title,description}). | Constraint | Must | `oscal_poam_metaschema.xml` | Validator reports required fields satisfied. | Demo | Met (v2) |
| R-OSC-03 | Output validates clean against NIST oscal-cli. | Non-functional | Must | ghcr.io oscal-cli:latest (3.2.0) | "The file is valid." exit clean. | Demo | PASS (v2) |
| R-OSC-04 | Element ordering conforms to the metaschema. | Constraint | Must | metaschema | No ordering errors from validator. | Demo | PASS (v2) |
| R-OSC-05 | All cross-references resolve (obs↔risk↔poam-item, subject↔inventory-item). | Constraint | Must | structural check | No dangling refs. | Test | PASS (v2) |

## DET — Determinism (reproducibility)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-DET-01 | Same scan → same OSCAL uuids (uuid5 over fixed namespace). | Non-functional | Must | `poam._det` | Re-run yields identical uuids. | Test | Built |
| R-DET-02 | Output byte-stable for same input + timestamp. | Non-functional | Should | – | diff of two runs is empty. | Test | Open |

## EVID — Evidence integrity (privacy of evidence)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-EVID-01 | Evidence carries hashes (command-sha256, stdout-sha256), never raw excerpts. | Constraint | Must | `adapters/qureddy._evidence` | No stdout/plaintext bodies in output. | Inspection | Built |
| R-EVID-02 | No live scan-target data committed to repo artifacts. | Constraint | Must | session rule | example.com samples only in /tmp + examples, not product code. | Inspection | Held |

## CTRL — Control mapping (finding → control crosswalk)

> The finding→control→ODP judgment is an **organization-policy assertion**, not a
> scanner-derived truth. Every row of the crosswalk must cite a control statement and
> carry reviewer sign-off; see [oscal-shapes.md](oscal-shapes.md) and the DRAFT crosswalk
> in the workbook. `R-CTRL-01` is **OPEN**.

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-CTRL-01 | finding→control crosswalk is authored, cited, human-reviewed; NOT LLM/scanner-guessed. | Constraint | Must | conformance lane; rev5 catalog | Every row cites a control statement; reviewer sign-off. | Inspection | OPEN |
| R-CTRL-02 | Mapping is framework-scoped (SP 800-53 rev5) and ODP-aware. | Functional | Must | rev5 catalog ODPs | Row records ODP id + org-set value. | Inspection | OPEN |
| R-CTRL-03 | POA&M states the verdict as an assertion tied to org ODP, not scanner truth. | Constraint | Must | v2 poam-item remarks | remarks makes the ODP dependency explicit. | Inspection | Met (v2) |
| R-CTRL-04 | SC-13 primary, SC-12 supporting for KEX/crypto-protection findings; SC-8 excluded (overreach). | Functional | Should | SC-13/12/8 catalog text | SC-8 not emitted; SC-13+SC-12 present. | Inspection | Met (v2) |
| R-CTRL-05 | No PQC/CNSA catalog exists; ODP bar is org-supplied, not shipped as fact. | Constraint | Must | reference tree has no PQC catalog | ODP value is caller/policy input. | Inspection | Held |

## VAL — Validation (checking output)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-VAL-01 | Structural validator (uuid validity, dangling refs) with no network/toolchain. | Functional | Must | `validate.structural_errors` | Returns `[]` for sound doc; lists problems otherwise. | Test | Built |
| R-VAL-02 | Optional oscal-cli integration when available (local or docker). | Functional | Should | `validate.oscal_cli_available` | Detects oscal-cli; runs full validation. | Demo | Partial |
| R-VAL-03 | CLI `--validate` flag runs the structural check. | Functional | Must | `cli.main` | `--validate` prints OK / errors + exit code. | Test | Built |

## CLI — CLI (command surface)

> See [cli-design.md](cli-design.md) for the full design set (R-CLI-D01..D12). Note: the
> command name below reflects the pre-naming RTM wording; the decided invocation is
> `mint-oscal <shape>` per [ADR-0003](adr/0003-naming.md).

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-CLI-01 | `breachsafe-oscal poam --from <source> report.json`. | Functional | Must | `cli.py` | Emits POA&M JSON to stdout. | Demo | Built |
| R-CLI-02 | Source registry is immutable at runtime (`MappingProxyType`). | Non-functional | Should | `cli._ADAPTERS` | Registry cannot be mutated. | Inspection | Built |
| R-CLI-03 | Explicit `--from` selection; no source auto-detection. | Constraint | Should | cli argparse choices | Unknown source rejected with choices. | Test | Built |

## PKG — Packaging / NFR (ship the library)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-PKG-01 | Installable: pyproject.toml, `__init__` files, README, LICENSE (PolyForm-Noncommercial-1.0.0). | Non-functional | Must | package skeleton | `pip install .` succeeds; entry point runs. | Demo | Built |
| R-PKG-02 | Python 3.12+ (matches type-hint syntax used). | Constraint | Should | `from __future__` / `X|None` | CI runs on 3.12. | Test | Built |
| R-PKG-03 | No runtime dependency on the NIST toolchain (validation is optional/external). | Constraint | Must | `validate.py shutil.which` | Library imports + emits with zero external tools. | Test | Built |
| R-PKG-04 | Deterministic, side-effect-free core; I/O only at the CLI edge. | Non-functional | Should | emitters/adapters pure | Core functions do no I/O. | Inspection | Built |

## NG — Non-goals (explicitly out of scope)

| ID | Requirement | Type | Priority | Grounding / Source | Acceptance Criteria | Verify | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-NG-01 | Does NOT assert an authoritative compliance pass/fail. | Constraint | Won't | CTRL-03 | Verdict is always ODP-conditioned. | Inspection | Held |
| R-NG-02 | Does NOT fabricate remediation milestones/dates. | Constraint | Won't | poam emitter | No invented deadlines. | Inspection | Held |
| R-NG-03 | Does NOT embed/transmit raw evidence excerpts. | Constraint | Won't | EVID-01 | Hashes only. | Inspection | Held |
