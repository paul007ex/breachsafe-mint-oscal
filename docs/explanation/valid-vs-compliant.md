# Valid is not compliant

The single most important idea to hold while reading any `mint-oscal` output: a document
being **valid OSCAL** says nothing about whether the scanned system is **compliant**. This
page explains why the two are separate, and where each one comes from.

## Contents

1. [Two different questions](#two-different-questions)
2. [What validation actually checks](#what-validation-actually-checks)
3. [Where the compliance verdict comes from](#where-the-compliance-verdict-comes-from)
4. [Why the crosswalk ships provisional](#why-the-crosswalk-ships-provisional)
5. [Consequences for a reader](#consequences-for-a-reader)

## Two different questions

- **Is it valid OSCAL?** — Does the document conform to the OSCAL schema and constraints?
  This is a mechanical, tool-decidable question.
- **Is the system compliant?** — Does the observed cryptographic posture satisfy an
  organization's control obligations? This is a policy judgment.

`mint-oscal` can answer the first with confidence. It deliberately refuses to answer the
second, because the answer depends on inputs the scanner does not have.

## What validation actually checks

Two layers, neither of which blesses the verdict:

- **In-process (`--validate`, and `poam validate`)** — pure-Python Layer-2 semantic checks:
  uuid/reference/namespace integrity, OSCAL structure and datatypes, and BreachSAFE domain
  vocabulary. No `oscal-cli` or Trestle needed. Necessary but **not** sufficient for full
  NIST conformance.
- **Authoritative (`oscal-cli`)** — schema and constraint conformance against the NIST OSCAL
  release. See [../how-to/validate-with-oscal-cli.md](../how-to/validate-with-oscal-cli.md).

Both confirm the document is well-formed OSCAL. Neither confirms that the finding→control
mapping is correct or that the system passes.

## Where the compliance verdict comes from

A compliance verdict depends on an **organization-defined parameter (ODP)** — for example,
whether the applicable control requires CNSA 2.0 post-quantum cryptography. That bar is set
by an organization's policy, not derived from a scan. `mint-oscal` therefore states any
verdict as an **assertion tied to the org ODP**, never as scanner-derived truth. A finding
is a deficiency only if the org's ODP requires PQC; otherwise the same fact is merely
informational.

This is why the tool consumes, rather than invents, the compliance bar: the ODP is meant to
arrive from a cited OSCAL Profile the organization supplies (a planned CONSUME path), keeping
the judgment an organization's assertion.

## Why the crosswalk ships provisional

The finding→control crosswalk (both the default `scf-qts` and the opt-in `nist` mapping) is
a draft pending conformance sign-off. Until a human review cites each control statement, every
finding carries an `interpretation-status: provisional` prop so no reader mistakes a draft
mapping for an authored compliance decision.

## Consequences for a reader

- A clean `oscal-cli validate` means the document is well-formed — nothing more.
- A `poam-item` describing a deficiency is conditional on the org ODP; read the item remarks.
- The crosswalk is a starting point for human review, not a finished compliance opinion.

For the framework mechanics behind this — the `scf-qts` default, the provisional marker, and
the fact→finding gate — see
[honest-state-and-frameworks.md](honest-state-and-frameworks.md).
