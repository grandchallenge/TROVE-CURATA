"""Governed PII transformation contracts for TC-FIXTURE-003."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

FIXTURE_ID = "TC-FIXTURE-003"
SCHEMA_VERSION = "0.1.0"
PREDECESSOR = {
    "fixture_id": "TC-FIXTURE-002",
    "pull_request": 30,
    "exact_merged_head": "04fdb6bb3232be2d94cb197e19aa0deb333b0c97",
    "protected_merge": "b6a1511a7f1d7ca01108f57cede2982377ebd270",
}
PROVIDER_LOCK = {
    "presidio-anonymizer": "2.2.363",
    "presidio-analyzer": "2.2.363",
    "regex": "2026.7.19",
}
ROUTES = {"transformation_verified", "review_required"}
PLAN_STATES = {"authorized", "withheld"}
PLAN_STATUSES = {
    "accepted",
    "withheld",
    "rejected_stale_source",
    "rejected_observation_digest",
    "rejected_observation_identity",
    "rejected_duplicate_observation",
    "rejected_overlap",
    "rejected_operator",
    "rejected_parameters",
}
ALLOWED_OPERATORS = {"replace", "mask", "keep"}
REQUIRED_CASE_CLASSES = {
    "email_phone_replacement",
    "postal_network_masking",
    "multilingual_utf8",
    "negative_control",
    "code_math_control",
    "stale_source_rejection",
    "overlap_rejection",
    "operator_rejection",
    "provider_baseline_disagreement",
    "exact_duplicate",
    "policy_withheld",
    "partial_residual",
}
FALSE_CLAIMS = {
    "source_overwritten",
    "corpus_admitted",
    "source_deleted",
    "privacy_compliance_proved",
    "pii_absence_proved",
    "anonymity_proved",
    "legality_proved",
    "safety_proved",
    "fitness_for_training_proved",
    "production_release_authorized",
    "downstream_improvement_proved",
    "novelty_or_priority_claimed",
    "commercial_claim_authorized",
}


class TroveCurataTransformError(ValueError):
    """Raised when transformation authority, evidence, or claims drift."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataTransformError(message)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def content_id(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{sha256_bytes(canonical_json_bytes(value))}"


def provider_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution, expected in PROVIDER_LOCK.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise TroveCurataTransformError(f"required provider not installed: {distribution}=={expected}") from exc
        require(actual == expected, f"provider identity drift: {distribution}=={actual}, expected {expected}")
        versions[distribution] = actual
    return versions


def safe_relative_path(value: Any) -> str:
    require(isinstance(value, str) and value, "manifest path required")
    require("://" not in value, "network paths are prohibited")
    path = Path(value)
    require(not path.is_absolute(), "manifest paths must be relative")
    require(".." not in path.parts, "path traversal prohibited")
    return value


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataTransformError(f"unable to load fixture manifest: {exc}") from exc
    require(isinstance(manifest, dict), "manifest root must be an object")
    require(set(manifest) == {"schema_version", "fixture_id", "predecessor", "authority", "predecessor_manifest", "cases"}, "manifest field set drift")
    require(manifest["schema_version"] == SCHEMA_VERSION, "manifest schema drift")
    require(manifest["fixture_id"] == FIXTURE_ID, "manifest identity drift")
    require(manifest["predecessor"] == PREDECESSOR, "predecessor identity drift")
    require(manifest["predecessor_manifest"] == "../TC-FIXTURE-002/manifest.json", "predecessor manifest binding drift")
    require(
        manifest["authority"]
        == {
            "project_owner": "grandchallenge",
            "repository": "grandchallenge/INTELLECT",
            "plan_authority": "gcl_authored_static_manifest",
            "providers_may_select_spans": False,
            "providers_may_select_operators": False,
            "providers_may_authorize_routes": False,
            "source_records_immutable": True,
            "external_project_dependency": False,
            "aether_required": False,
        },
        "authority boundary drift",
    )
    cases = manifest["cases"]
    require(isinstance(cases, list) and cases, "fixture cases required")
    case_ids: set[str] = set()
    classes: set[str] = set()
    for case in cases:
        require(
            isinstance(case, dict)
            and set(case)
            == {
                "case_id",
                "case_class",
                "predecessor_case_id",
                "source_sha256",
                "canonical_observation_digest",
                "policy_state",
                "plan_state",
                "expected_plan_status",
                "expected_route",
                "expect_provider_disagreement",
                "expect_residual",
                "duplicate_group",
                "operations",
            },
            "case field set drift",
        )
        case_id = case["case_id"]
        require(isinstance(case_id, str) and case_id and case_id not in case_ids, "invalid or duplicate case_id")
        case_ids.add(case_id)
        require(case["case_class"] in REQUIRED_CASE_CLASSES, "unsupported case class")
        classes.add(case["case_class"])
        require(isinstance(case["predecessor_case_id"], str) and case["predecessor_case_id"], "predecessor case required")
        require(isinstance(case["source_sha256"], str) and len(case["source_sha256"]) == 64, "source digest required")
        require(isinstance(case["canonical_observation_digest"], str) and len(case["canonical_observation_digest"]) == 64, "observation digest required")
        require(case["policy_state"] in {"fixture_only", "review_required"}, "invalid policy state")
        require(case["plan_state"] in PLAN_STATES, "invalid plan state")
        require(case["expected_plan_status"] in PLAN_STATUSES, "invalid expected plan status")
        require(case["expected_route"] in ROUTES, "invalid expected route")
        require(isinstance(case["expect_provider_disagreement"], bool), "provider disagreement expectation must be boolean")
        require(isinstance(case["expect_residual"], bool), "residual expectation must be boolean")
        require(case["duplicate_group"] is None or isinstance(case["duplicate_group"], str), "invalid duplicate group")
        require(isinstance(case["operations"], list), "operations must be a list")
        for operation in case["operations"]:
            require(
                isinstance(operation, dict)
                and set(operation)
                == {"observation_id", "entity_type", "start_char", "end_char", "operator", "parameters"},
                "operation field set drift",
            )
            require(isinstance(operation["observation_id"], str) and operation["observation_id"], "observation identity required")
            require(isinstance(operation["entity_type"], str) and operation["entity_type"], "entity type required")
            require(isinstance(operation["start_char"], int) and isinstance(operation["end_char"], int), "character spans must be integers")
            require(isinstance(operation["operator"], str) and operation["operator"], "operator required")
            require(isinstance(operation["parameters"], dict), "operator parameters must be an object")
    require(classes == REQUIRED_CASE_CLASSES, "fixture class coverage drift")
    return manifest
