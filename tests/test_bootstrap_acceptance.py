from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_bootstrap_acceptance", ROOT / "scripts" / "validate_bootstrap_acceptance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

BootstrapAcceptanceError = MODULE.BootstrapAcceptanceError
load_and_validate = MODULE.load_and_validate
validate_bootstrap_acceptance = MODULE.validate_bootstrap_acceptance
RECORD = ROOT / "governance" / "trove_curata_repo_acceptance.json"


class BootstrapAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))

    def reject(self, mutate, pattern: str) -> None:
        broken = copy.deepcopy(self.record)
        mutate(broken)
        with self.assertRaisesRegex(BootstrapAcceptanceError, pattern):
            validate_bootstrap_acceptance(broken)

    def reject_text_replacement(self, marker: str, replacement: str, pattern: str) -> None:
        source = RECORD.read_text(encoding="utf-8")
        self.assertEqual(source.count(marker), 1)
        broken = source.replace(marker, replacement, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated.json"
            path.write_text(broken, encoding="utf-8")
            with self.assertRaisesRegex(BootstrapAcceptanceError, pattern):
                load_and_validate(path)

    def reject_duplicate(self, marker: str, duplicate_member: str) -> None:
        source = RECORD.read_text(encoding="utf-8")
        self.assertEqual(source.count(marker), 1)
        broken = source.replace(marker, f"{duplicate_member}\n{marker}", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text(broken, encoding="utf-8")
            with self.assertRaisesRegex(BootstrapAcceptanceError, "duplicate JSON object key"):
                load_and_validate(path)

    def test_canonical_acceptance_validates(self) -> None:
        self.assertEqual(load_and_validate(RECORD), self.record)

    def test_unknown_root_field_rejected(self) -> None:
        self.reject(lambda record: record.update({"extra": True}), "field set drift")

    def test_source_candidate_head_drift_rejected(self) -> None:
        self.reject(
            lambda record: record["source"].update({"candidate_head": "0" * 40}),
            "source binding drift",
        )

    def test_source_protected_merge_identity_cannot_drift(self) -> None:
        self.reject(
            lambda record: record["source"].update(
                {"protected_source_closure_merge": "0" * 40}
            ),
            "source binding drift",
        )

    def test_source_cannot_be_downgraded_after_protected_merge(self) -> None:
        self.reject(
            lambda record: record["source"].update(
                {"source_closure_status": "review_ready_not_protected"}
            ),
            "source binding drift",
        )

    def test_source_review_remedy_head_drift_rejected(self) -> None:
        self.reject(
            lambda record: record["source_review_remedy"].update({"candidate_head": "0" * 40}),
            "source review remedy binding drift",
        )

    def test_historical_t3_gate_cannot_be_relabelled(self) -> None:
        self.reject(
            lambda record: record["source_review_remedy"].update({"historical_t3_gate_satisfied": True}),
            "source review remedy binding drift",
        )

    def test_source_review_remedy_must_be_protected(self) -> None:
        self.reject(
            lambda record: record["source_review_remedy"].update({"prospective_remedy_protected": False}),
            "source review remedy binding drift",
        )

    def test_source_review_remedy_workflows_must_succeed(self) -> None:
        self.reject(
            lambda record: record["source_review_remedy"].update({"all_post_merge_workflows_succeeded": False}),
            "source review remedy binding drift",
        )

    def test_holding_main_cannot_become_authority(self) -> None:
        self.reject(
            lambda record: record["destination"].update(
                {"holding_main_is_authority_source": True}
            ),
            "destination binding drift",
        )

    def test_destination_cannot_be_preactivated(self) -> None:
        self.reject(
            lambda record: record["destination"].update({"activation_state": "active"}),
            "destination binding drift",
        )

    def test_import_count_drift_rejected(self) -> None:
        self.reject(lambda record: record.update({"imported_artifact_count": 91}), "import count drift")

    def test_imported_blob_identity_drift_rejected(self) -> None:
        self.reject(
            lambda record: record["imported_artifacts"][0].update({"blob_sha": "0" * 40}),
            "artifact blob drift",
        )

    def test_imported_path_drift_rejected(self) -> None:
        self.reject(
            lambda record: record["imported_artifacts"][0].update(
                {"destination_path": "bootstrap/rewritten"}
            ),
            "import path drift",
        )

    def test_imported_mapping_digest_drift_rejected(self) -> None:
        self.reject(
            lambda record: record.update({"imported_mapping_sha256": "0" * 64}),
            "mapping digest drift",
        )

    def test_historical_defect_cannot_be_concealed(self) -> None:
        self.reject(
            lambda record: record["review_remedies"]["fixture_004"].update(
                {"historical_defect_preserved": False}
            ),
            "historical defect concealed",
        )

    def test_workflow_cannot_substitute_for_review(self) -> None:
        self.reject(
            lambda record: record["replay_contract"].update(
                {"workflow_success_is_review_substitute": True}
            ),
            "workflow substituted for review",
        )

    def test_offline_replay_cannot_be_relaxed(self) -> None:
        self.reject(
            lambda record: record["replay_contract"].update(
                {"network_after_provider_installation_allowed": True}
            ),
            "offline replay drift",
        )

    def test_source_merge_gate_cannot_be_removed(self) -> None:
        self.reject(
            lambda record: record["activation_contract"].update(
                {"source_protected_merge_required": False}
            ),
            "activation contract drift",
        )

    def test_two_sided_readback_cannot_be_removed(self) -> None:
        self.reject(
            lambda record: record["activation_contract"].update(
                {"two_sided_readback_required": False}
            ),
            "activation contract drift",
        )

    def test_fixture_006_cannot_begin(self) -> None:
        self.reject(
            lambda record: record["activation_contract"].update(
                {"fixture_006_may_begin": True}
            ),
            "activation contract drift",
        )

    def test_routine_human_reviewer_cannot_be_added(self) -> None:
        self.reject(
            lambda record: record["operating_authority"].update(
                {"mandatory_routine_reviewers": ["jimsteeg"]}
            ),
            "operating authority drift",
        )

    def test_recovery_owner_cannot_become_routine_merger(self) -> None:
        self.reject(
            lambda record: record["operating_authority"].update(
                {"recovery_owner_required_for_routine_merge": True}
            ),
            "operating authority drift",
        )

    def test_github_approval_cannot_substitute_for_steward_authorization(self) -> None:
        self.reject(
            lambda record: record["operating_authority"].update(
                {"github_approval_is_human_steward_authorization": True}
            ),
            "operating authority drift",
        )

    def test_agent_cannot_merge_own_work(self) -> None:
        self.reject(
            lambda record: record["operating_authority"].update(
                {"agent_may_merge_own_work": True}
            ),
            "operating authority drift",
        )

    def test_provider_admission_authority_rejected(self) -> None:
        self.reject(
            lambda record: record["authority_boundary"].update(
                {"providers_have_admission_authority": True}
            ),
            "authority boundary drift or escalation",
        )

    def test_import_cannot_create_authority(self) -> None:
        self.reject(
            lambda record: record["authority_boundary"].update(
                {"import_creates_new_bootstrap_authority": True}
            ),
            "authority boundary drift or escalation",
        )

    def test_claim_inflation_rejected(self) -> None:
        self.reject(
            lambda record: record["claim_boundary"].update(
                {"dataset_quality_certified": True}
            ),
            "claim boundary drift or inflation",
        )

    def test_claim_key_substitution_rejected(self) -> None:
        def substitute(record) -> None:
            del record["claim_boundary"]["canonical_record_selected"]
            record["claim_boundary"]["invented_claim"] = False

        self.reject(substitute, "claim boundary drift or inflation")

    def test_boolean_integer_substitution_rejected(self) -> None:
        self.reject(
            lambda record: record["operating_authority"].update({"agent_may_merge_own_work": 0}),
            "operating authority drift",
        )

    def test_duplicate_root_key_rejected(self) -> None:
        self.reject_duplicate('  "acceptance_id": "TC-REPO-ACCEPT-001",', '  "acceptance_id": "ESCALATED",')

    def test_duplicate_authority_key_rejected(self) -> None:
        self.reject_duplicate(
            '    "import_creates_new_bootstrap_authority": false,',
            '    "import_creates_new_bootstrap_authority": true,',
        )

    def test_precision_collision_rejected(self) -> None:
        self.reject_text_replacement(
            '    "issue_number": 70,',
            '    "issue_number": 70.000000000000000000000001,',
            "source review remedy binding drift",
        )

    def test_non_finite_number_rejected(self) -> None:
        self.reject_text_replacement(
            '    "issue_number": 70,',
            '    "issue_number": NaN,',
            "non-finite JSON number rejected",
        )

    def test_acceptance_record_digest_drift_rejected(self) -> None:
        self.reject(
            lambda record: record.update({"acceptance_record_sha256": "0" * 64}),
            "acceptance record digest drift",
        )


if __name__ == "__main__":
    unittest.main()
