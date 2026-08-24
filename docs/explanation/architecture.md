# mint-oscal architecture

> **Status: pre-alpha (design + prototype).** The POA&M path is prototyped and
> oscal-cli-validated end-to-end. The `ar` (Assessment Results) emitter and the
> agnostic-core restructure are designed, not yet shipped.

## Contents

1. [Overview](#overview)
2. [Data flow and trust boundaries](#data-flow-and-trust-boundaries)
3. [Decision ledger](#decision-ledger)
4. [Where mint-oscal fits the ecosystem](#where-mint-oscal-fits-the-ecosystem)
5. [Output](#output)
6. [Versioning](#versioning)
7. [References](#references)

## Overview

### Source layout and separation of concerns

The implementation is organized by responsibility, while compatibility modules preserve
the existing import and entry-point contracts:

```text
mint_oscal/
├── ingestion/       untrusted source parsing and CBOM boundary
├── adapters/        compatibility and third-party adapter ports
├── validation/      pure OSCAL structural/reference/domain checks
├── governance/      registry, lock, digest, and policy-pack integrity
├── ir/              trusted intermediate representation
├── emitters/        IR -> OSCAL model construction
├── render.py        encoding/delegation boundary
└── cli.py           user-facing orchestration and exit-code boundary
```

`adapters/cbom.py`, `validate.py`, and `registry.py` remain thin compatibility imports;
new code belongs under `ingestion`, `validation`, and `governance`. This prevents source
formats, validation policy, registry governance, and CLI concerns from becoming one
dependency cycle.

mint-oscal converts security-tool findings into NIST OSCAL documents through an
`N sources -> neutral IR -> M OSCAL shapes` pipeline. The core is agnostic: it knows only
the intermediate representation (IR) and OSCAL, never a source's schema
(see [ADR-0004](../adr/0004-agnostic-core.md)). Source knowledge lives in optional edge
adapters or in the sources themselves, which can emit the published `mint.ir.v1` contract
directly. See [the agnostic core](agnostic-core.md) for why the seam is shaped this way.

```
        (source-owned)              agnostic core (knows only IR + OSCAL)
 QuReddy ──emit mint.ir.v1──┐
 Prowler ──[adapter plugin]─┼──▶  IR  ──▶ emitters ──▶ POA&M / ar
 OCSF   ──[adapter plugin]──┘           ▲
                                        └── consume: profile / catalog (the ODP bar, planned)
```

Callers reach the same core through two surfaces. Embedded callers such as QuReddy or a
managed engine use the library API. Orchestrators such as TAO or Osmedeus pipe through the
composable CLI. Both compose the same adapter, emitter, and registry.

## Data flow and trust boundaries

```
 EXTERNAL (untrusted)         ║ INGESTION ║     TRUSTED CORE            ║ EXTERN ║
 [foreign scan JSON] ─1─►( adapter )──►( ir.schema )═╗                 ║        ║
 [mint.ir.v1 doc] ───2──────────────►( ir.schema )══╣ trusted IR      ║        ║
                                                     ▼                 ║        ║
                                             ( emitters )─►( render )─►( oscal-cli )─► OSCAL
 [OSCAL Profile] ─3─►( consume.profile )═════╝  ▲            (XML/YAML)    validate
 [SP800-53 catalog]─4─►( consume.catalog )═► crosswalk (POLICY, cited)   ║        ║
                       (consume path planned)

 TB-1  Ingestion: foreign input is schema-validated before it becomes IR.
 TB-2  Evidence:  only hashes cross into emitters; raw excerpts stay out (R-EVID-01).
 TB-3  Verdict:   control/ODP mapping is org policy (cited); the scanner supplies facts.
 TB-4  Tooling:   oscal-cli runs as an isolated subprocess (XML/YAML plus validation).
```

The consume boxes (profile and catalog ingestion for the organization-defined parameter)
are a planned path, not shipped. The boundaries hold today because the emitters already
carry only IR facts and hashes, and control mapping is versioned policy YAML rather than
scanner output.

### Profile resolver boundary (P0 design)

The future Profile path is a strict extension of the `oscal-cli` command grammar:

```text
mint-oscal profile <command> [<options>]
  create       BreachSAFE registry-backed objective resolver
  validate     same model/action meaning as oscal-cli
  convert      same model/action meaning as oscal-cli
  resolve      same model/action meaning as oscal-cli
  explain      BreachSAFE registry/provenance explanation
```

The parser remains the existing nested command tree (root → model → command), not a
framework-specific `mint-oscal nist profile` branch. `create` loads a versioned registry
entry, verifies selected IDs against the Catalog, constructs the Profile through the OSCAL
engine, and emits a resolution receipt. `validate`, `convert`, and `resolve` preserve the
official option names, positional source/destination conventions, and help hierarchy.

The registry is the BreachSAFE policy seam; the OSCAL Profile remains the authoritative
control-selection artifact. Targets are introduced later by an Assessment Plan, not added
to Profile creation. This design is proposed and does not change the shipped POA&M path.

### Registry deployment decision

The P0 source of truth is a reviewable Git policy pack, not a database or service:

```text
Git policy pack
  -> Mint-OSCAL registry library/CLI
  -> registry.lock / signed artifact
  -> optional Enterprise API + database projection
```

The database/API projection must be rebuildable from Git. It may add search, approvals,
tenant views, and workflow, but it cannot become an unreviewed policy authority. P0 ships
only Catalogs required by approved use cases, preserving each upstream Catalog unchanged
with source URL, version, and SHA-256. A lock file records policy/catalog digests and the
resolver version for deterministic compilation.

## Decision ledger

| ADR / tension | Decision | Status |
|---|---|---|
| ADR-0001 / T1 | Assessment Results (`ar`) canonical; POA&M is the first shipped open-risk extract | Proposed |
| ADR-0002 / CLI | Model-first subcommands + composable filter (NIST-aligned) | Proposed |
| ADR-0003 | Naming: repo `breachsafe-mint-oscal` · pypi `mint-oscal` · import `mint_oscal` | Accepted |
| ADR-0004 / T8 | Agnostic core; IR promoted to published `mint.ir.v1`; adapters at the edge | Accepted |
| ADR-0005 / T7 | JSON native; XML/YAML via oscal-cli (optional runtime dep) | Accepted |
| T2 · T3 · T4 · T5 · T6 | lifecycle merge · fleet · consume-profile ODP · import-ssp · ar import-ap | Open |

## Where mint-oscal fits the ecosystem

| Capability | mint-oscal | oscal-cli | Trestle | oscalkit | RegScale |
|---|---|---|---|---|---|
| Produce OSCAL from scanner findings | ✅ core | ❌ | ~ | ❌ | ✅ (commercial) |
| PQC/crypto-aware findings to OSCAL | ✅ | ❌ | ❌ | ❌ | ❌ |
| Validate / convert OSCAL | 🔁 delegates | ✅ | ✅ | ✅ | ✅ |
| Composable filter | ✅ | ✅ | ~ | ✅ | ~ |
| Deterministic, git-diffable | ✅ | n/a | ✅ | n/a | ? |
| License | PolyForm-NC-1.0.0 | public domain | Apache-2.0 | Apache-2.0 | commercial |

The open tools in this table transform or author OSCAL that already exists: oscal-cli and
oscalkit convert and validate it, Trestle authors and manages it. None ingest scanner
findings, and none carry a PQC crypto-posture crosswalk. mint-oscal fills that ingestion
gap.

Determinism makes the output git-diffable. UUIDs are `uuid5` over stable inputs, and the
document `last-modified` timestamp is the latest finding `observed_at`, derived from the
source scan rather than the wall clock (see [Output](#output)). Re-minting the same
captured scan produces byte-identical OSCAL, so a later scan yields a reviewable diff of
what actually changed. This applies the git-first discipline Trestle uses for authored
OSCAL to generated OSCAL.

## Output

mint-oscal emits canonical OSCAL. The native default is JSON; XML and YAML are produced by
delegating to oscal-cli. An oscal-cli-validated document lives at
[`examples/example.poam.v2.xml`](../../examples/example.poam.v2.xml). Crypto facts ride as
readable props under `ns="https://breachsafe.ai/ns/oscal"` (readiness, algorithm,
nistQuantumSecurityLevel, cert-signature, evidence hashes), stored as plain values with no
base64 blobs.

The document `last-modified` timestamp is the latest `observed_at` across the findings, not
a fresh wall-clock reading. The emitter derives it in `emitters/poam.py::_stamp`, which
takes the chronological maximum of the findings' observation times and falls back to the
Unix epoch when no finding carries one. There is no `--now` CLI flag; a `now=` keyword
exists only as an internal `emit()` argument for tests and is never wired to the command
line. This is what keeps re-mints byte-identical.

## Versioning

The output declares `oscal-version` 1.2.2, the current NIST OSCAL release, validated with
oscal-cli 3.2.0 against the NIST v1.2.2 JSON schema. Valid OSCAL is a separate claim from
compliant: the compliance verdict depends on the organization-defined parameter, which the
organization asserts. See [valid is not compliant](valid-vs-compliant.md).

## References

- [requirements.md](../reference/requirements.md) · [use-cases.md](../reference/use-cases.md) ·
  [oscal-shapes.md](../reference/oscal-shapes.md) · [cli.md](../reference/cli.md)
- [ADRs](../adr/) · `requirements.xlsx` (13-tab source of truth)
- Skill: `breachsafe-oscal-conformance` (OSCAL required-fields + crosswalk gate)
