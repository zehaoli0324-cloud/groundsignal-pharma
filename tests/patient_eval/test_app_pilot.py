from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval import app_pilot as app


def fixture(family='AP05'):
    suite,sha=app.get_suite(); plan=app.make_plan(suite,sha,smoke=True)
    slot=next(s for s in plan['slots'] if s['scenario_id']==family+'-base')
    c=next(c for c in suite['scenarios'] if c['scenario_id']==slot['scenario_id'])
    s=dict(session_id='synthetic-test-01',scenario_id=c['scenario_id'],family_id=c['family_id'],
      variant=c['variant'],platform=slot['platform'],observability='black_box',status='completed',
      turns=[dict(turn_id='u1',role='user',content=c['prefix'][0]['content']),
             dict(turn_id='a1',role='assistant',content='请问时间线是什么？')],trace=[],observations=[],
      disclosure_log=[dict(turn_id='u1',action='opening',fact_ids=[],event_id=None,phase='natural',question_quote='')],
      metadata=dict(collected_at='2026-09-12T10:00:00+08:00',ended_at='2026-09-12T10:05:00+08:00',
        app_version='synthetic-test',platform_mode='synthetic-test',input_mode='text',operator='test',
        session_protocol_id=c['protocol_id'],conversation_reset=True,deidentification_confirmed=True,
        use_authorized=True,comparison_lane='free_dialogue',question_source='synthetic',
        suite_sha256=sha,scenario_sha256=app.scenario_digest(c),plan_sha256=app.scenario_digest(plan),
        slot_id=slot['slot_id'],app_pilot_version=app.VERSION,session_note='synthetic fixture only',
        memory_setting='未知',network_setting='未知',device='synthetic-test',stop_reason='test ended'))
    return suite,sha,plan,c,s


def add(s,action,content,ids=None,eid=None,answer='还需要进一步核对。',phase='natural',quote=''):
    n=len(s['disclosure_log'])+1
    s['turns'].append(dict(turn_id=f'u{n}',role='user',content=content))
    s['disclosure_log'].append(dict(turn_id=f'u{n}',action=action,fact_ids=ids or [],event_id=eid,phase=phase,question_quote=quote))
    if answer is not None:s['turns'].append(dict(turn_id=f'a{n}',role='assistant',content=answer))


class AppPilotTests(unittest.TestCase):
    def setUp(self):self.suite,self.sha,self.plan,self.case,self.s=fixture()
    def validate(self,s=None):return app.validate_records([s or self.s],self.suite,self.sha,self.plan)
    def reviewed(self):
        sessions=self.validate(); p=app.make_review(sessions,self.suite,self.sha,'A')
        row=next(r for r in p['rows'] if r['opportunity']=='observed')
        row.update(outcome='pass',serious_error=False,reason='测试原句可核对，不代表临床评审。',
                   evidence=[dict(turn_id='a1',quote='请问时间线是什么？')])
        return sessions,p,row
    def test_twelve_cases_six_single_factor_pairs(self):
        self.assertEqual(12,len(self.suite['scenarios']))
        self.assertEqual(6,len({s['family_id'] for s in self.suite['scenarios']}))
        self.assertEqual(24,len(app.make_plan(self.suite,self.sha)['slots']))
    def test_pair_other_field_mutation_rejected(self):
        suite=deepcopy(self.suite);suite['scenarios'][1]['facts'][0]['answer']='被改变'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'suite.json';p.write_text(json.dumps(suite),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'additional changed'):app.get_suite(p)
    def test_duplicate_run_rejected_even_new_session_id(self):
        other=deepcopy(self.s);other['session_id']='another-id'
        with self.assertRaisesRegex(ValueError,'duplicate planned'):
            app.validate_records([self.s,other],self.suite,self.sha,self.plan)
    def test_wrong_suite_and_case_versions_rejected(self):
        for field in ['suite_sha256','scenario_sha256','plan_sha256']:
            s=deepcopy(self.s);s['metadata'][field]='0'*64
            with self.assertRaises(ValueError):self.validate(s)
    def test_plan_mutation_rejected(self):
        plan=deepcopy(self.plan);plan['max_wait_seconds']=999
        with self.assertRaisesRegex(ValueError,'plan changed'):app.validate_records([self.s],self.suite,self.sha,plan)
    def test_wrong_content_and_fabricated_question_quote_rejected(self):
        add(self.s,'facts',self.case['facts'][0]['answer'],['F1'],quote='模型从未问过')
        with self.assertRaisesRegex(ValueError,'question quote'):self.validate()
        self.s['disclosure_log'][-1]['question_quote']='请问时间线是什么？'
        self.s['turns'][2]['content']='周五开始'
        with self.assertRaisesRegex(ValueError,'frozen disclosure'):self.validate()
    def test_due_correction_priority_and_no_early_event(self):
        add(self.s,'event',self.case['events'][0]['answer'],eid='E1')
        with self.assertRaisesRegex(ValueError,'event not eligible'):self.validate()
        self.s=fixture()[-1]
        add(self.s,'facts',self.case['facts'][0]['answer'],['F1'],quote='请问时间线是什么？')
        add(self.s,'unknown',self.case['unknown'])
        with self.assertRaisesRegex(ValueError,'due correction'):self.validate()
    def test_corrected_fact_cannot_revert_to_old_value(self):
        add(self.s,'facts',self.case['facts'][0]['answer'],['F1'],quote='请问时间线是什么？')
        add(self.s,'event',self.case['events'][0]['answer'],eid='E1',answer='请再确认时间线？')
        add(self.s,'facts',self.case['facts'][0]['answer'],['F1'],quote='请再确认时间线？')
        with self.assertRaisesRegex(ValueError,'frozen disclosure'):self.validate()
        self.s['turns'][-2]['content']=self.case['events'][0]['answer']
        self.validate()
    def test_natural_cannot_follow_probe(self):
        add(self.s,'probe',self.case['probe'],phase='probe')
        add(self.s,'unknown',self.case['unknown'])
        with self.assertRaisesRegex(ValueError,'natural phase'):self.validate()
    def test_raw_capture_cannot_self_score(self):
        self.s['observations']=[dict(criterion_id='inquiry',outcome='pass',source='human',
          reviewer_id='test',rubric_version='x',evidence_turn_ids=['a1'],reason='test')]
        with self.assertRaisesRegex(ValueError,'self-score'):self.validate()
    def test_blank_reviews_stay_unknown_and_untriggered(self):
        sessions=self.validate();p=app.make_review(sessions,self.suite,self.sha,'A')
        report=app.report(sessions,self.suite,self.sha,[p])
        self.assertIsNone(report['overall_pass'])
        self.assertTrue(all(m['conditional_pass_rate'] is None for m in report['metrics']))
        self.assertIn('untriggered',{r['outcome'] for r in p['rows']})
    def test_target_outage_has_no_invented_response(self):
        self.s['turns'].pop();self.s['status']='target_error';self.s['error_detail']='120秒无回答'
        sessions=self.validate();p=app.make_review(sessions,self.suite,self.sha,'A')
        self.assertIn('not_observed',{r['outcome'] for r in p['rows']})
        self.assertFalse(any(r['response_turn_id'] for r in p['rows']))
    def test_stale_review_rejected(self):
        sessions,p,row=self.reviewed();sessions[0]['turns'][1]['content']+='更改'
        with self.assertRaisesRegex(ValueError,'stale review'):app.validate_review(p,sessions,self.suite,self.sha)
    def test_deleted_or_rebound_review_rows_rejected(self):
        sessions,p,row=self.reviewed();p['rows'].pop()
        with self.assertRaisesRegex(ValueError,'missing or extra'):app.validate_review(p,sessions,self.suite,self.sha)
        sessions,p,row=self.reviewed();row['response_turn_id']='u1'
        with self.assertRaisesRegex(ValueError,'boundary changed'):app.validate_review(p,sessions,self.suite,self.sha)
    def test_fabricated_and_future_quotes_rejected(self):
        sessions,p,row=self.reviewed();row['evidence'][0]['quote']='不存在的原句'
        with self.assertRaisesRegex(ValueError,'quote is not'):app.validate_review(p,sessions,self.suite,self.sha)
        add(self.s,'unknown',self.case['unknown'])
        sessions=self.validate();p=app.make_review(sessions,self.suite,self.sha,'A')
        row=next(r for r in p['rows'] if r['response_turn_id']=='a1')
        row.update(outcome='pass',serious_error=False,reason='test',evidence=[dict(turn_id='a2',quote='还需要进一步核对。')])
        with self.assertRaisesRegex(ValueError,'future evidence'):app.validate_review(p,sessions,self.suite,self.sha)
    def test_untriggered_cannot_pass(self):
        sessions,p,_=self.reviewed();row=next(r for r in p['rows'] if r['opportunity']=='untriggered');row['outcome']='pass'
        with self.assertRaisesRegex(ValueError,'cannot be scored'):app.validate_review(p,sessions,self.suite,self.sha)
    def test_unknown_safety_not_zero_and_serious_cannot_pass(self):
        sessions,p,row=self.reviewed();row['serious_error']=None
        with self.assertRaisesRegex(ValueError,'safety assessment'):app.validate_review(p,sessions,self.suite,self.sha)
        row['serious_error']=True
        with self.assertRaisesRegex(ValueError,'serious error cannot pass'):app.validate_review(p,sessions,self.suite,self.sha)
    def test_dual_review_disagreement_stays_disputed(self):
        sessions,p,row=self.reviewed();q=deepcopy(p);q['reviewer_id']='B'
        next(r for r in q['rows'] if r['row_id']==row['row_id'])['outcome']='fail'
        report=app.report(sessions,self.suite,self.sha,[p,q])
        self.assertEqual([row['row_id']],report['disagreement_row_ids']);self.assertEqual(0,report['exact_agreement'])
        self.assertFalse(report['clinical_approval'])
    def test_duplicate_reviewer_rejected(self):
        sessions,p,_=self.reviewed()
        with self.assertRaisesRegex(ValueError,'reviewers must differ'):app.report(sessions,self.suite,self.sha,[p,p])
    def test_invalid_measurement_is_counted_but_not_scored(self):
        self.s.update(status='measurement_invalid',invalid_reason='采集备注无法核实',invalid_component='collector')
        sessions=self.validate();p=app.make_review(sessions,self.suite,self.sha,'A')
        report=app.report(sessions,self.suite,self.sha,[p])
        self.assertEqual([],p['rows']);self.assertEqual(1,report['statuses']['measurement_invalid'])
    def test_html_embedded_json_cannot_execute_answer(self):
        html=app.render_page('review.html',{'text':'</script><script>alert(1)</script>'})
        self.assertNotIn('</script><script>alert',html)
        self.assertIn('\\u003c/script>',html)
    def test_import_roundtrip_is_stable(self):
        sessions=self.validate()
        self.assertEqual(sessions,app.validate_records(sessions,self.suite,self.sha,self.plan))


if __name__=='__main__':unittest.main()
