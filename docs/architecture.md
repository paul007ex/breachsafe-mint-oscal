# mint-oscal — architecture

> **Status: pre-alpha (design + prototype).** The POA&M path is prototyped and
> oscal-cli-validated end-to-end; `ar`/`component-definition` emitters and the
> agnostic-core restructure are designed, not yet shipped. Markers below:
> **[S]** shipped/prototyped · **[D]** designed · **[P]** planned.

## Contents

1. [Overview](#overview)
2. [Context: callers and trust boundaries](#context-callers-and-trust-boundaries)
3. [Data-flow diagram with trust boundaries](#data-flow-diagram-with-trust-boundaries)
4. [Decision ledger](#decision-ledger)
5. [Where mint-oscal fits the ecosystem](#where-mint-oscal-fits-the-ecosystem)
6. [Output](#output)
7. [Versioning](#versioning)
8. [References](#references)

## Overview

mint-oscal converts security-tool findings into NIST OSCAL documents through an
**N sources → neutral IR → M OSCAL shapes** pipeline. The core is *agnostic*: it
knows only the intermediate representation (IR) and OSCAL, never a source's schema
(see [ADR-0004](adr/0004-agnostic-core.md)). Source knowledge lives in optional edge
adapters or, better, in the sources themselves (which emit the published `mint.ir.v1`
contract directly).

```
        (source-owned)              agnostic core (knows only IR + OSCAL)
 QuReddy ──emit mint.ir.v1──┐
 Prowler ──[adapter plugin]─┼──▶  IR  ──▶ emitters ──▶ POA&M / ar / component-definition
 OCSF   ──[adapter plugin]──┘           ▲
                                        └── consume: profile / catalog (the ODP bar)
```

## Context: callers and trust boundaries

```
 QuReddy ─emit mint.ir.v1────────────►┐                     ┌──► oscal-cli (subprocess)
 TAO / Osmedeus ─CLI pipe─────────────►│  mint-oscal        │     validate · XML/YAML
 Managed engine ─API convert(ir,…)────►│  (lib + CLI)       ├──► OSCAL Profile / Catalog
                                       └────────┬───────────┘     (consumed: the bar)
                                                ▼
                              POA&M / ar / component-definition
```

Callers split by surface: **library API** for embedded callers (QuReddy, managed
engine); **composable CLI** for orchestrators (TAO, Osmedeus). Both hit the same core.

## Data-flow diagram with trust boundaries

```
 EXTERNAL (untrusted)         ║ INGESTION ║     TRUSTED CORE            ║ EXTERN ║
 [foreign scan JSON] ─1─►( adapter )──►( ir.schema )═╗                 ║        ║
 [mint.ir.v1 doc] ───2──────────────►( ir.schema )══╣ trusted IR      ║        ║
                                                     ▼                 ║        ║
                                             ( emitters )─►( render )─►( oscal-cli )─► OSCAL
 [OSCAL Profile] ─3─►( consume.profile )═════╝  ▲            (XML/YAML)    validate
 [SP800-53 catalog]─4─►( consume.catalog )═► crosswalk (POLICY, cited)   ║        ║

 TB-1  Ingestion — foreign input is schema-validated before it becomes IR.
 TB-2  Evidence  — only hashes cross into emitters; never raw excerpts (R-EVID-01).
 TB-3  Verdict   — control/ODP mapping is org POLICY (cited), not scanner truth.
 TB-4  Tooling   — oscal-cli runs as an isolated subprocess (XML/YAML + validation).
```

## Decision ledger

| ADR / tension | Decision | Status |
|---|---|---|
| ADR-0001 / T1 | Assessment Results (`ar`) canonical; POA&M is the flagship open-risk extract | Proposed |
| ADR-0002 / CLI | Model-first subcommands + composable filter (NIST-aligned) | Proposed |
| ADR-0003 | Naming: repo `breachsafe-mint-oscal` · pypi `mint-oscal` · import `mint_oscal` | Accepted |
| ADR-0004 / T8 | Agnostic core; IR promoted to published `mint.ir.v1`; adapters at the edge | Accepted |
| ADR-0005 / T7 | JSON native; XML/YAML via oscal-cli (optional runtime dep) | Accepted |
| T2 · T3 · T4 · T5 · T6 | lifecycle merge · fleet · consume-profile ODP · import-ssp · ar import-ap | Open |

## Where mint-oscal fits the ecosystem

| Capability | mint-oscal | oscal-cli | Trestle | oscalkit | RegScale |
|---|---|---|---|---|---|
| Produce OSCAL **from scanner findings** | ✅ core | ❌ | ~ | ❌ | ✅ (commercial) |
| **PQC/crypto-aware** findings → OSCAL | ✅ unique | ❌ | ❌ | ❌ | ❌ |
| Validate / convert OSCAL | 🔁 delegates | ✅ | ✅ | ✅ | ✅ |
| Composable filter | ✅ | ✅ | ~ | ✅ | ~ |
| Deterministic → git-diffable | ✅ | n/a | ✅ | n/a | ? |
| License | PolyForm-NC-1.0.0 | public domain | Apache-2.0 | Apache-2.0 | commercial |

**Niche:** no open tool converts scanner findings — least of all PQC posture — *into*
OSCAL. oscal-cli/oscalkit only transform existing OSCAL; Trestle authors/manages it.

**Git-diffability:** uuids are `uuid5` and `last-modified` is pinned via `--now`, so a
re-scan yields a clean, reviewable *delta* rather than churn — the same git-first
philosophy Trestle applies to authored OSCAL, applied here to generated OSCAL.

## Output

mint-oscal emits canonical OSCAL (it *is* OSCAL). Native default **JSON**; XML/YAML via
oscal-cli. A real, oscal-cli-validated document lives at
[`../examples/example.poam.v2.xml`](../examples/example.poam.v2.xml). Crypto facts ride as
readable `prop ns="https://breachsafe.ai/ns/oscal"` (readiness, algorithm,
nistQuantumSecurityLevel, cert-signature, evidence hashes) — standalone, no base64.

## Versioning

Declare `oscal-version` **1.1.2** for maximum validator interop (older oscal-cli, Trestle's
`^1.2.[0-1]$`); record the internal target **1.2.2** as
`prop name="oscal-target-version"`. Validated with oscal-cli 3.2.0. "Valid OSCAL" ≠
"compliant" — the verdict depends on the org's ODP, which is asserted, not scanner-derived.

## References

- [requirements.md](requirements.md) · [use-cases.md](use-cases.md) ·
  [oscal-shapes.md](oscal-shapes.md) · [cli.md](cli.md)
- [ADRs](adr/) · `requirements.xlsx` (13-tab source of truth)
- Skill: `breachsafe-oscal-conformance` (OSCAL required-fields + crosswalk gate)
