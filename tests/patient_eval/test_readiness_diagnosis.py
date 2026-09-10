import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.patient_eval import readiness_diagnosis as drill


class ReadinessDiagnosisTests(unittest.TestCase):
    def test_fixed_replay_has_raw_evidence_and_no_network(self):
        with patch('socket.socket', side_effect=AssertionError('no network')):
            report = drill.build_report()
        self.assertTrue(report['passed'])
        self.assertEqual((report['checks_passed'], report['checks_total']), (15, 15))
        self.assertEqual(len(report['pairs']), 3)
        for pair in report['pairs']:
            self.assertEqual(pair['baseline']['turns'][:-1], pair['restored']['turns'][:-1])
            self.assertNotEqual(pair['baseline']['turns'][-1], pair['restored']['turns'][-1])
            self.assertEqual(pair['state_outcomes'], ['fail', 'pass'])
            self.assertFalse(pair['restored_score']['evaluation_complete'])
        self.assertFalse(report['personal_skill_verified'])
        self.assertFalse(report['model_quality_assessed'])

    def test_good_answer_and_declared_pass_cannot_substitute_for_state_repair(self):
        report = drill.build_report()
        result = next(r for r in report['negative_controls'] if r['name'] == 'answer_only')
        self.assertTrue(result['rejected'])
        self.assertIn('dropped in baseline and delivered in control', result['control_reviews'][0]['reason'])

    def test_real_source_never_enters_this_drill(self):
        scenario = copy.deepcopy(drill.load_suite(drill.SUITE)['scenarios'][1])
        scenario.update(source='deidentified_real', use_authorized=True, deidentification_confirmed=True)
        with self.assertRaisesRegex(ValueError, 'restricted to synthetic'):
            drill.investigate(scenario)

    def test_existing_result_is_not_overwritten_or_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            output.write_text('previous observation', encoding='utf-8')
            with patch.object(drill, 'build_report') as build:
                with self.assertRaises(FileExistsError):
                    drill.main(['--out', str(output)])
                build.assert_not_called()
            self.assertEqual(output.read_text(encoding='utf-8'), 'previous observation')

    def test_unverified_restoration_fails_report_and_exit_without_losing_evidence(self):
        original = drill.diagnose
        def refuse(*args, **kwargs):
            result = original(*args, **kwargs)
            result['internal_cause_confirmed'] = False
            return result
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            with patch.object(drill, 'diagnose', side_effect=refuse), patch('sys.stdout', new=io.StringIO()):
                status = drill.main(['--out', str(output)])
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(status, 1)
            self.assertFalse(report['passed'])
            self.assertEqual(report['checks_passed'], 12)
            self.assertEqual(len(report['pairs']), 3)


if __name__ == '__main__':
    unittest.main()
