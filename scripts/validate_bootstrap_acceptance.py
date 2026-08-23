#!/usr/bin/env python3
"""Fail-closed validator for TC-REPO-ACCEPT-001."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MAPPING_SHA256 = "52a5c0d534d281ff8c562a6f8ca2321e337d183e868ad328a87eec6605fe0b45"
EXPECTED_RECORD_SHA256 = "c12e23d789d0f6e58d3b6dff17662c0d61d21794b4e997f56e888bfe7f32ddf7"
EXPECTED_SOURCE_CLOSURE_CANONICAL_SHA256 = "ec871730221523a55e09c81b7e81d785284e4b181ec84ac65480962c9f8dee27"

ROOT_FIELDS = {
    "schema_version",
    "acceptance_id",
    "status",
    "source",
    "source_review_remedy",
    "destination",
    "imported_artifact_count",
    "imported_artifacts",
    "imported_mapping_sha256",
    "bootstrap_roots",
    "review_remedies",
    "replay_contract",
    "activation_contract",
    "operating_authority",
    "authority_boundary",
    "claim_boundary",
    "acceptance_record_sha256",
}


class BootstrapAcceptanceError(ValueError):
    """Raised when source equivalence or inactive authority boundaries drift."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BootstrapAcceptanceError(message)


def exact_json_equal(actual: Any, expected: Any) -> bool:
    """Compare parsed JSON values with strict booleans and exact numbers."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is bool and type(expected) is bool and actual is expected
    if isinstance(actual, (int, float, Decimal)) and isinstance(expected, (int, float, Decimal)):
        return Decimal(str(actual)) == Decimal(str(expected))
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return set(actual) == set(expected) and all(
            exact_json_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            exact_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    return actual == expected


def normalize_json_numbers(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        require(value.is_finite(), "non-finite JSON number rejected")
        if value == value.to_integral_value():
            return int(value)
        return value
    if isinstance(value, float):
        decimal_value = Decimal(str(value))
        require(decimal_value.is_finite(), "non-finite JSON number rejected")
        if decimal_value == decimal_value.to_integral_value():
            return int(decimal_value)
        return value
    if isinstance(value, dict):
        return {key: normalize_json_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_json_numbers(item) for item in value]
    return value


def reject_duplicate_json_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def reject_non_finite_json_constant(token: str) -> None:
    raise BootstrapAcceptanceError(f"non-finite JSON number rejected: {token}")


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        normalize_json_numbers(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def validate_bootstrap_acceptance(record: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    require(set(record) == ROOT_FIELDS, "acceptance field set drift")
    require(record["schema_version"] == "0.3.0", "schema version drift")
    require(record["acceptance_id"] == "TC-REPO-ACCEPT-001", "acceptance identity drift")
    require(
        record["status"] == "prepared_pending_destination_protected_merge_and_two_sided_readback",
        "acceptance status drift",
    )

    source = record["source"]
    require(
        exact_json_equal(
            source,
            {
            "repository": "grandchallenge/INTELLECT",
            "issue_number": 68,
            "pull_request_number": 69,
            "candidate_head": "d587996f71a38aeb8ce4a0c667da1a8350b7f153",
            "candidate_tree": "27539df4924775abf5a841b7591aaaa38223d672",
            "protected_snapshot_head": "8c3da17b2c401944e43b6e9bb0fae3bc95b05624",
            "protected_snapshot_tree": "9d1f2d2b821a3398e8895b75f8badebc2fb6a059",
            "protected_source_closure_merge": "041f7d9b1c85e157a651bcf3edf07c7499185b00",
            "source_closure_status": "protected",
            "closure_record_canonical_sha256": EXPECTED_SOURCE_CLOSURE_CANONICAL_SHA256,
            "closure_record_file_sha256": "ec55bb8fe7b8235d880bea80995dbcffa2520c047b758363e7afe90c33802653",
            "closure_record_blob_sha": "ebb2e6c470748bb58daed0eff0b9af1e553c9c1a",
            "artifact_inventory_sha256": "ad2803363071e7402cdaa48b3d39062a0efcaac2e53eac69ab76a93001484d6d",
            },
        ),
        "source binding drift",
    )

    require(
        exact_json_equal(
            record["source_review_remedy"],
            {
                "repository": "grandchallenge/INTELLECT",
                "issue_number": 70,
                "pull_request_number": 71,
                "remedy_id": "TC-BOOTSTRAP-CLOSE-001-T3-REVIEW-REMEDY-001",
                "protected_predecessor": "041f7d9b1c85e157a651bcf3edf07c7499185b00",
                "candidate_head": "27930e1cc4d2c2de1e35c8b143e51651a71a9fb6",
                "candidate_tree": "21fc40b033aae1513d90945bc1667afaaf8cc937",
                "protected_merge": "08a3044e0363fa932012fa642ea15d9153ba876b",
                "protected_merge_tree": "21fc40b033aae1513d90945bc1667afaaf8cc937",
                "protected_merge_second_parent_is_authorized_candidate": True,
                "protected_main_readback": True,
                "historical_t3_gate_satisfied": False,
                "github_merged_by": "fyremael",
                "github_merged_by_is_executor_session_identity": False,
                "prospective_remedy_protected": True,
                "mechanical_executor_non_author": True,
                "mechanical_executor_receipt_url": "https://github.com/grandchallenge/INTELLECT/pull/71#issuecomment-5383546879",
                "mechanical_executor_session": "01a02c12-1dd9-7e32-a30a-cdf4a82bb609",
                "remedy_record_path": "governance/trove_curata_bootstrap_close_001_t3_review_remedy.json",
                "remedy_record_blob_sha": "ac7dadc7db8f1d7ee78dd906bba864a069df1751",
                "schema_path": "schemas/trove_curata_bootstrap_close_001_t3_review_remedy.schema.json",
                "schema_blob_sha": "0cebe69633d7c558a1048956d11f513fd367ad71",
                "validator_path": "src/grand_intellect/trove_curata_bootstrap_close_001_t3_review_remedy.py",
                "validator_blob_sha": "fadb30ce872d1c7c6cd9f1bc2dfea80a6c91c97f",
                "tests_path": "tests/test_trove_curata_bootstrap_close_001_t3_review_remedy.py",
                "tests_blob_sha": "3bc06851d4a6ba1552814dec338a616ea2b9d970",
                "documentation_path": "docs/TC_BOOTSTRAP_CLOSE_001_T3_REVIEW_REMEDY_001.md",
                "documentation_blob_sha": "5b31e0f752779f8adba8b8e79e9ffa6215944183",
                "adversary_comment_url": "https://github.com/grandchallenge/INTELLECT/pull/71#issuecomment-5383175234",
                "referee_comment_url": "https://github.com/grandchallenge/INTELLECT/pull/71#issuecomment-5383175345",
                "human_steward_disposition_url": "https://github.com/grandchallenge/INTELLECT/pull/71#issuecomment-5383424656",
                "post_merge_workflow_runs": {
                    "gcl_conformance": "32608640194",
                    "ci": "32608639842",
                    "trove_curata_bootstrap_closure": "32608639805",
                    "codeql": "32608639720",
                },
                "all_post_merge_workflows_succeeded": True,
            },
        ),
        "source review remedy binding drift",
    )

    destination = record["destination"]
    require(
        exact_json_equal(
            destination,
            {
            "repository": "grandchallenge/TROVE-CURATA",
            "issue_number": 1,
            "expected_pull_request_number": 1,
            "holding_main_head": "f9e5dafbda1c409fd416daca46a2f197b5e59034",
            "holding_main_is_authority_source": False,
            "candidate_branch": "agent/tc-repo-accept-001",
            "visibility": "public",
            "activation_state": "not_active",
            "canonical_from": "TC-FIXTURE-006",
            },
        ),
        "destination binding drift",
    )

    imported = record["imported_artifacts"]
    require(record["imported_artifact_count"] == len(imported) == 92, "import count drift")
    require(
        [entry["source_path"] for entry in imported]
        == sorted(entry["source_path"] for entry in imported),
        "import ordering drift",
    )
    for entry in imported:
        require(
            set(entry) == {"source_path", "destination_path", "blob_sha", "size"},
            "import field set drift",
        )
        require(
            entry["destination_path"]
            == f"bootstrap/intellect-snapshot/{entry['source_path']}",
            "import path drift",
        )
        require(bool(re.fullmatch(r"[0-9a-f]{40}", entry["blob_sha"])), "import blob identity drift")
        path = root / entry["destination_path"]
        require(path.is_file(), "imported artifact missing")
        data = path.read_bytes()
        require(len(data) == entry["size"], "imported artifact size drift")
        require(git_blob_sha(data) == entry["blob_sha"], "imported artifact blob drift")

    require(
        canonical_digest(imported)
        == record["imported_mapping_sha256"]
        == EXPECTED_MAPPING_SHA256,
        "imported mapping digest drift",
    )
    require(
        set(record["bootstrap_roots"])
        == {"fixtures/trove_curata", "schemas", "workflows"}
        and all(
            re.fullmatch(r"[0-9a-f]{40}", value)
            for value in record["bootstrap_roots"].values()
        ),
        "bootstrap root drift",
    )
    for remedy in record["review_remedies"].values():
        require(remedy["historical_defect_preserved"] is True, "historical defect concealed")
        require(remedy["historical_state_rewritten"] is False, "historical state rewritten")

    replay = record["replay_contract"]
    require(replay["fixtures"] == [f"TC-FIXTURE-00{i}" for i in range(1, 6)], "replay ladder drift")
    require(
        exact_json_equal(
            replay["expected_report_sha256"],
            {
            "TC-FIXTURE-001": "796da735806ecdeb84e83481c9b0dfed187b1fc0d68054744284839e6180e091",
            "TC-FIXTURE-002": "e31946855b4c3f67e43277586adce337716642e5a9b6bd37244b63b678ca1d58",
            "TC-FIXTURE-003": "f3b52e9ffe77f27bf37355f31a441e7096c9bf2b4684db4aae5b440580aac4d5",
            "TC-FIXTURE-004": "e54958a4e09b536795dde271486d4f32212f80c3168abb0b7b788ec52323ea13",
            "TC-FIXTURE-005": "2b6633a0174c57953637ad53b3c92e213d9a688180df8e0f0a13ac6486fbcae4",
            },
        ),
        "replay report identity drift",
    )
    require(replay["pinned_providers_required"] is True, "provider pinning disabled")
    require(replay["network_after_provider_installation_allowed"] is False, "offline replay drift")
    require(replay["two_fixture_005_replays_required"] is True, "deterministic replay disabled")
    require(replay["byte_identical_fixture_005_reports_required"] is True, "report equality disabled")
    require(replay["workflow_success_is_review_substitute"] is False, "workflow substituted for review")

    activation = record["activation_contract"]
    require(
        exact_json_equal(
            activation,
            {
                "review_tier": "T3",
                "source_protected_merge_required": True,
                "destination_protected_merge_required": True,
                "two_sided_readback_required": True,
                "source_and_destination_records_must_cross_bind": True,
                "activation_created_by_this_record": False,
                "fixture_006_may_begin": False,
            },
        ),
        "activation contract drift",
    )

    operating = record["operating_authority"]
    require(
        exact_json_equal(
            operating,
            {
            "repository": "grandchallenge/INTELLECT",
            "protected_head": "08a3044e0363fa932012fa642ea15d9153ba876b",
            "schedule_path": "governance/constitutional_authority_schedule.json",
            "schedule_blob_sha": "6f66ed27ed7ff2889e4dd67c34973c8fa2f798a8",
            "schedule_schema_version": "1.5.0",
            "directive_id": "GI-STEWARD-0002",
            "directive_path": "governance/steward_directives/GI-STEWARD-0002.md",
            "directive_blob_sha": "9c70ad6b9c0100ab571a59605de0531c23cd25d6",
            "ordinary_human_steward": "fyremael",
            "recovery_owner": "jimsteeg",
            "mandatory_routine_reviewers": [],
            "human_actions_per_governed_decision_target": 1,
            "non_author_agent_adversary_required": True,
            "distinct_non_author_agent_referee_required": True,
            "distinct_agent_sessions_required": True,
            "github_approval_is_human_steward_authorization": False,
            "mechanical_merge_is_human_steward_authorization": False,
            "recovery_owner_required_for_routine_merge": False,
            "agent_may_merge_own_work": False,
            },
        ),
        "operating authority drift",
    )

    authority = record["authority_boundary"]
    require(
        exact_json_equal(
            authority,
            {
                "project_owner": "grandchallenge",
                "gcl_contained": True,
                "aether_role": "future_projection_nonblocking",
                "holding_main_creates_authority": False,
                "import_creates_new_bootstrap_authority": False,
                "manifests_have_adjudication_authority": False,
                "metrics_have_admission_authority": False,
                "passports_have_admission_authority": False,
                "providers_have_admission_authority": False,
                "providers_have_policy_authority": False,
            },
        ),
        "authority boundary drift or escalation",
    )

    claims = record["claim_boundary"]
    require(
        exact_json_equal(
            claims,
            {
                "canonical_record_selected": False,
                "commercial_claim_authorized": False,
                "dataset_quality_certified": False,
                "downstream_improvement_proved": False,
                "legality_or_rights_certified": False,
                "novelty_or_priority_claimed": False,
                "privacy_certified": False,
                "production_corpus_admitted": False,
                "public_release_authorized": False,
                "records_admitted": False,
                "records_deleted": False,
                "records_ranked": False,
                "records_rejected": False,
                "records_retained_by_authority": False,
                "records_suppressed": False,
                "reference_contamination_absence_proved": False,
                "release_candidate_declared": False,
                "training_fitness_qualified": False,
            },
        ),
        "claim boundary drift or inflation",
    )

    subject = dict(record)
    supplied = subject.pop("acceptance_record_sha256")
    require(
        canonical_digest(subject) == supplied == EXPECTED_RECORD_SHA256,
        "acceptance record digest drift",
    )
    return record


def load_and_validate(path: str | Path, root: Path = ROOT) -> dict[str, Any]:
    record = json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_object_pairs,
        parse_float=Decimal,
        parse_constant=reject_non_finite_json_constant,
    )
    require(isinstance(record, dict), "acceptance record must be an object")
    return validate_bootstrap_acceptance(record, root)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: validate_bootstrap_acceptance.py RECORD")
    record = load_and_validate(args[0])
    print(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
