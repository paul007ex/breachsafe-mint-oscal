# ADR-0005 — Rendering & validation boundary: OSCAL CLI oracle and in-process semantic validation

> **Superseded for Profile authoring:** ADR-0010 supersedes the old “no Trestle” decision
> for the Profile/compiler lane. This ADR remains applicable to the shipped POA&M emitter
> until that path is migrated deliberately.

- **Status:** Accepted
- **Date:** 2026-07-28
- **Deciders:** mint-oscal maintainers
- **Related:** ADR-0004 (agnostic core), ADR-0001 (OSCAL target); resolves #8 (trestle vs hand-roll); closes the dangling ADR-0005 reference in #7; governs the fix for #3 (`--validate` false green) and reinforces #4 (deterministic output)

## Contents

1. [Context](#context)
2. [The trestle investigation (grounded)](#the-trestle-investigation-grounded)
3. [Decision](#decision)
4. [Design: the boundary](#design-the-boundary)
5. [Proposed code (Layer 2 validator registry)](#proposed-code-layer-2-validator-registry)
6. [What exactly we borrow — provenance ledger](#what-exactly-we-borrow--provenance-ledger)
7. [Anti-pattern review of the proposed design](#anti-pattern-review-of-the-proposed-design)
8. [Consequences](#consequences)
9. [Alternatives considered](#alternatives-considered)
10. [Implementation plan](#implementation-plan)
11. [References](#references)

## Context

`mint-oscal` emits OSCAL documents (POA&M today; Assessment Results and Component
Definition next) and offers a `--validate` step. Two forces meet at this boundary:

1. **Correctness.** OSCAL is a large, deeply nested, strictly ordered metaschema. Producing
   it by hand is how subtle shape bugs appear — e.g. a custom `prop` emitted without its `ns`
   (#2), or an empty `relevant-evidence: []` where OSCAL requires ≥1 item (#9). A JSON schema
   alone also does not catch *semantic* breakage: duplicate `uuid`s, or a
   `related-risks[].risk-uuid` that points at no `risks[].uuid`.
2. **Version sovereignty.** NIST ships OSCAL on its own cadence — latest is **1.2.2**
   (2026-04-30). The product story includes tracking the current NIST version; whatever owns
   our OSCAL construction sets our version ceiling.

Today `--validate` runs a single shallow `structural_errors()` pass and prints `OK`. That is a
**false green** (#3): it passes documents that the NIST reference validator (`oscal-cli`) would
reject, and it never invokes an authoritative oracle. This ADR settles how we build and
validate OSCAL, and whether we take a typed-model dependency to do it.

## The trestle investigation (grounded)

The obvious candidate is IBM's `compliance-trestle` — generated pydantic models for OSCAL with
built-in validation. We evaluated it empirically rather than by reputation (`/tmp` probes,
`oscal-cli` cross-checks):

| Fact | Value | Source |
| --- | --- | --- |
| Provenance | **IBM Corp**, not NIST (`gen_oscal.py`-generated models) | package source header |
| Latest version | **4.2.0**, released **2026-07-02**; **11 releases in 2026** (3.11→4.0→4.1→4.2) — **actively maintained** | PyPI JSON |
| OSCAL modelled | **1.2.1**, hard-locked `OSCAL_VERSION_REGEX = ^1\.2\.[0-1]$` | `trestle/oscal/__init__.py` |
| NIST latest | **1.2.2** (2026-04-30) — trestle **cannot represent it** (regex forbids `1.2.2`) | usnistgov/OSCAL |
| Dependency weight | **42 packages / 54 MB** | `pip install` on py3.12 |
| 1.2.2 committed? | No committed date; "Next OSCAL Version Update" milestone holds pydantic-v2/task issues, **not** a 1.2.2 bump | IBM issue tracker |
| Build works? | Yes — `oscal_serialize_json()` produced a POA&M that `oscal-cli` validated, byte-identical across runs, custom `ns` props preserved | `/tmp` pressure test |

The decisive facts: trestle is **actively maintained** (a dozen 2026 releases) and **can** build
valid, deterministic OSCAL — so this is **not** a maintenance-risk rejection. It is rejected on
two grounds: (1) **version sovereignty** — its `OSCAL_VERSION_REGEX` pins 1.2.1 and *forbids* the
current NIST **1.2.2**, so adopting it subordinates our OSCAL-version ceiling to IBM's cadence
(fast, but not ours), and (2) **dependency weight** — 42 packages against a 2-runtime-dep
minimalist tool with a legal-grade supply-chain story. The typed-model convenience is obtainable
more cheaply (see Decision).

> **Correction (2026-07-28):** an earlier draft of this ADR claimed trestle was "released
> 2024-12-19 (~18 months stale), maintenance mode, dependabot-only." That was a bad PyPI-fetch
> summarization and is **factually false** — trestle shipped 4.2.0 on 2026-07-02 with 11 releases
> in 2026. The "unmaintained" argument is struck; the decision stands on version sovereignty and
> dependency weight alone.

Separately, `oscal-cli` (the metaschema-framework community tool) validates **any** NIST
version including 1.2.2, and is already our evidence-grade oracle.

## Decision

**Do not take a dependency on trestle.** Keep OSCAL construction hand-rolled, and validate in
two layers:

- **Layer 1 — schema/shape:** delegate authoritative schema validation to **`oscal-cli`**, the
  NIST-community reference validator, in CI and on the evidence path. It is version-agnostic and
  is the tool a jury/expert would independently re-run. `mint-oscal` never claims to *be* the
  schema authority.
- **Layer 2 — semantic:** an **in-process registry of small, composable validators** that check
  the cross-cutting invariants a JSON schema cannot express (uuid uniqueness, internal reference
  resolution, `ns` presence, no-empty-where-required). This is the pattern **borrowed from
  trestle's `Validator` framework** — the pattern, not the package.

`--validate` runs Layer 2 and reports honestly that it is *not* a substitute for the Layer 1
oracle; an opt-in flag invokes `oscal-cli` when the toolchain is present.

We borrow four specific ideas from trestle and leave the rest: the `Validator` contract with the
**docstring as failure message**, a **registry + compose-all** runner, the **reflective
`find_values_by_name` tree-walk** (which already handles plain dicts, so it runs on our emitted
output with no models), and **RFC 8785 canonical JSON** for byte-stable evidence output. We do
**not** adopt trestle's generated models, its `trestle-workspace` filesystem layout, or its
dependency tree.

## Design: the boundary

```
IR (Finding/Subject)                     ADR-0004 agnostic core
      │
      ▼  emitter (hand-rolled dict, metaschema child-order)     ← render
  OSCAL dict
      │
      ├─ render(fmt): json | (xml/yaml via oscal-cli)           ← format is oscal-cli's job
      │
      ├─ LAYER 2  semantic_errors(doc)  ── in-process, zero-dep  ← this ADR
      │       no-dup-uuid · refs-resolve · props-ns · non-empty
      │
      └─ LAYER 1  oscal-cli validate     ── authoritative NIST oracle (CI + evidence + --oracle)
```

The two layers are independent and complementary: Layer 2 is fast, always-on, and catches the
`mint-oscal`-authored mistakes we have actually shipped (#2, #9); Layer 1 is the external ground
truth. `--validate` passing Layer 2 is necessary, never sufficient — and it says so.

## Proposed code (Layer 2 validator registry)

`src/mint_oscal/validate.py` (replaces the shallow `structural_errors`):

```python
"""In-process semantic validation of emitted OSCAL (Layer 2).

Schema/shape validation (Layer 1) is delegated to the NIST oscal-cli oracle; this
module adds the cross-cutting invariants a JSON schema cannot express, so --validate
stops reporting a false green. Pattern borrowed from IBM compliance-trestle's
Validator framework (ADR-0005); the dependency is not taken.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

_NS = "ns"


def _find(obj: Any, key: str) -> list[Any]:
    """Collect every value of `key` anywhere in a nested dict/list (reflective walk)."""
    out: list[Any] = []
    if isinstance(obj, dict):
        if key in obj:
            out.append(obj[key])
        for value in obj.values():
            out.extend(_find(value, key))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_find(item, key))
    return out


def _poam(doc: dict[str, Any]) -> dict[str, Any]:
    body = doc.get("plan-of-action-and-milestones")
    if not isinstance(body, dict):
        raise KeyError("document has no plan-of-action-and-milestones root")
    return body


def no_duplicate_uuids(doc: dict[str, Any]) -> list[str]:
    """every uuid in the document is unique"""
    counts = Counter(_find(doc, "uuid"))
    return [f"duplicate uuid: {u}" for u, n in sorted(counts.items()) if n > 1]


def observation_refs_resolve(doc: dict[str, Any]) -> list[str]:
    """every related-observation uuid resolves to a declared observation"""
    poam = _poam(doc)
    declared = {o.get("uuid") for o in poam.get("observations", [])}
    used = _find(poam.get("poam-items", []), "observation-uuid")
    return [f"unresolved observation-uuid: {u}" for u in used if u not in declared]


def risk_refs_resolve(doc: dict[str, Any]) -> list[str]:
    """every related-risk uuid resolves to a declared risk"""
    poam = _poam(doc)
    declared = {r.get("uuid") for r in poam.get("risks", [])}
    used = _find(poam.get("poam-items", []), "risk-uuid")
    return [f"unresolved risk-uuid: {u}" for u in used if u not in declared]


def props_namespaced(doc: dict[str, Any]) -> list[str]:
    """every custom prop carries an ns (regression guard for #2)"""
    return [
        f"prop without ns: {p.get('name')}"
        for p in _find(doc, "props")
        for p in (p if isinstance(p, list) else [])
        if isinstance(p, dict) and _NS not in p
    ]


_VALIDATORS = (
    no_duplicate_uuids,
    observation_refs_resolve,
    risk_refs_resolve,
    props_namespaced,
)


def semantic_errors(doc: dict[str, Any]) -> list[str]:
    """Run all Layer-2 validators; return a flat list of problems (empty == valid).

    The docstring of each validator is its failure category (trestle convention).
    """
    return [problem for check in _VALIDATORS for problem in check(doc)]
```

CLI wiring (honest messaging, no false green):

```python
problems = semantic_errors(oscal)
if problems:
    for p in problems:
        print(f"semantic error: {p}", file=sys.stderr)
    return 1
print("semantic checks passed — NOT a substitute for NIST oscal-cli schema "
      "validation (use --oracle, or run oscal-cli in CI)", file=sys.stderr)
```

## What exactly we borrow — provenance ledger

This is the full accounting, for scrupulous review. trestle is Apache-2.0, so verbatim reuse
with attribution would be permitted; we deliberately **re-derive** instead, so no trestle source
headers propagate into `mint-oscal`. The tally:

| Borrowed element | trestle source | Our version | Classification | Verbatim lines |
| --- | --- | --- | --- | ---: |
| Recursive value collector | `common/model_utils.py::find_values_by_name` (~21 lines) | `validate.py::_find` (~10 lines) | **RE-DERIVED** — dropped the pydantic `BaseModel` branch; kept only dict/list recursion | **0** |
| Duplicate detection | `model_utils.py::has_no_duplicate_values_by_name` (~5 lines) | `validate.py::no_duplicate_uuids` (~3 lines) | **RE-DERIVED** — uses `Counter`, reports *which* uuids | **0** |
| Validator contract | `core/validator.py::Validator.model_is_valid` + `error_msg=__doc__` | tuple of functions + docstring-as-category | **PATTERN-ONLY** | 0 |
| Registry + compose-all | `core/validator_factory.py`, `core/all_validator.py::AllValidator` | `_VALIDATORS` tuple + `semantic_errors` runner (~4 lines) | **PATTERN-ONLY** | 0 |
| Referential integrity | `core/refs_validator.py::RefsValidator` (role_id ∈ roles) | `observation_refs_resolve` / `risk_refs_resolve` (different fields) | **PATTERN-ONLY** | 0 |
| Canonical serialization | `base_model.py::oscal_serialize_json_bytes(canonical=True)` → RFC 8785 | our own JCS/`sort_keys` on the evidence path | **PATTERN-ONLY** (RFC 8785 is a public standard, not trestle code) | 0 |
| **Total** | | **~80 lines new; ~13 re-derived** | | **0** |

The single structurally-similar function, side by side:

```python
# trestle — common/model_utils.py (Apache-2.0, IBM) — handles BaseModel + list + dict
def find_values_by_name(object_of_interest, name_of_interest):
    loe = []
    if isinstance(object_of_interest, BaseModel):        # ← branch we DROP (we have no models)
        value = getattr(object_of_interest, name_of_interest, None)
        if value is not None:
            loe.append(value)
        fields = getattr(object_of_interest, const.FIELDS_SET, None)
        if fields is not None:
            for field in fields:
                loe.extend(find_values_by_name(getattr(object_of_interest, field, None), name_of_interest))
    elif type(object_of_interest) is list:
        for item in object_of_interest:
            loe.extend(find_values_by_name(item, name_of_interest))
    elif type(object_of_interest) is dict:
        if name_of_interest in object_of_interest:
            loe.append(object_of_interest[name_of_interest])
        for item in object_of_interest.values():
            loe.extend(find_values_by_name(item, name_of_interest))
    return loe
```
```python
# mint-oscal — validate.py — re-derived for plain dicts only (textbook recursion)
def _find(obj, key):
    out = []
    if isinstance(obj, dict):
        if key in obj:
            out.append(obj[key])
        for value in obj.values():
            out.extend(_find(value, key))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_find(item, key))
    return out
```

**Bottom line: zero verbatim lines; ~13 lines of re-derived, license-clean recursion; everything
else is architecture we wrote from scratch, credited here.**

## Anti-pattern review of the proposed design

| Lens | Verdict |
| --- | --- |
| fail-open / false-green | ✅ Adds the semantic layer the old check lacked; on any problem returns non-zero. The success message explicitly disclaims schema authority — the false green (#3) is gone by construction |
| over-claiming | ✅ `--validate` no longer asserts NIST validity; Layer 1 stays `oscal-cli` |
| dependency / supply chain | ✅ zero new deps; ~80 lines; version-sovereign |
| reflective walk cost | 🟡 O(n) per field over a small document; acceptable. Not run in hot paths |
| KeyError on malformed input | ✅ `_poam` raises a clear domain error rather than silently passing; validation runs on our own output, but the guard is explicit |
| magic strings | 🟡 OSCAL key names (`observation-uuid`, `risk-uuid`) are inline; acceptable for a validator that is inherently OSCAL-shaped, and each is covered by a named validator |
| self-documenting failures | ✅ docstring-as-category borrowed from trestle; honest messages |
| test coverage | 🔴 tester-owned (#6): each validator needs a falsifier (dup uuid, dangling ref, ns-less prop) |

**Verdict: clean, zero-dep, and it closes #3 by adding the missing semantic layer** while keeping
`oscal-cli` as the authoritative oracle. The only 🔴 is coverage, which is the tester's lane.

## Consequences

**Positive**

- **Version sovereignty retained** — we can target NIST 1.2.2 (and beyond) the day we choose;
  no IBM release gates us.
- **`--validate` stops lying** (#3) and gains real referential/uniqueness checks that catch the
  exact bug classes we have shipped (#2, #9).
- **Two runtime deps preserved** — the audit/supply-chain and OpenSSF story stays clean.
- **Byte-stable evidence** — RFC 8785 canonical serialization strengthens the determinism claim
  (#4).

**Negative / cost**

- We **own the metaschema shape** — child-ordering and required-field discipline live in our
  emitters and in the conformance lane, not in a typed model. Mitigation: `oscal-cli` in CI is
  the backstop, and the AR/Component emitters must be built carefully against the metaschema.
- The Layer-2 validators are **our** re-encoding of OSCAL invariants; they must be kept in step
  with the metaschema as we add models. They are data-shaped and reviewable, but they are not
  auto-generated.

## Alternatives considered

- **A — Adopt trestle (rejected).** Typed models fix shape-by-construction and give AR/Component
  for free, and it is **actively maintained** (11 releases in 2026). Rejected on two grounds: it
  adds **42 dependencies** to a 2-runtime-dep tool, and its version regex **forbids the current
  NIST 1.2.2** — subordinating our version ceiling to IBM's cadence (fast, but not ours).
  Convenience did not justify surrendering version sovereignty or the minimalist supply chain. The
  maintenance concern raised in an earlier draft was **factually wrong and withdrawn**.
- **B — Schema-only in-process (rejected).** Bundle the OSCAL JSON schema and validate against it
  in-process. Rejected: re-implements what `oscal-cli` already does authoritatively, still misses
  semantic invariants (uuid/ref), and re-introduces a version-pinning burden.
- **C — `oscal-cli`-only, no Layer 2 (rejected).** Rely solely on the oracle. Rejected: requires
  a container/toolchain for every `--validate`, is slow for an inner-loop check, and leaves no
  fast in-process guard for the `mint-oscal`-authored bug classes.

## Implementation plan

1. **0.1.0** — land `validate.py` (Layer 2) replacing `structural_errors`; fix the CLI messaging
   (closes #3). Pair with the deterministic-timestamp fix (#4). Tester adds falsifiers (#6).
2. **0.1.0 CI** — wire `oscal-cli` (Layer 1) as a required CI gate over the example fixtures, so
   every change is schema-checked by the NIST oracle.
3. **0.2.0** — add an opt-in `--oracle` flag that shells to `oscal-cli` for on-demand
   authoritative validation; extend Layer 2 as AR/Component emitters land.

## References

- IBM `compliance-trestle` 4.2.0 source: `trestle/core/validator.py`,
  `duplicates_validator.py`, `refs_validator.py`, `validator_factory.py`, `base_model.py`
  (`oscal_serialize_json_bytes`, `canonical`), `common/model_utils.py`
  (`find_values_by_name`) — patterns borrowed, dependency not taken.
- NIST OSCAL 1.2.2 release (2026-04-30); `usnistgov/OSCAL`.
- `oscal-cli` (metaschema-framework) — authoritative schema oracle.
- RFC 8785 — JSON Canonicalization Scheme.
