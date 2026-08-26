"""Governed PII-observation and policy-routing fixture for TROVE-CURATA."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


FIXTURE_ID = "TC-FIXTURE-002"
SCHEMA_VERSION = "0.1.0"
PREDECESSOR = {
    "fixture_id": "TC-FIXTURE-001",
    "pull_request": 28,
    "exact_merged_head": "e8d12e6f314ddabcf3a36f9ec49216b669d07024",
    "protected_merge": "59b34a195aa7d4fdd381d428dab3e4f18e2016e7",
}
PROVIDER_LOCK = {"presidio-analyzer": "2.2.363", "regex": "2026.7.19"}
REQUIRED_CASE_CLASSES = {
    "negative_control",
    "synthetic_email_phone",
    "synthetic_postal_network",
    "name_location_ambiguity",
    "multilingual_observation",
    "code_math_negative",
    "overlapping_spans",
    "provider_rules_disagreement",
    "exact_duplicate",
    "policy_review_without_pii",
}
ROUTES = {"observation_clear", "review_required"}
FALSE_CLAIMS = {
    "redaction_performed",
    "anonymization_performed",
    "deletion_performed",
    "corpus_admitted",
    "privacy_compliance_proved",
    "pii_absence_proved",
    "legality_proved",
    "safety_proved",
    "fitness_for_training_proved",
    "downstream_improvement_proved",
    "novelty_or_priority_claimed",
    "commercial_claim_authorized",
}

PRESIDIO_RULES = {
    "presidio-email-v1": {
        "entity_type": "EMAIL_ADDRESS",
        "regex": r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+(?![\w-]|\.[\w])",
        "score": "0.900000",
    },
    "presidio-phone-na-v1": {
        "entity_type": "PHONE_NUMBER",
        "regex": r"(?<!\w)(?:\+1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)",
        "score": "0.850000",
    },
    "presidio-ipv4-v1": {
        "entity_type": "IP_ADDRESS",
        "regex": r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d|\.\d)",
        "score": "0.900000",
    },
    "presidio-ca-postal-v1": {
        "entity_type": "CA_POSTAL_CODE",
        "regex": r"(?i)(?<![A-Z0-9])[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTVWXYZ][ -]?\d[ABCEGHJ-NPRSTVWXYZ]\d(?![A-Z0-9])",
        "score": "0.800000",
    },
    "presidio-domain-v1": {
        "entity_type": "DOMAIN_NAME",
        "regex": r"(?i)(?<![\w.-])(?:[A-Z0-9-]+\.)+(?:TEST|EXAMPLE|INVALID)(?![\w-]|\.[\w])",
        "score": "0.700000",
    },
}

BASELINE_RULES = {
    "gcl-email-v1": {
        "entity_type": "EMAIL_ADDRESS",
        "regex": r"(?i)\b[A-Z0-9][A-Z0-9._%+-]*@[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+\b",
    },
    "gcl-phone-na-v1": {
        "entity_type": "PHONE_NUMBER",
        "regex": r"(?<!\d)(?:\+1[ -])?[2-9]\d{2}-\d{3}-\d{4}(?!\d)",
    },
    "gcl-ipv4-v1": {
        "entity_type": "IP_ADDRESS",
        "regex": r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?!\d|\.\d)",
    },
    "gcl-ca-postal-v1": {
        "entity_type": "CA_POSTAL_CODE",
        "regex": r"(?i)\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTVWXYZ] \d[ABCEGHJ-NPRSTVWXYZ]\d\b",
    },
    "gcl-local-phone-v1": {
        "entity_type": "PHONE_NUMBER_LOCAL",
        "regex": r"(?<!\d)555-01\d{2}(?!\d)",
    },
}
AMBIGUITY_TERMS = {"Jordan", "Paris", "Victoria"}


class TroveCurataPiiFixtureError(ValueError):
    """Raised when observation evidence, routing, or claims fail closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataPiiFixtureError(message)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def content_id(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{sha256_bytes(canonical_json_bytes(value))}"


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [re.sub(r"[\t ]+", " ", line.strip()) for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _safe_relative_path(value: Any) -> str:
    _require(isinstance(value, str) and value, "fixture path required")
    _require("://" not in value, "network fixture paths are prohibited")
    path = Path(value)
    _require(not path.is_absolute(), "fixture paths must be relative")
    _require(".." not in path.parts, "fixture path traversal prohibited")
    return value


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataPiiFixtureError(f"unable to load fixture manifest: {exc}") from exc
    _require(isinstance(manifest, dict), "manifest root must be an object")
    _require(set(manifest) == {"schema_version", "fixture_id", "predecessor", "authority", "cases"}, "manifest field set drift")
    _require(manifest["schema_version"] == SCHEMA_VERSION, "manifest schema drift")
    _require(manifest["fixture_id"] == FIXTURE_ID, "manifest fixture identity drift")
    _require(manifest["predecessor"] == PREDECESSOR, "predecessor identity drift")
    _require(
        manifest["authority"]
        == {
            "project_owner": "grandchallenge",
            "repository": "grandchallenge/INTELLECT",
            "external_project_dependency": False,
            "aether_required": False,
            "providers_may_authorize_routes": False,
        },
        "authority boundary drift",
    )
    cases = manifest["cases"]
    _require(isinstance(cases, list) and cases, "fixture cases required")
    ids: set[str] = set()
    classes: set[str] = set()
    for case in cases:
        _require(
            isinstance(case, dict)
            and set(case)
            == {
                "case_id",
                "case_class",
                "path",
                "language",
                "policy_state",
                "expected_route",
                "provider_rules",
                "baseline_rules",
                "expected_provider_entities",
                "expected_baseline_entities",
                "expect_disagreement",
                "expect_overlap_rejection",
                "duplicate_group",
            },
            "fixture case field set drift",
        )
        case_id = case["case_id"]
        _require(isinstance(case_id, str) and case_id and case_id not in ids, "invalid or duplicate case_id")
        ids.add(case_id)
        _require(case["case_class"] in REQUIRED_CASE_CLASSES, "unsupported case class")
        classes.add(case["case_class"])
        _safe_relative_path(case["path"])
        _require(case["language"] in {"en", "fr"}, "unsupported fixture language")
        _require(case["policy_state"] in {"fixture_only", "review_required"}, "invalid policy state")
        _require(case["expected_route"] in ROUTES, "invalid expected route")
        _require(isinstance(case["provider_rules"], list), "provider_rules must be a list")
        _require(isinstance(case["baseline_rules"], list), "baseline_rules must be a list")
        _require(set(case["provider_rules"]) <= set(PRESIDIO_RULES), "unknown Presidio rule")
        _require(set(case["baseline_rules"]) <= set(BASELINE_RULES) | {"gcl-ambiguity-v1"}, "unknown baseline rule")
        _require(isinstance(case["expected_provider_entities"], list), "expected provider entities must be a list")
        _require(isinstance(case["expected_baseline_entities"], list), "expected baseline entities must be a list")
        _require(isinstance(case["expect_disagreement"], bool), "expect_disagreement must be boolean")
        _require(isinstance(case["expect_overlap_rejection"], bool), "expect_overlap_rejection must be boolean")
        _require(case["duplicate_group"] is None or isinstance(case["duplicate_group"], str), "invalid duplicate group")
    _require(classes == REQUIRED_CASE_CLASSES, "fixture class coverage drift")
    return manifest


def provider_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution, expected in PROVIDER_LOCK.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise TroveCurataPiiFixtureError(f"required provider not installed: {distribution}=={expected}") from exc
        _require(actual == expected, f"provider identity drift: {distribution}=={actual}, expected {expected}")
        versions[distribution] = actual
    return versions


def _score_text(value: str | float | int) -> str:
    try:
        score = Decimal(str(value)).quantize(Decimal("0.000001"))
    except InvalidOperation as exc:
        raise TroveCurataPiiFixtureError("invalid observation confidence") from exc
    _require(Decimal("0") <= score <= Decimal("1"), "confidence outside [0,1]")
    return f"{score:.6f}"


def _char_to_byte_offset(text: str, char_offset: int) -> int:
    return len(text[:char_offset].encode("utf-8"))


def make_observation(
    *,
    observer: str,
    rule_id: str,
    entity_type: str,
    score: str | float,
    text: str,
    start: int,
    end: int,
    provider_identity: dict[str, str],
) -> dict[str, Any]:
    _require(observer in {"presidio", "gcl_rules"}, "unsupported observer")
    _require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text), "invalid character span")
    matched = text[start:end]
    payload = {
        "observer": observer,
        "rule_id": rule_id,
        "entity_type": entity_type,
        "score": _score_text(score),
        "text_sha256": sha256_bytes(text.encode("utf-8")),
        "start_char": start,
        "end_char": end,
        "start_byte": _char_to_byte_offset(text, start),
        "end_byte": _char_to_byte_offset(text, end),
        "matched_text": matched,
        "provider_identity": provider_identity,
    }
    return {"observation_id": content_id("curata-observation", payload), **payload}


def validate_observation(observation: dict[str, Any], text: str) -> None:
    required = {
        "observation_id",
        "observer",
        "rule_id",
        "entity_type",
        "score",
        "text_sha256",
        "start_char",
        "end_char",
        "start_byte",
        "end_byte",
        "matched_text",
        "provider_identity",
    }
    _require(set(observation) == required, "observation field set drift")
    _require(observation["observer"] in {"presidio", "gcl_rules"}, "observer drift")
    _require(isinstance(observation["provider_identity"], dict), "provider identity required")
    _require("route" not in observation and "admission_state" not in observation, "provider self-authorization detected")
    start = observation["start_char"]
    end = observation["end_char"]
    _require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text), "observation span out of range")
    _require(observation["text_sha256"] == sha256_bytes(text.encode("utf-8")), "observation text identity drift")
    _require(observation["matched_text"] == text[start:end], "observation matched text drift")
    start_byte = _char_to_byte_offset(text, start)
    end_byte = _char_to_byte_offset(text, end)
    _require(observation["start_byte"] == start_byte and observation["end_byte"] == end_byte, "byte span drift")
    encoded = text.encode("utf-8")
    _require(encoded[start_byte:end_byte].decode("utf-8") == observation["matched_text"], "byte span does not resolve")
    _score_text(observation["score"])
    payload = {key: observation[key] for key in required if key != "observation_id"}
    _require(observation["observation_id"] == content_id("curata-observation", payload), "observation identity drift")
