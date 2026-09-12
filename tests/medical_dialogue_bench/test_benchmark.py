from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.medical_dialogue_bench.assets import load_assets,POLICY
from scripts.medical_dialogue_bench.runtime import run_case,batch,schedule
from scripts.medical_dialogue_bench.oracle import Oracle
from scripts.medical_dialogue_bench.verifier import verify
from scripts.medical_dialogue_bench.client import ResponsesClient
from scripts.medical_dialogue_bench.judge import draft
from scripts.patient_eval.app_pilot import make_review,validate_review
from scripts.patient_eval.import_batch import scenario_digest
from scripts.patient_eval.patient_intent import classify_requested_slots

class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.suite,self.sha,self.patients,self.asset=load_assets()
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/'run'
    def run_batch(self,mode='oracle',**kwargs):
        batch(self.suite,self.sha,self.patients,self.asset,Oracle(mode),self.out,backend=mode,model='authored-'+mode,**kwargs)
        return verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_oracle_runs_twelve_independent_cases(self):
        sessions,r=self.run_batch();self.assertEqual(r['sessions'],12);self.assertEqual(r['statuses'],{'completed':12})
        for s in sessions:
            self.assertEqual(len(s['requests'][0]['messages']),2)
            self.assertEqual(s['requests'][0]['messages'][0]['content'],POLICY)
    def test_no_hidden_information_in_payload(self):
        sessions,_=self.run_batch()
        for s in sessions:
            c=next(c for c in self.suite['scenarios'] if c['scenario_id']==s['scenario_id'])
            for r in s['requests']:
                self.assertTrue(all(set(m)=={'role','content'} for m in r['messages']))
                text=json.dumps(r['messages'],ensure_ascii=False)
                for key in ['source_ids','fail_example','clinical_approval','oracle-policy','available_fact_ids']:self.assertNotIn(key,text)
            self.assertNotIn(c['facts'][0]['answer'],s['requests'][0]['messages'][1]['content'])
    def test_noop_integrity_is_not_clinical_pass(self):
        _,r=self.run_batch('noop');self.assertIsNone(r['clinical_score']);self.assertEqual(r['readiness'],'NEEDS_SEMANTIC_REVIEW')
    def test_wrong_answer_not_confused_with_engineering_failure(self):
        _,r=self.run_batch('naive');self.assertEqual(r['engineering_integrity'],'PASS');self.assertFalse(r['clinical_approval'])
    def test_correction_is_actually_delivered(self):
        sessions,_=self.run_batch()
        for s in sessions:
            if s['family_id']=='AP05':
                self.assertIn('E1',[e['event_id'] for e in s['disclosure_log']])
                self.assertIn('周一',s['turns'][-1]['content'])
    def test_unsupported_patient_request_invalidates_measurement(self):
        def client(_):return dict(content='请问你的心电图结果是什么？')
        cfg=dict(model='fixture',suite_sha256=self.sha,asset_sha256=self.asset,backend='oracle',probe=False)
        s=run_case(self.suite['scenarios'][0],self.patients['AP01-base'],client,cfg,dict(id='x',repeat=0))
        self.assertEqual(s['status'],'measurement_invalid');self.assertEqual(s['invalid_component'],'simulator')
    def test_declarative_whether_does_not_count_as_question(self):
        facts=self.patients['AP02-base']['facts']
        r=classify_requested_slots('再决定是否需要及怎样使用。',facts)
        self.assertFalse(r['requested_slots']);self.assertNotIn('unsupported_or_ambiguous_slot',[c['reason'] for c in r['clauses']])
    def test_negated_and_quoted_questions_do_not_disclose(self):
        facts=self.patients['AP05-base']['facts']
        for text in ['不用告诉我时间线。','示例：“请问时间线是什么？”']:
            self.assertFalse(classify_requested_slots(text,facts)['requested_slots'])
    def test_budget_preflight_makes_zero_calls(self):
        calls=[]
        with self.assertRaises(ValueError):batch(self.suite,self.sha,self.patients,self.asset,lambda x:calls.append(x),self.out,backend='oracle',model='fixture',max_calls=1)
        self.assertFalse(calls)
    def test_probe_has_separate_phase(self):
        sessions,_=self.run_batch(probe=True,max_calls=84)
        self.assertTrue(all(s['disclosure_log'][-1]['phase']=='probe' for s in sessions))
    def test_target_timeout_preserved(self):
        cfg=dict(model='fixture',suite_sha256=self.sha,asset_sha256=self.asset,backend='oracle',probe=False)
        s=run_case(self.suite['scenarios'][0],self.patients['AP01-base'],lambda _:dict(error='transport_error'),cfg,dict(id='x',repeat=0))
        self.assertEqual(s['status'],'target_error');self.assertEqual(len(s['turns']),1)
    def test_partial_answer_not_scored_as_complete(self):
        cfg=dict(model='fixture',suite_sha256=self.sha,asset_sha256=self.asset,backend='oracle',probe=False)
        s=run_case(self.suite['scenarios'][0],self.patients['AP01-base'],lambda _:dict(content='部分文字',error='output_incomplete'),cfg,dict(id='x',repeat=0))
        self.assertEqual(len(s['turns']),1);self.assertEqual(s['requests'][0]['result']['content'],'部分文字')
    def test_missing_case_rejected(self):
        self.run_batch();next(self.out.glob('*.r0.json')).unlink()
        with self.assertRaises(ValueError):verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_extra_case_rejected(self):
        self.run_batch();(self.out/'extra.json').write_text('{}')
        with self.assertRaises(ValueError):verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_changed_trace_rejected(self):
        self.run_batch();p=next(self.out.glob('*.r0.json'));s=json.loads(p.read_text());s['requests'][0]['messages'].append(dict(role='user',content='hidden facts'));p.write_text(json.dumps(s))
        with self.assertRaises(ValueError):verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_changed_disclosure_rejected(self):
        self.run_batch();p=next(self.out.glob('*.r0.json'));s=json.loads(p.read_text());s['disclosure_log'][0]['fact_ids']=['F1'];p.write_text(json.dumps(s))
        with self.assertRaises(ValueError):verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_changed_journal_rejected(self):
        self.run_batch();p=next(self.out.glob('*.jsonl'));p.write_text('')
        with self.assertRaises(ValueError):verify(self.out,self.suite,self.sha,self.patients,self.asset)
    def test_resume_skips_completed_calls(self):
        self.run_batch();calls=[]
        batch(self.suite,self.sha,self.patients,self.asset,lambda x:calls.append(x),self.out,backend='oracle',model='authored-oracle',resume=True)
        self.assertEqual(calls,[])
    def test_interrupted_journal_blocks_resume(self):
        self.run_batch();next(self.out.glob('*.r0.json')).unlink()
        with self.assertRaisesRegex(ValueError,'interrupted'):batch(self.suite,self.sha,self.patients,self.asset,Oracle(),self.out,backend='oracle',model='authored-oracle',resume=True)
    def test_blank_review_never_passes(self):
        ss,_=self.run_batch();p=make_review(ss,self.suite,self.sha,'A');_,r=verify(self.out,self.suite,self.sha,self.patients,self.asset,[p])
        self.assertTrue(all(x['conditional_pass_rate'] is None for x in r['clinical_result']['metrics']))
    def test_future_evidence_rejected(self):
        ss,_=self.run_batch();p=make_review(ss,self.suite,self.sha,'A');row=next(r for r in p['rows'] if r['response_turn_id']=='a1');s=next(s for s in ss if s['session_id']==row['session_id'])
        row.update(outcome='fail',serious_error=False,reason='fixture',evidence=[dict(turn_id=s['turns'][-1]['turn_id'],quote=s['turns'][-1]['content'])])
        with self.assertRaises(ValueError):validate_review(p,ss,self.suite,self.sha)
    def test_judge_no_later_turns_or_oracle(self):
        ss,_=self.run_batch();seen=[]
        def judge(messages):
            data=json.loads(messages[1]['content']);seen.append(data)
            self.assertEqual(data['visible_turns'][-1]['turn_id'],data['target_turn_id'])
            self.assertNotIn('oracle',messages[1]['content'])
            return dict(content='not json')
        p,a=draft(ss,self.suite,self.sha,judge,'fixture',max_calls=500)
        self.assertTrue(seen);self.assertEqual(a['judge_calls'],len(a['invalid_or_failed_rows']));self.assertTrue(all(r['outcome'] in {'unassessed','untriggered'} for r in p['rows']))
    def test_responses_payload_and_parse(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return json.dumps(dict(status='completed',model='requested-test-model',output=[dict(type='reasoning',summary=[]),dict(type='message',role='assistant',content=[dict(type='output_text',text='回答')])],usage=dict(input_tokens=10,output_tokens=4,total_tokens=14))).encode()
        with patch.dict('os.environ',{'BENCH_TEST_KEY':'test-not-real'}):client=ResponsesClient('requested-test-model','BENCH_TEST_KEY')
        with patch.object(client.opener,'open',return_value=Response()) as opening:
            result=client([dict(role='user',content='问题')]);payload=json.loads(opening.call_args.args[0].data)
        self.assertEqual(result['content'],'回答');self.assertFalse(payload['store']);self.assertNotIn('previous_response_id',payload);self.assertNotIn('temperature',payload)
    def test_no_credential_requires_no_network(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ValueError):ResponsesClient('explicit-model')

if __name__=='__main__':unittest.main()
