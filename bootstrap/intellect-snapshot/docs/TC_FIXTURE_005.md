# TC-FIXTURE-005 — governed quality-signal observation

`TC-FIXTURE-005` is a bounded T2 fixture for structural and readability-related observations. It is not a quality classifier, corpus-admission gate, ranking system, or release qualification.

The fixture consumes immutable records from `TC-FIXTURE-004` together with five retained synthetic controls. Every selected source is bound by its UTF-8 SHA-256 digest before measurement.

## Observation surfaces

The GCL readability probe records deterministic lexical and repetition flags for ordinary English prose. It abstains on conservative record classes. The independently implemented structural baseline records symbol density, URL density, repeated lines, and transformation markers.

The canonical metrics are character, token, and non-empty line counts; alphabetic and symbol ratios; unique-token ratio; repeated-line ratio; URL count; and replacement-marker count.

These values are observations. They do not establish that a record is good, bad, useful, safe, legal, private, or fit for training.

## Conservative handling

`code_math`, `multilingual`, `boilerplate`, and `short_text` records route to `quality_review_required` without an English-prose verdict. A duplicate-component member is deliberately retained as a negative control: duplicate evidence alone cannot become a quality verdict.

## Routes

Only `no_quality_flag_observed` and `quality_review_required` exist. Neither route admits, rejects, ranks, deletes, suppresses, retains, or selects a canonical record.

## Replay

```console
python -m grand_intellect.trove_curata_quality_fixture \
  --manifest fixtures/trove_curata/TC-FIXTURE-005/manifest.json \
  --output /tmp/tc005.json
```

Two independent executions must be byte-identical. Standard CI remains dependency-light; the dedicated workflow replays the complete TROVE-CURATA fixture chain before executing Fixture 005 twice.

## Bound predecessor

Fixture 005 binds the merged Fixture 004 implementation head `6dc65962ec77e17ae5bdd2c75ccd5da63aefcef7`, protected merge `6e2385a841dfd55bbab480d79a47611cc6557103`, review-remedy head `dbb68b54aaf6df2eced710e6dd3936aa3bb2f7fc`, and protected remedy merge `70a0a74502e0480d387d740027e48751286e4bfe`.

## Claim boundary

The fixture makes no claim of dataset quality, privacy compliance, legality, training fitness, release readiness, downstream improvement, novelty, priority, or commercial value.
