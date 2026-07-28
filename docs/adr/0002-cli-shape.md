# ADR-0002 — CLI shape

- **Status:** Proposed
- **Deciders:** mint-oscal maintainers
- **Related:** CLI-1 (workbook *Open-Decisions*); [cli-design.md](../cli-design.md)

## Context

`mint-oscal` needs a command surface. Prior art offers three distinct shapes:

- **IBM Compliance Trestle** — verb/task subcommands (`trestle author`, `trestle task ...`)
  for a **stateful, git-workflow platform** that owns an OSCAL working directory and edits
  it in place.
- **NIST oscal-cli** — **model-first** (`oscal-cli poam validate`): name the model, then the
  action.
- **GoComply oscalkit** — **flat verbs** (`oscalkit convert`, `... sign`): one-shot
  transforms.

`mint-oscal`'s job is narrow and stateless: turn a source finding stream into an OSCAL
document. It must **chain** with upstream scanners and downstream validators, and its output
must be deterministic enough to review in git.

Options considered (workbook CLI-1): model-first (`mint <shape>`) · verb (`convert --to`) ·
trestle-tasks.

## Decision

Adopt **model-first subcommands + a composable stdin→stdout filter**.

- Subcommands are the OSCAL shape: `mint-oscal poam|sar|component`, reading as the brand verb
  "mint a `<shape>`" and matching NIST oscal-cli's model-first ergonomics.
- The tool is a **pure Unix filter**: stdin (or a path arg) in, OSCAL to stdout by default,
  no side effects beyond the declared output.
- The source is chosen explicitly with `--from <adapter>`; no auto-detection.

Explicitly rejected: the **Trestle-style stateful task** model. `mint-oscal` never edits an
OSCAL working directory in place (`R-CLI-D12`). Trestle owns that lane; `mint` is a producing
filter.

**Chaining requirement (load-bearing):**

```
qureddy scan | mint-oscal poam --from qureddy | oscal-cli validate -
```

Deterministic uuid5 output (`R-CLI-D09`) makes these pipeline artifacts diffable and safe to
review in git.

## Consequences

**Positive**

- Composes with any upstream scanner and downstream OSCAL tool; CI-friendly and scriptable
  (exit codes 0/1/2, `R-CLI-D08`).
- Model-first naming is discoverable and brand-aligned.
- Pure-filter contract keeps the core side-effect-free (`R-PKG-04`, `R-CLI-D10`).

**Negative / cost**

- No stateful conveniences (in-place edit, working-dir management) — by design; users needing
  that reach for Trestle.
- Introspection (`sources`, `shapes`, `--version`) and full exit-code handling are still
  **Open** (`R-CLI-D07`, `R-CLI-D08`).

**Status note:** Proposed. Core filter behavior and `--from` are Built; format/output/validate
plumbing is Designed/Partial.
