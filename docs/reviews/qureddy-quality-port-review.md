# QuReddy quality practices: Mint-OSCAL port review

**Status:** proposed for maintainer and test-owner review  
**Source reviewed:** `breachsafe/qureddy` through `v0.2.13`, including its local release gate,
CBOM conformance harness, documentation contract, and issue-driven regression practice.  
**Scope:** development and release-quality practices. This document does not change Mint-OSCAL
product behaviour or claim that a practice is implemented.

## Contents

1. [Purpose](#1-purpose)
2. [Decision principles](#2-decision-principles)
3. [Practices to port](#3-practices-to-port)
4. [Mint-OSCAL adoption matrix](#4-mint-oscal-adoption-matrix)
5. [Practices not to copy](#5-practices-not-to-copy)
6. [Suggested delivery sequence](#6-suggested-delivery-sequence)
7. [Review questions](#7-review-questions)

## 1. Purpose

QuReddy is an external-evidence producer: it observes TLS and emits scan results and a
CycloneDX CBOM. Mint-OSCAL is a standards-document producer: it converts normalized findings
into OSCAL. The products have different responsibilities, but both need a reviewer to be able
to answer four questions:

1. Did the released command, rather than only the source tree, run correctly?
2. Is every standards claim checked against an authority outside the project?
3. Will the same input produce a stable artifact that can be reviewed in Git?
4. Does a known defect become a durable, black-box regression?

The port should preserve Mint-OSCAL's ports-and-adapters architecture (ADR-0004), frozen IR,
and separation of structural validation from policy or control-mapping decisions.

## 2. Decision principles

### 2.1 Test the installed artifact

Source imports and unit tests are necessary but insufficient. Build the wheel, install it into a
fresh environment, invoke the `mint-oscal` console script, and inspect its stdout, stderr, exit
status, and generated OSCAL. This catches missing package data, entry-point defects, and source
path leakage.

### 2.2 Use an independent authority for standards conformance

Mint-OSCAL's internal validator protects project invariants. It does not replace the NIST
`oscal-cli` validator. The release proof should run both, with a pinned tool version and a
recorded acquisition/checksum path where practical. A document that passes the internal
validator but fails `oscal-cli` is a release blocker.

### 2.3 Preserve reproducibility

For a fixed input and declared policy version, output should be byte-identical. QuReddy now
proves this by running its installed console twice with distinct `PYTHONHASHSEED` values. Mint
already designs UUIDs and timestamps for stable output; it should prove that property at the
public CLI boundary and compare final bytes.

### 2.4 Keep standards, policy, and evidence separate

The OSCAL schema/constraints, Mint structural checks, and organization-specific control or ODP
judgments answer different questions. Tests must not turn a draft crosswalk into an asserted
fact merely because the document validates. Fixtures should cover this distinction, including
the provisional marking required by issue #84.

### 2.5 Make every fixed defect executable

For each bug, add or extend a black-box case that drives the real CLI with the smallest useful
input, checks its observable contract, and names the fixed issue. Unit tests remain useful for
isolating logic, but the regression case is the release-facing proof.

### 2.6 Make documentation part of the product contract

Commands, versions, supported formats, and the limits of validation are user-facing behaviour.
QuReddy uses a local documentation contract: numbered contents, valid local anchors, Markdown
style linting, and a deliberately manual external-link check. Mint should use an equivalent
local gate without introducing hosted CI dependence.

## 3. Practices to port

| Practice from QuReddy | Why it matters | Mint-OSCAL adaptation | Proof of completion |
| --- | --- | --- | --- |
| Fresh-build release gate | Tests what a user installs, not an editable checkout. | Build wheel and sdist; install the wheel into an empty Python 3.12 environment; run `mint-oscal`. | Gate reports artifact path, installed version, and command results. |
| External standards oracle | Prevents self-validation from becoming circular. | Run pinned `oscal-cli` validation for representative POA&M JSON and XML/YAML paths when emitted. | Gate fails on an `oscal-cli` validation error. |
| Final-byte determinism | Makes OSCAL a clean Git-review artifact. | Generate through the installed CLI twice under different `PYTHONHASHSEED` values; compare bytes. | A deliberately reordered implementation causes the gate to fail. |
| Known-good and known-bad corpus | Exercises accepted documents and rejects malformed or contradictory inputs. | Keep minimal fixtures for QuReddy, CBOM, malformed source, semantic invalid OSCAL, draft mapping, and zero-finding cases. | Each fixture has provenance and an expected exit code/result. |
| Black-box CLI contract | Covers flags, pipes, errors, stderr/stdout separation, and exit codes. | Evolve `scripts/regression.sh` into the release-facing contract; keep it independent of pytest mocks. | Harness invokes the installed console and exits nonzero on a contract failure. |
| Layered validation | Fast feedback without weakening release proof. | Run format/lint/type/unit tests first; then the installed CLI, internal validator, and `oscal-cli`. | A documented local command runs stages in order and identifies the failed stage. |
| Security and dependency checks | Finds common code and supply-chain faults early. | Use local Ruff security rules, Bandit, dependency audit, secret scan, and REUSE/SPDX checks as appropriate to this Python package. | Tool versions/results are recorded by the local gate; exceptions are explicit. |
| Documentation contract | Prevents stale commands and broken navigation. | Require numbered contents for long docs, local-anchor checks, Markdown lint, and a manual link command. | Documentation gate catches an invalid anchor and a missing numbered section. |
| Release provenance | Makes a release reconstructable. | Record source SHA, package SHA-256, Python version, Mint version, and `oscal-cli` version in a release report. | Re-running the gate produces a machine-readable report. |
| Issue-linked regressions | Preserves context and prevents a repaired flaw returning silently. | Add issue IDs in harness/test labels and keep a compact regression ledger. | Closing a defect includes one named automated reproduction. |

## 4. Mint-OSCAL adoption matrix

| Priority | Work item | Existing Mint asset to extend | Acceptance criteria | Dependencies / owner review |
| --- | --- | --- | --- | --- |
| P0 | Repair the quality baseline | `CONTRIBUTING.md`, issue #87, source headers | Contributor guidance and every first-party SPDX header name `PolyForm-Noncommercial-1.0.0`; no stale Apache instruction remains. | Resolve issue #87 before using REUSE as a release signal. |
| P0 | Make the current regression harness an installed-artifact proof | `scripts/regression.sh` | Harness never falls back silently to source execution in release mode; it records CLI path/version and checks JSON stdout, structured stderr, and exit codes. | Test owner approves additions, per `CONTRIBUTING.md`. |
| P0 | Add final-byte reproducibility | `scripts/regression.sh`, deterministic UUID/timestamp code | Same fixture through the installed console, with hash seeds `1` and `2`, has identical bytes; changed scan input has a meaningful diff. | Preserve current observation-time semantics. |
| P0 | Add external OSCAL conformance to the release gate | new local script or a `just`/`make` task | The supported POA&M fixture passes the pinned `oscal-cli`; invalid OSCAL fails; emitted XML/YAML paths are tested once implemented. | Tool acquisition/version policy must be decided; no GitHub Actions required. |
| P0 | Make defect cases a real corpus | `examples/`, `scripts/regression.sh`, issue #41 | Issue #62/#64/#67/#68/#70/#72/#73/#74 and #78–#86 each have a minimal observable regression or an explicit gap label. | Avoid duplicating source unit tests; favor CLI cases. |
| P1 | Add a documented local quality command | `pyproject.toml`, `CONTRIBUTING.md` | One command runs format, lint, type checks, tests, regression harness, and release proof; each step emits a concise result. | Keep Python 3.12 explicit. |
| P1 | Add local security/supply-chain checks | `pyproject.toml`, `scripts/leak_guard.py` | Secret scan, dependency audit, static security checks, and licensing check run locally with pinned or recorded tool versions. | Adopt only tools that run reliably without hosted credits. |
| P1 | Add documentation quality checks | `README.md`, `docs/` | Long documents have numbered contents; local links/anchors and Markdown style are checked locally; external links remain a separate manual command. | Align with the existing documentation voice. |
| P1 | Produce a release evidence record | `scripts/` and release process | JSON or text report records source commit, artifact hashes, interpreter, dependency/validator versions, and every gate result. | Decide whether reports are retained as release assets or internal evidence. |
| P2 | Test source-extension combinations systematically | adapters, extensions, ADR-0008 | Matrix covers adapter alone, extension alone where valid, idempotent repeated extension, and conflicting producer declaration. | Must preserve agnostic IR and avoid emitter-specific adapter behavior. |
| P2 | Add mutation or property testing selectively | parser/validator hot spots | At least one parser/validator property is falsified across generated malformed inputs, with stable shrinkable examples. | Use only after the P0 corpus is in place. |

## 5. Practices not to copy

Do not copy QuReddy's TLS transport matrix, OpenSSL invocation/replay, endpoint scanning, or
CycloneDX-specific validator into Mint-OSCAL. Mint receives input and emits OSCAL; it should
validate producer contracts and OSCAL output, not become a network scanner or a second CBOM
implementation.

Do not claim an OSCAL document is compliant because `oscal-cli` accepts it. Schema and
constraint validation, source-evidence interpretation, control mapping, and organization
parameters remain distinct review layers.

Do not add a hosted GitHub Actions workflow for this plan. The project currently needs local,
repeatable commands because hosted Actions capacity is unavailable.

Do not move all checks into `tests/` or rewrite the existing regression script in pytest. Keep
unit tests for focused logic and retain a shell-level installed-console harness for the public
contract.

## 6. Suggested delivery sequence

1. Close the P0 license/SPDX inconsistency (issue #87) so policy and tooling agree.
2. Define a `release-gate` command around the existing black-box harness and fresh wheel install.
3. Add hash-seed final-byte determinism and pinned `oscal-cli` validation to that gate.
4. Convert the open correctness issues into a prioritized fixture/regression matrix, beginning
   with #78–#86 because they can change PQC posture and OSCAL validity.
5. Add P1 local quality/security/docs commands and an evidence report once the release contract
   is stable.
6. Reassess P2 property testing and extension matrices after the core source/target contracts
   are covered.

## 7. Review questions

1. Which `oscal-cli` distribution, exact version, checksum, and platform support policy should
   Mint's local gate use?
2. Should release evidence be committed, attached to a release, or stored only in the internal
   assurance system?
3. Which open Mint defects need a fixture first because they could produce a misleading OSCAL
   document rather than a clear failure?
4. Does the project want the documentation contract applied to all Markdown now, or phased in
   starting with public README and `docs/`?
5. Who is the designated test owner for approval of the proposed regression additions?
