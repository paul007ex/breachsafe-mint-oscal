# The agnostic core

`mint-oscal` is built around one architectural choice: a **source- and target-agnostic
core**. This page explains what that means, why it was chosen, and what it costs. It is
rationale, not instructions; for the decision of record see
[ADR-0004](../adr/0004-agnostic-core.md).

## Contents

1. [The N×M problem](#the-nm-problem)
2. [The seam: a neutral IR](#the-seam-a-neutral-ir)
3. [What the boundary forbids](#what-the-boundary-forbids)
4. [Why this shape and not another](#why-this-shape-and-not-another)
5. [The cost](#the-cost)

## The N×M problem

`mint-oscal` bridges *many* security-scanner dialects to *many* OSCAL models. Wiring each
scanner directly to each OSCAL emitter is an **N×M** coupling: every new scanner would touch
every emitter, and every new OSCAL model would touch every scanner integration. With CBOM and
QuReddy as the first sources and POA&M, Assessment Results, and Component Definition as the
first targets, the matrix grows quadratically and every addition risks re-introducing subtle
OSCAL-shape bugs.

## The seam: a neutral IR

The core adopts **ports and adapters** around a neutral **intermediate representation (IR)**.
The IR — `Finding`, `Subject`, and the `IR` bundle — is the single shared contract:

- An **adapter** (`from_cbom`, `from_qureddy`, …) reads a source document and returns IR. It
  imports only the IR, never an emitter.
- An **emitter** (`poam`, and the planned `ar`/`component-definition`) consumes IR and produces
  an OSCAL document. It imports only the IR, never an adapter.
- A **registry** wires `source → adapter` and `model → emitter` by name, so the CLI composes
  them without either side knowing the other.

Adding a source is one adapter plus one registry row; adding an OSCAL model is one emitter.
That is **N + M** work instead of **N × M**. Scanner- or crypto-specific detail rides in the
IR as data (posture facts, evidence hashes), so a new fact type does not change the IR shape
or any emitter signature.

## What the boundary forbids

The seam is only worth having if it is enforced:

- **No cross-import.** An adapter importing an emitter, or vice versa, collapses the seam and
  is an architecture violation. The one shared import is the IR.
- **Adapters are pure.** They never log, print, or exit; malformed input raises a typed domain
  error the CLI decides how to surface. STDOUT stays pure data.
- **Determinism lives on the IR path.** Ids are `uuid5` over stable inputs and timestamps come
  from the source, so the same input yields byte-identical OSCAL. No wall-clock in the core.
- **Policy is data, not core.** Classification and control mapping are configuration; the core
  only moves facts from source to IR to OSCAL.

## Why this shape and not another

Two alternatives were rejected:

- **Direct source→OSCAL transformers.** Simplest for the first source, but recreates the N×M
  matrix and duplicates OSCAL-shape logic per scanner — the exact bug-multiplier the seam
  exists to prevent.
- **A typed OSCAL model as the IR.** Would couple the core to one OSCAL library's types and
  version ceiling. The neutral IR keeps the core independent of both scanner and OSCAL-library
  churn.

The same reasoning shapes the command line: `mint-oscal` is a composable, stateless
stdin→stdout filter, not a stateful repository tool. It produces OSCAL and hands off; it never
owns or edits an OSCAL working directory. See [../contributors/cli-design.md](../contributors/cli-design.md).

## The cost

The IR is a **lossy** intermediate by design: a fact no adapter records in `Finding`/posture
cannot be emitted. New fact types must be threaded through the IR rather than smuggled from
source straight to emitter. That friction is deliberate — it is what protects the seam.
