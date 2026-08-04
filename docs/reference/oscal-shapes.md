# OSCAL POA&M field reference

The exact structure of the OSCAL Plan of Action and Milestones (POA&M) document that
`mint-oscal poam generate` emits. Field names, sources, and namespaces are drawn from
the emitter (`src/mint_oscal/emitters/poam.py` and `src/mint_oscal/emitters/_common.py`)
and confirmed by minting `examples/example.cbom.json` with version `0.2.1`.

The emitted document targets OSCAL `1.2.2` and validates against `oscal-cli 3.2.0`.
`poam` is the only model that emits a document today. `ar` (Assessment Results) is a
planned model whose `generate` verb exits `3`; its fields are not documented here.

## Contents

1. [Document root](#document-root)
2. [metadata](#metadata)
3. [system-id and inventory](#system-id-and-inventory)
4. [observations](#observations)
5. [risks](#risks)
6. [poam-items](#poam-items)
7. [Property namespaces](#property-namespaces)
8. [Deterministic identifiers](#deterministic-identifiers)
9. [Cardinality and omission rules](#cardinality-and-omission-rules)
10. [Empty scans](#empty-scans)
11. [Control crosswalk caveat](#control-crosswalk-caveat)

## Document root

The document has a single root key, `plan-of-action-and-milestones`, whose value is an
object with these fields.

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `uuid` | UUID | Deterministic UUIDv5 | Derived from `poam`, the subject id, and the document date. |
| `metadata` | object | See [metadata](#metadata) | Always present. |
| `system-id` | object | Subject identity | See [system-id and inventory](#system-id-and-inventory). |
| `local-definitions` | object | Subject identity | Holds `inventory-items`. |
| `observations` | array | Findings | Present only when the scan produced at least one finding. |
| `risks` | array | Findings | Present only when the scan produced at least one finding. |
| `poam-items` | array | Findings | Always present, always at least one item. |

## metadata

Built by `_common.metadata`.

| Field | Type | Value |
| --- | --- | --- |
| `title` | string | `POA&M - <source> scan of <subject-id>`, where `<source>` is `CBOM` or `QuReddy`. |
| `last-modified` | dateTime-with-timezone | The document timestamp; the latest finding observation time, normalized to UTC. Falls back to `1970-01-01T00:00:00+00:00` when no finding carries an observation time. |
| `version` | string | `0.1.0` (fixed default). |
| `oscal-version` | string | `1.2.2` (from `_common.OSCAL_VERSION`). |

## system-id and inventory

| Path | Type | Value |
| --- | --- | --- |
| `system-id.identifier-type` | string | `https://ietf.org/rfc/rfc3986`. |
| `system-id.id` | string | The subject id, for example `example.com:443`. |
| `local-definitions.inventory-items[]` | array | One inventory item for the scanned subject. |
| `local-definitions.inventory-items[].uuid` | UUID | Deterministic UUIDv5 from `inventory-item` and the subject id. |
| `local-definitions.inventory-items[].description` | string | The subject description. |

The inventory item UUID is the target that every observation subject references.

## observations

One observation per finding. Present only when the scan produced findings. Child order
follows the OSCAL metaschema.

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `uuid` | UUID | Deterministic UUIDv5 from `observation` and the finding id. | Referenced by the poam-item `related-observations`. |
| `description` | string | Finding title. | |
| `props` | array | Finding crypto posture. | Omitted when the finding carries no posture. All props ride in the BreachSAFE namespace. See [Property namespaces](#property-namespaces). |
| `methods` | array | Fixed `["TEST"]`. | |
| `types` | array | Fixed `["finding"]`. | |
| `subjects` | array | One entry: `{"subject-uuid": <inventory-item uuid>, "type": "inventory-item"}`. | |
| `relevant-evidence` | array | Finding evidence. | Omitted when the finding has no evidence. Each entry has a `description` and optional BreachSAFE-namespaced `props`. |
| `collected` | dateTime-with-timezone | Finding observation time, normalized to UTC. | |

## risks

One risk per finding. Present only when the scan produced findings.

| Field | Type | Source |
| --- | --- | --- |
| `uuid` | UUID | Deterministic UUIDv5 from `risk` and the finding id. |
| `title` | string | Finding title. |
| `description` | string | Finding risk statement. |
| `statement` | string | Finding risk statement (same value as `description`). |
| `status` | token | The finding's own status, `open` or `closed`. |

## poam-items

One item per finding, and always at least one item. Referenced observations and risks
are linked by UUID.

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `uuid` | UUID | Deterministic UUIDv5 from `poam-item` and the finding id. | |
| `title` | string | Finding title. | |
| `description` | string | Finding description. | |
| `props` | array | Control mapping and interpretation. | See the property table below. |
| `related-observations` | array | One `{"observation-uuid": ...}` entry. | |
| `related-risks` | array | One `{"risk-uuid": ...}` entry. | |
| `links` | array | Catalog references. | Present only when the active framework declares a catalog and the finding has control ids. Each link is `{"href": "<catalog>#<control-id>", "rel": "reference"}`. |

The poam-item `props` array carries, in order:

| Prop name | Namespace | Value |
| --- | --- | --- |
| `control-id` | Framework authority | One prop per control id, for example `qts-06.9` (SCF) or `SC-13` (NIST). |
| `severity` | BreachSAFE | The finding severity, for example `low`. |
| `framework` | BreachSAFE | The framework version id, for example `scf-qts-2026.2`. Present when the pack declares one. |
| `interpretation-status` | BreachSAFE | `provisional`, present when the pack has not passed conformance sign-off. Both bundled packs are unreviewed, so this prop is currently always emitted. |

## Property namespaces

Emitted props ride in two namespaces. Control identifiers belong to the standards body
that owns them, so they are attributed to the framework authority namespace, not the
BreachSAFE namespace.

| Namespace | URI | Props |
| --- | --- | --- |
| BreachSAFE | `https://breachsafe.ai/ns/oscal` | `readiness`, `mapping-confidence`, `severity`, `framework`, `interpretation-status`, `nistQuantumSecurityLevel`, `provenance` (with `--extension breachsafe`), and posture facts such as `kex-offered` and `cert-signature`. |
| Framework authority | `https://securecontrolsframework.com/ns/oscal` for `scf-qts`; `https://csrc.nist.gov/ns/oscal/800-53` for `nist` | `control-id`. |

OSCAL constrains prop names in the core namespace (`http://csrc.nist.gov/ns/oscal`) to
an allowed set, so every custom prop carries an explicit `ns`. The `--framework` flag
selects the authority namespace and the catalog link target.

## Deterministic identifiers

Every UUID is a UUIDv5 computed with the fixed namespace
`6f9619ff-8b86-d011-b42d-00c04fc964ff` over stable inputs, so the same scan mints a
byte-identical document. The document timestamp is derived from the findings' own
observation times rather than the wall clock, which keeps the output reproducible.

## Cardinality and omission rules

The emitter follows the OSCAL cardinality rules that a JSON schema enforces.

| Rule | Behavior |
| --- | --- |
| `poam-items` requires at least one item. | An empty scan gets one summary item. See [Empty scans](#empty-scans). |
| `observations` and `risks` require at least one item when present. | The emitter omits the whole array when there are no findings, rather than emitting `[]`. |
| `props` requires at least one item when present. | The emitter omits `props` on an observation or evidence entry that has none. |
| `relevant-evidence` requires at least one item when present. | The emitter omits the key for an evidence-less finding. |

## Empty scans

A scan that produced no findings (for example a fully quantum-ready endpoint) still
emits a valid POA&M. The `observations` and `risks` arrays are absent, and `poam-items`
holds one summary item:

| Field | Value |
| --- | --- |
| `uuid` | Deterministic UUIDv5 from `poam-item`, `no-findings`, and the subject id. |
| `title` | `No findings`. |
| `description` | `No post-quantum cryptographic findings were identified for <subject-id>.` |

The emitter does not fabricate findings, observations, or risks to fill an empty scan.

## Control crosswalk caveat

The finding-to-control-to-parameter crosswalk that populates `control-id`, `framework`,
and the catalog links is a draft mapping authored by BreachSAFE, not a signed-off
compliance decision. Both bundled policy packs are unreviewed, so every emitted item
carries `interpretation-status: provisional`. A verdict is a deficiency only when the
organization's parameter requires post-quantum cryptography; otherwise it is
informational. An OSCAL-valid POA&M is not by itself a compliance assertion. See
[../explanation/valid-vs-compliant.md](../explanation/valid-vs-compliant.md).
</content>
