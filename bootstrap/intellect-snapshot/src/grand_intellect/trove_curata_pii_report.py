"""Canonical report construction and fail-closed validation for TC-FIXTURE-002."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .trove_curata_pii_contract import (
    AMBIGUITY_TERMS,
    BASELINE_RULES,
    FALSE_CLAIMS,
    FIXTURE_ID,
    PREDECESSOR,
    PRESIDIO_RULES,
    ROUTES,
    SCHEMA_VERSION,
    _require,
    canonical_json_bytes,
    content_id,
    normalize_text,
    sha256_bytes,
    validate_observation,
)
from .trove_curata_pii_analysis import (
    _entity_multiset,
    _observation_sort_key,
    analyze_with_gcl_rules,
    disagreement_record,
    observation_set,
    overlapping_pairs,
)


def _input_contract(case: dict[str, Any], text: str) -> dict[str, Any]:
    text_sha256 = sha256_bytes(text.encode("utf-8"))
    source_record_id = content_id("trove-source", {"fixture": FIXTURE_ID, "case_id": case["case_id"], "text_sha256": text_sha256})
    receipt_id = content_id("curata-receipt", {"stage": "retained_normalized_input", "source_record_id": source_record_id})
    passport_id = content_id("curata-passport", {"receipt_id": receipt_id, "policy_state": case["policy_state"]})
    return {
        "record_type": "curata_analysis_input",
        "input_id": content_id("curata-analysis-input", {"passport_id": passport_id, "text_sha256": text_sha256}),
        "predecessor": PREDECESSOR,
        "source_record_id": source_record_id,
        "transformation_receipt_id": receipt_id,
        "passport_id": passport_id,
        "text_sha256": text_sha256,
        "byte_length": len(text.encode("utf-8")),
        "language": case["language"],
        "policy_state": case["policy_state"],
        "network_required": False,
        "training_eligibility": "not_assessed",
    }


def _route(case: dict[str, Any], provider_set: dict[str, Any], baseline_set: dict[str, Any], disagreement: dict[str, Any]) -> str:
    if case["policy_state"] == "review_required":
        return "review_required"
    if provider_set["status"] != "accepted" or baseline_set["status"] != "accepted":
        return "review_required"
    if provider_set["observations"] or baseline_set["observations"] or disagreement["disagreement_present"]:
        return "review_required"
    return "observation_clear"


def build_report(
    manifest: dict[str, Any],
    fixture_root: str | Path,
    provider_rows: dict[str, list[dict[str, Any]]],
    versions: dict[str, str],
) -> dict[str, Any]:
    root = Path(fixture_root)
    configuration = {
        "fixture_id": FIXTURE_ID,
        "schema_version": SCHEMA_VERSION,
        "predecessor": PREDECESSOR,
        "providers": versions,
        "presidio_rules": PRESIDIO_RULES,
        "baseline_rules": BASELINE_RULES,
        "ambiguity_terms": sorted(AMBIGUITY_TERMS),
        "routing_authority": "gcl_owned",
        "external_project_dependency": False,
        "network_required_for_replay": False,
        "redaction_enabled": False,
        "anonymization_enabled": False,
    }
    configuration_sha256 = sha256_bytes(canonical_json_bytes(configuration))
    case_reports: list[dict[str, Any]] = []
    duplicate_groups: dict[str, list[tuple[str, str, str]]] = {}

    for case in sorted(manifest["cases"], key=lambda item: item["case_id"]):
        path = root / case["path"]
        _require(path.is_file(), f"missing retained fixture text: {case['path']}")
        text = normalize_text(path.read_text(encoding="utf-8"))
        _require(text, f"empty retained fixture text: {case['case_id']}")
        input_contract = _input_contract(case, text)
        provider_observations = sorted(provider_rows.get(case["case_id"], []), key=_observation_sort_key)
        baseline_observations = analyze_with_gcl_rules(text, case["baseline_rules"])
        provider_set = observation_set("presidio", provider_observations, text)
        baseline_set = observation_set("gcl_rules", baseline_observations, text)
        disagreement = disagreement_record(provider_set, baseline_set)
        route = _route(case, provider_set, baseline_set, disagreement)
        observation_payload = {
            "input_id": input_contract["input_id"],
            "provider_set_digest": provider_set["observation_digest"],
            "baseline_set_digest": baseline_set["observation_digest"],
            "disagreement_digest": disagreement["disagreement_digest"],
            "configuration_sha256": configuration_sha256,
        }
        receipt = {
            "record_type": "curata_analysis_receipt",
            "receipt_id": content_id("curata-analysis-receipt", observation_payload),
            **observation_payload,
            "stage": "pii_observation_and_policy_routing",
            "content_mutated": False,
            "network_used": False,
            "provider_may_authorize_route": False,
        }
        routing_payload = {
            "analysis_receipt_id": receipt["receipt_id"],
            "route": route,
            "routing_authority": "grandchallenge",
            "policy_state": case["policy_state"],
        }
        routing_record = {
            "record_type": "curata_routing_record",
            "routing_record_id": content_id("curata-routing", routing_payload),
            **routing_payload,
            "admission_state": "not_admitted",
            "deletion_state": "not_deleted",
            "redaction_state": "not_performed",
            "anonymization_state": "not_performed",
        }
        checks = {
            "provider_entities_match": _entity_multiset(provider_observations) == sorted(case["expected_provider_entities"]),
            "baseline_entities_match": _entity_multiset(baseline_observations) == sorted(case["expected_baseline_entities"]),
            "disagreement_expectation_matches": disagreement["disagreement_present"] is case["expect_disagreement"],
            "overlap_expectation_matches": (provider_set["status"] == "rejected_overlap") is case["expect_overlap_rejection"],
            "route_matches": route == case["expected_route"],
            "provider_has_no_route_authority": receipt["provider_may_authorize_route"] is False,
            "content_not_mutated": receipt["content_mutated"] is False,
            "no_release_action": routing_record["admission_state"] == "not_admitted"
            and routing_record["deletion_state"] == "not_deleted",
        }
        canonical_observation_digest = sha256_bytes(
            canonical_json_bytes(
                {
                    "text_sha256": input_contract["text_sha256"],
                    "provider": provider_set,
                    "baseline": baseline_set,
                    "disagreement": disagreement,
                    "route": route,
                }
            )
        )
        if case["duplicate_group"]:
            duplicate_groups.setdefault(case["duplicate_group"], []).append(
                (case["case_id"], input_contract["text_sha256"], canonical_observation_digest)
            )
        case_reports.append(
            {
                "case_id": case["case_id"],
                "case_class": case["case_class"],
                "input_contract": input_contract,
                "provider_observation_set": provider_set,
                "baseline_observation_set": baseline_set,
                "disagreement": disagreement,
                "analysis_receipt": receipt,
                "routing_record": routing_record,
                "canonical_observation_digest": canonical_observation_digest,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    duplicate_checks: list[dict[str, Any]] = []
    for group, members in sorted(duplicate_groups.items()):
        duplicate_checks.append(
            {
                "duplicate_group": group,
                "members": sorted(item[0] for item in members),
                "input_digest_equal": len({item[1] for item in members}) == 1,
                "observation_digest_equal": len({item[2] for item in members}) == 1,
            }
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "predecessor": PREDECESSOR,
        "configuration": configuration,
        "configuration_sha256": configuration_sha256,
        "case_count": len(case_reports),
        "cases": case_reports,
        "duplicate_checks": duplicate_checks,
        "claims": {claim: False for claim in sorted(FALSE_CLAIMS)},
        "passed": all(case["passed"] for case in case_reports)
        and all(check["input_digest_equal"] and check["observation_digest_equal"] for check in duplicate_checks),
    }
    validate_report(report, manifest, root)
    _require(report["passed"], "fixture acceptance checks failed")
    return report


def validate_report(report: dict[str, Any], manifest: dict[str, Any], fixture_root: str | Path) -> None:
    _require(
        set(report)
        == {
            "schema_version",
            "fixture_id",
            "predecessor",
            "configuration",
            "configuration_sha256",
            "case_count",
            "cases",
            "duplicate_checks",
            "claims",
            "passed",
        },
        "report field set drift",
    )
    _require(report["schema_version"] == SCHEMA_VERSION and report["fixture_id"] == FIXTURE_ID, "report identity drift")
    _require(report["predecessor"] == PREDECESSOR, "report predecessor drift")
    _require(report["configuration"]["external_project_dependency"] is False, "external project dependency introduced")
    _require(report["configuration"]["routing_authority"] == "gcl_owned", "routing authority drift")
    _require(report["configuration"]["redaction_enabled"] is False, "redaction escalation detected")
    _require(report["configuration"]["anonymization_enabled"] is False, "anonymization escalation detected")
    _require(report["configuration_sha256"] == sha256_bytes(canonical_json_bytes(report["configuration"])), "configuration digest drift")
    _require(set(report["claims"]) == FALSE_CLAIMS, "claim field set drift")
    _require(all(value is False for value in report["claims"].values()), "claim inflation detected")
    _require(report["case_count"] == len(report["cases"]) == len(manifest["cases"]), "case count drift")
    case_manifest = {case["case_id"]: case for case in manifest["cases"]}
    root = Path(fixture_root)
    for case_report in report["cases"]:
        _require(
            set(case_report)
            == {
                "case_id",
                "case_class",
                "input_contract",
                "provider_observation_set",
                "baseline_observation_set",
                "disagreement",
                "analysis_receipt",
                "routing_record",
                "canonical_observation_digest",
                "checks",
                "passed",
            },
            "case report field set drift",
        )
        case = case_manifest[case_report["case_id"]]
        text = normalize_text((root / case["path"]).read_text(encoding="utf-8"))
        for key, observer in (("provider_observation_set", "presidio"), ("baseline_observation_set", "gcl_rules")):
            observation_group = case_report[key]
            _require(
                set(observation_group) == {"observer", "status", "observations", "overlap_pairs", "observation_digest"},
                "observation set field drift",
            )
            _require(observation_group["observer"] == observer, "observation set observer drift")
            for observation in observation_group["observations"]:
                validate_observation(observation, text)
            pairs = overlapping_pairs(observation_group["observations"])
            _require(observation_group["overlap_pairs"] == pairs, "hidden overlap detected")
            _require(observation_group["status"] == ("rejected_overlap" if pairs else "accepted"), "overlap status drift")
            payload = {key: observation_group[key] for key in ("observer", "status", "observations", "overlap_pairs")}
            _require(observation_group["observation_digest"] == sha256_bytes(canonical_json_bytes(payload)), "observation digest drift")
        expected_disagreement = disagreement_record(case_report["provider_observation_set"], case_report["baseline_observation_set"])
        _require(case_report["disagreement"] == expected_disagreement, "hidden disagreement detected")
        routing = case_report["routing_record"]
        _require(routing["route"] in ROUTES, "route escalation detected")
        _require(routing["routing_authority"] == "grandchallenge", "provider routing authority detected")
        _require(routing["admission_state"] == "not_admitted", "corpus admission escalation detected")
        _require(routing["deletion_state"] == "not_deleted", "deletion escalation detected")
        _require(routing["redaction_state"] == "not_performed", "redaction escalation detected")
        _require(routing["anonymization_state"] == "not_performed", "anonymization escalation detected")
        receipt = case_report["analysis_receipt"]
        _require(receipt["provider_may_authorize_route"] is False, "provider self-authorization detected")
        _require(receipt["content_mutated"] is False, "content mutation detected")
        _require(receipt["network_used"] is False, "network use detected")
        _require(case_report["passed"] == all(case_report["checks"].values()), "case pass inflation detected")
    _require(isinstance(report["passed"], bool), "report passed must be boolean")
