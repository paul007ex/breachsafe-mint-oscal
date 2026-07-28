# ADR-0004 — Agnostic core: ports & adapters (N sources → IR → M emitters)

- **Status:** Accepted
- **Date:** 2026-07-28
- **Deciders:** mint-oscal maintainers
- **Related:** ADR-0001 (OSCAL target), ADR-0006 (CBOM ingestion), ADR-0005 (render/validation boundary); closes the dangling ADR-0004 reference in #7

## Contents

- [Context](#context)
- [Decision](#decision)
- [The contract (IR)](#the-contract-ir)
- [Rules the boundary enforces](#rules-the-boundary-enforces)
- [Consequences](#consequences)
- [Alternatives considered](#alternatives-considered)

## Context

`mint-oscal` bridges *many* security-scanner dialects to *many* OSCAL models. Naively wiring
each scanner to each OSCAL emitter is an **N×M** coupling: every new scanner would touch every
emitter, and every new OSCAL model would touch every scanner integration. QuReddy and CBOM are
only the first two sources; POA&M, Assessment Results, and Component Definition are only the
first emitters. Without a seam, the matrix becomes unmaintainable and every addition risks the
subtle OSCAL-shape bugs we have already shipped (#2, #9).

## Decision

Adopt **ports & adapters** around a **neutral intermediate representation (IR)**. The IR is the
single contract; nothing that ingests knows anything about OSCAL, and nothing that emits knows
anything about a scanner.

```
  N SOURCES                     NEUTRAL IR                  M EMITTERS
 ┌──────────┐   from_*()      ┌──────────────┐   emit()    ┌───────────────┐
 │ cbom     │───adapter──────▶│ Finding      │────────────▶│ poam          │
 │ qureddy  │───adapter──────▶│ Subject      │────────────▶│ ar   (next)   │
 │ ocsf …   │───adapter──────▶│ IR bundle    │────────────▶│ component …   │
 └──────────┘                 └──────────────┘             └───────────────┘
        │                            ▲                            │
        └── may import ONLY ─────────┘ ──── may import ONLY ──────┘
                     mint_oscal.ir  (never each other)
```

- An **adapter** (`from_cbom`, `from_qureddy`, …) reads a source document and returns IR
  (`list[Finding]`, `Subject`). It imports **only** `mint_oscal.ir` — never an emitter.
- An **emitter** (`emit`/`to_poam`, …) consumes IR and produces an OSCAL document. It imports
  **only** `mint_oscal.ir` — never an adapter.
- A **registry** (`adapters/__init__.py`, `emitters/__init__.py`) wires `source → adapter` and
  `model → emitter` by name, so the CLI composes them without either side knowing the other.

Adding a **source** is one `from_*()` function plus one registry row. Adding an **OSCAL model**
is one emitter. Neither touches the other side of the matrix — N+M work, not N×M.

## The contract (IR)

`mint_oscal.ir` defines the whole vocabulary the two sides share:

- **`Finding`** — a single observation with `id`, `title`, `description`, `severity`, `status`,
  `subject`, `observed_at`, `control_ids`, `risk_statement`, `evidence`, and `posture`
  (`dict[str, str]` carrying producer facts such as cryptographic readiness, emitted as
  namespaced observation props).
- **`Subject`** — what the finding is about (`id`, `kind`, `description`).
- **`IR`** — the bundle (`findings`, `subject`, `source`) passed to an emitter.

The IR is deliberately **scanner- and OSCAL-agnostic**: it names facts, not schema. Crypto- or
scanner-specific detail travels in `posture`/`evidence` as data, so a new fact type does not
change the IR shape or any emitter signature.

## Rules the boundary enforces

- **No cross-import.** An adapter importing an emitter (or vice versa) is an architecture
  violation — it collapses the seam. The only shared import is `mint_oscal.ir`.
- **Adapters are pure.** They never log, print, or exit; a malformed input raises a domain error
  (e.g. `MalformedCbomError`) that the CLI decides how to surface. This keeps stdout pure data.
- **Determinism lives in the IR path.** Ids are derived (`uuid5`) from stable inputs and
  timestamps come from the source, so the same input yields byte-identical OSCAL (see ADR-0005
  and #4). No wall-clock in the core.
- **Policy is data, not core.** Classification and readiness are configuration (ADR-0006); the
  core only moves facts from source to IR to OSCAL.

## Consequences

**Positive**

- New scanners and new OSCAL models compose independently; the marginal cost of the *M-th*
  emitter or *N-th* source is a single unit of work.
- The core is trivially testable: adapters and emitters are pure functions over plain data.
- The seam localizes OSCAL-shape risk to the emitters, where ADR-0005's validation layers guard
  it.

**Negative / cost**

- The IR is a **lossy** intermediate: a fact no adapter puts into `Finding`/`posture` cannot be
  emitted. New fact types must be threaded through the IR (as `posture`/`evidence` data) rather
  than smuggled straight from source to emitter — by design, to protect the seam.

## Alternatives considered

- **Direct source→OSCAL transformers (rejected).** Simplest for the first source, but recreates
  the N×M matrix and duplicates OSCAL-shape logic per scanner — precisely the bug-multiplier
  ADR-0005 warns about.
- **A typed OSCAL model as the IR (rejected).** Would couple the core to one OSCAL library's
  types and version ceiling (see ADR-0005's rejection of a trestle dependency). The neutral IR
  keeps the core independent of both scanner and OSCAL-library churn.
