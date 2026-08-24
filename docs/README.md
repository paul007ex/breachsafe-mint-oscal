# mint-oscal documentation

`mint-oscal` (repo `breachsafe-mint-oscal`, import `mint_oscal`) converts security-tool
findings into NIST OSCAL documents. This directory follows
**[Diátaxis](https://diataxis.fr)**: every page belongs to one of four quadrants and has one
job.

> **Status: pre-alpha.** The POA&M path is prototyped and validated against NIST `oscal-cli`.
> The `ar` emitter is a stub. Not yet published to PyPI.

> **Validation caveat (applies throughout).** A document being *valid OSCAL* does **not**
> make it *compliant*. Any finding→control→ODP judgment is an organization-policy assertion,
> not a scanner-derived truth. See
> [explanation/valid-vs-compliant.md](explanation/valid-vs-compliant.md).

## Contents

1. [The four quadrants](#the-four-quadrants)
2. [Tutorials](#tutorials)
3. [How-to guides](#how-to-guides)
4. [Reference](#reference)
5. [Explanation](#explanation)
6. [Decision records](#decision-records)
7. [Contributor documentation](#contributor-documentation)

## The four quadrants

|  | Theoretical (concept) | Practical (action) |
|---|---|---|
| **Studying** (learning) | [Explanation](explanation/) | [Tutorials](tutorials/) |
| **Working** (doing) | (none) | [How-to guides](how-to/) and [Reference](reference/) |

- **Tutorials**: learning-oriented. One walkthrough for someone new, from install to a validated document.
- **How-to guides**: task-oriented recipes for someone who knows the basics.
- **Reference**: information-oriented. Complete, dry, accurate.
- **Explanation**: understanding-oriented. Rationale and context.

## Tutorials

Learning-oriented walkthroughs.

- [Your first POA&M](tutorials/your-first-poam.md): CBOM to POA&M to validate, end to end.

## How-to guides

Task-oriented recipes.

- [Mint a POA&M from a CBOM](how-to/mint-from-a-cbom.md)
- [Choose a control framework](how-to/choose-a-control-framework.md): `scf-qts` vs `nist`
- [Validate with oscal-cli](how-to/validate-with-oscal-cli.md)
- [OSCAL conformance contract](conformance.md): Profile/POA&M validation sequence and gates
- [Emit XML or YAML](how-to/emit-xml-or-yaml.md): convert minted JSON to XML or YAML with `oscal-cli`

## Reference

Look-it-up information: comprehensive, accurate, dry.

- [CLI reference](reference/cli.md): every command, flag, default, and value
- [Exit codes](reference/exit-codes.md): `generate` and `validate` code sets
- [OSCAL shapes](reference/oscal-shapes.md): per-model required fields (POA&M shipped; others planned)
- [Registry reference](reference/registry.md): governed Catalog/objective source of truth
- [Profile compiler reference](reference/profile-compiler.md): Registry consumer and Trestle boundary
- [Requirements (RTM)](reference/requirements.md): the traceability matrix
- [Use cases](reference/use-cases.md): the sources × OSCAL-shapes matrix and its status
- [Registry and Profile compiler plan](roadmap/registry-and-profile-plan.md): detailed P0-to-P2 execution contract

## Explanation

Rationale and context. No commands.

- [The agnostic core](explanation/agnostic-core.md): N sources → neutral IR → M shapes
- [Valid is not compliant](explanation/valid-vs-compliant.md): what validation does and does not mean
- [State and control frameworks](explanation/honest-state-and-frameworks.md): the `scf-qts` default, the provisional marker, the fact→finding gate
- [Architecture](explanation/architecture.md): components, data flow, trust boundaries

## Decision records

- [Architecture Decision Records](adr/README.md): the ADR index.

## Contributor documentation

Rules and conventions for working *on* `mint-oscal`, not *with* it.

- [CONTRIBUTING.md](../CONTRIBUTING.md): setup, ground rules, PR checklist.
- [contributors/cli-design.md](contributors/cli-design.md): the CLI design record (R-CLI-D01..D12).
