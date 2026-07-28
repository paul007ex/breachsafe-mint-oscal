# ADR-0008 — `breachsafe:v1` facts-only CBOM overlay (additive)

- **Status:** Accepted
- **Date:** 2026-07-28
- **Deciders:** BreachSAFE (owner); mint-oscal maintainers
- **Related:** #28; ADR-0004 (agnostic core); ADR-0006 (CBOM-first ingestion, whose
  "retain the native `qureddy` adapter" clause this ADR complements, not supersedes);
  ADR-0005 (render/validation boundary); `adapters/cbom.py`,
  `adapters/breachsafe/cbom.py`

## Contents

- [Context](#context)
- [Decision](#decision)
  - [1. `breachsafe:v1` is a facts-only, native-first extension](#1-breachsafev1-is-a-facts-only-native-first-extension)
  - [2. Standard vs `breachsafe/` split (ports & adapters)](#2-standard-vs-breachsafe-split-ports--adapters)
  - [3. Provenance and cross-check (ours authoritative)](#3-provenance-and-cross-check-ours-authoritative)
  - [4. Scope of trust: atomic facts vs the aggregate verdict](#4-scope-of-trust-atomic-facts-vs-the-aggregate-verdict)
  - [5. The native `qureddy` adapter is RETAINED (deletion deferred)](#5-the-native-qureddy-adapter-is-retained-deletion-deferred)
- [Consequences](#consequences)
- [Compatibility evidence](#compatibility-evidence)
- [Alternatives considered](#alternatives-considered)
- [Implementation](#implementation)
- [Falsifiers](#falsifiers)

## Context

`mint-oscal` ingests via two doors: the vendor-neutral CycloneDX **CBOM** adapter
(`--from cbom`, ADR-0006) and a native **QuReddy** scan-JSON adapter (`--from qureddy`,
`adapters/qureddy.py`, `from_scan_v1`). BreachSAFE producers, however, have more to say
than raw CycloneDX carries — a producer's own opinion of quantum readiness, and an
evidence hash — and today that annotation has nowhere to live on the CBOM path without
either polluting the vendor-neutral adapter or inventing a non-standard input format.

The open question (#28): where do BreachSAFE-specific producer facts live on the CBOM
path without (a) polluting the neutral adapter, (b) letting a producer overstate its
own aggregate posture, or (c) inventing a bespoke input schema?

This ADR is **additive**: it adds an overlay adapter and changes nothing about the
existing `cbom` or `qureddy` doors. **`cbom` remains the flagship, default ingestion
path** (vendor-neutral, derives everything from CycloneDX); the documented flagship
pipe is unchanged — `qureddy … --format cbom | mint-oscal poam generate --from cbom -`.
`breachsafe` is a strictly **opt-in progressive enhancement**: it does exactly what
`cbom` does and *additionally* records provenance when — and only when — a producer
declares `breachsafe:v1` facts. Issue #29's `--from cbom` acceptance is unaffected.

## Decision

### 1. `breachsafe:v1` is a facts-only, native-first extension

A producer carries what raw CycloneDX cannot express in the standard CycloneDX
**`properties[]`** slot — the sanctioned extension point — under a namespaced string
key `breachsafe:v1:<field>`. The extension is:

- **Facts-only.** It annotates; it never redefines the model. The crypto posture is
  **DERIVED** by `from_cbom` from `cryptoProperties` and is **never** read from the
  extension — no duplication, and no path by which a producer's self-report replaces a
  measured fact.
- **Native-first.** Anything CycloneDX can already express (an algorithm, a level, a
  cipher suite) MUST be expressed natively; the extension only carries what the standard
  has no native slot for (today: a declared `readiness` and an `evidence-sha256`).
- **String values in `properties[]`.** CycloneDX `properties` are name/value string
  pairs, so every `breachsafe:v1` document stays **schema-valid CycloneDX** with no
  custom schema and round-trips losslessly through `cyclonedx-python-lib`.

### 2. Standard vs `breachsafe/` split (ports & adapters)

The vendor-neutral adapter stays at `adapters/cbom.py` (pure CycloneDX → IR, **zero**
BreachSAFE/QuReddy input parsing; the `https://breachsafe.ai/ns/oscal` namespace on
emitted *output* props is unrelated output branding). The overlay lives in its own
subpackage, `adapters/breachsafe/cbom.py`. `from_breachsafe_cbom`:

- imports ONLY the public `from_cbom` and `mint_oscal.ir` — never a `cbom.py` private
  (`_readiness`, `_det`, `_config`, `_NAMESPACE`, `_SEVERITY`);
- **composes** `from_cbom` for findings/subject (which already validates the shape and
  raises `MalformedCbomError`) — it does **not** re-parse the BOM or re-implement the
  shape guard;
- reads `breachsafe:v1:*` by walking the **raw document dict** directly
  (`document["metadata"]["component"]["properties"]`, `document["components"][i]
  ["properties"]`);
- applies provenance via `dataclasses.replace(finding, posture={**finding.posture,
  "provenance": …})`;
- never logs, prints, exits, or raises for a conflict — the disagreement is surfaced as
  posture **data** only (adapter purity).

This respects ADR-0004 (ports & adapters): the core knows nothing of `breachsafe:v1`,
and the whole `breachsafe/` subtree is **promotable to a separate distribution** through
the existing `mint_oscal.adapters` entry-point group with no core change. Registration
is additive:

```toml
[project.entry-points."mint_oscal.adapters"]
qureddy    = "mint_oscal.adapters.qureddy:from_scan_v1"
cbom       = "mint_oscal.adapters.cbom:from_cbom"
breachsafe = "mint_oscal.adapters.breachsafe.cbom:from_breachsafe_cbom"
```

### 3. Provenance and cross-check (ours authoritative)

The overlay keeps the `breachsafe:v1:*` pairs from `metadata.component` and every
`components[].properties`, then **cross-checks** the producer's declared `readiness`
(valid only if ∈ {`quantum_vulnerable`, `transitional_hybrid`, `quantum_ready`,
`unknown`}; anything else is ignored as if absent) against the readiness we derived, and
records a `provenance` posture prop drawn from a **stable vocabulary**:

| `provenance` value | Meaning |
| --- | --- |
| `derived` | no producer declaration, or a malformed one |
| `producer-confirmed` | producer declares exactly our derived verdict |
| `conflict:producer=X,derived=Y` | producer declares a different valid verdict; ours (Y) is kept |

**Our derivation is always authoritative.** On conflict the emitted readiness stays the
one we derived; the disagreement is *recorded*, never *resolved* in the producer's
favour. An `evidence-sha256`, if present, is carried through as a posture prop. Both
surface in emitted OSCAL as `https://breachsafe.ai/ns/oscal`-namespaced observation
props.

### 4. Scope of trust: atomic facts vs the aggregate verdict

An honest boundary: `from_cbom` **already trusts** producer-declared *atomic* facts —
`cbom.py` reads `nistQuantumSecurityLevel` and `primitive` off `algorithmProperties` in
preference to the bundled registry (`cbom.py:168-176`). So native atomic facts are
**trusted-by-design** on the standard path; that is not new and this ADR does not change
it. What the overlay adjudicates is only the **aggregate readiness verdict** — the one
value a producer might use to overstate its whole posture. Atomic facts (trusted, from
`cryptoProperties`) and the aggregate verdict (cross-checked, ours authoritative) are
deliberately treated differently.

### 5. The native `qureddy` adapter is RETAINED (deletion deferred)

The overlay does **not** justify deleting `from_scan_v1` yet, because the CBOM path is
strictly less expressive than the native path in two ways that matter:

1. **Multiple findings vs one aggregate.** `from_cbom` collapses a subject to **one**
   aggregate crypto-posture finding with flat props; the native adapter emits **one
   finding per scan finding**.
2. **Structured evidence vs a flat hash.** The native adapter populates IR `Evidence`,
   which the POA&M emitter renders as OSCAL **`relevant-evidence[]`** (`poam.py:86-93`);
   the overlay can only carry a flat `evidence-sha256` prop.

Because of (1) and (2), "the native door loses nothing" is **false** today, so this ADR
**retains** `adapters/qureddy.py` and its `qureddy` entry point — complementing, not
superseding, ADR-0006's retain clause. **Deprecation plan:** deleting `from_scan_v1`
(and `examples/example.scan.json`, closing #21) is a **separate future PR, gated on
proven CBOM parity** for multi-finding output and structured `relevant-evidence[]`.
Until that parity is demonstrated, the native adapter stays.

## Consequences

**Positive**

- Producer facts have a home on the CBOM path with **no core pollution** and **no
  posture inflation** — the aggregate verdict cannot be overstated.
- `breachsafe:v1` documents are **schema-valid CycloneDX** (1.6 and 1.7) with no bespoke
  schema; they round-trip losslessly.
- Clean promotion boundary: `breachsafe/` can ship as its own distribution via the
  entry-point group with no core change.
- **Purely additive** — no behaviour change to `cbom` or `qureddy`.

**Negative / cost**

- **Two CBOM adapter names.** `cbom` and `breachsafe` differ only by the overlay; CLI
  help and docs must make the "standard vs overlay" distinction clear.
- **Extension governance.** `breachsafe:v1` is now a small public contract: adding a
  field is a versioned change (`v2`), not a silent edit.
- **Deferred cleanup.** Two ingestion doors remain until CBOM parity is proven; the
  duplication the single-door idea would remove is carried a while longer.

## Compatibility evidence

Gathered against `examples/example.cbom.json` with the overlay applied
(`/tmp/mintvenv`, `/tmp/trestle4`, oscal-cli container):

- **CycloneDX schema-valid, 1.6 AND 1.7.** `JsonStrictValidator(SchemaVersion.V1_6)`
  and `…V1_7` both return no errors for the `breachsafe:v1`-annotated document.
- **`cyclonedx-python-lib` round-trip preserves.** `Bom.from_json` → JSON outputter
  round-trip keeps the `breachsafe:v1:readiness` property, and re-ingesting the
  round-tripped document derives the same readiness and provenance.
- **Emitted OSCAL valid in BOTH validators across oscal-version 1.1.2 / 1.2.1 /
  1.2.2.** The minted POA&M validates under the NIST **oscal-cli** container
  (`poam validate`) and loads under **trestle**
  (`PlanOfActionAndMilestones.oscal_read`) at all three `oscal-version`s.
- **Provenance behaviour.** A matching `breachsafe:v1:readiness` → `producer-confirmed`;
  a conflicting one → `conflict:producer=…,derived=…` with the derived verdict kept; a
  malformed value → `derived` (ignored).

## Alternatives considered

- **A separate `breachsafe.cbom.v1` input format (rejected).** Re-introduces a bespoke
  schema and a second contract; loses free CycloneDX validation and round-trip.
- **Custom top-level extension object instead of `properties[]` (rejected).** Not a
  sanctioned CycloneDX slot; breaks strict schema validation and lib round-trip.
- **Let the extension carry crypto facts / override the aggregate readiness (rejected).**
  Duplicates the derivation and lets a producer inflate its own posture — precisely what
  "facts-only, ours authoritative" forbids.
- **Delete `qureddy` now and route everything through CBOM (rejected for now).** CBOM is
  strictly less expressive (single aggregate finding; no structured `relevant-evidence`);
  deletion is deferred to a parity-gated PR.
- **Facts-only `properties[]` overlay in a `breachsafe/` subpackage (chosen).**
  Vendor-neutral core, standard-valid input, no duplication, producer cannot overstate
  the aggregate posture, promotable to its own package, and additive.

## Implementation

1. `adapters/cbom.py` — unchanged translator; confirmed free of any BreachSAFE/QuReddy
   input parsing.
2. `adapters/breachsafe/cbom.py` — `from_breachsafe_cbom` composes `from_cbom`, walks the
   raw document's `properties[]` for `breachsafe:v1:*`, cross-checks readiness, and emits
   `provenance` (+ optional `evidence-sha256`) posture props via `dataclasses.replace`.
3. `pyproject.toml` + `adapters/__init__._BUILTINS` — add `breachsafe` **additively**
   (keep `qureddy` and `cbom`).
4. This ADR + row in [`docs/adr/README.md`](README.md).
5. `from_scan_v1` / `qureddy` / `example.scan.json` deletion: **deferred** to a future,
   parity-gated PR (closes #21 then, not here).

## Falsifiers

For the tester (#6) — this ADR is wrong if any hold:

- A `breachsafe:v1:*` value changes the derived crypto readiness (facts must stay derived
  from `cryptoProperties`).
- A conflicting `breachsafe:v1:readiness` flips the emitted readiness to the producer's
  value (ours must stay authoritative).
- A malformed `breachsafe:v1:readiness` (not in the allowed set) yields anything other
  than `provenance=derived`.
- `--from cbom` on a `breachsafe:v1`-annotated document reads the extension (the neutral
  door must ignore it).
- The overlay imports a `cbom.py` private, re-parses the BOM, or logs/prints/raises on a
  conflict.
- A `breachsafe:v1`-annotated document fails `JsonStrictValidator` at 1.6 or 1.7.
- The minted POA&M fails oscal-cli or trestle at oscal-version 1.1.2, 1.2.1, or 1.2.2.
