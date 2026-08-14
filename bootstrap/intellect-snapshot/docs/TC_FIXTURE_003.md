# TC-FIXTURE-003 — governed PII transformation and residual audit

This synthetic fixture consumes the immutable text and canonical observation identities established by `TC-FIXTURE-002`. A separate GCL-authored manifest binds every permitted transformation to the exact source digest, observation digest, observation identity, entity class, character span, operator, and parameters.

Presidio Anonymizer is a replaceable execution provider. It receives only one authorized matched fragment at a time. It cannot select spans, operators, routes, admitted uses, or source mutations. GCL reassembles the final output from unchanged source gaps and transformed fragments, then compares the provider output with an independent deterministic baseline.

The fixture covers replacement, masking, multilingual UTF-8 spans, byte-identical controls, stale and overlapping plans, unsupported operators, provider-contract disagreement, duplicate identity, withheld policy authority, and residual observations after partial transformation.

A passing route of `transformation_verified` means only that the declared synthetic plan was executed and audited under the pinned fixture configuration. It does not establish anonymity, privacy compliance, legality, corpus admission, deletion authority, training fitness, production release qualification, novelty, priority, or commercial value.
