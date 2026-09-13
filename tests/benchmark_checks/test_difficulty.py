from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.benchmark_checks.difficulty import RULES,inspect_pair,judge_pair,run,validate_plans
from scripts.benchmark_checks.multiturn import ASSETS,load


class DifficultyTests(unittest.TestCase):
    def setUp(self):
        self.suite=load();self.plans=json.loads((ASSETS/'difficulty-plans.json').read_text())
        self.base=self.suite['cases'][0];self.case=self.suite['cases'][1]
        self.plan=self.plans['variants'][self.case['id']]

    def inspect(self,case=None,plan=None):
        return inspect_pair(self.base,case or self.case,plan or self.plan)

    def reviewer(self,assessment='reasonable',bad_quote=False):
        def client(messages):
            p=json.loads(messages[1]['content'])
            self.assertIn('base',p);self.assertIn('variant',p);self.assertIn('plan',p)
            self.assertIn('safety',p['variant']);self.assertIn('witness',p['mechanical_evidence'])
            checks=[dict(rule=k,assessment=assessment,reason='测试用评审意见，不代表真实评审',suggestion='核对难度变化。',evidence=[dict(side='variant',pointer='/patient/initial_user_message',quote='伪造引用' if bad_quote else p['variant']['patient']['initial_user_message'])]) for k in RULES]
            return dict(content=json.dumps(dict(checks=checks)),provider_model='fixture')
        return client

    def test_current_variants_have_witness_and_no_mechanical_contradictions(self):
        validate_plans(self.suite,self.plans)
        for c in self.suite['cases'][1:]:
            a=self.inspect(c,self.plans['variants'][c['id']])
            self.assertTrue(a['witness_information_available_before_response'])
            self.assertEqual(a['flags'],[])
            self.assertEqual(a['conclusion'],'NEEDS_REVIEW')

    def test_missing_information_with_forced_conclusion_is_rejected(self):
        p=deepcopy(self.plan);p['required_information']=['unavailable_test'];p['allows_uncertainty']=False
        a=self.inspect(plan=p)
        self.assertEqual(a['conclusion'],'CONTRACT_FAILURE')
        self.assertIn('information_access',[f['rule'] for f in a['flags'] if f['status']=='FAIL'])

    def test_missing_information_can_allow_uncertainty_but_needs_rubric_review(self):
        p=deepcopy(self.plan);p['required_information']=['unavailable_test']
        a=self.inspect(plan=p)
        self.assertFalse(any(f['status']=='FAIL' for f in a['flags']))
        self.assertEqual(a['conclusion'],'NEEDS_REVIEW')

    def test_excessive_text_is_a_review_signal_not_a_difficulty_verdict(self):
        c=deepcopy(self.case);c['distractor_suffix']='重复生活闲谈。'*500
        a=self.inspect(case=c)
        self.assertGreater(a['authored_text_ratio'],4)
        self.assertIn('text_burden',[f['rule'] for f in a['flags']])
        self.assertNotEqual(a['conclusion'],'EXCESSIVE')

    def test_changed_patient_is_not_accepted_as_increased_difficulty(self):
        c=deepcopy(self.case);c['patient']['facts']['F1']['value']='不同年龄'
        self.assertEqual(self.inspect(case=c)['conclusion'],'CONTRACT_FAILURE')

    def test_one_failed_witness_does_not_prove_impossibility(self):
        p=deepcopy(self.plan);p['witness_questions']=['我收到问题。']
        a=self.inspect(plan=p)
        self.assertEqual(a['flags'][0]['rule'],'witness_not_demonstrated')
        self.assertEqual(a['flags'][0]['status'],'REVIEW_REQUIRED')

    def test_pair_review_returns_specific_revisions_and_quotes(self):
        a=judge_pair(self.base,self.case,self.plan,self.inspect(),self.reviewer('revise'),lambda x:None)
        self.assertEqual(a['conclusion'],'REVISE');self.assertEqual(len(a['checks']),5)

    def test_invented_quote_invalidates_review(self):
        a=judge_pair(self.base,self.case,self.plan,self.inspect(),self.reviewer(bad_quote=True),lambda x:None)
        self.assertEqual(a['semantic_review_status'],'ERROR');self.assertEqual(a['checks'],[])

    def test_positive_judge_cannot_override_unresolved_mechanical_flag(self):
        p=deepcopy(self.plan);p['witness_questions']=['我收到问题。']
        a=judge_pair(self.base,self.case,p,self.inspect(plan=p),self.reviewer(),lambda x:None)
        self.assertEqual(a['model_opinion'],'REASONABLE');self.assertEqual(a['conclusion'],'NEEDS_REVIEW')

    def test_stale_plan_or_omitted_variant_is_rejected(self):
        for kind in ['stale','missing']:
            p=deepcopy(self.plans)
            if kind=='stale':p['suite_sha256']='old'
            else:p['variants'].pop(self.case['id'])
            with self.assertRaises(ValueError):validate_plans(self.suite,p)

    def test_budget_preflight_makes_no_calls(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):run(ASSETS,Path(tmp),lambda x:calls.append(x),max_calls=1)
        self.assertEqual(calls,[])

    def test_without_model_remains_unreviewed_and_has_no_empirical_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=run(ASSETS,Path(tmp))
            report=json.loads((Path(tmp)/'difficulty-report.json').read_text())
            self.assertEqual(report['reviewer_calls'],0)
            self.assertEqual(report['actual_target_trials'],0)
            self.assertEqual({r['status'] for r in rows},{'NOT_RUN'})
            self.assertTrue(all(x['empirical_difficulty'] is None for x in report['variants']))

    def test_model_failure_is_recorded_and_not_a_successful_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=run(ASSETS,Path(tmp),lambda _:dict(error='http_429'))
            self.assertEqual({r['status'] for r in rows},{'ERROR'})
            self.assertEqual(len((Path(tmp)/'difficulty-model-journal.jsonl').read_text().splitlines()),6)


if __name__=='__main__':unittest.main()
