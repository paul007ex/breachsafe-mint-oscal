# ADR-0010: Trestle-aligned Profile compiler

## Status

Accepted (P0 control-plane design)

## Context

Mint-OSCAL must add BreachSAFE registry/objective resolution without creating a second
OSCAL authoring platform. Trestle already defines the workspace layout, model names,
Profile import/resolution semantics, and validation workflow. `oscal-cli` defines the
model-first validation/conversion/resolution grammar.

## Decision

The Mint-OSCAL Profile compiler is a thin Trestle-aligned extension:

```text
Mint registry/objective
  -> Trestle Profile model/API
  -> Trestle workspace artifact
  -> Trestle validation/resolution
  -> oscal-cli independent validation
```

Mint-OSCAL must reuse Trestle conventions wherever they exist:

- workspace directories: `catalogs/`, `profiles/`, `assessment-plans/`, and `dist/`;
- model naming: `profile`, `catalog`, `assessment-plan`, `assessment-results`, `poam`;
- model-aware `--name` and `--output` behavior;
- `--trestle-root` workspace selection;
- `json|yaml|yml` model extensions where Trestle supports them;
- `trestle://` workspace references;
- Profile import, include/exclude, parameter, merge, and resolution semantics; and
- Trestle validation before independent `oscal-cli` validation.

The Mint command tree remains model-first and compatible with `oscal-cli`:

```text
mint-oscal profile <command> [<options>]
  create       BreachSAFE registry-backed addition
  validate     same meaning as oscal-cli
  convert      same meaning as oscal-cli
  resolve      same meaning as oscal-cli
  explain      BreachSAFE provenance addition
```

`create` adds only the registry/objective decision. It must not implement its own OSCAL
schema, Profile resolver, Catalog model, or alternate workspace. A framework-specific
branch such as `mint-oscal nist profile` is prohibited. NIST is the first fixture; the
same pack contract must support other governed frameworks.

## Consequences

Positive:

- Existing Trestle users can understand the Mint-OSCAL workflow immediately.
- Profile semantics are delegated rather than duplicated.
- Trestle and `oscal-cli` remain independent validation gates.
- The registry is the only BreachSAFE-specific policy seam.

Costs:

- Mint must preserve Trestle workspace and option conventions even when a simpler custom
  CLI would be easier.
- Some Trestle limitations become explicit integration constraints.
- The Profile compiler needs workspace-aware tests, not only pure JSON tests.

## Verification

- Every Profile command has cascading help matching `oscal-cli` style.
- A real Trestle workspace can consume the generated Profile without manual rewrites.
- `trestle validate` and Profile resolution pass before `oscal-cli validate`.
- The same registry objective produces the same Profile and resolution receipt.
- No Profile/control/validator implementation is duplicated in Mint-OSCAL.
