# Choose a control framework

Goal: decide whether to map findings to `scf-qts` (the default) or `nist`, and set it.

## Contents

1. [Set the framework](#set-the-framework)
2. [scf-qts (default)](#scf-qts-default)
3. [nist](#nist)
4. [Which to pick](#which-to-pick)
5. [Related](#related)

## Set the framework

Pass `--framework` to `poam generate`. Omit it and you get `scf-qts`.

```bash
# default: PQC-native SCF Quantum Security controls
mint-oscal poam generate --from cbom scan.cbom.json > poam.json

# opt in to NIST SP 800-53r5 instead
mint-oscal poam generate --from cbom scan.cbom.json --framework nist > poam.json
```

Control ids are attributed to the chosen framework's own namespace and linked to its catalog.

## scf-qts (default)

The Secure Controls Framework **Quantum Security (QTS)** controls. These are written for
post-quantum readiness, so crypto-posture findings map to them directly. Because `mint-oscal`'s
first-class subject is PQC posture, this is the closest honest fit and therefore the default.

## nist

NIST **SP 800-53r5**, using **SC-13** as primary with **SC-12** supporting for
key-establishment and cryptographic-protection findings. **SC-8 is deliberately excluded** as
overreach. Choose this when you must express results in the 800-53 vocabulary.

## Which to pick

- Reporting PQC readiness on its own terms → `scf-qts`.
- Feeding a program that already speaks 800-53 → `nist`.

Either way, the mapping ships **provisional**: every finding carries an
`interpretation-status: provisional` prop until the crosswalk earns cited human sign-off, and
any verdict remains conditional on your organization-defined parameter. See
[../explanation/honest-state-and-frameworks.md](../explanation/honest-state-and-frameworks.md)
and [../explanation/valid-vs-compliant.md](../explanation/valid-vs-compliant.md).

## Related

- [Mint from a CBOM](mint-from-a-cbom.md)
- [CLI reference](../reference/cli.md)
