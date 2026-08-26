"""Fail-closed validation for the TC-FIXTURE-003 final-head review remedy."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FALSE_CLAIMS = {
    "corpus_admitted",
    "deletion_authorized",
    "anonymity_proved",
    "privacy_compliance_proved",
    "legality_proved",
    "safety_proved",
    "fitness_for_training_proved",
    "production_release_qualified",
    "downstream_improvement_proved",
    "novelty_or_priority_claimed",
    "commercial_claim_authorized",
}

EXPECTED_WORKFLOWS = [
    {"name": "CI", "run_id": 30880451010, "conclusion": "success"},
    {"name": "GCL conformance", "run_id": 30880451499, "conclusion": "success"},
    {"name": "TROVE-CURATA fixture", "run_id": 30880450978, "conclusion": "success"},
    {
        "name": "TROVE-CURATA transformation fixture",
        "run_id": 30880450995,
        "conclusion": "success",
    },
]


class TroveCurataFixture003ReviewAttestationError(ValueError):
    """Raised when the historical defect or prospective remedy drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataFixture003ReviewAttestationError(message)


def _parse_utc(value: Any, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"{label} must be UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TroveCurataFixture003ReviewAttestationError(f"invalid {label}") from exc
    _require(parsed.tzinfo == timezone.utc, f"{label} must be UTC")
    return parsed


def validate_trove_curata_fixture_003_review_attestation(record: dict[str, Any]) -> dict[str, Any]:
    """Validate exact PR #44 chronology, final-head evidence, and remedy semantics."""

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
        record["attestation_id"] == "TC-FIXTURE-003-REVIEW-REMEDY-001",
        "attestation identity drift",
    )
    _require(record["status"] == "pending_independent_review", "invalid remedy status")

    subject = record["historical_subject"]
    expected_subject = {
        "repository": "grandchallenge/INTELLECT",
        "work_package_id": "TC-FIXTURE-003",
        "issue_number": 31,
        "pull_request_number": 44,
        "author_account": "fyremael",
        "advertised_review_head": "c312bff71e9d9269de8abd52e85ae33f4a775571",
        "stale_review": {
            "review_id": "PRR_kwDOTcUbys8AAAABISLRyQ",
            "reviewer": "jimsteeg",
            "event": "APPROVED",
            "submitted_at": "2026-08-04T05:21:36Z",
        },
        "final_merged_head": "af5a568a2f49db949ff5c355f33ab29231cabac4",
        "final_head_created_at": "2026-08-04T05:21:42Z",
        "final_head_commit_kind": "merge_main_into_topic",
        "protected_merge_commit": "0096eb21ca62c5ef7f6e458f358edcb1cd963a20",
        "merged_at": "2026-08-04T05:22:36Z",
        "historical_exact_head_review_satisfied": False,
    }
    _require(subject == expected_subject, "historical subject identity drift")

    review_at = _parse_utc(subject["stale_review"]["submitted_at"], "review time")
    final_head_at = _parse_utc(subject["final_head_created_at"], "final-head time")
    merged_at = _parse_utc(subject["merged_at"], "merge time")
    _require(review_at < final_head_at < merged_at, "historical chronology drift")
    _require(int((final_head_at - review_at).total_seconds()) == 6, "stale-review interval drift")
    _require(
        subject["advertised_review_head"] != subject["final_merged_head"],
        "advertised and final heads must remain distinct",
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
    _require(evidence["head_sha"] == subject["final_merged_head"], "final-head evidence identity drift")
    _require(evidence["workflow_runs"] == EXPECTED_WORKFLOWS, "final-head workflow evidence drift")
    _require(evidence["all_required_workflows_successful"] is True, "final-head workflow state drift")
    _require(evidence["workflow_success_is_review_substitute"] is False, "workflow substituted for review")

    defect = record["defect"]
    _require(
        defect
        == {
            "kind": "approval_preceded_final_head",
            "review_preceded_final_head_seconds": 6,
            "advertised_head_differs_from_final_head": True,
            "qualifying_exact_head_approval_count": 0,
            "historical_timeline_rewritten": False,
        },
        "defect characterization drift",
    )

    remedy = record["remedy_contract"]
    _require(
        remedy
        == {
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
            "fixture_004_blocked_until_remedy_merge": True,
        },
        "review remedy semantics drift",
    )

    _require(
        record["authority_boundary"]
        == {
            "project_owner": "grandchallenge",
            "project_scope": "gcl_contained",
            "implementation_changed": False,
            "external_project_dependency": False,
            "aether_role": "future_projection_nonblocking",
        },
        "authority boundary drift",
    )

    claims = record["claim_boundary"]
    _require(isinstance(claims, dict) and set(claims) == FALSE_CLAIMS, "claim boundary field set drift")
    for claim in FALSE_CLAIMS:
        _require(claims[claim] is False, f"claim inflation: {claim}")

    return record


def load_and_validate_trove_curata_fixture_003_review_attestation(path: str | Path) -> dict[str, Any]:
    """Load and validate the versioned post-merge review attestation."""

    attestation_path = Path(path)
    try:
        record = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataFixture003ReviewAttestationError(f"unable to load attestation: {exc}") from exc
    _require(isinstance(record, dict), "attestation root must be an object")
    return validate_trove_curata_fixture_003_review_attestation(record)
