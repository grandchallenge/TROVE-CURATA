from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from grand_intellect.trove_curata_fixture import (
    REQUIRED_CASE_CLASSES,
    TroveCurataFixtureError,
    build_report,
    identify_language_metadata,
    load_manifest,
    normalize_text,
    novel_output_tokens,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fixtures" / "trove_curata" / "TC-FIXTURE-001" / "manifest.json"


class TroveCurataFixtureTests(unittest.TestCase):
    def test_normalization_is_idempotent(self) -> None:
        value = "A\t  line\r\n\r\n  second   line  "
        normalized = normalize_text(value)
        self.assertEqual(normalized, "A line\nsecond line")
        self.assertEqual(normalize_text(normalized), normalized)

    def test_language_metadata_is_explicit_and_fail_closed(self) -> None:
        self.assertEqual(identify_language_metadata('<html lang="EN-ca">'), "en-ca")
        self.assertEqual(identify_language_metadata("<html><body>x</body></html>"), "und")

    def test_novel_token_detection(self) -> None:
        raw = "<p>Alpha &amp; beta.</p>"
        self.assertEqual(novel_output_tokens(raw, "Alpha & beta"), [])
        self.assertEqual(novel_output_tokens(raw, "Alpha gamma"), ["gamma"])

    def test_manifest_has_exact_class_coverage(self) -> None:
        manifest = load_manifest(MANIFEST)
        self.assertEqual({case["case_class"] for case in manifest["cases"]}, REQUIRED_CASE_CLASSES)
        self.assertEqual(len(manifest["cases"]), 9)

    def test_manifest_rejects_network_dependency(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["cases"][0]["path"] = "https://example.test/page.html"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(TroveCurataFixtureError):
                load_manifest(path)

    def test_pure_report_builder_accepts_declared_fixture(self) -> None:
        manifest = load_manifest(MANIFEST)
        root = MANIFEST.parent
        extracted_rows = []
        for case in manifest["cases"]:
            raw_html = (root / case["path"]).read_text(encoding="utf-8")
            text = " ".join(case["required_tokens"])
            if case.get("duplicate_group"):
                text = "A shared duplicate article about governed data fixtures."
            extracted_rows.append({"case_id": case["case_id"], "html": raw_html, "extracted_text": text})
        report = build_report(manifest, root, extracted_rows, {"daft": "0.7.21", "trafilatura": "2.1.0"})
        self.assertTrue(report["passed"])
        self.assertFalse(report["claims"]["corpus_admitted"])
        policy_case = next(case for case in report["cases"] if case["case_class"] == "policy_review")
        self.assertEqual(policy_case["passport"]["admission_state"], "review_required")

    def test_report_rejects_claim_or_identity_drift_by_construction(self) -> None:
        manifest = load_manifest(MANIFEST)
        mutated = copy.deepcopy(manifest)
        mutated["fixture_id"] = "OTHER"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaises(TroveCurataFixtureError):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()
