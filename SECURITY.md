# Security Policy

## Contents

1. [Supported Versions](#supported-versions)
2. [Reporting a Vulnerability](#reporting-a-vulnerability)
3. [Scope notes](#scope-notes)

## Supported Versions

This project is pre-1.0. Security fixes are applied to the latest `0.0.x` release
and to `main`.

| Version | Supported          |
| ------- | ------------------ |
| 0.0.x   | :white_check_mark: |
| < 0.0.1 | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them privately:

- Use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
  ("Report a vulnerability" on the Security tab), or
- Email **security@breachsafe.dev** with a description, reproduction steps, and
  any relevant logs (redact secrets).

You can expect an acknowledgement within **3 business days** and a substantive
response within **10 business days**. We will coordinate a disclosure timeline
with you and credit you in the release notes unless you prefer to remain
anonymous.

## Scope notes

This tool emits compliance artifacts (OSCAL). Please treat as security-relevant:

- any path that could write attacker-controlled data into an OSCAL document
  consumed as trusted evidence, and
- any adapter that mishandles a hostile source report (parsing, resource
  exhaustion).

Evidence handling is hash-only by design: raw secret-bearing tool output must
never be embedded in emitted documents. A regression here is a security issue.
