import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.patient_eval.readiness_drill import ScriptedClient, synthetic_suite
from scripts.patient_eval.recovery import inspect_recovery
from scripts.patient_eval.study import run_study


class RecoveryPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'interrupted'
        self.suite = synthetic_suite()
        self.client = ScriptedClient(crash_after=3)
        with self.assertRaises(KeyboardInterrupt):
            run_study(self.suite, self.client, self.root)
        self.config = self.client.public_config()

    def inspect(self, **kwargs):
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file() and not p.is_symlink()}
        calls = self.client.calls
        report = inspect_recovery(kwargs.pop('suite', self.suite), self.config, self.root, **kwargs)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file() and not p.is_symlink()})
        self.assertEqual(calls, self.client.calls)
        self.assertFalse(report['resume_allowed'])
        return report

    def edit(self, name, change):
        path = self.root / name
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value), encoding='utf-8')

    def assert_rejected(self, code, **kwargs):
        report = self.inspect(**kwargs)
        self.assertFalse(report['consistency_passed'])
        self.assertIn(code, report['issues'])

    def test_intact_checkpoint_is_read_only_but_not_authorized_to_resume(self):
        report = self.inspect()
        self.assertTrue(report['consistency_passed'])
        self.assertEqual(report['persisted_sessions'], 1)
        self.assertEqual(report['pending_sessions'], 1)
        self.assertEqual(report['process_liveness'], 'unknown')
        self.assertEqual(report['checkpoint_integrity'], 'unanchored')
        self.assertIn('legacy_checkpoint_has_no_trusted_file_digests', report['blockers'])

    def test_changed_input(self):
        suite = copy.deepcopy(self.suite)
        suite['scenarios'][0]['patient']['initial_user_message'] += '补充。'
        self.assert_rejected('suite_mismatch', suite=suite)

    def test_changed_config_or_schedule_parameters(self):
        self.config['mode'] = 'empty'
        self.assert_rejected('config_mismatch')
        self.config['mode'] = 'normal'
        self.assert_rejected('config_mismatch', seed=17)
        self.assert_rejected('schedule_mismatch', repeats=2)

    def test_changed_stored_schedule(self):
        self.edit('manifest.json', lambda m: m['schedule'].reverse())
        self.assert_rejected('schedule_mismatch')

    def test_changed_checkpoint_metadata(self):
        self.edit('session-0001.json', lambda s: s['metadata'].update(arm='unknown'))
        self.assert_rejected('checkpoint_provenance_mismatch')

    def test_missing_checkpoint(self):
        (self.root / 'session-0001.json').unlink()
        self.assert_rejected('directory_inventory_mismatch')

    def test_orphan_and_temporary_files_are_never_adopted_or_deleted(self):
        (self.root / 'session-0002.json').write_text('{}')
        (self.root / '.manifest.json.tmp').write_text('partial')
        self.assert_rejected('directory_inventory_mismatch')

    def test_path_escape_is_rejected_without_opening_it(self):
        self.edit('manifest.json', lambda m: m['sessions'][0].update(file='../outside.json'))
        self.assert_rejected('checkpoint_index_mismatch')

    def test_symlink_is_not_followed(self):
        checkpoint = self.root / 'session-0001.json'
        checkpoint.unlink()
        checkpoint.symlink_to(self.root.parent / 'outside.json')
        self.assert_rejected('unsafe_directory_entry')

    def test_invalid_json_and_count(self):
        self.edit('manifest.json', lambda m: m.update(completed_sessions=2))
        self.assert_rejected('checkpoint_count_mismatch')
        (self.root / 'manifest.json').write_text('{')
        self.assert_rejected('manifest_unreadable')

    def test_real_source_rejected_before_directory_inspection(self):
        self.suite['scenarios'][0]['source'] = 'deidentified_real'
        self.assert_rejected('invalid_synthetic_input')

    def test_completed_run_is_not_rerun(self):
        self.root = Path(self.temp.name) / 'complete'
        run_study(self.suite, ScriptedClient(), self.root)
        self.config = ScriptedClient().public_config()
        report = self.inspect()
        self.assertTrue(report['consistency_passed'])
        self.assertEqual(report['pending_sessions'], 0)
        self.assertIn('already_completed', report['blockers'])

    def test_valid_text_mutation_cannot_be_claimed_integrity_verified(self):
        self.edit('session-0001.json', lambda s: s['turns'][1].update(content='不同的合成回答。'))
        report = self.inspect()
        self.assertTrue(report['consistency_passed'])
        self.assertEqual(report['checkpoint_integrity'], 'unanchored')
        self.assertFalse(report['resume_allowed'])

    def test_completed_aggregate_mismatch(self):
        self.root = Path(self.temp.name) / 'complete'
        run_study(self.suite, ScriptedClient(), self.root)
        self.config = ScriptedClient().public_config()
        (self.root / 'sessions.json').write_text('[]')
        self.assert_rejected('aggregate_mismatch')

    def test_error_records_are_retained_as_persisted_not_successful(self):
        self.root = Path(self.temp.name) / 'errors'
        target = ScriptedClient(mode='timeout')
        run_study(self.suite, target, self.root)
        self.config = target.public_config()
        report = self.inspect()
        self.assertTrue(report['consistency_passed'])
        self.assertEqual(report['persisted_sessions'], 2)
        self.assertEqual(report['pending_sessions'], 0)
        self.assertNotIn('successful_sessions', report)


if __name__ == '__main__':
    unittest.main()
