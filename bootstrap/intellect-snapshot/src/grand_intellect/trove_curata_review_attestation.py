"""Fail-closed validation for TROVE-CURATA retrospective review remediation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FALSE_CLAIMS = {
    "dataset_quality_proved",
    "privacy_proved",
    "legality_proved",
    "safety_proved",
    "fitness_for_training_proved",
    "downstream_improvement_proved",
    "novelty_or_priority_claimed",
    "commercial_claim_authorized",
}


class TroveCurataReviewAttestationError(ValueError):
    """Raised when retrospective review evidence is incomplete or inflated."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataReviewAttestationError(message)


def validate_trove_curata_review_attestation(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the immutable historical subject and prospective remedy contract."""

    _require(record.get("schema_version") == "0.1.0", "unsupported schema version")
    _require(
        record.get("attestation_id") == "TROVE-CURATA-REVIEW-REMEDY-001",
        "attestation identity drift",
    )
    _require(record.get("status") == "pending_independent_review", "invalid remedy status")

    subject = record.get("historical_subject")
    _require(isinstance(subject, dict), "historical subject required")
    expected_subject = {
        "repository": "grandchallenge/INTELLECT",
        "work_package_id": "TROVE-CURATA-XREF-WP00",
        "pull_request_number": 24,
        "author_account": "fyremael",
        "exact_merged_head": "b6158a995a97ae58abfe139925de4ec6c9cd0a0b",
        "protected_merge_commit": "e080192f3c4cb1881cf781572dd1246b22792163",
        "exact_head_ci_run": 30710145476,
        "exact_head_conformance_run": 30710145683,
        "submitted_review_count": 0,
        "historically_reviewed": False,
    }
    _require(subject == expected_subject, "historical subject identity drift")

    remedy = record.get("remedy_contract")
    _require(isinstance(remedy, dict), "remedy contract required")
    expected_remedy = {
        "historical_state_rewritten": False,
        "required_review_event": "APPROVED",
        "reviewer_must_be_non_author": True,
        "reviewer_must_be_maintainer": True,
        "review_must_target_final_head": True,
        "comment_is_substitute": False,
        "reaction_is_substitute": False,
        "merge_action_is_substitute": False,
        "author_self_review_is_substitute": False,
        "protected_merge_required": True,
        "prospective_remediation_only": True,
    }
    _require(remedy == expected_remedy, "review remedy semantics drift")

    authority = record.get("authority_boundary")
    _require(
        authority
        == {
            "project_owner": "grandchallenge",
            "project_scope": "gcl_contained",
            "external_project_dependency": False,
            "aether_role": "future_projection_nonblocking",
        },
        "authority boundary drift",
    )

    claims = record.get("claim_boundary")
    _require(isinstance(claims, dict), "claim boundary required")
    _require(set(claims) == FALSE_CLAIMS, "claim boundary field set drift")
    for claim in FALSE_CLAIMS:
        _require(claims.get(claim) is False, f"claim inflation: {claim}")

    return record


def load_and_validate_trove_curata_review_attestation(path: str | Path) -> dict[str, Any]:
    """Load and validate a retrospective review attestation from disk."""

    attestation_path = Path(path)
    try:
        record = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataReviewAttestationError(f"unable to load attestation: {exc}") from exc
    _require(isinstance(record, dict), "attestation root must be an object")
    return validate_trove_curata_review_attestation(record)
