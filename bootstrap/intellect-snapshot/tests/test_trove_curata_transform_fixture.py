from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from grand_intellect.trove_curata_transform_contract import FALSE_CLAIMS, TroveCurataTransformError, load_manifest
from grand_intellect.trove_curata_transform_engine import evaluate_plan, predecessor_context, simulate_provider_fragment
from grand_intellect.trove_curata_transform_report import build_report, validate_report

ROOT=Path(__file__).resolve().parents[1]
MANIFEST_PATH=ROOT/'fixtures/trove_curata/TC-FIXTURE-003/manifest.json'
VERSIONS={'presidio-anonymizer':'2.2.363','presidio-analyzer':'2.2.363','regex':'2026.7.19'}

class TransformFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load_manifest(MANIFEST_PATH)
        cls.report=build_report(cls.manifest,MANIFEST_PATH.parent,VERSIONS,provider_transform=simulate_provider_fragment)
        cls.pred=json.loads((MANIFEST_PATH.parent/'../TC-FIXTURE-002/manifest.json').read_text())
        cls.pred_root=(MANIFEST_PATH.parent/'../TC-FIXTURE-002').resolve()

    def case(self, cid): return next(c for c in self.manifest['cases'] if c['case_id']==cid)
    def report_case(self,cid): return next(c for c in self.report['cases'] if c['case_id']==cid)
    def context(self,cid):
        c=self.case(cid); return predecessor_context(self.pred,self.pred_root,c['predecessor_case_id'])

    def test_manifest_class_coverage(self): self.assertEqual(len(self.manifest['cases']),13)
    def test_report_passes(self): self.assertTrue(self.report['passed'])
    def test_claims_all_false(self): self.assertEqual(set(self.report['claims']),FALSE_CLAIMS); self.assertFalse(any(self.report['claims'].values()))
    def test_stale_source_rejected(self): self.assertEqual(evaluate_plan(self.case('stale-source-rejection'),self.context('stale-source-rejection'))['status'],'rejected_stale_source')
    def test_overlap_rejected(self): self.assertEqual(evaluate_plan(self.case('overlap-rejection'),self.context('overlap-rejection'))['status'],'rejected_overlap')
    def test_operator_rejected(self): self.assertEqual(evaluate_plan(self.case('operator-rejection'),self.context('operator-rejection'))['status'],'rejected_operator')
    def test_provider_disagreement_preserved(self): self.assertTrue(self.report_case('provider-baseline-disagreement')['transformation_receipt']['provider_disagreement'])
    def test_partial_residual_explicit(self): self.assertGreater(self.report_case('partial-residual')['residual_audit']['observation_count'],0)
    def test_controls_byte_identical(self):
        for cid in ('negative-control','code-math-control','policy-withheld'):
            c=self.report_case(cid); self.assertEqual(c['provider_output'],c['baseline_output'])
    def test_duplicate_identities_equal(self):
        d=self.report['duplicate_checks'][0]; self.assertTrue(all(d[k] for k in ('source_digest_equal','plan_digest_equal','output_digest_equal','receipt_digest_equal')))
    def test_utf8_byte_binding(self):
        ctx=self.context('multilingual-utf8'); obs=ctx['provider_observation_set']['observations'][0]
        self.assertEqual(ctx['text'].encode()[obs['start_byte']:obs['end_byte']].decode(),obs['matched_text'])
    def test_observation_digest_mutation_rejected(self):
        c=copy.deepcopy(self.case('email-phone-replacement')); c['canonical_observation_digest']='0'*64
        self.assertEqual(evaluate_plan(c,self.context('email-phone-replacement'))['status'],'rejected_observation_digest')
    def test_duplicate_observation_mutation_rejected(self):
        c=copy.deepcopy(self.case('email-phone-replacement')); c['operations'].append(copy.deepcopy(c['operations'][0]))
        self.assertEqual(evaluate_plan(c,self.context('email-phone-replacement'))['status'],'rejected_duplicate_observation')
    def test_span_mutation_rejected(self):
        c=copy.deepcopy(self.case('email-phone-replacement')); c['operations'][0]['start_char']+=1
        self.assertEqual(evaluate_plan(c,self.context('email-phone-replacement'))['status'],'rejected_observation_identity')
    def test_parameter_mutation_rejected(self):
        c=copy.deepcopy(self.case('postal-network-masking')); c['operations'][0]['parameters']['chars_to_mask']=99
        self.assertEqual(evaluate_plan(c,self.context('postal-network-masking'))['status'],'rejected_parameters')
    def assert_invalid(self, mutate):
        r=copy.deepcopy(self.report); mutate(r)
        with self.assertRaises(TroveCurataTransformError): validate_report(r,self.manifest,MANIFEST_PATH.parent)
    def test_output_digest_mutation_rejected(self): self.assert_invalid(lambda r:r['cases'][0]['provider_output_record'].__setitem__('output_sha256','0'*64))
    def test_hidden_disagreement_rejected(self): self.assert_invalid(lambda r:r['cases'][0]['transformation_receipt'].__setitem__('provider_disagreement',True))
    def test_residual_suppression_rejected(self): self.assert_invalid(lambda r:r['cases'][-1]['residual_audit'].__setitem__('observations',[]))
    def test_route_escalation_rejected(self): self.assert_invalid(lambda r:r['cases'][0]['routing_record'].__setitem__('route','admitted'))
    def test_provider_authority_rejected(self): self.assert_invalid(lambda r:r['cases'][0]['transformation_receipt'].__setitem__('provider_may_select_spans',True))
    def test_claim_inflation_rejected(self): self.assert_invalid(lambda r:r['claims'].__setitem__('privacy_compliance_proved',True))
    def test_external_dependency_rejected(self): self.assert_invalid(lambda r:r['configuration'].__setitem__('external_project_dependency',True))

if __name__=='__main__': unittest.main()
