from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from grand_intellect.trove_curata_fixture_003_review_attestation import (
    TroveCurataFixture003ReviewAttestationError,
    load_and_validate_trove_curata_fixture_003_review_attestation,
    validate_trove_curata_fixture_003_review_attestation,
)


ROOT = Path(__file__).resolve().parents[1]
ATTESTATION = ROOT / "governance" / "trove_curata_fixture_003_review_attestation.json"


class TroveCurataFixture003ReviewAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(ATTESTATION.read_text(encoding="utf-8"))

    def assert_rejected(self, mutate, message: str) -> None:
        broken = copy.deepcopy(self.record)
        mutate(broken)
        with self.assertRaisesRegex(TroveCurataFixture003ReviewAttestationError, message):
            validate_trove_curata_fixture_003_review_attestation(broken)

    def test_canonical_attestation_validates(self) -> None:
        self.assertEqual(
            load_and_validate_trove_curata_fixture_003_review_attestation(ATTESTATION),
            self.record,
        )

    def test_unknown_root_field_rejected(self) -> None:
        self.assert_rejected(lambda record: record.update({"extra": True}), "field set drift")

    def test_final_head_drift_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].update({"final_merged_head": "0" * 40}),
            "historical subject identity drift",
        )

    def test_advertised_head_cannot_be_rewritten_to_final_head(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].update(
                {"advertised_review_head": record["historical_subject"]["final_merged_head"]}
            ),
            "historical subject identity drift",
        )

    def test_stale_review_time_drift_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"]["stale_review"].update(
                {"submitted_at": "2026-08-04T05:21:43Z"}
            ),
            "historical subject identity drift",
        )

    def test_final_head_time_drift_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].update(
                {"final_head_created_at": "2026-08-04T05:21:41Z"}
            ),
            "historical subject identity drift",
        )

    def test_historical_review_cannot_be_promoted(self) -> None:
        self.assert_rejected(
            lambda record: record["historical_subject"].update(
                {"historical_exact_head_review_satisfied": True}
            ),
            "historical subject identity drift",
        )

    def test_qualifying_review_count_cannot_be_inflated(self) -> None:
        self.assert_rejected(
            lambda record: record["defect"].update({"qualifying_exact_head_approval_count": 1}),
            "defect characterization drift",
        )

    def test_workflow_run_identity_drift_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["final_head_evidence"]["workflow_runs"][0].update(
                {"run_id": 1}
            ),
            "workflow evidence drift",
        )

    def test_workflow_cannot_substitute_for_review(self) -> None:
        self.assert_rejected(
            lambda record: record["final_head_evidence"].update(
                {"workflow_success_is_review_substitute": True}
            ),
            "workflow substituted for review",
        )

    def test_corrective_review_must_target_final_head(self) -> None:
        self.assert_rejected(
            lambda record: record["remedy_contract"].update(
                {"review_must_target_corrective_pr_final_head": False}
            ),
            "review remedy semantics drift",
        )

    def test_fixture_004_cannot_be_unblocked_early(self) -> None:
        self.assert_rejected(
            lambda record: record["remedy_contract"].update(
                {"fixture_004_blocked_until_remedy_merge": False}
            ),
            "review remedy semantics drift",
        )

    def test_implementation_change_escalation_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["authority_boundary"].update({"implementation_changed": True}),
            "authority boundary drift",
        )

    def test_external_dependency_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["authority_boundary"].update(
                {"external_project_dependency": True}
            ),
            "authority boundary drift",
        )

    def test_claim_inflation_rejected(self) -> None:
        self.assert_rejected(
            lambda record: record["claim_boundary"].update({"privacy_compliance_proved": True}),
            "claim inflation",
        )


if __name__ == "__main__":
    unittest.main()
