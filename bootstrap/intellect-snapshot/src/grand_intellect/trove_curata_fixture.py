"""Executable offline HTML fixture for the GCL-contained TROVE-CURATA programme."""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import importlib.metadata
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


FIXTURE_ID = "TC-FIXTURE-001"
FIXTURE_SCHEMA_VERSION = "0.1.0"
PROVIDER_LOCK = {"daft": "0.7.21", "trafilatura": "2.1.0"}
EXTRACTION_CONFIG = {
    "favor_precision": True,
    "include_comments": False,
    "include_tables": True,
    "output_format": "txt",
}
REQUIRED_CASE_CLASSES = {
    "ordinary_article",
    "boilerplate_heavy",
    "math_and_code",
    "multilingual",
    "malformed_markup",
    "pii_observation",
    "exact_duplicate",
    "policy_review",
}


class TroveCurataFixtureError(ValueError):
    """Raised when fixture inputs, provider identities, or outputs drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TroveCurataFixtureError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def content_id(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{sha256_bytes(canonical_json_bytes(value))}"


def normalize_text(value: str) -> str:
    """Normalize Unicode and horizontal whitespace while preserving line boundaries."""

    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [re.sub(r"[\t ]+", " ", line.strip()) for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def identify_language_metadata(raw_html: str) -> str:
    match = re.search(r"<html\b[^>]*\blang\s*=\s*['\"]([^'\"]+)['\"]", raw_html, re.IGNORECASE)
    if match is None:
        return "und"
    value = match.group(1).strip().lower()
    return value or "und"


def lexical_tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[\w]+(?:[@.+^-][\w]+)*", value, flags=re.UNICODE)
        if len(token) >= 2
    }


def novel_output_tokens(raw_html: str, output_text: str) -> list[str]:
    source_tokens = lexical_tokens(html_module.unescape(raw_html))
    return sorted(lexical_tokens(output_text) - source_tokens)


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TroveCurataFixtureError(f"unable to load fixture manifest: {exc}") from exc
    _require(isinstance(manifest, dict), "manifest root must be an object")
    _require(manifest.get("fixture_id") == FIXTURE_ID, "fixture identity drift")
    _require(manifest.get("schema_version") == FIXTURE_SCHEMA_VERSION, "fixture schema version drift")
    cases = manifest.get("cases")
    _require(isinstance(cases, list) and cases, "fixture cases required")
    case_ids: set[str] = set()
    classes: set[str] = set()
    for case in cases:
        _require(isinstance(case, dict), "fixture case must be an object")
        case_id = case.get("case_id")
        _require(isinstance(case_id, str) and case_id and case_id not in case_ids, "invalid or duplicate case_id")
        case_ids.add(case_id)
        case_class = case.get("case_class")
        _require(case_class in REQUIRED_CASE_CLASSES, f"unsupported case class: {case_class}")
        classes.add(case_class)
        relative_path = case.get("path")
        _require(isinstance(relative_path, str) and relative_path, "fixture path required")
        _require("://" not in relative_path, "network fixture paths are prohibited")
        _require(not Path(relative_path).is_absolute(), "fixture paths must be repository-relative")
        _require(".." not in Path(relative_path).parts, "fixture path traversal prohibited")
        _require(case.get("policy_state") in {"fixture_only", "review_required"}, "invalid policy state")
        _require(isinstance(case.get("required_tokens", []), list), "required_tokens must be a list")
        _require(isinstance(case.get("boilerplate_tokens", []), list), "boilerplate_tokens must be a list")
    _require(classes == REQUIRED_CASE_CLASSES, "fixture class coverage drift")
    return manifest


def provider_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution, expected in PROVIDER_LOCK.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise TroveCurataFixtureError(f"required provider not installed: {distribution}=={expected}") from exc
        _require(actual == expected, f"provider identity drift: {distribution}=={actual}, expected {expected}")
        versions[distribution] = actual
    return versions


def extract_with_daft(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Execute Trafilatura extraction as a Daft function over repository-retained bytes."""

    try:
        import daft
        from trafilatura import extract
    except ImportError as exc:  # pragma: no cover - dedicated provider workflow
        raise TroveCurataFixtureError(f"fixture provider import failed: {exc}") from exc

    @daft.func
    def extract_text(raw_html: str) -> str:
        extracted = extract(raw_html, **EXTRACTION_CONFIG)
        return extracted or ""

    dataframe = daft.from_pylist(rows)
    materialized = dataframe.with_column("extracted_text", extract_text(dataframe["html"])).collect()
    return materialized.to_pylist()


def _validate_record_shape(record: dict[str, Any], record_type: str, required_keys: set[str]) -> None:
    _require(record.get("record_type") == record_type, f"record type drift: {record_type}")
    _require(set(record) == required_keys | {"record_type"}, f"{record_type} field set drift")


def build_report(
    manifest: dict[str, Any],
    fixture_root: str | Path,
    extracted_rows: list[dict[str, Any]],
    versions: dict[str, str],
) -> dict[str, Any]:
    root = Path(fixture_root)
    cases_by_id = {case["case_id"]: case for case in manifest["cases"]}
    _require(len(extracted_rows) == len(cases_by_id), "provider row count drift")

    configuration = {
        "fixture_id": FIXTURE_ID,
        "providers": versions,
        "extraction": EXTRACTION_CONFIG,
        "network_required_for_replay": False,
        "fixture_bytes_authority": "gcl_retained",
    }
    configuration_sha256 = sha256_bytes(canonical_json_bytes(configuration))
    case_reports: list[dict[str, Any]] = []
    duplicate_groups: dict[str, list[tuple[str, str]]] = {}

    for row in sorted(extracted_rows, key=lambda item: item["case_id"]):
        case_id = row["case_id"]
        _require(case_id in cases_by_id, f"unexpected provider row: {case_id}")
        case = cases_by_id[case_id]
        raw_html = row["html"]
        raw_bytes = raw_html.encode("utf-8")
        raw_digest = sha256_bytes(raw_bytes)
        extracted_text = row.get("extracted_text")
        _require(isinstance(extracted_text, str), f"non-string extraction output: {case_id}")
        normalized_text = normalize_text(extracted_text)
        extraction_status = "success" if normalized_text else "failed_empty_output"
        language = identify_language_metadata(raw_html)
        required_tokens = case.get("required_tokens", [])
        missing_tokens = [token for token in required_tokens if token not in normalized_text]
        boilerplate_tokens = case.get("boilerplate_tokens", [])
        boilerplate_residue = [token for token in boilerplate_tokens if token in normalized_text]
        novel_tokens = novel_output_tokens(raw_html, normalized_text)

        source_record = {
            "record_type": "trove_source_record",
            "source_record_id": content_id("trove-source", {"case_id": case_id, "raw_sha256": raw_digest}),
            "fixture_case_id": case_id,
            "source_family": "html",
            "source_locator": case["path"],
            "raw_sha256": raw_digest,
            "byte_length": len(raw_bytes),
            "language_metadata": language,
            "acquisition_method": "repository_retained_fixture",
            "network_required": False,
            "training_eligibility": "not_assessed",
        }
        _validate_record_shape(
            source_record,
            "trove_source_record",
            {
                "source_record_id",
                "fixture_case_id",
                "source_family",
                "source_locator",
                "raw_sha256",
                "byte_length",
                "language_metadata",
                "acquisition_method",
                "network_required",
                "training_eligibility",
            },
        )

        extraction_receipt_payload = {
            "stage": "html_extraction",
            "case_id": case_id,
            "input_sha256": raw_digest,
            "provider": {"name": "trafilatura", "version": versions["trafilatura"]},
            "execution_provider": {"name": "daft", "version": versions["daft"]},
            "configuration_sha256": configuration_sha256,
            "output_sha256": sha256_bytes(extracted_text.encode("utf-8")),
            "status": extraction_status,
        }
        extraction_receipt = {
            "record_type": "curata_transformation_receipt",
            "receipt_id": content_id("curata-receipt", extraction_receipt_payload),
            **extraction_receipt_payload,
            "content_altering": True,
            "network_used": False,
        }
        _validate_record_shape(
            extraction_receipt,
            "curata_transformation_receipt",
            {
                "receipt_id",
                "stage",
                "case_id",
                "input_sha256",
                "provider",
                "execution_provider",
                "configuration_sha256",
                "output_sha256",
                "status",
                "content_altering",
                "network_used",
            },
        )

        normalized_sha256 = sha256_bytes(normalized_text.encode("utf-8"))
        normalization_receipt_payload = {
            "stage": "deterministic_normalization",
            "case_id": case_id,
            "input_sha256": extraction_receipt["output_sha256"],
            "provider": {"name": "grand_intellect.normalize_text", "version": FIXTURE_SCHEMA_VERSION},
            "execution_provider": {"name": "python", "version": "3.11+"},
            "configuration_sha256": configuration_sha256,
            "output_sha256": normalized_sha256,
            "status": "success" if normalized_text else "blocked_empty_input",
        }
        normalization_receipt = {
            "record_type": "curata_transformation_receipt",
            "receipt_id": content_id("curata-receipt", normalization_receipt_payload),
            **normalization_receipt_payload,
            "content_altering": True,
            "network_used": False,
        }
        _validate_record_shape(
            normalization_receipt,
            "curata_transformation_receipt",
            {
                "receipt_id",
                "stage",
                "case_id",
                "input_sha256",
                "provider",
                "execution_provider",
                "configuration_sha256",
                "output_sha256",
                "status",
                "content_altering",
                "network_used",
            },
        )

        policy_state = case["policy_state"]
        pii_state = "observed_not_remediated" if case["case_class"] == "pii_observation" else "not_observed_by_fixture"
        passport_payload = {
            "case_id": case_id,
            "source_record_id": source_record["source_record_id"],
            "receipt_ids": [extraction_receipt["receipt_id"], normalization_receipt["receipt_id"]],
            "normalized_sha256": normalized_sha256,
            "policy_state": policy_state,
            "pii_state": pii_state,
        }
        passport = {
            "record_type": "curata_passport",
            "passport_id": content_id("curata-passport", passport_payload),
            **passport_payload,
            "admission_state": "review_required" if policy_state == "review_required" else "fixture_evaluated_not_admitted",
            "admitted_uses": ["fixture_replay"],
            "prohibited_uses": ["corpus_admission_without_T3_review"],
            "residual_risks": ["quality_not_established", "legality_not_established", "privacy_not_established"],
        }
        _validate_record_shape(
            passport,
            "curata_passport",
            {
                "passport_id",
                "case_id",
                "source_record_id",
                "receipt_ids",
                "normalized_sha256",
                "policy_state",
                "pii_state",
                "admission_state",
                "admitted_uses",
                "prohibited_uses",
                "residual_risks",
            },
        )

        checks = {
            "extraction_nonempty": bool(normalized_text),
            "language_metadata_matches": language == case["expected_language"],
            "required_tokens_preserved": not missing_tokens,
            "novel_lexical_tokens_absent": not novel_tokens,
            "policy_not_auto_resolved": policy_state != "review_required" or passport["admission_state"] == "review_required",
        }
        case_passed = all(checks.values())
        duplicate_group = case.get("duplicate_group")
        if duplicate_group:
            duplicate_groups.setdefault(duplicate_group, []).append((case_id, normalized_sha256))

        case_reports.append(
            {
                "case_id": case_id,
                "case_class": case["case_class"],
                "source_record": source_record,
                "transformation_receipts": [extraction_receipt, normalization_receipt],
                "passport": passport,
                "normalized_text": normalized_text,
                "checks": checks,
                "missing_required_tokens": missing_tokens,
                "boilerplate_residue": boilerplate_residue,
                "novel_lexical_tokens": novel_tokens,
                "passed": case_passed,
            }
        )

    duplicate_checks: list[dict[str, Any]] = []
    for group, members in sorted(duplicate_groups.items()):
        digests = {digest for _, digest in members}
        duplicate_checks.append(
            {
                "duplicate_group": group,
                "members": [case_id for case_id, _ in sorted(members)],
                "normalized_digest_equal": len(digests) == 1,
            }
        )

    report = {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "configuration": configuration,
        "configuration_sha256": configuration_sha256,
        "case_count": len(case_reports),
        "cases": case_reports,
        "duplicate_checks": duplicate_checks,
        "claims": {
            "corpus_admitted": False,
            "quality_proved": False,
            "privacy_proved": False,
            "legality_proved": False,
            "safety_proved": False,
            "fitness_for_training_proved": False,
            "downstream_improvement_proved": False,
            "commercial_claim_authorized": False,
        },
        "passed": all(case["passed"] for case in case_reports)
        and all(check["normalized_digest_equal"] for check in duplicate_checks),
    }
    if not report["passed"]:
        failures = [
            {
                "case_id": case["case_id"],
                "checks": case["checks"],
                "missing_required_tokens": case["missing_required_tokens"],
                "novel_lexical_tokens": case["novel_lexical_tokens"],
                "normalized_text": case["normalized_text"],
            }
            for case in case_reports
            if not case["passed"]
        ]
        duplicate_failures = [check for check in duplicate_checks if not check["normalized_digest_equal"]]
        raise TroveCurataFixtureError(
            "fixture acceptance checks failed: "
            + json.dumps(
                {"case_failures": failures, "duplicate_failures": duplicate_failures},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return report


def run_fixture(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    root = manifest_file.parent
    rows: list[dict[str, str]] = []
    for case in manifest["cases"]:
        source_path = root / case["path"]
        _require(source_path.is_file(), f"fixture source missing: {case['path']}")
        raw_html = source_path.read_text(encoding="utf-8")
        rows.append({"case_id": case["case_id"], "html": raw_html})
    versions = provider_versions()
    extracted_rows = extract_with_daft(rows)
    report = build_report(manifest, root, extracted_rows, versions)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to TC-FIXTURE-001 manifest.json")
    parser.add_argument("--output", required=True, help="Path for deterministic JSON report")
    arguments = parser.parse_args(argv)
    run_fixture(arguments.manifest, arguments.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
