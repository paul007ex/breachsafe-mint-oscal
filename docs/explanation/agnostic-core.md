# The agnostic core

`mint-oscal` is built around one architectural choice: a source- and target-agnostic core.
This page explains what that means, why it was chosen, and what it costs. For the decision
of record see [ADR-0004](../adr/0004-agnostic-core.md).

## Contents

1. [The N×M problem](#the-nm-problem)
2. [The seam: a neutral IR](#the-seam-a-neutral-ir)
3. [What the boundary forbids](#what-the-boundary-forbids)
4. [Why this shape and not another](#why-this-shape-and-not-another)
5. [The cost](#the-cost)

## The N×M problem

`mint-oscal` bridges many security-scanner dialects to many OSCAL models. Wiring each scanner
directly to each OSCAL emitter is an `N x M` coupling: every new scanner would touch every
emitter, and every new OSCAL model would touch every scanner integration. CBOM and QuReddy are
the first sources; POA&M is the first shipped target and Assessment Results the next. As those
lists grow, the matrix grows with their product, and every cell is another place to
re-introduce a subtle OSCAL-shape bug.

## The seam: a neutral IR

The core adopts ports and adapters around a neutral intermediate representation (IR). The IR
is `Finding`, `Subject`, and the `IR` bundle, and it is the single shared contract:

- An adapter reads a source document and returns IR. It imports only the IR, never an emitter.
  The bundled adapters are `cbom` (`adapters/cbom.py::from_cbom`) and `qureddy`
  (`adapters/qureddy.py::from_scan_v1`); the registry keys them by their source name, `cbom`
  and `qureddy`, so a caller passes `--from cbom`, not a function name.
- An emitter consumes IR and produces an OSCAL document. It imports only the IR, never an
  adapter. `poam` (`emitters/poam.py`) is shipped; `ar` (`emitters/ar.py`) is a stub that
  raises `NotImplementedError` until its required `import-ap` reference lands.
- A registry (`_registry.py`) wires `source -> adapter` and `model -> emitter` by name, so the
  CLI composes them without either side knowing the other. Entry-point plugins win over the
  bundled built-ins, so a third party can register a source without editing the core.

Adding a source is one adapter plus one registry row; adding an OSCAL model is one emitter.
That is `N + M` work instead of `N x M`. Concretely, adding an OCSF source means writing one
`from_ocsf` adapter and one `_BUILTINS` row (`"ocsf": "mint_oscal.adapters.ocsf:from_ocsf"`).
It touches zero emitters: the existing POA&M and AR emitters read IR and never learn that OCSF
exists. Scanner- or crypto-specific detail rides in the IR as data (posture facts, evidence
hashes), so a new fact type does not change the IR shape or any emitter signature.

## What the boundary forbids

The seam is only worth having if it is enforced:

- No cross-import. An adapter importing an emitter, or the reverse, collapses the seam and is
  an architecture violation. The one shared import is the IR.
- Adapters are pure. They never log, print, or exit; malformed input raises a typed domain
  error that the CLI decides how to surface. STDOUT stays parseable data.
- Determinism lives on the IR path. Ids are `uuid5` over stable inputs, and the document
  timestamp is the latest finding `observed_at` (source-derived, via `poam.py::_stamp`), so
  the same input yields byte-identical OSCAL. The core reads no wall clock.
- Policy is data, not core. Classification and control mapping are versioned YAML packs; the
  core moves facts from source to IR to OSCAL and leaves the verdict to policy.

## Why this shape and not another

Two alternatives were rejected:

- Direct source-to-OSCAL transformers. Simplest for the first source, but this recreates the
  `N x M` matrix and duplicates OSCAL-shape logic in every scanner integration, which is the
  bug-multiplier the seam exists to prevent.
- A typed OSCAL model as the IR. This would couple the core to one OSCAL library's types and
  version ceiling. The neutral IR keeps the core independent of both scanner and OSCAL-library
  churn.

The same reasoning shapes the command line. `mint-oscal` is a composable stdin-to-stdout
filter that produces OSCAL and hands off; it does not own or edit an OSCAL working directory,
which keeps it composable in a pipe and leaves repository management to tools built for it.
The full command-line rationale is in [cli-design.md](../contributors/cli-design.md).

## The cost

The IR is a lossy intermediate by design: a fact that no adapter records in `Finding` or its
posture data cannot be emitted. A new fact type must be threaded through the IR rather than
passed from a source straight to an emitter. That friction is the price of the seam: it forces
every fact through one reviewed contract instead of letting scanner details leak into OSCAL.
