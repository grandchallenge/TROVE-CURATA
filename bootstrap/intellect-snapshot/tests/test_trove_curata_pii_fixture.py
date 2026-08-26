from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from grand_intellect.trove_curata_pii_analysis import (
    overlapping_pairs,
    simulate_presidio_observations,
)
from grand_intellect.trove_curata_pii_contract import (
    FALSE_CLAIMS,
    PROVIDER_LOCK,
    TroveCurataPiiFixtureError,
    canonical_json_bytes,
    load_manifest,
    make_observation,
    normalize_text,
    sha256_bytes,
    validate_observation,
)
from grand_intellect.trove_curata_pii_report import build_report, validate_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "fixtures" / "trove_curata" / "TC-FIXTURE-002"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
SCHEMA_PATH = ROOT / "schemas" / "trove_curata_pii_fixture_report.schema.json"


class TroveCurataPiiFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(MANIFEST_PATH)
        self.provider_rows = {}
        for case in self.manifest["cases"]:
            text = normalize_text((FIXTURE_ROOT / case["path"]).read_text(encoding="utf-8"))
            self.provider_rows[case["case_id"]] = simulate_presidio_observations(text, case["provider_rules"])
        self.report = build_report(self.manifest, FIXTURE_ROOT, self.provider_rows, dict(PROVIDER_LOCK))

    def test_manifest_is_gcl_contained_and_complete(self) -> None:
        self.assertFalse(self.manifest["authority"]["external_project_dependency"])
        self.assertFalse(self.manifest["authority"]["providers_may_authorize_routes"])
        self.assertEqual(len(self.manifest["cases"]), 11)

    def test_schema_is_closed(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["$defs"]["claims"]["additionalProperties"])
        for definition in ("predecessor", "configuration", "providerIdentity", "inputContract", "observation", "observationSet", "disagreement", "analysisReceipt", "routingRecord", "checks", "caseReport", "duplicateCheck", "claims"):
            self.assertFalse(schema["$defs"][definition]["additionalProperties"], definition)

    def test_pure_fixture_passes_and_claims_remain_false(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(set(self.report["claims"]), FALSE_CLAIMS)
        self.assertTrue(all(value is False for value in self.report["claims"].values()))

    def test_duplicate_inputs_have_identical_observation_digests(self) -> None:
        self.assertEqual(len(self.report["duplicate_checks"]), 1)
        check = self.report["duplicate_checks"][0]
        self.assertTrue(check["input_digest_equal"])
        self.assertTrue(check["observation_digest_equal"])

    def test_overlap_case_is_rejected_and_routed_to_review(self) -> None:
        case = next(item for item in self.report["cases"] if item["case_id"] == "overlapping-spans")
        self.assertEqual(case["provider_observation_set"]["status"], "rejected_overlap")
        self.assertTrue(case["provider_observation_set"]["overlap_pairs"])
        self.assertEqual(case["routing_record"]["route"], "review_required")

    def test_unicode_byte_spans_resolve_exactly(self) -> None:
        text = "Courriel synthétique: exemple@example.test"
        start = text.index("exemple")
        observation = make_observation(
            observer="gcl_rules",
            rule_id="test-rule",
            entity_type="EMAIL_ADDRESS",
            score="1.0",
            text=text,
            start=start,
            end=len(text),
            provider_identity={"name": "test", "version": "1", "adapter": "test"},
        )
        validate_observation(observation, text)
        self.assertEqual(text.encode("utf-8")[observation["start_byte"] : observation["end_byte"]].decode("utf-8"), observation["matched_text"])

    def test_out_of_range_span_fails_closed(self) -> None:
        text = "synthetic@example.test"
        observation = make_observation(
            observer="gcl_rules",
            rule_id="test-rule",
            entity_type="EMAIL_ADDRESS",
            score="1.0",
            text=text,
            start=0,
            end=len(text),
            provider_identity={"name": "test", "version": "1", "adapter": "test"},
        )
        observation["end_char"] = len(text) + 1
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_observation(observation, text)

    def test_confidence_inflation_fails_closed(self) -> None:
        text = "synthetic@example.test"
        with self.assertRaises(TroveCurataPiiFixtureError):
            make_observation(
                observer="presidio",
                rule_id="test-rule",
                entity_type="EMAIL_ADDRESS",
                score="1.000001",
                text=text,
                start=0,
                end=len(text),
                provider_identity={"name": "test", "version": "1", "adapter": "test"},
            )

    def test_hidden_overlap_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        case = next(item for item in mutated["cases"] if item["case_id"] == "overlapping-spans")
        case["provider_observation_set"]["overlap_pairs"] = []
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_hidden_disagreement_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        case = next(item for item in mutated["cases"] if item["case_id"] == "provider-rules-disagreement")
        case["disagreement"]["disagreement_present"] = False
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_provider_self_authorization_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["cases"][0]["analysis_receipt"]["provider_may_authorize_route"] = True
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_route_escalation_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["cases"][0]["routing_record"]["route"] = "admit"
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_claim_inflation_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["claims"]["privacy_compliance_proved"] = True
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_external_dependency_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["configuration"]["external_project_dependency"] = True
        mutated["configuration_sha256"] = sha256_bytes(canonical_json_bytes(mutated["configuration"]))
        with self.assertRaises(TroveCurataPiiFixtureError):
            validate_report(mutated, self.manifest, FIXTURE_ROOT)

    def test_overlapping_pair_detection_is_order_independent(self) -> None:
        case = next(item for item in self.report["cases"] if item["case_id"] == "overlapping-spans")
        observations = case["provider_observation_set"]["observations"]
        self.assertEqual(overlapping_pairs(observations), overlapping_pairs(list(reversed(observations))))


if __name__ == "__main__":
    unittest.main()
