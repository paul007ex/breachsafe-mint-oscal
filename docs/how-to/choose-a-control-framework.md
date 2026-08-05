# Choose a control framework

Goal: decide whether to map findings to `scf-qts` (the default) or `nist`, set it, and see
what changes in the output.

## Contents

1. [Set the framework](#set-the-framework)
2. [What changes in the output](#what-changes-in-the-output)
3. [Which to pick](#which-to-pick)
4. [Related](#related)

## Set the framework

Pass `--framework` to `poam generate`. Omit it and you get `scf-qts`.

```bash
# default: SCF Quantum Security (QTS) controls
mint-oscal poam generate --from cbom examples/example.cbom.json > poam.json

# opt in to NIST SP 800-53r5 instead
mint-oscal poam generate --from cbom examples/example.cbom.json --framework nist > poam-nist.json
```

`scf-qts` maps crypto-posture findings to SCF Quantum Security (QTS) controls. `nist` maps them
to NIST SP 800-53r5, using SC-13 as primary and SC-12 as supporting for cryptographic-protection
findings; SC-8 is excluded. Both mappings ship provisional: every finding carries an
`interpretation-status: provisional` prop, and any verdict stays conditional on your
organization-defined parameter. The reasoning is in
[../explanation/honest-state-and-frameworks.md](../explanation/honest-state-and-frameworks.md)
and [../explanation/valid-vs-compliant.md](../explanation/valid-vs-compliant.md).

## What changes in the output

Switching the framework changes each finding's `control-id` prop, that prop's authority
namespace, and the catalog `href` on its reference link. The values below are for the
`transitional_hybrid` finding in `examples/example.cbom.json`; the specific control-id depends
on the finding.

| Field | `scf-qts` (default) | `nist` |
| --- | --- | --- |
| `control-id` value | `qts-06.9` | `SC-13` |
| `control-id` `ns` | `https://securecontrolsframework.com/ns/oscal` | `https://csrc.nist.gov/ns/oscal/800-53` |
| catalog link `href` | `scf-qts-2026.2-catalog.json#qts-06.9` | `NIST_SP-800-53_rev5_catalog.json#SC-13` |

Reproduce the difference by minting both and diffing:

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json > poam-scf.json
mint-oscal poam generate --from cbom examples/example.cbom.json --framework nist > poam-nist.json
diff poam-scf.json poam-nist.json
```

## Which to pick

- Reporting PQC readiness on its own terms: `scf-qts`.
- Feeding a program that already speaks 800-53: `nist`.

## Related

- [Mint from a CBOM](mint-from-a-cbom.md)
- [Validate with oscal-cli](validate-with-oscal-cli.md)
- [CLI reference](../reference/cli.md)
