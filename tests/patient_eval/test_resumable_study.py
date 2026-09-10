import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.patient_eval.readiness_drill import ScriptedClient, synthetic_suite
from scripts.patient_eval.recovery import run_resumable_study
from scripts.patient_eval.study import run_dialogue, run_study


class StableClient(ScriptedClient):
    """Fault controls are local harness behavior, not persisted target config."""
    def __init__(self, *, interrupt_after=None, mode='normal'):
        super().__init__(mode=mode)
        self.interrupt_after = interrupt_after

    def public_config(self):
        return {'model': self.model, 'platform': self.platform,
                'fixture_protocol': 'stable-v0.1', 'mode': self.mode,
                'external_calls': False}

    def __call__(self, messages):
        if self.interrupt_after is not None and self.calls >= self.interrupt_after:
            raise KeyboardInterrupt('intentional local interruption')
        return super().__call__(messages)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResumableStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'run'
        self.suite = synthetic_suite()
        probe = StableClient()
        first_arm = __import__('scripts.patient_eval.study', fromlist=['make_schedule']).make_schedule(
            self.suite['scenarios'])[0]['arm']
        run_dialogue(self.suite['scenarios'][0], probe, first_arm)
        self.first_session_calls = probe.calls

    def interrupt(self, client=None):
        client = client or StableClient(interrupt_after=self.first_session_calls)
        with self.assertRaises(KeyboardInterrupt):
            run_resumable_study(self.suite, client, self.root)
        manifest = json.loads((self.root / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'interrupted')
        self.assertEqual(manifest['completed_sessions'], 1)
        self.assertFalse((self.root / '.study.lock').exists())
        return client, manifest

    def test_resume_skips_verified_checkpoint_and_finishes_pending(self):
        _, manifest = self.interrupt()
        original = sha(self.root / 'session-0001.json')
        full = StableClient()
        full_root = Path(self.temp.name) / 'full'
        run_resumable_study(self.suite, full, full_root)

        resumed = StableClient()
        result = run_resumable_study(self.suite, resumed, self.root, resume=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['completed_sessions'], 2)
        self.assertEqual(resumed.calls, full.calls - self.first_session_calls)
        self.assertEqual(sha(self.root / 'session-0001.json'), original)
        self.assertEqual(result['sessions'][0]['sha256'], manifest['sessions'][0]['sha256'])
        self.assertEqual(result['run_attempts'][-1]['kind'], 'resume')
        self.assertTrue(result['run_attempts'][-1]['uncheckpointed_call_replay_possible'])
        self.assertEqual(result['config']['checkpoint_hash_algorithm'], 'sha256')
        self.assertEqual(len(result['config']['runner_implementation_sha256']), 64)
        self.assertFalse((self.root / '.study.lock').exists())

    def test_checkpoint_digest_mutation_rejected_before_call(self):
        self.interrupt()
        path = self.root / 'session-0001.json'
        value = json.loads(path.read_text())
        value['turns'][1]['content'] = '仍满足结构但字节不同。'
        path.write_text(json.dumps(value), encoding='utf-8')
        client = StableClient()
        with self.assertRaisesRegex(ValueError, 'checkpoint_digest_mismatch'):
            run_resumable_study(self.suite, client, self.root, resume=True)
        self.assertEqual(client.calls, 0)

    def test_lock_blocks_without_liveness_or_staleness_guess(self):
        self.interrupt()
        lock = self.root / '.study.lock'
        lock.write_text('{"old": true}')
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        client = StableClient()
        with self.assertRaises(FileExistsError):
            run_resumable_study(self.suite, client, self.root, resume=True)
        self.assertEqual(client.calls, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_input_config_and_schedule_changes_rejected(self):
        self.interrupt()
        changed = copy.deepcopy(self.suite)
        changed['scenarios'][0]['patient']['initial_user_message'] += '变化。'
        for kwargs in ({'suite': changed}, {'client': StableClient(mode='empty')},
                       {'seed': 11}, {'repeats': 2}):
            client = kwargs.pop('client', StableClient())
            suite = kwargs.pop('suite', self.suite)
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    run_resumable_study(suite, client, self.root, resume=True, **kwargs)
                self.assertEqual(client.calls, 0)

    def test_orphan_temp_and_legacy_formats_rejected(self):
        for name in ('session-0002.json', '.session-0002.json.tmp'):
            with self.subTest(name=name):
                root = Path(self.temp.name) / ('case-' + name.replace('/', '_'))
                self.root = root
                self.interrupt()
                (root / name).write_text('{}')
                client = StableClient()
                with self.assertRaisesRegex(ValueError, 'directory_inventory_mismatch'):
                    run_resumable_study(self.suite, client, root, resume=True)
                self.assertEqual(client.calls, 0)
        legacy = Path(self.temp.name) / 'legacy'
        run_study(self.suite, ScriptedClient(), legacy)
        client = StableClient()
        with self.assertRaisesRegex(ValueError, 'unsupported_manifest_contract'):
            run_resumable_study(self.suite, client, legacy, resume=True)
        self.assertEqual(client.calls, 0)

    def test_persisted_failure_is_retained_not_retried(self):
        failing = StableClient(mode='timeout', interrupt_after=1)
        self.interrupt(failing)
        first = (self.root / 'session-0001.json').read_bytes()
        self.assertEqual(json.loads(first)['status'], 'target_error')
        resumed = StableClient(mode='timeout')
        result = run_resumable_study(self.suite, resumed, self.root, resume=True)
        self.assertEqual((self.root / 'session-0001.json').read_bytes(), first)
        self.assertEqual(resumed.calls, 1)
        self.assertEqual([s['status'] for s in result['sessions']], ['target_error', 'target_error'])

    def test_completed_resume_is_read_only_and_makes_no_calls(self):
        run_resumable_study(self.suite, StableClient(), self.root)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        client = StableClient()
        result = run_resumable_study(self.suite, client, self.root, resume=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(client.calls, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_running_status_requires_operator_resolution(self):
        self.interrupt()
        path = self.root / 'manifest.json'
        value = json.loads(path.read_text())
        value['status'] = 'running'
        path.write_text(json.dumps(value), encoding='utf-8')
        client = StableClient()
        with self.assertRaisesRegex(ValueError, 'run_state_requires_operator_resolution'):
            run_resumable_study(self.suite, client, self.root, resume=True)
        self.assertEqual(client.calls, 0)

    def test_real_source_rejected_before_creation_or_call(self):
        self.suite['scenarios'][0]['source'] = 'deidentified_real'
        client = StableClient()
        with self.assertRaises(ValueError):
            run_resumable_study(self.suite, client, self.root)
        self.assertFalse(self.root.exists())
        self.assertEqual(client.calls, 0)


if __name__ == '__main__':
    unittest.main()
