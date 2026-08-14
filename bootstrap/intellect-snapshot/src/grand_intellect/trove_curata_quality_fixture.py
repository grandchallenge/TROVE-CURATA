"""TC-FIXTURE-005 governed quality-signal observation.

This module is deliberately dependency-light. It produces observations only and
cannot rank, admit, reject, delete, suppress, or select canonical records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[\w’'-]+", re.UNICODE)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
MARKER_RE = re.compile(r"<[A-Z][A-Z0-9_]*>")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
SIX = Decimal("0.000001")

ROUTES = {"no_quality_flag_observed", "quality_review_required"}
CONSERVATIVE_CLASSES = ["code_math", "multilingual", "boilerplate", "short_text"]
THRESHOLDS = {
    "very_short_tokens": 5,
    "low_unique_token_ratio": "0.450000",
    "repeated_line_ratio": "0.500000",
    "symbol_ratio": "0.250000",
    "url_count": 2,
}
CLAIMS = {
    "records_ranked": False,
    "records_deleted": False,
    "records_suppressed": False,
    "canonical_member_selected": False,
    "corpus_admitted": False,
    "corpus_rejected": False,
    "dataset_quality_certified": False,
    "privacy_compliance_proved": False,
    "legality_proved": False,
    "fitness_for_training_proved": False,
    "release_qualified": False,
    "downstream_improvement_proved": False,
    "novelty_or_priority_claimed": False,
    "commercial_claim_authorized": False,
}


class TroveCurataQualityError(ValueError):
    """Raised when Fixture 005 input, evidence, or authority drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataQualityError(message)


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.000000"
    return format(
        (Decimal(numerator) / Decimal(denominator)).quantize(SIX, rounding=ROUND_HALF_UP),
        "f",
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure_text(text: str) -> dict[str, Any]:
    tokens = TOKEN_RE.findall(text)
    lowered = [token.casefold() for token in tokens]
    nonspace = [char for char in text if not char.isspace()]
    alphabetic = sum(char.isalpha() for char in nonspace)
    symbols = sum(not char.isalnum() for char in nonspace)
    lines = [
        line.strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if line.strip()
    ]
    repeated_count = len(lines) - len(set(lines)) if lines else 0
    return {
        "char_count": len(text),
        "token_count": len(tokens),
        "line_count": len(lines),
        "alphabetic_ratio": _ratio(alphabetic, len(nonspace)),
        "symbol_ratio": _ratio(symbols, len(nonspace)),
        "unique_token_ratio": _ratio(len(set(lowered)), len(lowered)),
        "repeated_line_ratio": _ratio(repeated_count, len(lines)),
        "url_count": len(URL_RE.findall(text)),
        "replacement_marker_count": len(MARKER_RE.findall(text)),
    }


def _probe_flags(metrics: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if metrics["token_count"] < THRESHOLDS["very_short_tokens"]:
        flags.append("very_short")
    if (
        metrics["token_count"] >= 12
        and Decimal(metrics["unique_token_ratio"])
        < Decimal(THRESHOLDS["low_unique_token_ratio"])
    ):
        flags.append("low_unique_token_ratio")
    if Decimal(metrics["repeated_line_ratio"]) >= Decimal(
        THRESHOLDS["repeated_line_ratio"]
    ):
        flags.append("repeated_lines")
    return flags


def _baseline_flags(metrics: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if Decimal(metrics["symbol_ratio"]) >= Decimal(THRESHOLDS["symbol_ratio"]):
        flags.append("symbol_heavy")
    if metrics["url_count"] >= THRESHOLDS["url_count"]:
        flags.append("url_heavy")
    if Decimal(metrics["repeated_line_ratio"]) >= Decimal(
        THRESHOLDS["repeated_line_ratio"]
    ):
        flags.append("repeated_lines")
    if metrics["replacement_marker_count"] > 0:
        flags.append("replacement_marker_observed")
    return flags


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataQualityError(f"unable to load manifest: {exc}") from exc

    _require(
        isinstance(manifest, dict)
        and set(manifest)
        == {
            "schema_version",
            "fixture_id",
            "predecessor",
            "authority",
            "predecessor_records",
            "synthetic_records",
            "configuration",
            "cases",
        },
        "manifest field set drift",
    )
    _require(manifest["schema_version"] == "0.1.0", "schema version drift")
    _require(manifest["fixture_id"] == "TC-FIXTURE-005", "fixture identity drift")
    _require(
        manifest["predecessor"]
        == {
            "fixture_id": "TC-FIXTURE-004",
            "subject_pull_request": 49,
            "exact_merged_implementation_head": "6dc65962ec77e17ae5bdd2c75ccd5da63aefcef7",
            "protected_implementation_merge": "6e2385a841dfd55bbab480d79a47611cc6557103",
            "review_remedy_pull_request": 51,
            "exact_remedy_head": "dbb68b54aaf6df2eced710e6dd3936aa3bb2f7fc",
            "protected_remedy_merge": "70a0a74502e0480d387d740027e48751286e4bfe",
        },
        "predecessor identity drift",
    )

    authority = manifest["authority"]
    _require(
        set(authority)
        == {
            "quality_probe_role",
            "route_authority",
            "providers_may_authorize_admission",
            "providers_may_authorize_rejection",
            "ranking_enabled",
            "deletion_enabled",
            "suppression_enabled",
            "canonical_member_selection_enabled",
            "source_records_immutable",
            "external_project_dependency",
            "aether_required",
        },
        "authority field set drift",
    )
    _require(authority["quality_probe_role"] == "observation_only", "probe authority drift")
    _require(authority["route_authority"] == "gcl_owned_configuration", "route authority drift")
    for field in (
        "providers_may_authorize_admission",
        "providers_may_authorize_rejection",
        "ranking_enabled",
        "deletion_enabled",
        "suppression_enabled",
        "canonical_member_selection_enabled",
        "external_project_dependency",
        "aether_required",
    ):
        _require(authority[field] is False, f"authority escalation: {field}")
    _require(authority["source_records_immutable"] is True, "source immutability drift")

    cfg = manifest["configuration"]
    _require(
        set(cfg)
        == {"version", "thresholds", "conservative_record_classes", "probe", "baseline"},
        "configuration field set drift",
    )
    _require(cfg["version"] == "gcl_quality_observation_v1", "configuration version drift")
    _require(cfg["thresholds"] == THRESHOLDS, "threshold drift")
    _require(
        cfg["conservative_record_classes"] == CONSERVATIVE_CLASSES,
        "conservative class drift",
    )
    _require(
        cfg["probe"] == {"name": "gcl_readability_probe", "version": "0.1.0"},
        "probe identity drift",
    )
    _require(
        cfg["baseline"] == {"name": "gcl_structural_baseline", "version": "0.1.0"},
        "baseline identity drift",
    )

    cases = manifest["cases"]
    _require(isinstance(cases, list) and len(cases) == 12, "case count drift")
    ids: set[str] = set()
    case_fields = {
        "case_id",
        "case_class",
        "source_kind",
        "record_id",
        "expected_source_sha256",
        "duplicate_component_member",
        "expected_route",
    }
    for case in cases:
        _require(isinstance(case, dict) and set(case) == case_fields, "case field set drift")
        _require(case["case_id"] not in ids, "duplicate case id")
        ids.add(case["case_id"])
        _require(case["source_kind"] in {"predecessor", "synthetic"}, "source kind drift")
        _require(DIGEST_RE.fullmatch(case["expected_source_sha256"]) is not None, "source digest format drift")
        _require(case["expected_route"] in ROUTES, "route vocabulary drift")
        _require(
            isinstance(case["duplicate_component_member"], bool),
            "duplicate membership type drift",
        )
    return manifest


def _load_records(path: Path, expected_fixture: str) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataQualityError(f"unable to load records: {exc}") from exc
    _require(
        set(data) == {"schema_version", "fixture_id", "records"}
        and data["schema_version"] == "0.1.0"
        and data["fixture_id"] == expected_fixture,
        "record collection identity drift",
    )
    out: dict[str, dict[str, Any]] = {}
    for record in data["records"]:
        expected_fields = {"record_id", "record_class", "language", "origin", "text"}
        if expected_fixture == "TC-FIXTURE-005":
            expected_fields = {"record_id", "record_class", "language", "text"}
        _require(
            isinstance(record, dict) and set(record) == expected_fields,
            "record field set drift",
        )
        rid = record["record_id"]
        _require(rid not in out and isinstance(record["text"], str), "record identity drift")
        out[rid] = record
    return out


def build_quality_report(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path)
    base = manifest_path.parent
    predecessor_records = _load_records(
        (base / manifest["predecessor_records"]).resolve(), "TC-FIXTURE-004"
    )
    synthetic_records = _load_records(
        (base / manifest["synthetic_records"]).resolve(), "TC-FIXTURE-005"
    )

    outputs = []
    conservative = set(CONSERVATIVE_CLASSES)
    for case in manifest["cases"]:
        records = (
            predecessor_records if case["source_kind"] == "predecessor" else synthetic_records
        )
        _require(case["record_id"] in records, "missing source record")
        record = records[case["record_id"]]
        text = record["text"]
        source_digest = _sha256_text(text)
        _require(source_digest == case["expected_source_sha256"], "source digest drift")

        metrics = measure_text(text)
        record_class = record["record_class"]
        language = record["language"]
        conservative_reason = record_class if record_class in conservative else None

        if conservative_reason is None and language == "en":
            p_flags = _probe_flags(metrics)
            probe_evaluated = True
            probe_skipped_reason = None
        else:
            p_flags = []
            probe_evaluated = False
            probe_skipped_reason = (
                "conservative_record_class" if conservative_reason else "non_english"
            )

        b_flags = _baseline_flags(metrics)
        disagreement = (
            bool(p_flags) != bool(b_flags) if probe_evaluated else False
        )
        route = (
            "quality_review_required"
            if conservative_reason is not None or p_flags or b_flags or disagreement
            else "no_quality_flag_observed"
        )
        _require(route == case["expected_route"], f"route expectation drift: {case['case_id']}")

        observation = {
            "case_id": case["case_id"],
            "case_class": case["case_class"],
            "source_kind": case["source_kind"],
            "record_id": case["record_id"],
            "record_class": record_class,
            "language": language,
            "source_sha256": source_digest,
            "source_record_mutated": False,
            "duplicate_component_member": case["duplicate_component_member"],
            "metrics": metrics,
            "probe": {
                "name": "gcl_readability_probe",
                "version": "0.1.0",
                "evaluated": probe_evaluated,
                "skipped_reason": probe_skipped_reason,
                "flags": p_flags,
                "may_authorize_route": False,
                "may_authorize_admission": False,
                "may_authorize_rejection": False,
            },
            "baseline": {
                "name": "gcl_structural_baseline",
                "version": "0.1.0",
                "flags": b_flags,
                "may_authorize_route": False,
            },
            "disagreement": disagreement,
            "route": route,
            "ranking": None,
            "admission_state": "not_admitted",
            "rejection_state": "not_rejected",
            "deletion_state": "not_deleted",
            "canonical_member": None,
        }
        observation["observation_sha256"] = _canonical_digest(observation)
        outputs.append(observation)

    report = {
        "schema_version": "0.1.0",
        "fixture_id": "TC-FIXTURE-005",
        "configuration_sha256": _canonical_digest(manifest["configuration"]),
        "record_count": len(outputs),
        "records": outputs,
        "routes": {
            "no_quality_flag_observed": sum(
                record["route"] == "no_quality_flag_observed" for record in outputs
            ),
            "quality_review_required": sum(
                record["route"] == "quality_review_required" for record in outputs
            ),
        },
        "claims": dict(CLAIMS),
        "passed": True,
    }
    report["report_sha256"] = _canonical_digest(report)
    return report


def validate_quality_report(report: dict[str, Any]) -> dict[str, Any]:
    _require(
        set(report)
        == {
            "schema_version",
            "fixture_id",
            "configuration_sha256",
            "record_count",
            "records",
            "routes",
            "claims",
            "passed",
            "report_sha256",
        },
        "report field set drift",
    )
    _require(
        report["schema_version"] == "0.1.0"
        and report["fixture_id"] == "TC-FIXTURE-005",
        "report identity drift",
    )
    _require(report["record_count"] == 12 == len(report["records"]), "record count drift")
    _require(report["passed"] is True, "fixture not passed")
    _require(report["claims"] == CLAIMS, "claim boundary drift")
    _require(
        report["routes"]["no_quality_flag_observed"]
        + report["routes"]["quality_review_required"]
        == 12,
        "route count drift",
    )

    seen = set()
    for record in report["records"]:
        _require(record["case_id"] not in seen, "duplicate case")
        seen.add(record["case_id"])
        _require(record["source_record_mutated"] is False, "source mutation")
        _require(record["route"] in ROUTES, "route vocabulary drift")
        _require(record["ranking"] is None, "ranking authority escalation")
        _require(record["admission_state"] == "not_admitted", "admission authority escalation")
        _require(record["rejection_state"] == "not_rejected", "rejection authority escalation")
        _require(record["deletion_state"] == "not_deleted", "deletion authority escalation")
        _require(record["canonical_member"] is None, "canonical selection escalation")
        _require(record["probe"]["may_authorize_route"] is False, "probe route authority escalation")
        _require(record["probe"]["may_authorize_admission"] is False, "probe admission authority escalation")
        _require(record["probe"]["may_authorize_rejection"] is False, "probe rejection authority escalation")
        _require(record["baseline"]["may_authorize_route"] is False, "baseline route authority escalation")
        expected_disagreement = (
            bool(record["probe"]["flags"]) != bool(record["baseline"]["flags"])
            if record["probe"]["evaluated"]
            else False
        )
        _require(record["disagreement"] is expected_disagreement, "disagreement drift")
        if record["record_class"] in set(CONSERVATIVE_CLASSES):
            _require(record["route"] == "quality_review_required", "conservative class cleared")
        if record["case_id"] == "duplicate-member":
            _require(
                record["duplicate_component_member"] is True
                and record["route"] == "no_quality_flag_observed",
                "duplicate evidence became quality verdict",
            )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = validate_quality_report(build_quality_report(args.manifest))
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
