# mint-oscal — Documentation

`mint-oscal` (repo `breachsafe-mint-oscal`, PyPI `mint-oscal`, import `mint_oscal`)
converts security-tool findings into NIST OSCAL documents.

It is built on an **N sources → neutral IR → M OSCAL shapes** architecture:

- **Sources (adapters):** QuReddy scan JSON first; later Prowler, OCSF, CycloneDX CBOM.
- **Neutral IR:** frozen dataclasses `Finding` / `Subject` / `Evidence` / `Risk`,
  source- and target-agnostic.
- **Targets (emitters):** OSCAL POA&M (flagship, prototyped and validated),
  Assessment Results (SAR), Component Definition.

`mint-oscal` is a **composable stdin→stdout filter**, not a stateful repo tool like
IBM Trestle. A typical chain:

```
qureddy scan | mint-oscal poam --from qureddy | oscal-cli validate -
```

Output is **deterministic** (uuid5 over a fixed namespace) so generated OSCAL is
git-diffable.

> **OSCAL version note:** Docs declare `oscal-version = 1.1.2` for maximum validator
> interop; the internal target is `1.2.2`, recorded as a prop. Validated end-to-end with
> `oscal-cli 3.2.0`.

> **Honest-verdict caveat (applies throughout):** any finding→control→ODP judgment is an
> **organization-policy assertion** (an organization-defined parameter), **not** a
> scanner-derived truth. The control crosswalk requires human conformance review with
> catalog citations. A document being OSCAL-*valid* does **not** make it *compliant*.

## Documents

| Doc | Description |
| --- | --- |
| [requirements.md](requirements.md) | Requirements Traceability Matrix — 42 requirements across 11 categories. |
| [use-cases.md](use-cases.md) | 8 use cases; the sources × OSCAL-shapes matrix. |
| [oscal-shapes.md](oscal-shapes.md) | Per-model requirement sets (POA&M, SAR, Component, Profile, Catalog, SSP, Assessment Plan). |
| [cli-design.md](cli-design.md) | CLI design (R-CLI-D01..D12), prior-art comparison, synopsis, exit codes. |
| [adr/README.md](adr/README.md) | Architecture Decision Record index. |
| [adr/0001-primary-oscal-target.md](adr/0001-primary-oscal-target.md) | SAR canonical, POA&M derived (flagship). |
| [adr/0002-cli-shape.md](adr/0002-cli-shape.md) | Model-first subcommands + composable filter. |
| [adr/0003-naming.md](adr/0003-naming.md) | Package naming (Accepted). |

## Status at a glance

| Area | State | Notes |
| --- | --- | --- |
| POA&M emitter | **Built** | Prototype v2 validated clean against `oscal-cli 3.2.0`. |
| Neutral IR (`Finding/Subject/Evidence/Risk`) | **Built** | Frozen, source/target-agnostic. |
| QuReddy adapter | **Built** | Live scan → IR findings + subject. |
| Determinism (uuid5) | **Built** | Re-run yields identical uuids. |
| Structural validator | **Built** | No network/toolchain needed. |
| Assessment Results (SAR) emitter | **Designed** | Required fields **NEEDS CONFIRM** from metaschema. |
| Component Definition emitter | **Designed** | Required fields **NEEDS CONFIRM** from metaschema. |
| Prowler / OCSF / CBOM adapters | **Backlog** | Roadmap. |
| Packaging (`R-PKG-01`) | **OPEN** | pyproject / entry point / LICENSE not yet shipped. |
| Control crosswalk (`R-CTRL-01`) | **OPEN** | Draft only; needs cited human conformance review. |
| Primary target (ADR-0001) | **Proposed** | SAR canonical + POA&M derived. |
| CLI shape (ADR-0002) | **Proposed** | Model-first + composable filter. |
| Naming (ADR-0003) | **Accepted** | `breachsafe-mint-oscal` / `mint-oscal` / `mint_oscal`. |
