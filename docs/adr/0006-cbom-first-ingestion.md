# ADR-0006 — File-driven CycloneDX-CBOM ingestion

- **Status:** Proposed
- **Deciders:** mint-oscal maintainers
- **Related:** ADR-0004 (agnostic core); UC-1, UC-2; [oscal-shapes.md](../oscal-shapes.md)

## Context

CBOM (CycloneDX Cryptography Bill of Materials) is the generic, standards-based ingestion
path for `mint-oscal`. Under the ADR-0004 agnostic-core stance, the core reads a neutral IR
and CBOM is the vendor-independent way to feed it — any producer that emits CycloneDX-CBOM
should flow through the same engine as QuReddy, without a bespoke integration per source.

The problem is that **real CBOMs vary structurally** — by CycloneDX version and by producer —
in ways that are not cosmetic. This was verified first-hand against two corpora:

- **QuReddy CBOMs** are CycloneDX **1.7** and **endpoint-centric**: `metadata.component` is
  the scanned host, algorithm assets are **bare** (`assetType: algorithm` with little detail),
  and the key-exchange signal is carried in
  `protocolProperties.cipherSuites[].algorithms` rather than on the algorithm component
  itself.
- **IBM cbomkit CBOMs** are CycloneDX **1.6**, have **no `metadata.component`**, and instead
  carry rich `algorithmProperties` — `primitive`, `parameterSetIdentifier`, and
  `cryptoFunctions` — on each algorithm component.

The same logical fact (e.g. "this endpoint negotiates a quantum-vulnerable key exchange")
lives at different paths, under different keys, in different versions. A hard-coded adapter
would have to branch on `specVersion`, on the presence of `metadata.component`, and on each
producer's placement of the crypto signal. That branching would **accrete indefinitely**:
every CycloneDX revision, every new PQC algorithm, and every customer or enterprise extension
would force a code change plus a release. That is exactly the coupling ADR-0004 exists to
avoid.

## Decision

**CBOM ingestion is a small generic engine driven by declarative, overlayable configuration**,
not hard-coded field access. The engine holds the pipeline; the knowledge of *where fields
live*, *how algorithms classify*, and *what counts as ready* is data.

Three data layers:

1. **Extraction profiles** — `profiles/*.yaml`. Each profile is a set of path selectors that
   map CBOM structure onto the neutral IR, plus a `detect` block that matches the profile to a
   document (`bomFormat` + a `specVersion` range). Profiles are **overlayable**, merged
   base → producer → customer, so a customer extension is an overlay, not a fork.

   ```yaml
   # profiles/qureddy-1.7.yaml
   detect:
     bomFormat: CycloneDX
     specVersion: ">=1.7 <1.8"
   subject:
     from: metadata.component        # endpoint-centric
   algorithms:
     each: components[?assetType=='algorithm']
     name: name
     key_exchange: protocolProperties.cipherSuites[].algorithms
   ```

2. **Crypto registry** — `crypto-registry.yaml`. A flat algorithm → classification map:
   `{ quantum_safe, nistLevel, kind }`. This is where "ML-KEM is safe, RSA-2048 is not" lives
   as reviewable data.

   ```yaml
   ML-KEM-768: { quantum_safe: true,  nistLevel: 3, kind: kem }
   RSA-2048:   { quantum_safe: false, nistLevel: 0, kind: signature }
   ```

3. **Readiness rules** — `readiness-rules.yaml`. A declarative mapping from the extracted,
   classified inventory to a readiness verdict.

The engine flow is: **profile-match → selector extraction → registry classification → rule
evaluation → IR**.

From that IR, the existing emitters run unchanged: **CBOM → Component Definition** maps
faithfully (inventory in, inventory out), and **CBOM → POA&M / AR** derives findings via the
readiness step (per ADR-0001, SAR canonical, POA&M derived).

The native **`qureddy.scan.v1`** adapter is **retained** — it carries QuReddy-specific rule
semantics that are not part of the generic CBOM contract. The file-driven CBOM engine is the
general path; the native adapter stays the specialized one.

Config files carry a schema version: `mint.cbom.map/v1`.

## Consequences

**Positive**

- CycloneDX version bumps, new PQC algorithms, and customer/enterprise enhancements become
  **config edits, not code changes** — no release to add an algorithm or absorb a `specVersion`.
- **One engine serves the whole CycloneDX ecosystem** — QuReddy, IBM cbomkit, and future
  producers — validated against **both** corpora rather than one.
- Readiness verdicts and algorithm classifications are **auditable data**: reviewable by the
  conformance lane the same way the metaschemas are, not buried in imperative code.

**Negative / cost**

- A **selector mini-language** plus config validation is new surface to specify, version, and
  test. A malformed profile MUST **fail loudly, not silently mis-map** — a selector that
  matches nothing has to error, not quietly drop the subject.
- Readiness rules are deliberately **simple**. Complex organizational policy still belongs in a
  consumed OSCAL **Profile** (T4), not in `readiness-rules.yaml`; the rules file classifies
  inventory, it does not encode an org's full control baseline.

**Status note:** Proposed. Selector mini-language and profile-merge semantics are Designed; the
QuReddy 1.7 and cbomkit 1.6 profiles are the two reference fixtures to validate against.
