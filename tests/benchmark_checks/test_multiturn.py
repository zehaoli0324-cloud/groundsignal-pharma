from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.benchmark_checks.multiturn import (
    ContractError, PresentationPatient, load, validate_suite, run_transcript,
    verify_trace, review_template, safety_summary, verify_safety_report, acceptance,
)


class MultiTurnAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.suite=load();self.cases={c['variant']:c for c in self.suite['cases']}

    def assertRule(self,rule,call):
        with self.assertRaises(ContractError) as caught: call()
        self.assertEqual(caught.exception.rule,rule)

    def test_complete_factorial_contract_passes(self):
        self.assertEqual(len(validate_suite(self.suite)['cases']),4)

    def test_ambiguous_hidden_fact_marked_disclosed_is_rejected(self):
        bad=deepcopy(self.suite)
        bad['cases'][1]['presentations']['F3'][0]['discloses']=['F3']
        self.assertRule('ambiguous_hidden_disclosure',lambda:validate_suite(bad))

    def test_distractor_cannot_change_clinical_truth(self):
        bad=deepcopy(self.suite);bad['cases'][2]['patient']['facts']['F1']['value']='另一年龄'
        self.assertRule('clinical_fact_invariance',lambda:validate_suite(bad))

    def test_distractor_cannot_add_clinical_information_in_suffix(self):
        bad=deepcopy(self.suite);bad['cases'][2]['distractor_suffix']='另外体温39度。'
        self.assertRule('distractor_content',lambda:validate_suite(bad))

    def test_quoted_questions_do_not_disclose_or_trigger_events(self):
        for case in self.cases.values():
            for text in ['示例：“请问疼痛严重程度如何？”','不用告诉我疼痛程度。']:
                with self.subTest(case=case['id'],text=text):
                    t=run_transcript(case,[text]*5)
                    self.assertEqual(t['snapshot']['disclosed'],[])
                    self.assertEqual(t['snapshot']['fired_event_ids'],[])
                    self.assertEqual(t['snapshot']['not_reached_event_ids'],['E1'])

    def test_actual_clarification_discloses_then_event_fires_later(self):
        sim=PresentationPatient(self.cases['mixed']);sim.opening()
        quote=sim.respond('示例：“请问疼痛严重程度如何？”')
        first=sim.respond('请问疼痛严重程度如何？')
        self.assertEqual(quote['disclosed'],[]);self.assertEqual(first['disclosed'],[])
        self.assertNotIn('F3',sim.snapshot()['disclosed'])
        second=sim.respond('请问疼痛严重程度如何？')
        self.assertEqual(second['disclosed'],['F3']);self.assertEqual(second['event_ids'],[])
        event=sim.respond('我收到你的补充。')
        self.assertEqual(event['event_ids'],['E1'])

    def test_runtime_ambiguous_disclosure_bug_is_detectable(self):
        case=self.cases['ambiguous']
        original=PresentationPatient._answer_slots
        def broken(sim,slots):
            content,_=original(sim,slots)
            return content,list(slots)  # Reproduces marking requested as disclosed.
        with patch.object(PresentationPatient,'_answer_slots',broken):
            bad=run_transcript(case,['请问疼痛严重程度如何？','我收到补充。'])
        self.assertRule('disclosure_replay',lambda:verify_trace(case,bad))

    def test_runtime_quoted_question_bug_triggers_false_event_and_fails_replay(self):
        case=self.cases['base']
        with patch('scripts.patient_eval.patient.classify_requested_slots',return_value={'requested_slots':['F3'],'clauses':[]}):
            bad=run_transcript(case,['示例：“请问疼痛严重程度如何？”']*3)
        self.assertEqual(bad['snapshot']['fired_event_ids'],['E1'])
        self.assertRule('disclosure_replay',lambda:verify_trace(case,bad))

    def test_untriggered_safety_cannot_report_zero_errors(self):
        case=self.cases['base'];t=run_transcript(case,['我收到问题。'])
        rows=review_template(case,t);report=safety_summary(case,t,rows)
        self.assertEqual(report['opportunities'],0);self.assertIsNone(report['safety_errors'])
        report['safety_errors']=0
        self.assertRule('safety_denominator',lambda:verify_safety_report(case,t,rows,report))

    def test_unassessed_and_partial_safety_remain_unknown(self):
        case=self.cases['base'];t=run_transcript(case,['请问疼痛严重程度如何？','我收到信息。','我收到信息。','我收到信息。'])
        rows=review_template(case,t);report=safety_summary(case,t,rows)
        self.assertEqual(report['opportunities'],2);self.assertIsNone(report['safety_errors'])
        rows[2].update(outcome='pass',quote='我收到信息。')
        partial=safety_summary(case,t,rows)
        self.assertEqual(partial['coverage'],'partial');self.assertIsNone(partial['error_rate'])
        rows[3].update(outcome='fail',quote='我收到信息。')
        complete=safety_summary(case,t,rows)
        self.assertEqual(complete['scored'],2);self.assertEqual(complete['safety_errors'],1)
        self.assertEqual(complete['error_rate'],0.5)

    def test_later_patient_event_cannot_score_previous_answer(self):
        case=self.cases['base'];t=run_transcript(case,['请问疼痛严重程度如何？','我收到信息。','我收到信息。'])
        rows=review_template(case,t)
        self.assertEqual([r['outcome'] for r in rows],['untriggered','untriggered','unassessed'])
        rows[1].update(outcome='pass',quote='我收到信息。')
        self.assertRule('safety_trigger',lambda:safety_summary(case,t,rows))

    def test_missing_opportunities_cannot_hide_denominator(self):
        case=self.cases['base'];t=run_transcript(case,['我收到问题。'])
        self.assertRule('safety_coverage',lambda:safety_summary(case,t,[]))

    def test_legacy_suite_is_explicitly_incompatible(self):
        bad=deepcopy(self.suite);bad['track']='app-pilot/v1'
        self.assertRule('unsupported_track',lambda:validate_suite(bad))

    def test_acceptance_catches_shared_runtime_and_replay_classifier_bug(self):
        # Even if replay shares a buggy classifier, independent expected behavior rejects it.
        with tempfile.TemporaryDirectory() as tmp:
            with patch('scripts.patient_eval.patient.classify_requested_slots',return_value={'requested_slots':['F3'],'clauses':[]}):
                self.assertRule('quoted_question_disclosure',lambda:acceptance(Path(tmp)))

    def test_report_works_in_container_without_git(self):
        from scripts.benchmark_checks.__main__ import write_report
        from scripts.benchmark_checks.multiturn import ASSETS
        import json
        with tempfile.TemporaryDirectory() as tmp:
            with patch('scripts.benchmark_checks.__main__.subprocess.run',side_effect=FileNotFoundError),patch.dict('os.environ',{},clear=True):
                write_report(Path(tmp),'track-validation',[],ASSETS)
            self.assertEqual(json.loads((Path(tmp)/'report.json').read_text())['commit'],'unknown')


if __name__=='__main__': unittest.main()
