# ADR-0001 — Primary OSCAL target for scan findings

- **Status:** Proposed
- **Deciders:** mint-oscal maintainers
- **Related:** T1 (workbook *Open-Decisions*); UC-1, UC-2; [oscal-shapes.md](../oscal-shapes.md)

## Context

A scanner (QuReddy, later Prowler/OCSF) **observes** the state of a system. In OSCAL terms,
an observation maps naturally onto **Assessment Results (SAR)**: `result` records containing
`observations`, `findings`, and `risks` — a faithful account of *what was observed*.

A **POA&M**, by contrast, is a downstream **management plan**: it carries owners, remediation
milestones, deadlines, and accepted-risk decisions. A scanner cannot assert those things —
inventing them would violate `R-NG-02` (no fabricated milestones/dates) and undercut the
honest-verdict stance (the compliance judgment is an org ODP assertion, not scanner truth).

The NIST assessment flow is **Assessment Plan → Assessment Results (SAR) → POA&M**. SAR is
the canonical, scanner-authorable artifact; POA&M is derived from it by extracting the open
risks that need management action.

Options considered (workbook T1):

- **A)** POA&M only.
- **B)** SAR canonical + POA&M derived.
- **C)** both, independent.

Because all emitters read the same neutral IR (`Finding/Subject/Evidence`), emitting
both shapes from one scan is cheap — the marginal cost of SAR is a second emitter over data
we already hold.

## Decision

Adopt **Option B**: **Assessment Results (SAR) is the canonical, faithful artifact** — the
honest "what we observed." **POA&M is the derived open-risk extract** taken from the SAR, and
**remains the flagship deliverable** (it is the shape customers ask for and the one already
prototyped and validated).

The shared IR keeps SAR and POA&M in sync rather than independently authored (rejecting
Option C's drift risk), and avoids Option A's temptation to fabricate management data the
scanner cannot assert.

## Consequences

**Positive**

- POA&M items trace back to SAR observations/findings/risks — provenance is explicit and
  cross-references resolve (`R-OSC-05`).
- The scanner only asserts what it can observe; management data (owners, deadlines) stays out
  unless supplied, honoring `R-NG-02`.
- Adding SAR is a single new emitter over the existing IR (`R-ARCH-03`).

**Negative / cost**

- Requires building and validating the SAR emitter. Its required fields are **NEEDS CONFIRM**
  — in particular `import-ap` is *likely* required — and MUST be read from the SAR metaschema
  in `reference/` before coding (see [oscal-shapes.md](../oscal-shapes.md)).
- POA&M-as-derived means the derivation rule (which findings/risks become poam-items) must be
  defined and kept honest against the ODP-conditioned verdict (`R-CTRL-03`).

**Status note:** Proposed. POA&M is Built/validated; SAR is Designed pending metaschema
confirmation.
