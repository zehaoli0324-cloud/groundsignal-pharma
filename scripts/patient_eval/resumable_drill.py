"""Fixed synthetic interruption/resume drill with local scripted replies only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .readiness_drill import ScriptedClient, synthetic_suite
from .recovery import run_resumable_study
from .study import _write_json, make_schedule, run_dialogue


class StableDrillClient(ScriptedClient):
    """Local fault injection does not change the declared target identity."""
    def __init__(self, *, interrupt_after=None, mode='normal'):
        super().__init__(mode=mode)
        self.interrupt_after = interrupt_after

    def public_config(self):
        return {'model': self.model, 'platform': self.platform,
                'fixture_protocol': 'resumable-drill/v0.1', 'mode': self.mode,
                'external_calls': False}

    def __call__(self, messages):
        if self.interrupt_after is not None and self.calls >= self.interrupt_after:
            raise KeyboardInterrupt('intentional local resumable drill interruption')
        return super().__call__(messages)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_drill(out: str | Path) -> dict:
    root = Path(out)
    root.mkdir(parents=True, exist_ok=False)
    suite = synthetic_suite()
    first = make_schedule(suite['scenarios'])[0]
    probe = StableDrillClient()
    run_dialogue(suite['scenarios'][0], probe, first['arm'], first['repeat_id'])
    first_session_calls = probe.calls

    interrupted_client = StableDrillClient(interrupt_after=first_session_calls)
    interrupted = False
    try:
        run_resumable_study(suite, interrupted_client, root / 'interrupted')
    except KeyboardInterrupt:
        interrupted = True
    interrupted_manifest = json.loads((root / 'interrupted/manifest.json').read_text())
    checkpoint_before = _sha(root / 'interrupted/session-0001.json')

    reference_client = StableDrillClient()
    run_resumable_study(suite, reference_client, root / 'complete-reference')
    resume_client = StableDrillClient()
    completed = run_resumable_study(suite, resume_client, root / 'interrupted', resume=True)
    checkpoint_after = _sha(root / 'interrupted/session-0001.json')

    checks = [
        {'check': 'intentional_interruption_recorded',
         'passed': interrupted and interrupted_manifest['status'] == 'interrupted',
         'observed': {'status': interrupted_manifest['status']}},
        {'check': 'one_checkpoint_persisted',
         'passed': interrupted_manifest['completed_sessions'] == 1,
         'observed': {'persisted': interrupted_manifest['completed_sessions'], 'planned': 2}},
        {'check': 'lock_released_after_handled_interrupt',
         'passed': not (root / 'interrupted/.study.lock').exists(),
         'observed': {'lock_present': (root / 'interrupted/.study.lock').exists()}},
        {'check': 'checkpoint_digest_bound_and_unchanged',
         'passed': checkpoint_before == checkpoint_after
                   == interrupted_manifest['sessions'][0]['sha256'],
         'observed': {'unchanged': checkpoint_before == checkpoint_after}},
        {'check': 'only_pending_session_invoked',
         'passed': resume_client.calls == reference_client.calls - first_session_calls,
         'observed': {'resume_calls': resume_client.calls,
                      'full_calls': reference_client.calls,
                      'persisted_session_calls': first_session_calls}},
        {'check': 'resume_completed_all_sessions',
         'passed': completed['status'] == 'completed'
                   and completed['completed_sessions'] == completed['planned_sessions'] == 2,
         'observed': {'status': completed['status'],
                      'persisted': completed['completed_sessions']}},
        {'check': 'replay_risk_disclosed',
         'passed': completed['config']['delivery_semantics']
                   == 'at_least_once_for_uncheckpointed_session'
                   and completed['run_attempts'][-1]['uncheckpointed_call_replay_possible'] is True,
         'observed': {'delivery_semantics': completed['config']['delivery_semantics']}},
        {'check': 'lock_released_after_completion',
         'passed': not (root / 'interrupted/.study.lock').exists(),
         'observed': {'lock_present': (root / 'interrupted/.study.lock').exists()}},
    ]
    report = {
        'schema_version': 'resumable-readiness-drill/v0.1',
        'source': 'synthetic', 'passed': all(item['passed'] for item in checks),
        'checks_passed': sum(item['passed'] for item in checks),
        'checks_total': len(checks), 'checks': checks,
        'external_model_calls': 0, 'real_source_sessions': 0,
        'clinical_approval': False, 's5_freeze_modified': False,
        's6_automatic_trust': 'BLOCKED', 'training_data_generated': False,
        'personal_skill_verified': False, 'human_handoff_verified': False,
        'interpretation': ('Synthetic local recovery evidence only. Digest binding detects accidental '
                           'checkpoint changes relative to the manifest; it is not an external trust root. '
                           'An uncheckpointed request may be replayed after interruption.'),
    }
    _write_json(root / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path,
                        help='new directory; existing paths are rejected')
    args = parser.parse_args()
    report = run_drill(args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
