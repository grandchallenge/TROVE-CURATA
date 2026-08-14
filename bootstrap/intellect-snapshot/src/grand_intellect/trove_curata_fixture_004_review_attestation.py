"""Fail-closed validation for the TC-FIXTURE-004 final-head review remedy."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FALSE_CLAIMS = {
    "records_deleted",
    "records_suppressed",
    "canonical_member_selected",
    "corpus_admitted",
    "dataset_quality_proved",
    "equivalence_proved",
    "train_test_contamination_absent",
    "privacy_compliance_proved",
    "legality_proved",
    "fitness_for_training_proved",
    "production_release_authorized",
    "downstream_improvement_proved",
    "novelty_or_priority_claimed",
    "commercial_claim_authorized",
}

EXPECTED_SUBJECT = {
    "repository": "grandchallenge/INTELLECT",
    "work_package_id": "TC-FIXTURE-004",
    "issue_number": 48,
    "pull_request_number": 49,
    "author_account": "fyremael",
    "advertised_review_head": "7a88be479edc73d4b001e16047f4b199cbb89ae1",
    "stale_review": {
        "review_id": "PRR_kwDOTcUbys8AAAABIa9ueQ",
        "reviewer": "jimsteeg",
        "event": "APPROVED",
        "submitted_at": "2026-08-05T00:53:42Z",
    },
    "stale_disposition": {
        "comment_id": 5186276356,
        "author": "fyremael",
        "posted_at": "2026-08-05T00:54:28Z",
        "stated_head": "7a88be479edc73d4b001e16047f4b199cbb89ae1",
        "targeted_final_head": False,
    },
    "final_merged_head": "6dc65962ec77e17ae5bdd2c75ccd5da63aefcef7",
    "final_head_created_at": "2026-08-05T00:53:58Z",
    "final_head_commit_kind": "merge_main_into_topic",
    "protected_merge_commit": "6e2385a841dfd55bbab480d79a47611cc6557103",
    "merged_at": "2026-08-05T00:54:46Z",
    "historical_exact_head_review_satisfied": False,
    "historical_exact_head_disposition_satisfied": False,
}

EXPECTED_WORKFLOWS = [
    {"name": "CI", "run_id": 30964757745, "conclusion": "success"},
    {"name": "GCL conformance", "run_id": 30964758126, "conclusion": "success"},
    {"name": "TROVE-CURATA fixture", "run_id": 30964757686, "conclusion": "success"},
    {
        "name": "TROVE-CURATA duplicate fixture",
        "run_id": 30964757700,
        "conclusion": "success",
    },
]

EXPECTED_DEFECT = {
    "kind": "approval_and_disposition_target_pre_final_head",
    "review_preceded_final_head_seconds": 16,
    "disposition_followed_final_head_seconds": 30,
    "advertised_head_differs_from_final_head": True,
    "disposition_head_differs_from_final_head": True,
    "qualifying_exact_head_approval_count": 0,
    "qualifying_exact_head_disposition_count": 0,
    "historical_timeline_rewritten": False,
}

EXPECTED_REMEDY = {
    "historical_state_rewritten": False,
    "required_review_event": "APPROVED",
    "corrective_reviewer_must_be_non_author": True,
    "corrective_reviewer_must_be_maintainer": True,
    "review_must_target_corrective_pr_final_head": True,
    "comment_is_substitute": False,
    "reaction_is_substitute": False,
    "merge_action_is_substitute": False,
    "author_self_review_is_substitute": False,
    "protected_merge_required": True,
    "prospective_remediation_only": True,
    "fixture_005_blocked_until_remedy_merge": True,
}

EXPECTED_AUTHORITY = {
    "project_owner": "grandchallenge",
    "project_scope": "gcl_contained",
    "implementation_changed": False,
    "fixture_data_changed": False,
    "external_project_dependency": False,
    "aether_role": "future_projection_nonblocking",
}


class TroveCurataFixture004ReviewAttestationError(ValueError):
    """Raised when the historical defect or prospective remedy drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataFixture004ReviewAttestationError(message)


def _parse_utc(value: Any, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"{label} must be UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TroveCurataFixture004ReviewAttestationError(f"invalid {label}") from exc
    _require(parsed.tzinfo == timezone.utc, f"{label} must be UTC")
    return parsed


def validate_trove_curata_fixture_004_review_attestation(
    record: dict[str, Any],
) -> dict[str, Any]:
    """Validate exact PR #49 chronology, final-head evidence, and remedy semantics."""

    _require(
        set(record)
        == {
            "schema_version",
            "attestation_id",
            "status",
            "historical_subject",
            "final_head_evidence",
            "defect",
            "remedy_contract",
            "authority_boundary",
            "claim_boundary",
        },
        "attestation field set drift",
    )
    _require(record["schema_version"] == "0.1.0", "unsupported schema version")
    _require(
        record["attestation_id"] == "TC-FIXTURE-004-REVIEW-REMEDY-001",
        "attestation identity drift",
    )
    _require(record["status"] == "pending_independent_review", "invalid remedy status")

    subject = record["historical_subject"]
    _require(subject == EXPECTED_SUBJECT, "historical subject identity drift")

    review_at = _parse_utc(subject["stale_review"]["submitted_at"], "review time")
    final_head_at = _parse_utc(subject["final_head_created_at"], "final-head time")
    disposition_at = _parse_utc(
        subject["stale_disposition"]["posted_at"], "disposition time"
    )
    merged_at = _parse_utc(subject["merged_at"], "merge time")
    _require(
        review_at < final_head_at < disposition_at < merged_at,
        "historical chronology drift",
    )
    _require(
        int((final_head_at - review_at).total_seconds()) == 16,
        "stale-review interval drift",
    )
    _require(
        int((disposition_at - final_head_at).total_seconds()) == 30,
        "stale-disposition interval drift",
    )
    _require(
        subject["advertised_review_head"] != subject["final_merged_head"],
        "advertised and final heads must remain distinct",
    )
    _require(
        subject["stale_disposition"]["stated_head"] != subject["final_merged_head"],
        "disposition and final heads must remain distinct",
    )
    _require(
        subject["stale_disposition"]["stated_head"]
        == subject["advertised_review_head"],
        "review and disposition head identity drift",
    )

    evidence = record["final_head_evidence"]
    _require(
        set(evidence)
        == {
            "head_sha",
            "workflow_runs",
            "all_required_workflows_successful",
            "workflow_success_is_review_substitute",
        },
        "final-head evidence field set drift",
    )
    _require(
        evidence["head_sha"] == subject["final_merged_head"],
        "final-head evidence identity drift",
    )
    _require(
        evidence["workflow_runs"] == EXPECTED_WORKFLOWS,
        "final-head workflow evidence drift",
    )
    _require(
        evidence["all_required_workflows_successful"] is True,
        "final-head workflow state drift",
    )
    _require(
        evidence["workflow_success_is_review_substitute"] is False,
        "workflow substituted for review",
    )

    _require(record["defect"] == EXPECTED_DEFECT, "defect characterization drift")
    _require(record["remedy_contract"] == EXPECTED_REMEDY, "review remedy semantics drift")
    _require(record["authority_boundary"] == EXPECTED_AUTHORITY, "authority boundary drift")

    claims = record["claim_boundary"]
    _require(
        isinstance(claims, dict) and set(claims) == FALSE_CLAIMS,
        "claim boundary field set drift",
    )
    for claim in FALSE_CLAIMS:
        _require(claims[claim] is False, f"claim inflation: {claim}")

    return record


def load_and_validate_trove_curata_fixture_004_review_attestation(
    path: str | Path,
) -> dict[str, Any]:
    """Load and validate the versioned post-merge review attestation."""

    attestation_path = Path(path)
    try:
        record = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataFixture004ReviewAttestationError(
            f"unable to load attestation: {exc}"
        ) from exc
    _require(isinstance(record, dict), "attestation root must be an object")
    return validate_trove_curata_fixture_004_review_attestation(record)
