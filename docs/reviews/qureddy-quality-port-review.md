# QuReddy quality practices: Mint-OSCAL review

## Contents

1. [Purpose](#purpose)
2. [Adopted practices](#adopted-practices)
3. [Boundaries](#boundaries)
4. [Acceptance gates](#acceptance-gates)

## Purpose

This review identifies quality practices worth porting from QuReddy into Mint-OSCAL. It is
planning and governance material; it does not turn Mint-OSCAL into a network scanner or claim
that QuReddy's runtime behavior belongs in the OSCAL emitter.

## Adopted practices

| Practice | Mint-OSCAL application | Proof |
| --- | --- | --- |
| Installed-artifact testing | Build the wheel, install it into a clean Python 3.14 environment, and invoke the console script. | The release gate records the installed path and version. |
| Independent standards validation | Validate emitted OSCAL with the pinned NIST `oscal-cli`, in addition to in-process checks. | Invalid OSCAL must fail the external validator. |
| Deterministic output | Generate the same fixture twice and compare final bytes. | Different hash seeds must not change output. |
| Black-box regressions | Exercise the real CLI for malformed input, stdout/stderr separation, and exit codes. | Every fixed defect has a CLI-level regression. |
| Layered quality gates | Run formatting, lint, typing, tests, package build, and standards validation in order. | A failed stage stops the gate and reports its command. |
| Provenance | Record source revision, package digest, Python version, Mint version, and validator version. | Release evidence is reproducible. |

## Boundaries

Mint-OSCAL should not copy QuReddy's TLS transport tests, endpoint scanning, OpenSSL replay, or
CycloneDX scanner implementation. QuReddy produces evidence; Mint-OSCAL consumes evidence and
emits OSCAL. The projects share quality discipline, not product responsibilities.

## Acceptance gates

Before release, the local gate must demonstrate:

1. The installed console script runs from a clean environment.
2. Internal structural validation and independent `oscal-cli` validation both pass for valid
   fixtures.
3. Malformed and unsupported input returns the documented nonzero exit code.
4. Repeated runs produce byte-identical output for deterministic fixtures.
5. Documentation commands and supported formats match the actual CLI.
