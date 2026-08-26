# TROVE-CURATA-XREF-WP00

## Status

Approved GCL-contained foundation and capability-reconciliation work package.

## Purpose

TROVE-CURATA is a Grand Challenge Labs pre-training data curation programme with two distinct responsibilities:

- **TROVE** is the governed data estate: acquired source objects, shards, corpus versions, and mixture-ready releases.
- **CURATA** is the curation control plane: extraction, normalization, policy processing, classification, deduplication, scoring, lineage, qualification, and admission decisions.

This work package reconciles TROVE-CURATA with existing GCL mechanisms so the programme does not create a parallel governance, provenance, review, or certification vocabulary.

## Containment boundary

1. TROVE-CURATA is a GCL-owned and GCL-governed project.
2. `grandchallenge/INTELLECT` is the bootstrap authority and implementation location for WP00 contracts, validators, fixtures, and review records.
3. No external project repository is an implementation, schema, artifact, release, or governance dependency.
4. External projects and papers may be cited as references or prior inspiration only. Their branches, releases, schemas, and availability cannot determine TROVE-CURATA state.
5. Open-source libraries such as Daft, Trafilatura, Presidio, OCR systems, embedding models, and vector-search systems may be used as replaceable execution providers. Every provider must be version-pinned and has no policy authority.
6. GitHub remains the present operational record. AETHER is a future nonblocking semantic projection and is not required for execution.
7. Successful pipeline execution is not equivalent to data quality, privacy, legality, safety, factuality, fitness for training, or downstream benefit.

A later dedicated GCL repository may be created when implementation scale warrants separation. WP00 does not depend on that repository existing.

## GCL capability architecture

| Existing capability | Reuse in TROVE-CURATA | Decision |
|---|---|---|
| INTELLECT event-sourced work packages and office review | Govern material curation changes and GCL release decisions | Generalize |
| AETHER provenance and replay model | Future projection of source, transformation, review, and release events | Defer |
| GCL-GHOS repository controls | Baseline branch protection, immutable actions, CI, and review controls | Reuse directly |
| MATHFORGE source locks and provider manifests | Source/corpus provider manifests and deterministic acquisition records | Generalize |
| MATH-PROGRAMME artifact authority and claim ledgers | Corpus release manifests, admission state, and curation-claim boundaries | Generalize |
| MATHCERT intake/replay/qualification separation | CURATA-CERT qualification states and independent replay | Adapt locally |
| CSS adversarial fixtures | Parser, PII, dedup, contamination, and label-drift fixtures | Reuse directly |
| ALIGN matched comparisons | Ablations for curation interventions and mixture decisions | Reuse directly |
| MODULUS intervention telemetry | Threshold response curves and distribution-shift accounting | Adapt locally |
| MATHSOLVE mathematical routing | No direct data-curation analogue | Reject |

## Four-record contract

### TROVE Source Record

Identifies acquired material without asserting training eligibility.

Required concepts:

- stable source identifier;
- source family and URI;
- acquisition time or snapshot identity;
- raw byte or object digest;
- acquisition method and provider identity;
- rights and policy observations, explicitly non-dispositive;
- raw-content reference;
- source-level warnings.

### CURATA Transformation Receipt

Records one deterministic or model-assisted transformation.

Required concepts:

- input identity;
- stage contract and implementation identity;
- configuration and environment identity;
- model, tokenizer, prompt, or classifier identities where applicable;
- output identity;
- metrics, warnings, and failure state;
- statement of whether the stage may alter content;
- independent replay method where available.

### CURATA Passport

Aggregates ordered lineage and eligibility decisions for a document or shard.

Required concepts:

- source record identity;
- ordered transformation receipt identities;
- PII and policy decisions;
- dedup memberships and retention role;
- quality and attribute scores with calibration references;
- admitted and prohibited uses;
- residual risks and unresolved review items.

At scale, passports should be shard-level by default, with document-level exception records. A verbose record per document is not required where it would make the estate operationally unmanageable.

### TROVE Release Manifest

Defines a content-addressed GCL corpus release.

Required concepts:

- release identity and version;
- shard identities and aggregate digests;
- source-family and token accounting;
- mixture weights and sampling policy;
- provider manifests;
- qualification records;
- known limitations;
- admitted and prohibited uses;
- supersession and disposal relations.

## Identity model

Every material qualification must distinguish:

1. source or corpus identity;
2. curation-tooling identity;
3. qualification-tooling identity;
4. execution identity.

Model-assisted stages must additionally bind model weights, tokenizer, prompt or classifier contract, decoding or scoring parameters, and runtime versions. A fixed corpus processed by changed tooling is a distinct qualified object.

## Dependency policy

TROVE-CURATA permits pinned software providers but rejects external project-state dependencies.

Allowed:

- pinned packages and model artifacts;
- independently acquired public source data;
- published algorithms and papers;
- optional provider adapters behind GCL-owned contracts.

Prohibited:

- requiring an external project repository to exist or remain available;
- importing external governance, release, or admission state as GCL authority;
- treating a third-party branch, issue, PR, schema, or artifact as the canonical TROVE-CURATA record;
- making external implementation progress a gate for GCL work;
- allowing a provider to self-certify its outputs.

## Review tiers

### T0 — editorial or nonsemantic

Examples: prose correction, link repair, comments, formatting.

Required: ordinary review and applicable CI.

### T1 — deterministic transformation

Examples: parser change, normalization rule, metadata extraction.

Required: fixtures, deterministic replay, output-diff report, and non-author review.

### T2 — judgment or retention policy

Examples: PII detector, content filter, classifier, dedup threshold, representative-selection policy.

Required: adversarial fixtures, calibration or error analysis, subgroup accounting, reversal plan, and independent Referee review.

### T3 — corpus admission or high-impact policy

Examples: GCL release admission, source-family exclusion, licensing interpretation, destructive deletion, or major mixture decision.

Required: complete provider and qualification records, claim ledger, independent Adversary and Referee review, and Human Steward disposition.

## First fixture

**TC-FIXTURE-001 — HTML extraction baseline**

Pipeline:

```text
GCL-controlled fixture HTML
→ pinned Trafilatura extraction
→ language identification
→ deterministic normalization
→ TROVE Source Record
→ CURATA Transformation Receipts
→ CURATA Passport
→ fixture report
```

Daft is the initial execution provider, not an authority and not an irreplaceable project dependency.

Fixture classes:

- ordinary long-form article;
- navigation and boilerplate-heavy page;
- MathML, LaTeX, or MathJax page;
- code-heavy page;
- multilingual page;
- malformed markup and encoding;
- explicit PII examples;
- duplicate and near-duplicate pair;
- content requiring a keep or remove decision.

Minimum acceptance criteria:

- schema-valid records;
- byte- and configuration-bound stage identities;
- no synthetic content insertion;
- preserved source-to-output traceability;
- explicit measurement of boilerplate residue;
- explicit math and code preservation report;
- explicit failures rather than silent admission;
- reproducible output under the pinned environment;
- no network or external repository dependency for fixture replay.

## Scientific evaluation boundary

CURATA-CERT answers whether a transformation behaved according to its declared contract. ALIGN evaluates whether the intervention improved downstream behavior.

Material interventions require matched comparisons where feasible, including rare-stratum retention and not merely aggregate validation loss. Candidate comparisons include:

- no fuzzy dedup versus MinHash/LSH threshold variants;
- source-local versus global deduplication;
- semantic cluster representative caps;
- quality-filter retention thresholds;
- generic versus STEM-preserving extraction;
- stripped versus markup-preserving wiki representations;
- PII redaction versus document removal.

## First executable sequence

1. Admit this GCL-contained authority and dependency contract.
2. Define the four record schemas independently within GCL.
3. Implement `TC-FIXTURE-001` using locally retained fixture bytes.
4. Add provider-version locks, deterministic output digests, and mutation tests.
5. Run T1 review and exact-head CI.
6. Open T2 work only after the deterministic extraction baseline is admitted.

## Non-claims

This work package does not establish that any corpus is safe, private, legal, unbiased, factual, non-synthetic, contamination-free, high quality, optimal, or suitable for model training. It does not establish downstream performance improvement, novelty, priority, or commercial value.
