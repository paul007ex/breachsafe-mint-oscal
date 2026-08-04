# OSCAL Shapes — one requirement set per model

Source: [`requirements.xlsx`](../requirements.xlsx) → *OSCAL-Shapes* sheet. See the
[docs index](../README.md).

Each OSCAL model `mint-oscal` touches has a defined **role**: `EMIT` (we produce it),
`CONSUME` (we read it as input), `LINK` (we only reference it), or `SKIP` (out of scope).

> **⚠ Read the metaschema before writing an emitter.** For SAR / Component Definition /
> Profile, the required roots/fields below are marked **NEEDS CONFIRM**. They **MUST** be
> read straight from the metaschemas in `reference/` — with the same rigor already applied
> to POA&M — before any emitter is written. Do not treat the sketches below as the field
> list; treat them as prompts for what to confirm.

## Contents

1. [Shapes](#shapes)
2. [Notes per shape](#notes-per-shape)
3. [Control crosswalk caveat](#control-crosswalk-caveat)

## Shapes

| Shape | mint role | Required roots / fields | Grounding | Priority | Verified |
| --- | --- | --- | --- | --- | --- |
| POA&M | EMIT | `uuid`; `metadata{title,last-modified,version,oscal-version}`; (`system-id` OR `import-ssp`); ≥1 `poam-item{title,description}` | `reference/OSCAL/.../oscal_poam_metaschema.xml` | Must | **YES — validated** |
| Assessment Results (SAR) | EMIT | `uuid`; `metadata`; `import-ap` (LIKELY required); ≥1 `result{title,description,start}` with observations/findings/risks | metaschema — CONFIRM | Must | **NEEDS CONFIRM** |
| Component Definition | EMIT | `uuid`; `metadata`; ≥1 `component{type,title,description}` and/or `capability` | metaschema — CONFIRM | Should | **NEEDS CONFIRM** |
| Profile | CONSUME | `imports` (href + include/exclude); `merge`; `modify`/`set-parameters` (ODP values) | metaschema — CONFIRM | Should | **NEEDS CONFIRM** |
| Catalog | CONSUME | `controls`, `params`, `groups` (control text + ODP ids) | reference SP 800-53 rev5 catalog | Should | **YES — read** |
| SSP | LINK | referenced only, via POA&M `import-ssp`; not emitted in v1 | – | Could | n/a |
| Assessment Plan | SKIP | forward-looking; not scan-derived | – | Won't | – |

## Notes per shape

### POA&M — EMIT (flagship, verified)

Required fields are **verified against the metaschema** and validated end-to-end with
`oscal-cli 3.2.0` (prototype v2). This is the only shape whose field list is proven; see
[requirements.md](requirements.md) OSC-02..05.

### Assessment Results (SAR) — EMIT (needs confirm)

Per [ADR-0001](../adr/0001-primary-oscal-target.md), SAR is the canonical faithful record of
what the scanner observed. The sketch above notably includes `import-ap`, which is
**likely** required — confirm against the SAR metaschema before building the emitter.

### Component Definition — EMIT (needs confirm)

For rendering QuReddy CBOM crypto inventory (UC-3). Required `component` vs `capability`
shape to be confirmed from the metaschema.

### Profile — CONSUME (needs confirm)

`mint-oscal` reads a Profile to obtain org ODP values (`set-parameters`) rather than
hardcoding the compliance bar (UC-6, decision T4). This is the mechanism that keeps the
verdict an **organization-policy assertion** rather than a scanner-asserted fact.

### Catalog — CONSUME (read)

SP 800-53 rev5 catalog supplies verbatim control text (SC-13 / SC-12 / SC-8) and the
organization-defined parameter (ODP) identifiers used by the crosswalk.

### SSP — LINK only

Referenced through POA&M `import-ssp` when the org has an SSP; not emitted in v1
(decision T5 supports both standalone `system-id` and optional `import-ssp`).

### Assessment Plan — SKIP

Forward-looking and not scan-derived; explicitly out of scope.

## Control crosswalk caveat

The finding→control→ODP crosswalk that feeds these shapes is a **DRAFT starting point,
not an authored compliance decision**. It requires human conformance review and citation
sign-off (`R-CTRL-01`, **OPEN**). SC-8 is intentionally excluded as overreach; SC-13 is
primary with SC-12 supporting. A verdict is a **deficiency only if the org ODP requires
PQC** (e.g. CNSA 2.0) — otherwise it is informational. No PQC/CNSA catalog is shipped as
fact; the ODP bar is org-supplied. OSCAL-*valid* ≠ *compliant*.
