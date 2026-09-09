import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from scripts.patient_eval.adapters import run_api
from scripts.patient_eval.cli import DEFAULT_SUITE, evaluate_sessions, main
from scripts.patient_eval.contracts import load_suite, validate_scenario, visible_prefix
from scripts.patient_eval.diagnosis import diagnose
from scripts.patient_eval.runner import replay_control, run_fixture
from scripts.patient_eval.scoring import score_session


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite(DEFAULT_SUITE)
        self.scenario = self.suite['scenarios'][1]

    def test_real_event_loss_and_replay_verify_only_development_mechanism(self):
        baseline = run_fixture(self.scenario, True)
        restored = run_fixture(self.scenario)
        score = score_session(baseline, self.scenario)
        result = diagnose(baseline, score, replay_control(self.scenario, baseline, restored))
        self.assertTrue(result['internal_cause_confirmed'])
        self.assertFalse(score['evaluation_complete'])
        self.assertIsNone(score['critical_failure'])
        self.assertEqual(baseline['turns'][:-1], restored['turns'][:-1])
        self.assertNotEqual(baseline['turns'][-1]['content'], restored['turns'][-1]['content'])
        events = [e for e in baseline['trace'] if e['kind'] == 'state_transition' and not e['delivered']]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['before'], events[0]['after'])

    def test_hidden_annotations_never_enter_model_messages(self):
        scenario = copy.deepcopy(self.scenario)
        scenario['hidden_patient_facts'] = {'secret': 'DO_NOT_SEND'}
        scenario['criteria'][0]['expected'] = 'DO_NOT_SEND'
        scenario['fault_label'] = 'DO_NOT_SEND'
        messages = visible_prefix(scenario)
        self.assertNotIn('DO_NOT_SEND', json.dumps(messages))
        self.assertTrue(all(set(message) == {'role', 'content'} for message in messages))

    def test_development_success_does_not_admit_test_split(self):
        scenario = copy.deepcopy(self.scenario)
        scenario['split'] = 'sealed_test'
        scenario['gold_approved'] = True
        with self.assertRaises(ValueError):
            validate_scenario(scenario)

    def test_mismatched_and_extra_prefixes_cannot_be_compared(self):
        session = run_fixture(self.scenario)
        session['turns'][0]['content'] += ' changed'
        with self.assertRaises(ValueError):
            evaluate_sessions(self.suite, [session])
        session = run_fixture(self.scenario)
        session['turns'].extend([{'turn_id': 'extra-user', 'role': 'user', 'content': 'Extra hint'},
                                 {'turn_id': 'extra-assistant', 'role': 'assistant', 'content': 'Revised answer'}])
        with self.assertRaises(ValueError):
            evaluate_sessions(self.suite, [session])

    def test_cli_demo_runs_without_network_and_preserves_unknown_clinical_results(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('no network')), patch('sys.stdout', new=io.StringIO()):
            main(['demo', '--out', directory])
            from pathlib import Path
            result = json.loads((Path(directory) / 'results.json').read_text())
            self.assertEqual(len(result['sessions']), 16)
            self.assertEqual(result['aggregate']['critical_unassessed_sessions'], 16)
            self.assertEqual(sum(d['internal_cause_confirmed'] for d in result['diagnoses']), 4)
            self.assertEqual(result['comparison']['mean_delta'], 0.5)
            self.assertTrue((Path(directory) / 'report.html').exists())


class ApiAdapterTests(unittest.TestCase):
    def setUp(self):
        self.scenario = load_suite(DEFAULT_SUITE)['scenarios'][1]
        self.options = dict(base_url='https://model.example/v1', model='test-model', key_env='PATIENT_TEST_KEY')

    @patch.dict(os.environ, {'PATIENT_TEST_KEY': 'dummy-secret-never-log'})
    def test_target_timeout_is_retained_and_retries_are_bounded(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=TimeoutError()) as opener, patch('time.sleep'):
            session = run_api(self.scenario, **self.options, retries=1)
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(session['status'], 'target_error')
        self.assertEqual(session['turns'][-1]['role'], 'user')
        score = score_session(session, self.scenario)
        self.assertTrue(score['target_service_failure'])
        self.assertFalse(score['excluded_from_target_metrics'])
        self.assertNotIn('dummy-secret-never-log', json.dumps(session))

    @patch.dict(os.environ, {'PATIENT_TEST_KEY': 'dummy-secret-never-log'})
    def test_api_only_sends_visible_text_and_leaves_scoring_unassessed(self):
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': '示例回答'}}]}).encode())
        with patch('urllib.request.OpenerDirector.open', return_value=response) as opener:
            session = run_api(self.scenario, **self.options)
        sent = json.loads(opener.call_args.args[0].data)
        self.assertEqual(sent['messages'], visible_prefix(self.scenario))
        self.assertEqual(session['observations'], [])
        self.assertEqual(session['observability'], 'black_box')
        self.assertEqual(session['status'], 'completed')

    @patch.dict(os.environ, {'PATIENT_TEST_KEY': 'dummy-secret-never-log'})
    def test_schema_fault_is_not_a_success_and_plain_http_is_rejected(self):
        with patch('urllib.request.OpenerDirector.open', return_value=io.BytesIO(b'{"choices": []}')):
            session = run_api(self.scenario, **self.options)
        self.assertEqual(session['status'], 'target_error')
        self.assertEqual(session['metadata']['attempts'][0]['error'], 'invalid_response_schema')
        options = dict(self.options, base_url='http://model.example/v1')
        with self.assertRaises(ValueError):
            run_api(self.scenario, **options)


if __name__ == '__main__':
    unittest.main()
