#!/usr/bin/env python3
"""Fail-closed validator for TC-REPO-ACCEPT-001."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MAPPING_SHA256 = "52a5c0d534d281ff8c562a6f8ca2321e337d183e868ad328a87eec6605fe0b45"
EXPECTED_RECORD_SHA256 = "2e4cf8154451b598c7bddeb27ff43d1acdf77bd77561d7fd7128dcb5ee0a1526"
EXPECTED_SOURCE_CLOSURE_CANONICAL_SHA256 = "ec871730221523a55e09c81b7e81d785284e4b181ec84ac65480962c9f8dee27"

ROOT_FIELDS = {
    "schema_version",
    "acceptance_id",
    "status",
    "source",
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


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def validate_bootstrap_acceptance(record: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    require(set(record) == ROOT_FIELDS, "acceptance field set drift")
    require(record["schema_version"] == "0.2.0", "schema version drift")
    require(record["acceptance_id"] == "TC-REPO-ACCEPT-001", "acceptance identity drift")
    require(
        record["status"] == "prepared_pending_destination_protected_merge_and_two_sided_readback",
        "acceptance status drift",
    )

    source = record["source"]
    require(
        source
        == {
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
        "source binding drift",
    )

    destination = record["destination"]
    require(
        destination
        == {
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
        replay["expected_report_sha256"]
        == {
            "TC-FIXTURE-001": "796da735806ecdeb84e83481c9b0dfed187b1fc0d68054744284839e6180e091",
            "TC-FIXTURE-002": "e31946855b4c3f67e43277586adce337716642e5a9b6bd37244b63b678ca1d58",
            "TC-FIXTURE-003": "f3b52e9ffe77f27bf37355f31a441e7096c9bf2b4684db4aae5b440580aac4d5",
            "TC-FIXTURE-004": "e54958a4e09b536795dde271486d4f32212f80c3168abb0b7b788ec52323ea13",
            "TC-FIXTURE-005": "2b6633a0174c57953637ad53b3c92e213d9a688180df8e0f0a13ac6486fbcae4",
        },
        "replay report identity drift",
    )
    require(replay["pinned_providers_required"] is True, "provider pinning disabled")
    require(replay["network_after_provider_installation_allowed"] is False, "offline replay drift")
    require(replay["two_fixture_005_replays_required"] is True, "deterministic replay disabled")
    require(replay["byte_identical_fixture_005_reports_required"] is True, "report equality disabled")
    require(replay["workflow_success_is_review_substitute"] is False, "workflow substituted for review")

    activation = record["activation_contract"]
    require(activation["review_tier"] == "T3", "review tier drift")
    for key in {
        "source_protected_merge_required",
        "destination_protected_merge_required",
        "two_sided_readback_required",
        "source_and_destination_records_must_cross_bind",
    }:
        require(activation[key] is True, "activation safeguard disabled")
    require(activation["activation_created_by_this_record"] is False, "premature activation")
    require(activation["fixture_006_may_begin"] is False, "premature fixture 006 authority")

    operating = record["operating_authority"]
    require(
        operating
        == {
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
        "operating authority drift",
    )

    authority = record["authority_boundary"]
    require(
        authority["project_owner"] == "grandchallenge"
        and authority["gcl_contained"] is True
        and authority["aether_role"] == "future_projection_nonblocking",
        "authority identity drift",
    )
    for key, value in authority.items():
        if key not in {"project_owner", "gcl_contained", "aether_role"}:
            require(value is False, "authority escalation")

    claims = record["claim_boundary"]
    require(isinstance(claims, dict) and len(claims) == 18, "claim boundary field set drift")
    require(all(value is False for value in claims.values()), "claim inflation")

    subject = dict(record)
    supplied = subject.pop("acceptance_record_sha256")
    require(
        canonical_digest(subject) == supplied == EXPECTED_RECORD_SHA256,
        "acceptance record digest drift",
    )
    return record


def load_and_validate(path: str | Path, root: Path = ROOT) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
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
