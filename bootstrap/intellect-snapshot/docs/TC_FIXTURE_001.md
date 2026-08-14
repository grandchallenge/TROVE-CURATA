# TC-FIXTURE-001 — offline HTML extraction baseline

## Purpose

This fixture is the first executable TROVE-CURATA artifact. It tests one bounded deterministic route:

```text
repository-retained HTML
→ Daft execution
→ Trafilatura extraction
→ deterministic normalization
→ TROVE Source Record
→ CURATA Transformation Receipts
→ CURATA Passport
→ deterministic fixture report
```

It does not admit a corpus or establish quality, privacy, legality, safety, factuality, training fitness, downstream performance, novelty, priority, or commercial value.

## Provider lock

- Python: 3.11.14 in the integration workflow;
- Daft: 0.7.21;
- Trafilatura: 2.1.0;
- Daft telemetry disabled with `DO_NOT_TRACK=true`.

Provider packages are replaceable execution dependencies. They have no policy or qualification authority.

## Fixture classes

The repository retains nine HTML cases covering ordinary prose, boilerplate, math and code, multilingual content, malformed markup, explicit test PII, an exact duplicate pair, and a keep/remove policy-review case.

The PII strings use reserved test identifiers. They are intentionally preserved because this fixture tests extraction, not privacy remediation. The policy case remains `review_required`; the runner cannot admit or delete it.

## Replay

```bash
python -m pip install -r requirements-ci.txt -r requirements-trove-curata.txt
python -m pip install --no-build-isolation --no-deps -e .
DO_NOT_TRACK=true python -m grand_intellect.trove_curata_fixture \
  --manifest fixtures/trove_curata/TC-FIXTURE-001/manifest.json \
  --output /tmp/tc-fixture.json
```

The dedicated workflow executes the fixture twice and requires byte-identical JSON reports. Source bytes, provider versions, extraction configuration, outputs, receipts, and passports are digest-bound.

## Admission boundary

A passing fixture means only that the pinned extraction route satisfied its declared fixture checks. It does not authorize a TROVE release, source-family admission, PII policy, deduplication policy, or model-training use.
