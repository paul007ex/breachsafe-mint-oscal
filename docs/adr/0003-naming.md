# ADR-0003 — Package naming

- **Status:** Accepted
- **Deciders:** mint-oscal maintainers
- **Related:** NAME (workbook *Open-Decisions*); `R-PKG-01`

## Contents

1. [Context](#context)
2. [Decision](#decision)
3. [Consequences](#consequences)

## Context

The library needs a name that is brand-consistent, memorable, and collision-free across the
registries it will publish to. The BreachSAFE portfolio already ships **`mint-sts`**, and the
recurring product metaphor is that the tool **"mints"** a standards artifact from raw input.

## Decision

Adopt the following names:

| Facet | Value |
| --- | --- |
| Repository | `breachsafe-mint-oscal` |
| PyPI distribution | `mint-oscal` |
| Import package | `mint_oscal` |
| CLI entry point | `mint-oscal` |

Rationale: brand-consistent with the existing `mint-sts`; the verb reads naturally as "we
**mint** OSCAL" and pairs with the model-first CLI ("mint a `<shape>`", see
[ADR-0002](0002-cli-shape.md)). The names were **collision-checked clean** on PyPI, npm, and
GitHub.

## Consequences

**Positive**

- Consistent `mint-*` family branding; the CLI verb and the package name reinforce each other.
- No registry collisions to work around.

**Negative / cost**

- The repo name (`breachsafe-mint-oscal`) differs from the PyPI/import name (`mint-oscal` /
  `mint_oscal`) and from the CLI (`mint-oscal`) — contributors must know all three forms.
- Pre-decision material in the RTM still refers to `breachsafe-oscal` (e.g. `R-CLI-01`'s
  `breachsafe-oscal poam ...`); those references should be read as the decided
  `mint-oscal poam ...`.

**Status note:** Accepted (workbook records this decision as DECIDED).
