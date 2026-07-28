# Use Cases

Eight use cases for `mint-oscal`, source: [`requirements.xlsx`](requirements.xlsx) →
*Use-Cases* sheet. See the [README](README.md) index and the honest-verdict caveat.

Use cases sit on a **two-axis matrix**: **N sources** (QuReddy scan JSON, QuReddy CBOM,
Prowler, OCSF, org PQC policy, an existing POA&M, fleet scans) crossed with **M OSCAL
shapes** (POA&M, Assessment Results, Component Definition, Profile). The shared neutral IR
is what makes each new source × shape cell cheap: an adapter fills the IR, an emitter reads
it, and neither knows about the other.

| UC | Source | OSCAL target | Description | Priority | Depends on | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UC-1 | QuReddy scan JSON | POA&M | Convert one scan into a standalone, readable POA&M. | Must | T1 | Prototyped (v2 validated) |
| UC-2 | QuReddy scan JSON | Assessment Results | Emit canonical observations/findings/risks (what was observed). | Must | T1 | Designed |
| UC-3 | QuReddy CBOM | Component Definition | Render crypto inventory as OSCAL components. | Should | – | Backlog |
| UC-4 | Prowler | POA&M / SAR | Second source adapter into the same IR. | Should | – | Backlog |
| UC-5 | OCSF | Assessment Results | Normalized findings source. | Could | – | Backlog |
| UC-6 | Org PQC policy | Profile (CONSUME) | Read the ODP/CNSA bar to parameterize the verdict instead of hardcoding it. | Should | T4 | Backlog |
| UC-7 | Existing POA&M + new scan | POA&M (merge) | Reconcile item status across re-scans (open→closed) by deterministic uuid. | Should | T2 | Backlog |
| UC-8 | Fleet scan (many endpoints) | POA&M / SAR | One document, many inventory-items; findings reference their subject. | Should | T3 | Backlog |

## UC-1 — QuReddy scan → POA&M *(Must, prototyped and validated)*

Convert a single QuReddy scan into a standalone, human-readable OSCAL POA&M. This is the
flagship path and the only end-to-end proven one: prototype v2 validated clean against
`oscal-cli 3.2.0`. The document is self-contained (no base64, no mandatory external fetch)
with crypto facts carried as readable namespaced props. Depends on decision **T1**
([ADR-0001](adr/0001-primary-oscal-target.md)).

## UC-2 — QuReddy scan → Assessment Results (SAR) *(Must)*

Emit the canonical, faithful artifact: what the scanner actually *observed*
(observations/findings/risks), as opposed to the downstream management plan. Per
[ADR-0001](adr/0001-primary-oscal-target.md), SAR is the canonical record and POA&M is its
open-risk extract. Designed; required fields **NEEDS CONFIRM** from the SAR metaschema
before the emitter is written (see [oscal-shapes.md](oscal-shapes.md)).

## UC-3 — QuReddy CBOM → Component Definition *(Should)*

Render a CycloneDX CBOM crypto inventory as OSCAL Component Definition components. Backlog;
component required fields **NEEDS CONFIRM** from the metaschema.

## UC-4 — Prowler → POA&M / SAR *(Should)*

Prove the N-sources thesis: a second, unrelated source adapter feeds the same IR and reuses
the existing emitters with no emitter changes (R-ARCH-01/03). Backlog.

## UC-5 — OCSF → Assessment Results *(Could)*

OCSF as a normalized findings source into the IR, emitting SAR. Roadmap.

## UC-6 — Org PQC policy → Profile (CONSUME) *(Should)*

Instead of hardcoding the compliance bar, **consume** an OSCAL Profile that carries the
org's ODP/CNSA values (e.g. `set-parameters`) and parameterize the verdict from that cited
artifact. This is the integrity mechanism behind the honest-verdict caveat: the pass/fail
bar is an organization-defined parameter supplied by policy, not a scanner-asserted fact.
Depends on decision **T4**. Backlog.

## UC-7 — Existing POA&M + new scan → merge *(Should)*

Reconcile POA&M item status across re-scans (e.g. open→closed) using deterministic uuid5 to
match items between runs. For v1 the tool emits an honest point-in-time snapshot (decision
T2 option A); merge is a v2 capability that uuid5 makes feasible. Depends on **T2**.
Backlog.

## UC-8 — Fleet / multi-subject *(Should)*

One OSCAL document spanning many endpoints: multiple `inventory-item`s, with each finding
referencing its own subject. The IR already carries `Finding.subject`; the emitter must be
generalized from single-subject to fleet (decision T3 option B). Depends on **T3**. Backlog.
