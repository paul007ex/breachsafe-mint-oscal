# Your first POA&M

This tutorial walks you from a scanner report to a validated OSCAL Plan of Action &
Milestones (POA&M). You will use a sample CBOM bundled with the repository, so every step
runs offline without a live scan. You will finish with one OSCAL document and two ways of
checking it.

By the end you will have:

1. minted a POA&M from a CycloneDX CBOM;
2. read what the document does and does not claim;
3. checked it with the built-in validator;
4. seen where the authoritative NIST check fits.

## Contents

1. [Install mint-oscal](#1-install-mint-oscal)
2. [Check the command](#2-check-the-command)
3. [Mint a POA&M from a CBOM](#3-mint-a-poam-from-a-cbom)
4. [Read what you produced](#4-read-what-you-produced)
5. [Validate in-process](#5-validate-in-process)
6. [Validate authoritatively with oscal-cli](#6-validate-authoritatively-with-oscal-cli)
7. [Try the QuReddy source](#7-try-the-qureddy-source)
8. [What you verified](#8-what-you-verified)
9. [Next steps](#9-next-steps)

## 1. Install mint-oscal

`mint-oscal` requires Python 3.12+. It is not yet on PyPI, so install from a source checkout:

```bash
git clone https://github.com/breachsafe/breachsafe-mint-oscal
cd breachsafe-mint-oscal
pip install .
```

The commands below are run from that checkout, because they use the bundled sample under
`examples/`.

## 2. Check the command

This is offline and confirms the entry point is on your `PATH`:

```bash
mint-oscal --version
```

It prints a line of the form:

```text
BreachSAFE Mint-OSCAL <version> -- https://www.breachsafe.ai
```

## 3. Mint a POA&M from a CBOM

Turn the bundled CycloneDX CBOM into an OSCAL POA&M. With no `--framework`, findings map to
the default `scf-qts` controls, and output is JSON on STDOUT. Redirect it to a file:

```bash
mint-oscal poam generate --from cbom examples/example.cbom.json > first.poam.json
```

Exit code `0` means a document was minted. Nothing was sent to any network.

## 4. Read what you produced

Confirm the shape of the document:

```bash
python -m json.tool first.poam.json | head -n 30
```

You are looking at an OSCAL POA&M. Two things to notice:

- The top object is `plan-of-action-and-milestones`, with `metadata` declaring
  `oscal-version` `1.2.2`.
- Crypto facts ride as readable `prop` entries in the `https://breachsafe.ai/ns/oscal`
  namespace; evidence is carried as hashes, never as raw excerpts.

The document also carries an `interpretation-status: provisional` marker on findings. That is
intentional: the control mapping is a draft pending human sign-off, so a minted deficiency is
conditional on your organization's policy, not an authored compliance verdict. See
[valid-vs-compliant.md](../explanation/valid-vs-compliant.md).

## 5. Validate in-process

The built-in validator needs no external tool. It checks uuid/reference/namespace integrity,
OSCAL structure and datatypes, and BreachSAFE domain vocabulary:

```bash
mint-oscal poam validate first.poam.json
```

Exit `0` means no semantic problems were found. This check is **necessary but not sufficient**
for full NIST conformance. A warning in the log says as much.

## 6. Validate authoritatively with oscal-cli

This optional step needs Java 17+ and NIST
[`oscal-cli`](https://github.com/metaschema-framework/oscal-cli) on your `PATH`. Setup is in
[validate-with-oscal-cli.md](../how-to/validate-with-oscal-cli.md). For the authoritative
schema-and-constraint check, pass the file to `oscal-cli`:

```bash
oscal-cli validate first.poam.json
```

A valid document prints `The file '...' is valid.` and exits `0`. If `oscal-cli` is not
installed, skip this step for now; step 5 already told you the document is structurally sound.

## 7. Try the QuReddy source

The same command mints from a QuReddy scan report instead of a CBOM. The only change is
`--from`:

```bash
mint-oscal poam generate --from qureddy examples/example.scan.json > from-scan.poam.json
```

The output is another valid POA&M. That is the agnostic core at work: one emitter, two
sources, no source-specific code in the POA&M path. See
[agnostic-core.md](../explanation/agnostic-core.md).

## 8. What you verified

You used the installed command to:

1. mint a POA&M from a CBOM with the default `scf-qts` framework;
2. distinguish a minted document from an authored compliance verdict;
3. run the in-process validator to `0`;
4. locate the authoritative `oscal-cli` check;
5. mint from a second source with a one-flag change.

## 9. Next steps

- [Mint from a CBOM](../how-to/mint-from-a-cbom.md): the recipe, including piping from a scan
- [Choose a control framework](../how-to/choose-a-control-framework.md): `scf-qts` vs `nist`
- [Emit XML or YAML](../how-to/emit-xml-or-yaml.md)
- [CLI reference](../reference/cli.md): every flag, default, and value
