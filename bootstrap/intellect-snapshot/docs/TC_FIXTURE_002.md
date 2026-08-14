# TC-FIXTURE-002

## Purpose

`TC-FIXTURE-002` is a bounded T2 analysis-and-routing fixture for TROVE-CURATA. It consumes GCL-retained normalized text, records PII observations from a pinned Presidio provider and an independent GCL rules baseline, preserves disagreements, and applies GCL-owned routing rules.

It does not redact, anonymize, delete, admit, or certify data.

## Bound predecessor

- `TC-FIXTURE-001`
- INTELLECT PR #28
- exact merged head `e8d12e6f314ddabcf3a36f9ec49216b669d07024`
- protected merge `59b34a195aa7d4fdd381d428dab3e4f18e2016e7`

## Providers

The dedicated replay pins `presidio-analyzer==2.2.363` and `regex==2026.7.19`. The adapter uses Presidio `PatternRecognizer` objects only. No NLP model is downloaded, and no network is required after package installation.

Provider output is observational evidence. It has no route, admission, deletion, privacy, or release authority.

## Independent baseline

The GCL baseline uses separately defined Python regular expressions and an explicit ambiguity lexicon. It is not presented as a reference truth. Its purpose is to expose agreement, disagreement, and span-handling behavior.

## Fail-closed behavior

The validator rejects:

- out-of-range or byte-incoherent spans;
- accepted observation sets containing overlaps;
- hidden provider/baseline disagreements;
- confidence outside `[0,1]`;
- provider self-authorization;
- routes outside `observation_clear` and `review_required`;
- corpus admission, deletion, redaction, or anonymization;
- claim inflation;
- external project dependency.

The overlapping-span case is expected to produce a rejected provider observation set and a `review_required` route. This is an admitted fixture outcome, not an accepted overlapping observation set.

## Claims boundary

`observation_clear` means only that the declared detectors produced no blocking observation under the pinned fixture configuration. It does not prove that PII is absent.

`review_required` is a routing state. It is not a finding of illegality, harm, or privacy breach.
