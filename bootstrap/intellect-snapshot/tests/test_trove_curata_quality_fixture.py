from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from grand_intellect.trove_curata_quality_fixture import (
    TroveCurataQualityError,
    load_manifest,
    build_quality_report,
    validate_quality_report,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fixtures" / "trove_curata" / "TC-FIXTURE-005" / "manifest.json"

class QualityFixtureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.report = build_quality_report(MANIFEST)

    def test_manifest_validates(self):
        self.assertEqual(load_manifest(MANIFEST), self.manifest)

    def test_report_validates(self):
        self.assertEqual(validate_quality_report(self.report), self.report)

    def test_route_counts(self):
        self.assertEqual(self.report["routes"], {"no_quality_flag_observed": 3, "quality_review_required": 9})

    def test_two_replays_identical(self):
        first = json.dumps(build_quality_report(MANIFEST), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        second = json.dumps(build_quality_report(MANIFEST), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)

    def test_source_records_immutable(self):
        self.assertTrue(all(record["source_record_mutated"] is False for record in self.report["records"]))

    def test_duplicate_membership_not_quality_verdict(self):
        record = next(r for r in self.report["records"] if r["case_id"] == "duplicate-member")
        self.assertTrue(record["duplicate_component_member"])
        self.assertEqual(record["route"], "no_quality_flag_observed")

    def test_multilingual_probe_abstains(self):
        record = next(r for r in self.report["records"] if r["case_id"] == "multilingual-fr")
        self.assertFalse(record["probe"]["evaluated"])
        self.assertEqual(record["probe"]["skipped_reason"], "conservative_record_class")
        self.assertEqual(record["route"], "quality_review_required")

    def test_code_math_probe_abstains(self):
        record = next(r for r in self.report["records"] if r["case_id"] == "code-math")
        self.assertFalse(record["probe"]["evaluated"])
        self.assertEqual(record["route"], "quality_review_required")

    def test_disagreements_preserved(self):
        ids = {r["case_id"] for r in self.report["records"] if r["disagreement"]}
        self.assertEqual(ids, {"url-heavy", "transformed-marker", "probe-disagreement"})

    def test_no_authority_or_claim_promotion(self):
        for record in self.report["records"]:
            self.assertIsNone(record["ranking"])
            self.assertEqual(record["admission_state"], "not_admitted")
            self.assertEqual(record["rejection_state"], "not_rejected")
            self.assertEqual(record["deletion_state"], "not_deleted")
            self.assertIsNone(record["canonical_member"])
        self.assertTrue(all(value is False for value in self.report["claims"].values()))

class QualityMutationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.report = build_quality_report(MANIFEST)

    def _write_manifest_and_reject(self, mutate, pattern):
        broken = copy.deepcopy(self.manifest)
        mutate(broken)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            tc = temp_path / "TC-FIXTURE-005"
            prev = temp_path / "TC-FIXTURE-004"
            tc.mkdir(); prev.mkdir()
            (tc / "manifest.json").write_text(json.dumps(broken), encoding="utf-8")
            (tc / "records.json").write_text((MANIFEST.parent / "records.json").read_text(encoding="utf-8"), encoding="utf-8")
            (prev / "records.json").write_text((MANIFEST.parent.parent / "TC-FIXTURE-004" / "records.json").read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaisesRegex(TroveCurataQualityError, pattern):
                build_quality_report(tc / "manifest.json")

    def test_threshold_drift_rejected(self):
        self._write_manifest_and_reject(lambda m: m["configuration"]["thresholds"].update({"symbol_ratio":"0.300000"}), "threshold drift")

    def test_predecessor_head_drift_rejected(self):
        self._write_manifest_and_reject(lambda m: m["predecessor"].update({"exact_remedy_head":"0"*40}), "predecessor identity drift")

    def test_source_digest_drift_rejected(self):
        self._write_manifest_and_reject(lambda m: m["cases"][0].update({"expected_source_sha256":"0"*64}), "source digest drift")

    def test_route_escalation_rejected(self):
        self._write_manifest_and_reject(lambda m: m["cases"][0].update({"expected_route":"admit"}), "route vocabulary drift")

    def test_admission_authority_rejected(self):
        self._write_manifest_and_reject(lambda m: m["authority"].update({"providers_may_authorize_admission":True}), "authority escalation")

    def test_ranking_authority_rejected(self):
        self._write_manifest_and_reject(lambda m: m["authority"].update({"ranking_enabled":True}), "authority escalation")

    def test_external_dependency_rejected(self):
        self._write_manifest_and_reject(lambda m: m["authority"].update({"external_project_dependency":True}), "authority escalation")

    def test_hidden_disagreement_rejected_in_report(self):
        broken = copy.deepcopy(self.report)
        record = next(r for r in broken["records"] if r["case_id"] == "probe-disagreement")
        record["disagreement"] = False
        with self.assertRaisesRegex(TroveCurataQualityError, "disagreement drift"):
            validate_quality_report(broken)

    def test_ranking_in_report_rejected(self):
        broken = copy.deepcopy(self.report)
        broken["records"][0]["ranking"] = 1
        with self.assertRaisesRegex(TroveCurataQualityError, "ranking authority escalation"):
            validate_quality_report(broken)

    def test_claim_inflation_rejected(self):
        broken = copy.deepcopy(self.report)
        broken["claims"]["dataset_quality_certified"] = True
        with self.assertRaisesRegex(TroveCurataQualityError, "claim boundary drift"):
            validate_quality_report(broken)

if __name__ == "__main__":
    unittest.main()
