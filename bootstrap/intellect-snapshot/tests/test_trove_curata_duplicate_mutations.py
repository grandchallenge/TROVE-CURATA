from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from grand_intellect.trove_curata_duplicate_contract import PROVIDER_LOCK, TroveCurataDuplicateError, canonical_json_bytes, load_manifest, load_records
from grand_intellect.trove_curata_duplicate_engine import derive_tc003_baseline_output, simulate_datasketch_score
from grand_intellect.trove_curata_duplicate_report import build_report, validate_report
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / 'fixtures' / 'trove_curata' / 'TC-FIXTURE-004' / 'manifest.json'
if __name__ == '__main__':
    unittest.main()

class TroveCurataDuplicateMutationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(MANIFEST_PATH)
        cls.records = load_records(MANIFEST_PATH.parent / cls.manifest['records_file'])
        cls.versions = dict(PROVIDER_LOCK)
        cls.report = build_report(cls.manifest, cls.records, MANIFEST_PATH.parent, cls.versions, simulate_datasketch_score)

    def validate(self, report) -> None:
        validate_report(report, self.manifest, self.records, MANIFEST_PATH.parent, self.versions, simulate_datasketch_score)

    def test_mutation_rejects_pair_order_drift(self) -> None:
        broken = copy.deepcopy(self.report)
        pair = broken['pairs'][0]
        pair['left_record_id'], pair['right_record_id'] = (pair['right_record_id'], pair['left_record_id'])
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_hidden_disagreement(self) -> None:
        broken = copy.deepcopy(self.report)
        pair = next((item for item in broken['pairs'] if item['case_id'] == 'method-disagreement'))
        pair['disagreement_present'] = False
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_score_inflation(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['provider_observation']['score'] = '1.000000'
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_fabricated_edge(self) -> None:
        broken = copy.deepcopy(self.report)
        pair = next((item for item in broken['pairs'] if item['case_id'] == 'transitive-ac'))
        pair['admitted_edge'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_component_drift(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['components'][0]['members'].append('negative-a')
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_provider_edge_authority(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['provider_observation']['may_authorize_edge'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'provider edge authority'):
            self.validate(broken)

    def test_mutation_rejects_provider_route_authority(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['provider_observation']['may_authorize_route'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'provider route authority'):
            self.validate(broken)

    def test_mutation_rejects_deletion(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['routing_record']['deletion_state'] = 'deleted'
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'deletion escalation'):
            self.validate(broken)

    def test_mutation_rejects_suppression(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['routing_record']['suppression_state'] = 'suppressed'
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'suppression escalation'):
            self.validate(broken)

    def test_mutation_rejects_admission(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['pairs'][0]['routing_record']['admission_state'] = 'admitted'
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'admission escalation'):
            self.validate(broken)

    def test_mutation_rejects_canonical_member_selection(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['components'][0]['canonical_member'] = broken['components'][0]['members'][0]
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_source_record_mutation(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['records'][0]['source_record_mutated'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'canonical duplicate report drift'):
            self.validate(broken)

    def test_mutation_rejects_external_dependency(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['configuration']['external_project_dependency'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'external project dependency'):
            self.validate(broken)

    def test_mutation_rejects_claim_inflation(self) -> None:
        broken = copy.deepcopy(self.report)
        broken['claims']['dataset_quality_proved'] = True
        with self.assertRaisesRegex(TroveCurataDuplicateError, 'claim inflation'):
            self.validate(broken)
