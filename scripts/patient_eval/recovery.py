"""Read-only legacy checkpoint preflight. Never resumes or invokes a client.

An internally consistent legacy record is not integrity-authenticated. In
particular, valid response edits cannot be detected without prior trusted
digests. This module deliberately refuses execution even on a clean report.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import require, validate_session
from .study import _digest, _validate_study_scenario, make_schedule, study_config


def inspect_recovery(suite: dict, client_config: dict, out: str | Path,
                     repeats: int = 1, seed: int = 7) -> dict:
    report = {
        'schema_version': 'patient-recovery-preflight/v0.1',
        'source': 'synthetic', 'read_only': True, 'resume_allowed': False,
        'consistency_passed': False, 'issues': [],
        'blockers': ['resume_executor_not_implemented',
                     'legacy_checkpoint_has_no_trusted_file_digests',
                     'exclusive_writer_lock_not_implemented'],
        'process_liveness': 'unknown', 'checkpoint_integrity': 'unanchored',
        'persisted_sessions': None, 'pending_sessions': None,
        'observed_file_sha256': {},
        'clinical_approval': False, 'real_source_sessions_executed': 0,
    }
    def issue(code):
        if code not in report['issues']:
            report['issues'].append(code)

    try:
        require(isinstance(suite, dict) and suite.get('scope') == 'development_only', 'scope')
        scenarios = suite['scenarios']
        schedule = make_schedule(scenarios, repeats, seed)
        for scenario in scenarios:
            _validate_study_scenario(scenario)
        config = study_config(client_config, repeats, seed)
    except (ValueError, TypeError, KeyError, AttributeError):
        issue('invalid_synthetic_input')
        return report

    directory = Path(out).absolute()
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        issue('unsafe_directory_entry')
        return report
    try:
        entries = list(directory.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in entries):
            issue('unsafe_directory_entry')
            return report
    except OSError:
        issue('directory_unreadable')
        return report

    def read(name):
        raw = (directory / name).read_bytes()
        report['observed_file_sha256'][name] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    try:
        manifest = read('manifest.json')
        require(isinstance(manifest, dict), 'manifest')
    except (OSError, ValueError, UnicodeError):
        issue('manifest_unreadable')
        return report
    report['manifest_status'] = manifest.get('status')
    if (manifest.get('schema_version') != 'patient-study/v0.2'
            or manifest.get('scope') != 'development_only'
            or manifest.get('clinical_approval') is not False
            or manifest.get('resume_supported') is not False
            or manifest.get('status') not in ('running', 'completed')):
        issue('unsupported_manifest_contract')
    if manifest.get('suite_sha256') != _digest(suite):
        issue('suite_mismatch')
    if manifest.get('config') != config or manifest.get('config_sha256') != _digest(config):
        issue('config_mismatch')
    if manifest.get('schedule') != schedule or manifest.get('planned_sessions') != len(schedule):
        issue('schedule_mismatch')
    count = manifest.get('completed_sessions')
    summaries = manifest.get('sessions', [])
    if (type(count) is not int or not 0 <= count <= len(schedule)
            or not isinstance(summaries, list) or len(summaries) != count):
        issue('checkpoint_count_mismatch')
        return report
    report['persisted_sessions'], report['pending_sessions'] = count, len(schedule) - count
    finished = manifest.get('status') == 'completed'
    if finished:
        report['blockers'].append('already_completed')
        if count != len(schedule):
            issue('checkpoint_count_mismatch')
    expected = {'manifest.json'} | {f'session-{i+1:04d}.json' for i in range(count)}
    if finished:
        expected.add('sessions.json')
    if {p.name for p in entries} != expected:
        # Includes orphan checkpoints, temporary files and unexpected aggregates.
        # None are adopted, removed or overwritten.
        issue('directory_inventory_mismatch')
    indexed = {s['scenario_id']: s for s in scenarios}
    sessions = []
    for i, summary in enumerate(summaries):
        item = schedule[i]
        filename = f'session-{i+1:04d}.json'
        if (not isinstance(summary, dict) or summary.get('file') != filename
                or any(summary.get(k) != v for k, v in item.items())):
            issue('checkpoint_index_mismatch')
            continue
        try:
            session = read(filename)
            validate_session(session)
            sessions.append(session)
            scenario = indexed[item['scenario_id']]
            metadata = session['metadata']
            expected_id = (item['scenario_id'] + ':' + item['arm'] + ':'
                           + str(item['repeat_id']) + ':' + _digest(client_config)[:12])
            if (any(session.get(k) != scenario[k] for k in ('scenario_id', 'family_id', 'variant'))
                    or session.get('session_id') != expected_id
                    or summary.get('session_id') != expected_id
                    or summary.get('status') != session['status']
                    or summary.get('termination_reason') != metadata.get('termination_reason')
                    or metadata.get('scenario_sha256') != _digest(scenario)
                    or metadata.get('target_config') != client_config
                    or metadata.get('system_policy_sha256') != config['system_policy_sha256']
                    or metadata.get('patient_classifier_version') != config['patient_classifier_version']
                    or metadata.get('session_protocol_id') != scenario['protocol_id']
                    or metadata.get('arm') != item['arm']
                    or metadata.get('repeat_id') != item['repeat_id']
                    or metadata.get('question_source') != 'synthetic'
                    or metadata.get('clinical_approval') is not False):
                issue('checkpoint_provenance_mismatch')
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            issue('checkpoint_unreadable_or_invalid')
    if finished:
        try:
            if read('sessions.json') != sessions:
                issue('aggregate_mismatch')
        except (OSError, ValueError):
            issue('aggregate_unreadable')
    # No lock exists in v0.2; hashes here are observations, never a trusted anchor
    # or a guarantee against a concurrent writer. No live/stale inference is made.
    report['consistency_passed'] = not report['issues']
    return report


def main():
    """Generate only fixed local synthetic fixtures; no arbitrary source loader."""
    import argparse
    from .readiness_drill import ScriptedClient, synthetic_suite
    from .study import _write_json, run_study

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drill-out', required=True, type=Path,
                        help='new directory for fixed synthetic preflight drill')
    args = parser.parse_args()
    args.drill_out.mkdir(parents=True, exist_ok=False)
    suite = synthetic_suite()
    client = ScriptedClient(crash_after=3)
    interrupted = False
    try:
        run_study(suite, client, args.drill_out / 'interrupted')
    except KeyboardInterrupt:
        interrupted = True
    before_calls = client.calls
    report = inspect_recovery(suite, client.public_config(), args.drill_out / 'interrupted')
    report['intentional_interruption_observed'] = interrupted
    report['preflight_client_calls'] = client.calls - before_calls
    report['external_model_calls'] = 0
    report['personal_skill_verified'] = False
    report['human_handoff_verified'] = False
    _write_json(args.drill_out / 'preflight-report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not interrupted or not report['consistency_passed'] or report['resume_allowed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
