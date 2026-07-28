# ADR-0008 — Source × extension model (`breachsafe:v1` enricher)

- **Status:** Proposed
- **Deciders:** mint-oscal maintainers
- **Related:** ADR-0004 (agnostic core); ADR-0006 (CBOM-first ingestion); supersedes the
  approach in closed PR #35 (breachsafe wired as a `--from` adapter); issue #28

## Context

`mint-oscal` ingests a source document through a `--from` *adapter* (ADR-0004/0006) into a
neutral IR, then emits OSCAL. The BreachSAFE product wants to add value on top of a generic
CycloneDX-CBOM: cross-check the readiness verdict mint *derives* from the inventory against
the readiness a producer *declares*, and record where the emitted verdict came from.

The first attempt (closed PR #35) wired `breachsafe` as its own `--from` **adapter**. That
conflated two orthogonal axes:

- **Source** — *what document am I reading?* (generic CBOM, QuReddy scan JSON, …)
- **Enrichment** — *what extra, opt-in refinement do I run on the derived IR?*

Modeling BreachSAFE as a source meant a BreachSAFE-flavored CBOM could not also be read as a
plain, vendor-neutral CBOM, and every enrichment would need a parallel source. It also pushed
mint toward vendor lock-in in the one path (`--from cbom`) that is meant to stay neutral.

## Decision

**Source and extension are orthogonal.** `--from` selects a vendor-neutral adapter;
`--extension` (repeatable) selects opt-in enrichers that run on the IR *after* the adapter and
*before* the emitter. They compose independently:

```
mint-oscal poam generate --from cbom scan.json                          # neutral flagship
mint-oscal poam generate --from cbom scan.json --extension breachsafe   # + BreachSAFE cross-check
```

- `--from cbom` is the **neutral flagship**: any CycloneDX-CBOM producer flows through it and
  gets a POA&M with **no** `provenance` prop. It never reads a vendor namespace.
- `--extension breachsafe` is an **opt-in enricher** discovered through the
  `mint_oscal.extensions` entry-point group (mirroring `mint_oscal.adapters`, ADR-0004), so a
  third party ships an enricher as its own distribution without editing the core. An enricher is
  a pure `enrich(findings, subject, *, document) -> (findings, subject)`.

### `breachsafe:v1` — a facts-only extension

`breachsafe:v1` is **facts-only**: a producer declares small, **native-first**, **string-valued**
facts as CycloneDX `properties[]` (`name`/`value`) on `metadata.component` or on any component —
`breachsafe:v1:readiness`, `breachsafe:v1:evidence-sha256`. No bespoke object model, no schema
fork; just namespaced properties that ride inside a standard CBOM. This keeps the carrying
document a valid CycloneDX BOM (see *Compatibility evidence*).

### Provenance & the honest trust scope

The enricher reconciles only the **aggregate readiness verdict**, and mint's own **derived**
verdict is always authoritative:

| Situation | `posture["provenance"]` | Emitted readiness |
| --- | --- | --- |
| No usable producer claim (absent or malformed value) | `derived` | mint's derived verdict |
| Producer's declared readiness matches derived | `producer-confirmed` | mint's derived verdict |
| Producer's declared readiness differs | `conflict:producer=X,derived=Y` | **Y (derived) kept** |

A declared `readiness` outside `{quantum_vulnerable, transitional_hybrid, quantum_ready,
unknown}` is ignored (treated as absent), never an error — the enricher is pure and cannot fail
the pipeline over a stray value. `breachsafe:v1:evidence-sha256` is carried onto the finding
posture when present.

**Trust is scoped honestly.** Native *atomic* facts a CBOM already carries (e.g.
`nistQuantumSecurityLevel` on an algorithm) are **trusted-by-design**: `adapters/cbom.py`
consumes them directly as producer declarations. This enricher does **not** re-adjudicate those
atoms — it would be dishonest to claim we "verified" a producer's per-algorithm level. Only the
**aggregate** verdict — the one mint itself re-derived from the whole inventory — is compared,
and on conflict mint keeps its own. The producer claim is *recorded*, not *obeyed*.

### Additive, not a deletion

This is **additive**. The `qureddy` native adapter and the generic `cbom` adapter are retained
unchanged; `breachsafe` is not registered as a `--from` source. Removing the (now superseded)
PR-#35 adapter approach is already done in effect (never merged); any further consolidation of
`qureddy` into `cbom + extension` is **deferred and gated on parity** — QuReddy carries native
rule semantics not yet in the generic CBOM contract (ADR-0006), so it stays until proven equal.

## Compatibility evidence

Verified on the `feat/extension-model` worktree:

- **CycloneDX validity** — a CBOM carrying `breachsafe:v1:*` properties is strict-valid under
  **both** CycloneDX **1.6** and **1.7** (`JsonStrictValidator(SchemaVersion.V1_6/V1_7)`). The
  properties are plain namespaced `name`/`value` pairs, valid in every CycloneDX version.
- **Round-trip** — `cyclonedx-python-lib` (`Bom.from_json`) round-trips the `breachsafe:v1`
  properties without loss.
- **OSCAL validity** — the emitted POA&M (with the `provenance` prop) is valid in **both**
  NIST `oscal-cli` (`ghcr.io/metaschema-framework/oscal-cli` `poam validate`) **and** IBM
  `compliance-trestle` (`PlanOfActionAndMilestones.oscal_read`), at `oscal-version`
  **1.1.2**, **1.2.1**, and **1.2.2**.
- **Flagship unaffected** — `--from cbom` with no `--extension` emits **no** `provenance` prop;
  the stdin pipe (`cat … | … --from cbom -`) is unchanged.

## Consequences

**Positive**

- The flagship `--from cbom` stays genuinely vendor-neutral; BreachSAFE value is a clean opt-in.
- New enrichers (other vendors, other cross-checks) are one entry-point away, no core edit and no
  parallel source — the N+M property of ADR-0004 extended to a third axis.
- Provenance is explicit and honest: consumers can see whether a verdict was derived, confirmed,
  or contested, and the derived verdict is never silently overridden by a producer claim.

**Negative / cost**

- A second discovery axis (`mint_oscal.extensions`) is new surface to version and document.
- The trust scoping is a *convention* the enricher must uphold (adjudicate only the aggregate);
  a future enricher author could violate it, so the boundary is documented here, not enforced by
  a type.
- QuReddy/CBOM consolidation is left open (deferred, parity-gated), so two adapters coexist for now.

**Status note:** Proposed. The `breachsafe` enricher and the `mint_oscal.extensions` registry are
Implemented and validated; consolidation of native `qureddy` into `cbom + extension` is the open
follow-on, gated on rule-semantics parity.
