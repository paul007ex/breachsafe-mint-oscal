# Roadmap

Tiers are ordered by priority. Items move to `CHANGELOG.md` as they ship. This
roadmap is intentionally interface-first: the agnostic core (ADR-0004) lets each
tier add adapters or emitters without disturbing the others.

## P0 - POA&M generate (foundational)

- [x] Source-neutral IR (`mint.ir.v1`) and frozen dataclasses.
- [x] OSCAL POA&M emitter with deterministic UUIDs.
- [x] QuReddy `qureddy.scan.v1` adapter (bundled).
- [x] `mint-oscal poam generate --from ...` CLI + structural validation.
- [ ] `oscal-cli` conformance validation wired into `--validate`.

## P1 - Assessment Results, profile consume, crosswalk sign-off

- [ ] `ar` emitter (requires `import-ap`; see `emitters/ar.py`).
- [ ] Profile consume: read `set-parameters` / ODPs (`consume/profile.py`).
- [ ] SP 800-53r5 crosswalk conformance sign-off (R-CTRL-01) so a crosswalk-driven
      mapping can ship.
- [ ] IR wire-format load + schema validation (`ir/schema.py`).

## P2 - Component Definition, fleet, merge

- [ ] `component-definition` emitter (requires catalog consume).
- [ ] Catalog consume: control prose by id (`consume/catalog.py`).
- [ ] Fleet mode: many subjects into one document.
- [ ] Merge/diff of successive scans into an evolving POA&M.

## P3 - OCSF, profile emit

- [ ] OCSF adapter (additional source).
- [ ] XML/YAML render via `oscal-cli` (ADR-0005) as a first-class output.
- [ ] Profile emit: produce a tailored baseline as output, not just consume it.
