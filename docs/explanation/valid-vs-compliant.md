# Valid is not compliant

A document being valid OSCAL says nothing about whether the scanned system is compliant. Hold
that distinction while reading any `mint-oscal` output. This page explains why the two are
separate and where each one comes from.

## Contents

1. [Two different questions](#two-different-questions)
2. [What validation actually checks](#what-validation-actually-checks)
3. [Where the compliance verdict comes from](#where-the-compliance-verdict-comes-from)
4. [Why the crosswalk ships provisional](#why-the-crosswalk-ships-provisional)
5. [Consequences for a reader](#consequences-for-a-reader)

## Two different questions

- Is it valid OSCAL? Does the document conform to the OSCAL schema and constraints? This is a
  mechanical, tool-decidable question.
- Is the system compliant? Does the observed cryptographic posture satisfy an organization's
  control obligations? This is a policy judgment.

`mint-oscal` answers the first with confidence. It does not answer the second, because the
answer depends on an input the scanner does not hold: the organization's control-parameter
selections.

## What validation actually checks

Two layers exist, and neither settles the verdict:

- In-process (`--validate` on generate, and the `poam validate` verb): pure-Python Layer-2
  semantic checks covering uuid, reference, and namespace integrity, OSCAL structure and
  datatypes, and BreachSAFE domain vocabulary. No `oscal-cli` or Trestle is required. These
  checks are necessary but not sufficient for full NIST conformance.
- Authoritative (`oscal-cli validate <file>`): schema and constraint conformance against the
  NIST OSCAL release, run as an external subprocess. See
  [../how-to/validate-with-oscal-cli.md](../how-to/validate-with-oscal-cli.md).

Both confirm the document is well-formed OSCAL. Neither confirms that the finding-to-control
mapping is correct or that the system passes.

## Where the compliance verdict comes from

A compliance verdict depends on an organization-defined parameter (ODP), for example whether
the applicable control requires CNSA 2.0 post-quantum cryptography. That bar is set by an
organization's policy, not derived from a scan. `mint-oscal` therefore states any verdict as
an assertion tied to the org ODP. A finding is a deficiency only if the org's ODP requires
PQC; where the ODP does not require it, the same fact is informational.

The scanner cannot supply the ODP for a structural reason. It observes what a target
negotiates: the key-exchange algorithms offered, the certificate signature algorithm, the
readiness class those imply. It does not observe the organization's control-parameter
selection, which lives in policy documents and profiles, not on the wire. `X25519MLKEM768`
being negotiated is a fact about the endpoint. Whether that satisfies the control is a fact
about the organization's chosen parameter. The second fact is never present in the scan
input, so the tool cannot derive it and does not guess at it.

An ODP dependency would read like the following illustrative `poam-item` remark:

```text
remarks: >-
  Deficiency is conditional on the applicable control's ODP. If the control requires
  CNSA 2.0 key establishment, the observed classical KEX is a gap; if PQC is not
  required for this system, the same observation is informational.
```

The current emitter does not write this remark. It records the ODP conditioning through the
`interpretation-status: provisional` prop and the linked risk `statement` (see below);
attaching a caller-supplied remark is left to the program that owns the ODP. The snippet above
is illustrative of the dependency, not emitted verbatim.

This is why the tool consumes rather than invents the compliance bar. The ODP is meant to
arrive from a cited OSCAL Profile the organization supplies through a planned consume path,
which keeps the judgment an organization's assertion.

## Why the crosswalk ships provisional

The finding-to-control crosswalk, both the default `scf-qts` and the opt-in `nist` mapping, is
a draft pending conformance sign-off. Until a human review cites each control statement, every
finding carries an `interpretation-status: provisional` prop so no reader mistakes a draft
mapping for an authored compliance decision. The policy YAML packs carry the matching comment
`DRAFT - UNREVIEWED - needs conformance sign-off (R-CTRL-01)`.

## Consequences for a reader

- A clean `oscal-cli validate` means the document is well-formed OSCAL, and no more.
- A `poam-item` describing a deficiency is conditional on the org ODP. Read its `control-id`
  prop and linked risk `statement`, and treat the mapping as provisional while the
  `interpretation-status` prop says so.
- The crosswalk is a starting point for human review, not a finished compliance opinion.

For the framework mechanics behind this, the `scf-qts` default, the provisional marker, and
the fact-to-finding gate, see
[honest-state-and-frameworks.md](honest-state-and-frameworks.md).
