# State and control frameworks

`mint-oscal` reports what a scanner observed and maps it to controls without overstating what
it knows. This page covers the framework side of that discipline: the `scf-qts` default and
the `nist` alternative, the provisional marker, how unknown and not-applicable states are
preserved, and the gate between a fact and a finding.
[valid-vs-compliant.md](valid-vs-compliant.md) argues that valid OSCAL is not a compliance
verdict; this page adds the control-mapping mechanics that decide which control a fact lands
on and how the tool marks a mapping it has not yet reviewed.

## Contents

1. [Facts do not become findings by themselves](#facts-do-not-become-findings-by-themselves)
2. [Two frameworks, and why scf-qts is the default](#two-frameworks-and-why-scf-qts-is-the-default)
3. [The provisional marker](#the-provisional-marker)
4. [Unknown and not-applicable are first-class](#unknown-and-not-applicable-are-first-class)
5. [How to read a minted POA&M](#how-to-read-a-minted-poam)

## Facts do not become findings by themselves

A scanner produces facts: this endpoint offered this key exchange, this certificate used this
signature algorithm. Turning a fact into a finding, an asserted deficiency against a control,
is a separate governed step. `mint-oscal` carries the facts as readable namespaced props and
attaches a control mapping, but whether the fact constitutes a deficiency stays conditional on
an organization-defined parameter (ODP). The tool never promotes a fact to a compliance
failure on its own authority. This is the same boundary described in
[valid-vs-compliant.md](valid-vs-compliant.md), viewed from the framework side.

## Two frameworks, and why scf-qts is the default

`--framework` selects the control namespace findings are attributed to:

- `scf-qts` (default): the PQC-native Secure Controls Framework Quantum Security (QTS)
  controls. These controls are written for post-quantum readiness, so a crypto-posture fact
  maps to a specific one without stretching a general-purpose control to cover PQC.
- `nist`: NIST SP 800-53r5, using SC-13 (Cryptographic Protection) as primary and SC-12
  (Cryptographic Key Establishment and Management) as supporting for key-establishment
  findings. SC-8 (Transmission Confidentiality and Integrity) is excluded because the finding
  is about a primitive's quantum readiness, not transmission integrity.

`scf-qts` is the default because the tool's first-class subject is post-quantum crypto posture,
and the QTS controls are the closest fit. `nist` is offered for organizations that must express
results in the 800-53 vocabulary.

The difference is concrete. A CBOM readiness verdict of `quantum_vulnerable` (a CRQC-exposed
key-establishment primitive) maps to `qts-04.3`, Post-Quantum Cryptography Exposure, under
`scf-qts`. Under `nist` the same verdict maps to SC-13, Cryptographic Protection. Both
crosswalks are in `policy/scf_qts/control-crosswalk.yaml` and `policy/default/control-crosswalk.yaml`.
The QTS control names the exact posture problem; SC-13 is the general cryptographic-protection
control that also has to absorb classically-weak, hybrid, and ready verdicts. So under `nist`,
several distinct readiness states collapse onto one SC-13 line, and a reader cannot tell them
apart from the control id. Under `scf-qts` each state has its own QTS control. Both mappings
carry the same evidence; they differ in how much the control id alone discriminates.

## The provisional marker

Both crosswalks ship as drafts pending conformance sign-off. Until a human review cites each
control statement, every finding carries an `interpretation-status: provisional` prop under
the `https://breachsafe.ai/ns/oscal` namespace. The prop is machine-readable and records that
the mapping has not yet been authored to conformance; the policy YAML packs carry the matching
comment `DRAFT - UNREVIEWED - needs conformance sign-off (R-CTRL-01)`. When a crosswalk earns
cited sign-off, tracked as requirement `R-CTRL-01`, the prop is what a consumer can filter on
to tell a reviewed mapping from a draft one. The emitter sets it in `emitters/poam.py`, and
`validate.py` treats it as a known BreachSAFE prop.

## Unknown and not-applicable are first-class

The absence of evidence is never rendered as a pass:

- Unknown: when evidence cannot establish a posture, that state stays explicit and maps to
  `qts-04` (PQC Discovery and Visibility) under `scf-qts`. A missing result is recorded as
  undetermined, not as a passing result.
- Not-applicable: a fact counts as a deficiency only if the org ODP requires the property in
  question, for example PQC per CNSA 2.0. Where the ODP does not require it, the crosswalk maps
  the verdict to no control at all (`not_applicable: []`), so it is never minted as a spurious
  SC-13 or QTS finding.

No PQC or CNSA catalog ships as fact. The compliance bar is org-supplied, so the tool does not
invent one.

## How to read a minted POA&M

- Treat the control mapping as provisional while each `poam-item` carries the
  `interpretation-status: provisional` prop.
- Read the finding's `control-id` prop and the linked risk `statement` to see which control
  the verdict implicates and on what posture. The current emitter records the ODP conditioning
  through these props and the risk statement; it does not write `poam-item` remarks.
- Distinguish scan completed from system compliant. A clean run reports posture; it does not
  assert that the system passes its control obligations.

The exact `--framework` values and defaults are in [../reference/cli.md](../reference/cli.md);
the recipe for choosing between them is
[../how-to/choose-a-control-framework.md](../how-to/choose-a-control-framework.md).
