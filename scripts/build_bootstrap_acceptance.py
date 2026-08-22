#!/usr/bin/env python3
"""Build TC-REPO-ACCEPT-001 from the bound INTELLECT closure record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CLOSURE = ROOT / "governance" / "source" / "TC-BOOTSTRAP-CLOSE-001.json"
SNAPSHOT = ROOT / "bootstrap" / "intellect-snapshot"
OUTPUT = ROOT / "governance" / "trove_curata_repo_acceptance.json"


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def load_source_closure() -> dict[str, object]:
    raw = SOURCE_CLOSURE.read_bytes()
    record = json.loads(raw)
    subject = dict(record)
    supplied = subject.pop("closure_record_sha256")
    if canonical_digest(subject) != supplied:
        raise RuntimeError("source closure canonical digest mismatch")
    if supplied != "ec871730221523a55e09c81b7e81d785284e4b181ec84ac65480962c9f8dee27":
        raise RuntimeError("source closure identity drift")
    if hashlib.sha256(raw).hexdigest() != "ec55bb8fe7b8235d880bea80995dbcffa2520c047b758363e7afe90c33802653":
        raise RuntimeError("source closure file digest drift")
    if git_blob_sha(raw) != "ebb2e6c470748bb58daed0eff0b9af1e553c9c1a":
        raise RuntimeError("source closure blob identity drift")
    return record


def build_record() -> dict[str, object]:
    closure = load_source_closure()
    imported: list[dict[str, object]] = []
    for source in closure["artifact_inventory"]:
        source_path = str(source["path"])
        destination_path = f"bootstrap/intellect-snapshot/{source_path}"
        path = ROOT / destination_path
        data = path.read_bytes()
        observed_sha = git_blob_sha(data)
        if observed_sha != source["blob_sha"]:
            raise RuntimeError(f"blob mismatch: {source_path}")
        if len(data) != source["size"]:
            raise RuntimeError(f"size mismatch: {source_path}")
        imported.append(
            {
                "source_path": source_path,
                "destination_path": destination_path,
                "blob_sha": observed_sha,
                "size": len(data),
            }
        )

    record: dict[str, object] = {
        "schema_version": "0.2.0",
        "acceptance_id": "TC-REPO-ACCEPT-001",
        "status": "prepared_pending_destination_protected_merge_and_two_sided_readback",
        "source": {
            "repository": "grandchallenge/INTELLECT",
            "issue_number": 68,
            "pull_request_number": 69,
            "candidate_head": "d587996f71a38aeb8ce4a0c667da1a8350b7f153",
            "candidate_tree": "27539df4924775abf5a841b7591aaaa38223d672",
            "protected_snapshot_head": closure["source"]["protected_head_at_preparation"],
            "protected_snapshot_tree": closure["source"]["protected_tree_at_preparation"],
            "protected_source_closure_merge": "041f7d9b1c85e157a651bcf3edf07c7499185b00",
            "source_closure_status": "protected",
            "closure_record_canonical_sha256": closure["closure_record_sha256"],
            "closure_record_file_sha256": "ec55bb8fe7b8235d880bea80995dbcffa2520c047b758363e7afe90c33802653",
            "closure_record_blob_sha": "ebb2e6c470748bb58daed0eff0b9af1e553c9c1a",
            "artifact_inventory_sha256": closure["artifact_inventory_sha256"],
        },
        "destination": {
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
        "imported_artifact_count": len(imported),
        "imported_artifacts": imported,
        "imported_mapping_sha256": canonical_digest(imported),
        "bootstrap_roots": closure["bootstrap_roots"],
        "review_remedies": closure["review_remedies"],
        "replay_contract": {
            "fixtures": [f"TC-FIXTURE-00{index}" for index in range(1, 6)],
            "expected_report_sha256": {
                "TC-FIXTURE-001": "796da735806ecdeb84e83481c9b0dfed187b1fc0d68054744284839e6180e091",
                "TC-FIXTURE-002": "e31946855b4c3f67e43277586adce337716642e5a9b6bd37244b63b678ca1d58",
                "TC-FIXTURE-003": "f3b52e9ffe77f27bf37355f31a441e7096c9bf2b4684db4aae5b440580aac4d5",
                "TC-FIXTURE-004": "e54958a4e09b536795dde271486d4f32212f80c3168abb0b7b788ec52323ea13",
                "TC-FIXTURE-005": "2b6633a0174c57953637ad53b3c92e213d9a688180df8e0f0a13ac6486fbcae4",
            },
            "pinned_providers_required": True,
            "network_after_provider_installation_allowed": False,
            "two_fixture_005_replays_required": True,
            "byte_identical_fixture_005_reports_required": True,
            "workflow_success_is_review_substitute": False,
        },
        "activation_contract": {
            "review_tier": "T3",
            "source_protected_merge_required": True,
            "destination_protected_merge_required": True,
            "two_sided_readback_required": True,
            "source_and_destination_records_must_cross_bind": True,
            "activation_created_by_this_record": False,
            "fixture_006_may_begin": False,
        },
        "operating_authority": {
            "repository": "grandchallenge/INTELLECT",
            "protected_head": "041f7d9b1c85e157a651bcf3edf07c7499185b00",
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
        "authority_boundary": {
            "project_owner": "grandchallenge",
            "gcl_contained": True,
            "providers_have_policy_authority": False,
            "providers_have_admission_authority": False,
            "metrics_have_admission_authority": False,
            "passports_have_admission_authority": False,
            "manifests_have_adjudication_authority": False,
            "import_creates_new_bootstrap_authority": False,
            "holding_main_creates_authority": False,
            "aether_role": "future_projection_nonblocking",
        },
        "claim_boundary": {
            "production_corpus_admitted": False,
            "records_ranked": False,
            "records_admitted": False,
            "records_rejected": False,
            "records_retained_by_authority": False,
            "records_deleted": False,
            "records_suppressed": False,
            "canonical_record_selected": False,
            "dataset_quality_certified": False,
            "privacy_certified": False,
            "legality_or_rights_certified": False,
            "reference_contamination_absence_proved": False,
            "training_fitness_qualified": False,
            "release_candidate_declared": False,
            "public_release_authorized": False,
            "downstream_improvement_proved": False,
            "novelty_or_priority_claimed": False,
            "commercial_claim_authorized": False,
        },
    }
    record["acceptance_record_sha256"] = canonical_digest(record)
    return record


def main() -> int:
    record = build_record()
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(record["imported_mapping_sha256"])
    print(record["acceptance_record_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
