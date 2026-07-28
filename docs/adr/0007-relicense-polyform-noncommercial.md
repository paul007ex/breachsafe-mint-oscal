# ADR-0007 — Relicense to PolyForm Noncommercial 1.0.0 (source-available)

- **Status:** Accepted
- **Date:** 2026-07-28
- **Deciders:** BreachSAFE (owner)
- **Related:** #16; `LICENSE`; `NOTICE`

## Contents

- [Context](#context)
- [Decision](#decision)
- [Consequences](#consequences)
- [Alternatives considered](#alternatives-considered)
- [Implementation](#implementation)

## Context

`mint-oscal` was initially published under **Apache-2.0** (OSI open-source), and the
repository's license state was inconsistent: source files carried
`SPDX-License-Identifier: Apache-2.0` while GitHub detected no top-level license. The
owner's intent is that BreachSAFE code be **source-available for noncommercial use** —
anyone may read, run, evaluate, self-host, modify, and share it, but **may not use it in
or for a commercial product, or for commercial advantage, without a separate commercial
license.** Apache-2.0 permits unrestricted commercial use and therefore does not express
that intent.

## Decision

Relicense the project to the **PolyForm Noncommercial License 1.0.0** (SPDX
`PolyForm-Noncommercial-1.0.0`). PolyForm Noncommercial is a clear, standard-form,
source-available license whose permitted-purpose is *any noncommercial purpose*, with
explicit carve-outs for personal use and noncommercial organizations (charities,
educational/research institutions, government). Commercial use is reserved to a separate
license.

The project is now **source-available, not open source** — all public wording must say
"source-available," and OSI/"open source" claims or badges are not used.

## Consequences

**Positive**
- The license now matches the owner's intent: noncommercial use is free; commercial use
  requires a deal.
- License state is consistent: `LICENSE` (PolyForm text + `Required Notice`), `NOTICE`,
  every source `SPDX-License-Identifier`, and the `pyproject` `license` field all agree,
  and the wheel builds with the SPDX id validated by hatchling.

**Negative / cost**
- **One-way perception shift.** Moving from OSI open-source to source-available is hard to
  reverse in the public eye; hence this dated record.
- **No OpenSSF/"open source" positioning.** Any CI badges or copy implying open source must
  be dropped (relevant to the #17 CI hardening: OpenSSF Scorecard is out of scope).
- **Contribution boundary.** Relicensing binds only copyright the owner holds (or has
  contributor rights to). Outside contributions previously under Apache-2.0 would need
  sign-off; at relicense time the code is first-party.
- PolyForm Noncommercial is **not** OSI-approved; the PyPI classifier is
  `License :: Other/Proprietary License`.

## Alternatives considered

- **Keep Apache-2.0 (rejected).** Permits unrestricted commercial use — contrary to intent.
- **Elastic License 2.0 (rejected).** Permits commercial use except hosted-service resale;
  more permissive than intended.
- **Business Source License (rejected).** Adds a time-delayed open-source conversion that is
  not wanted.
- **PolyForm Noncommercial 1.0.0 (chosen).** Cleanly expresses "noncommercial free,
  commercial by separate license" with no conversion clause.

## Implementation

1. `LICENSE` — PolyForm Noncommercial 1.0.0 text, prefixed with a `Required Notice:`
   copyright line per the license's Notices clause.
2. `NOTICE` — source-available statement + commercial-license contact.
3. Every source `SPDX-License-Identifier: Apache-2.0` → `PolyForm-Noncommercial-1.0.0`.
4. `pyproject` `license = "PolyForm-Noncommercial-1.0.0"`; classifier →
   `License :: Other/Proprietary License`.
5. `CHANGELOG` entry; public docs say "source-available," never "open source."
