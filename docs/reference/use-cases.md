# Use Cases

Eight use cases for `mint-oscal`, source: [`requirements.xlsx`](../requirements.xlsx) →
*Use-Cases* sheet. See the [docs index](../README.md) and the honest-verdict caveat.

Use cases sit on a two-axis matrix: N sources (CycloneDX CBOM, QuReddy scan JSON, Prowler,
OCSF, org PQC policy, an existing POA&M, fleet scans) crossed with M OSCAL shapes (POA&M,
Assessment Results, Profile). The shared neutral IR keeps each new source × shape cell
cheap: an adapter fills the IR, an emitter reads it, and neither depends on the other.

Two cells are shipped and runnable today (UC-1 and UC-3, both `mint-oscal poam generate`).
Every other cell is roadmap: its command does not exist yet. Read the `Status` column
before treating a row as an available command.

| UC | Source | OSCAL target | Description | Priority | Depends on | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UC-1 | QuReddy scan JSON | POA&M | `--from qureddy`: convert one scan into a standalone, readable POA&M. | Must | T1 | Built (oscal-cli 3.2.0 clean) |
| UC-2 | QuReddy scan JSON | Assessment Results | Emit canonical observations/findings/risks (what was observed). | Must | T1 | Designed |
| UC-3 | CycloneDX CBOM | POA&M | `--from cbom` (default): convert a CBOM crypto inventory into a standalone POA&M. | Must | n/a | Built (oscal-cli 3.2.0 clean) |
| UC-4 | Prowler | POA&M / Assessment Results | Second source adapter into the same IR. | Should | n/a | Backlog |
| UC-5 | OCSF | Assessment Results | Normalized findings source. | Could | n/a | Backlog |
| UC-6 | Org PQC policy | Profile (CONSUME) | Read the ODP/CNSA bar to parameterize the verdict instead of hardcoding it. | Should | T4 | Backlog |
| UC-7 | Existing POA&M + new scan | POA&M (merge) | Reconcile item status across re-scans (open→closed) by deterministic uuid. | Should | T2 | Backlog |
| UC-8 | Fleet scan (many endpoints) | POA&M / Assessment Results | One document, many inventory-items; findings reference their subject. | Should | T3 | Backlog |

## Contents

1. [UC-1: QuReddy scan → POA&M](#uc-1-qureddy-scan--poam-must-shipped)
2. [UC-2: QuReddy scan → Assessment Results](#uc-2-qureddy-scan--assessment-results-must)
3. [UC-3: CycloneDX CBOM → POA&M](#uc-3-cyclonedx-cbom--poam-must-shipped-default)
4. [UC-4: Prowler → POA&M / Assessment Results](#uc-4-prowler--poam--assessment-results-should)
5. [UC-5: OCSF → Assessment Results](#uc-5-ocsf--assessment-results-could)
6. [UC-6: Org PQC policy → Profile (CONSUME)](#uc-6-org-pqc-policy--profile-consume-should)
7. [UC-7: Existing POA&M + new scan → merge](#uc-7-existing-poam--new-scan--merge-should)
8. [UC-8: Fleet / multi-subject](#uc-8-fleet--multi-subject-should)

## UC-1: QuReddy scan → POA&M *(Must, shipped)*

Convert a single QuReddy scan into a standalone, human-readable OSCAL POA&M with
`mint-oscal poam generate --from qureddy scan.json`. The document is self-contained (no
base64, no mandatory external fetch) with crypto facts carried as readable namespaced
props. This path and the CBOM path (UC-3) both ship today and validate clean against
`oscal-cli 3.2.0`. Depends on decision **T1**
([ADR-0001](../adr/0001-primary-oscal-target.md)).

## UC-2: QuReddy scan → Assessment Results *(Must)*

Emit the canonical artifact recording what the scanner observed
(observations/findings/risks), separate from the downstream management plan. Per
[ADR-0001](../adr/0001-primary-oscal-target.md), Assessment Results is the canonical record
and POA&M is its open-risk extract. The `ar` model is registered but planned: the emitter
raises `NotImplementedError` (exit 3). Required fields **NEEDS CONFIRM** from the Assessment
Results metaschema before the emitter is written (see [oscal-shapes.md](oscal-shapes.md)).

## UC-3: CycloneDX CBOM → POA&M *(Must, shipped default)*

Convert a CycloneDX CBOM crypto inventory into a standalone OSCAL POA&M with
`mint-oscal poam generate --from cbom scan.cbom.json`. `cbom` is the default source
([ADR-0006](../adr/0006-cbom-first-ingestion.md)); the CBOM adapter is registered through the
`cbom` entry-point and parses input with `cyclonedx-python-lib`. Verified end to end: the
emitted document validates clean against `oscal-cli 3.2.0`.

## UC-4: Prowler → POA&M / Assessment Results *(Should)*

Add a second, unrelated source adapter that feeds the same IR and reuses the existing
emitters with no emitter changes (R-ARCH-01/03). Backlog.

## UC-5: OCSF → Assessment Results *(Could)*

OCSF as a normalized findings source into the IR, emitting Assessment Results. Roadmap.

## UC-6: Org PQC policy → Profile (CONSUME) *(Should)*

Today the compliance bar is selected per run through `--framework`: `scf-qts` (default, SCF
Quantum Security controls) or `nist` (SP 800-53r5). Each framework is a reviewable policy
pack; the pass/fail bar stays an organization-defined parameter, not a scanner-asserted
fact. UC-6 extends that mechanism: instead of picking a bundled pack, **consume** an OSCAL
Profile that carries the org's ODP/CNSA values (e.g. `set-parameters`) and parameterize the
verdict from that cited artifact. This is the integrity mechanism behind the honest-verdict
caveat. Depends on decision **T4**. Backlog.

## UC-7: Existing POA&M + new scan → merge *(Should)*

Reconcile POA&M item status across re-scans (e.g. open→closed) using deterministic uuid5 to
match items between runs. Today the tool emits a point-in-time snapshot (decision T2 option
A); merge is a later capability that uuid5 makes feasible. Depends on **T2**. Backlog.

## UC-8: Fleet / multi-subject *(Should)*

One OSCAL document spanning many endpoints: multiple `inventory-item`s, with each finding
referencing its own subject. The IR already carries `Finding.subject`; the emitter must be
generalized from single-subject to fleet (decision T3 option B). Depends on **T3**. Backlog.
