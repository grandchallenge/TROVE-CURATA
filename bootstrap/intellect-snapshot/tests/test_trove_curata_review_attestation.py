from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from grand_intellect.trove_curata_review_attestation import (
    TroveCurataReviewAttestationError,
    load_and_validate_trove_curata_review_attestation,
    validate_trove_curata_review_attestation,
)


ROOT = Path(__file__).resolve().parents[1]
ATTESTATION_PATH = ROOT / "governance" / "trove_curata_review_attestation.json"
SCHEMA_PATH = ROOT / "schemas" / "trove_curata_review_attestation.schema.json"


class TroveCurataReviewAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(ATTESTATION_PATH.read_text(encoding="utf-8"))

    def assert_rejected(self, mutate) -> None:
        candidate = copy.deepcopy(self.record)
        mutate(candidate)
        with self.assertRaises(TroveCurataReviewAttestationError):
            validate_trove_curata_review_attestation(candidate)

    def test_schema_is_closed(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["status"]["const"], "pending_independent_review")

    def test_canonical_attestation_is_valid(self) -> None:
        record = load_and_validate_trove_curata_review_attestation(ATTESTATION_PATH)
        self.assertEqual(record["historical_subject"]["submitted_review_count"], 0)
        self.assertFalse(record["historical_subject"]["historically_reviewed"])

    def test_original_head_cannot_drift(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].__setitem__("exact_merged_head", "0" * 40)
        )

    def test_merge_commit_cannot_drift(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].__setitem__("protected_merge_commit", "0" * 40)
        )

    def test_historical_review_cannot_be_backdated(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].__setitem__("historically_reviewed", True)
        )

    def test_review_count_cannot_be_inflated(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].__setitem__("submitted_review_count", 1)
        )

    def test_comment_cannot_substitute_for_approval(self) -> None:
        self.assert_rejected(
            lambda record: record["remedy_contract"].__setitem__("comment_is_substitute", True)
        )

    def test_author_self_review_cannot_substitute(self) -> None:
        self.assert_rejected(
            lambda record: record["remedy_contract"].__setitem__("author_self_review_is_substitute", True)
        )

    def test_stale_head_review_cannot_satisfy_gate(self) -> None:
        self.assert_rejected(
            lambda record: record["remedy_contract"].__setitem__("review_must_target_final_head", False)
        )

    def test_external_project_dependency_cannot_be_added(self) -> None:
        self.assert_rejected(
            lambda record: record["authority_boundary"].__setitem__("external_project_dependency", True)
        )

    def test_aether_cannot_become_blocking(self) -> None:
        self.assert_rejected(
            lambda record: record["authority_boundary"].__setitem__("aether_role", "required_runtime")
        )

    def test_claim_inflation_is_rejected(self) -> None:
        for claim in self.record["claim_boundary"]:
            with self.subTest(claim=claim):
                self.assert_rejected(
                    lambda record, claim=claim: record["claim_boundary"].__setitem__(claim, True)
                )


if __name__ == "__main__":
    unittest.main()
