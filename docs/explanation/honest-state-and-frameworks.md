# Honest state and control frameworks

`mint-oscal` reports what a scanner observed and maps it to controls, but it is careful never
to overstate what it knows. This page explains the honest-state discipline: the framework
choice, the provisional marker, how unknown and not-applicable states are preserved, and the
gate that separates a *fact* from a *finding*.

## Contents

1. [Facts do not become findings by themselves](#facts-do-not-become-findings-by-themselves)
2. [Two frameworks, and why scf-qts is the default](#two-frameworks-and-why-scf-qts-is-the-default)
3. [The provisional marker](#the-provisional-marker)
4. [Unknown and not-applicable are first-class](#unknown-and-not-applicable-are-first-class)
5. [How to read a minted POA&M honestly](#how-to-read-a-minted-poam-honestly)

## Facts do not become findings by themselves

A scanner produces **facts**: this endpoint offered this key exchange, this certificate used
this signature algorithm. Turning a fact into a **finding** — an asserted deficiency against a
control — is a separate, governed step. `mint-oscal` carries the facts as readable namespaced
props and attaches a control mapping, but the *verdict* of whether the fact constitutes a
deficiency remains conditional on an organization-defined parameter (ODP). The tool never
promotes a fact to a compliance failure on its own authority. This is the same boundary
described in [valid-vs-compliant.md](valid-vs-compliant.md), viewed from the framework side.

## Two frameworks, and why scf-qts is the default

`--framework` selects the control namespace findings are attributed to:

- **`scf-qts` (default)** — the PQC-native Secure Controls Framework *Quantum Security (QTS)*
  controls. These controls are written for post-quantum readiness, so a crypto-posture fact
  maps to them directly, without straining a general-purpose control to cover PQC.
- **`nist`** — NIST SP 800-53r5, using **SC-13** as primary with **SC-12** supporting for
  key-establishment and cryptographic-protection findings. SC-8 is deliberately excluded as
  overreach.

`scf-qts` is the default because the tool's first-class subject is post-quantum crypto posture,
and the QTS controls are the closest honest fit. `nist` is offered for organizations that must
express results in the 800-53 vocabulary.

## The provisional marker

Both crosswalks ship as **drafts pending conformance sign-off**. Until a human review cites each
control statement, every finding carries an `interpretation-status: provisional` prop. The
marker is not decoration — it is the machine-readable admission that the mapping has not yet
been authored to conformance. When a crosswalk earns cited sign-off (tracked as requirement
`R-CTRL-01`), the marker is what changes.

## Unknown and not-applicable are first-class

Honest state means the absence of evidence is never silently rendered as a pass:

- **Unknown** — when evidence cannot establish a posture, that stays explicit. A missing result
  is not a passing result.
- **Not-applicable** — a fact only counts as a deficiency if the org ODP requires the property
  in question (for example, PQC per CNSA 2.0). Where the ODP does not require it, the same fact
  is informational, not a failure.

No PQC or CNSA catalog ships as fact; the compliance bar is org-supplied, so the tool cannot and
does not invent one.

## How to read a minted POA&M honestly

- Treat the control mapping as **provisional** until the marker says otherwise.
- Read `poam-item` remarks: they state the ODP dependency that conditions the verdict.
- Distinguish *scan completed* from *system compliant* — a clean run and a passing posture are
  different claims.

The exact `--framework` values and defaults are in [../reference/cli.md](../reference/cli.md);
the recipe for choosing between them is
[../how-to/choose-a-control-framework.md](../how-to/choose-a-control-framework.md).
