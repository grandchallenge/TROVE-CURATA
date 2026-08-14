from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from grand_intellect.trove_curata_duplicate_contract import (
    PROVIDER_LOCK,
    TroveCurataDuplicateError,
    canonical_json_bytes,
    load_manifest,
    load_records,
)
from grand_intellect.trove_curata_duplicate_engine import (
    derive_tc003_baseline_output,
    simulate_datasketch_score,
)
from grand_intellect.trove_curata_duplicate_report import build_report, validate_report

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "fixtures" / "trove_curata" / "TC-FIXTURE-004" / "manifest.json"


class TroveCurataDuplicateFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(MANIFEST_PATH)
        cls.records = load_records(MANIFEST_PATH.parent / cls.manifest["records_file"])
        cls.versions = dict(PROVIDER_LOCK)
        cls.report = build_report(
            cls.manifest,
            cls.records,
            MANIFEST_PATH.parent,
            cls.versions,
            simulate_datasketch_score,
        )

    def validate(self, report: dict) -> None:
        validate_report(
            report,
            self.manifest,
            self.records,
            MANIFEST_PATH.parent,
            self.versions,
            simulate_datasketch_score,
        )

    @staticmethod
    def _write_json(root: Path, name: str, value: dict) -> Path:
        path = root / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def test_manifest_and_records_load(self) -> None:
        self.assertEqual(self.manifest["fixture_id"], "TC-FIXTURE-004")
        self.assertEqual(len(self.records["records"]), 29)

    def test_pure_replay_passes(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["pair_count"], 16)
        self.assertEqual(len(self.report["components"]), 6)

    def test_replay_is_byte_deterministic(self) -> None:
        second = build_report(
            self.manifest,
            self.records,
            MANIFEST_PATH.parent,
            self.versions,
            simulate_datasketch_score,
        )
        self.assertEqual(canonical_json_bytes(self.report), canonical_json_bytes(second))

    def test_expected_provider_scores_are_retained(self) -> None:
        pairs = {item["case_id"]: item for item in self.report["pairs"]}
        self.assertEqual(
            pairs["reordered-sentences"]["provider_observation"]["score"],
            "0.671875",
        )
        self.assertEqual(
            pairs["method-disagreement"]["provider_observation"]["score"],
            "0.718750",
        )
        self.assertEqual(
            pairs["threshold-above"]["provider_observation"]["score"],
            "0.773438",
        )

    def test_normalized_duplicate_is_not_byte_duplicate(self) -> None:
        pair = next(
            item for item in self.report["pairs"] if item["case_id"] == "normalized-text"
        )
        self.assertFalse(pair["exact_byte_equal"])
        self.assertTrue(pair["normalized_text_equal"])
        self.assertEqual(pair["edge_basis"], "normalized_text")

    def test_transitive_component_does_not_fabricate_direct_edge(self) -> None:
        pairs = {item["case_id"]: item for item in self.report["pairs"]}
        self.assertTrue(pairs["transitive-ab"]["admitted_edge"])
        self.assertTrue(pairs["transitive-bc"]["admitted_edge"])
        self.assertFalse(pairs["transitive-ac"]["admitted_edge"])
        component = next(
            item
            for item in self.report["components"]
            if item["members"] == ["trans-a", "trans-b", "trans-c"]
        )
        self.assertEqual(len(component["admitted_observation_ids"]), 2)

    def test_chain_outputs_are_bound(self) -> None:
        predecessor = MANIFEST_PATH.parent / self.manifest["predecessor_manifest"]
        self.assertEqual(
            derive_tc003_baseline_output(predecessor, "duplicate-a"),
            "Duplicate synthetic contact: <EMAIL_ADDRESS> and <PHONE_NUMBER>.",
        )

    def test_manifest_rejects_self_pair(self) -> None:
        broken = copy.deepcopy(self.manifest)
        broken["cases"][0]["right_record_id"] = broken["cases"][0]["left_record_id"]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(Path(directory), "manifest.json", broken)
            with self.assertRaisesRegex(
                TroveCurataDuplicateError,
                "self-pairs are prohibited",
            ):
                load_manifest(path)

    def test_manifest_rejects_duplicate_unordered_pair(self) -> None:
        broken = copy.deepcopy(self.manifest)
        first = broken["cases"][0]
        second = broken["cases"][1]
        second["left_record_id"] = first["right_record_id"]
        second["right_record_id"] = first["left_record_id"]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(Path(directory), "manifest.json", broken)
            with self.assertRaisesRegex(
                TroveCurataDuplicateError,
                "duplicate unordered pair identity",
            ):
                load_manifest(path)

    def test_records_reject_duplicate_identity(self) -> None:
        broken = copy.deepcopy(self.records)
        broken["records"][1]["record_id"] = broken["records"][0]["record_id"]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(Path(directory), "records.json", broken)
            with self.assertRaisesRegex(
                TroveCurataDuplicateError,
                "invalid or duplicate record identity",
            ):
                load_records(path)


if __name__ == "__main__":
    unittest.main()
