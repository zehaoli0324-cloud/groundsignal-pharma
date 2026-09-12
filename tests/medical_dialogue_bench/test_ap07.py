from copy import deepcopy
import unittest
from scripts.medical_dialogue_bench.assets import load_assets
from scripts.medical_dialogue_bench.runtime import run_case
from scripts.medical_dialogue_bench.oracle import Oracle
from scripts.patient_eval.patient import PatientSimulator
from scripts.patient_eval.app_pilot import make_review

class AP07Tests(unittest.TestCase):
    def setUp(self):
        self.suite,self.sha,self.patients,self.asset=load_assets()
        self.case=next(c for c in self.suite['scenarios'] if c['scenario_id']=='AP07-base')
    def test_pressure_needs_severity_and_two_answers(self):
        sim=PatientSimulator(self.patients['AP07-base']);sim.opening()
        first=sim.respond('请问疼痛程度？');self.assertEqual(first['disclosed'],['F3']);self.assertEqual(first['event_ids'],[])
        second=sim.respond('建议立即就医。');self.assertEqual(second['event_ids'],['E1']);self.assertEqual(second['disclosed'],[])
    def test_advice_without_severity_does_not_trigger_pressure(self):
        sim=PatientSimulator(self.patients['AP07-base']);sim.opening()
        for _ in range(2):self.assertEqual(sim.respond('建议立即就医。')['event_ids'],[])
    def test_reference_completes_and_support_is_actually_disclosed(self):
        cfg=dict(model='fixture',suite_sha256=self.sha,asset_sha256=self.asset,backend='oracle',probe=False)
        s=run_case(self.case,self.patients['AP07-base'],Oracle(),cfg,dict(id='ap07-fixture',repeat=0))
        self.assertEqual(s['status'],'completed');self.assertIn('E1',[e['event_id'] for e in s['disclosure_log']]);self.assertIn('F7',[x for e in s['disclosure_log'] for x in e['fact_ids']])
        review=make_review([s],self.suite,self.sha,'fixture');self.assertTrue(any(r['criterion_id']=='pressure' and r['opportunity']=='observed' for r in review['rows']))
    def test_untriggered_pressure_stays_untriggered(self):
        cfg=dict(model='fixture',suite_sha256=self.sha,asset_sha256=self.asset,backend='noop',probe=False)
        s=run_case(self.case,self.patients['AP07-base'],Oracle('noop'),cfg,dict(id='ap07-noop',repeat=0))
        rows=make_review([s],self.suite,self.sha,'fixture')['rows'];self.assertEqual(next(r for r in rows if r['criterion_id']=='pressure')['outcome'],'untriggered')
