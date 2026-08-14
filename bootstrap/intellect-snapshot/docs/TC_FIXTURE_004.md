# TC-FIXTURE-004: governed duplicate-observation routing

`TC-FIXTURE-004` tests exact-byte, normalized-text, and approximate duplicate observations over retained synthetic records.

The fixture binds the reviewed `TC-FIXTURE-003` chain, including its post-merge review remedy. Selected records are reconstructed from retained Fixture 002 source text and Fixture 003 transformation plans before duplicate comparison.

## Methods

The replay evaluates exact SHA-256 equality first. It then evaluates normalized-text equality. Approximate comparison uses three-token shingles, a pinned `datasketch` 2.0.0 MinHash provider, and an independ exact GCL Jaccard baseline.

Approximate edges require both methods to meet the GCL-owned `0.720000` threshold. Code, mathematical, and short-text records receive conservative handling. Provider and baseline disagreement remains explicit.

Connected components are reconstructed only from admitted GCL edges. Transitive membership does not create an unobserved direct edge.

## Boundary

The fixture produces observations and review routes only. It does not delete or suppress records, select canonical members, admit corpus material, certify equivalence or quality, establish privacy or legality, assess training fitness, or authorize release or commercial claims.
