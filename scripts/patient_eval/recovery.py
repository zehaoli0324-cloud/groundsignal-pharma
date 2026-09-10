"""Read-only legacy checkpoint preflight. Never resumes or invokes a client.

An internally consistent legacy record is not integrity-authenticated. In
particular, valid response edits cannot be detected without prior trusted
digests. This module deliberately refuses execution even on a clean report.
"""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .contracts import require, validate_session
from . import contracts as contracts_module
from . import extraction as extraction_module
from . import patient as patient_module
from . import patient_intent as patient_intent_module
from . import study as study_module
from .study import (_client_config, _digest, _validate_study_scenario, _write_json,
                    make_schedule, run_dialogue, study_config)


RESUMABLE_SCHEMA = 'patient-study/v0.3'
RESUMABLE_RUNNER = 'patient-study-resumable/v0.1'
LOCK_NAME = '.study.lock'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _implementation_sha256() -> str:
    """Bind the local modules that can change execution or validation behavior."""
    digest = hashlib.sha256()
    paths = [Path(__file__).resolve()] + [Path(module.__file__).resolve() for module in (
        study_module, contracts_module, extraction_module, patient_module,
        patient_intent_module)]
    for path in paths:
        digest.update(path.name.encode('utf-8') + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def _resumable_config(client_config: dict, repeats: int, seed: int) -> dict:
    config = study_config(client_config, repeats, seed)
    config.update(runner_version=RESUMABLE_RUNNER,
                  runner_implementation_sha256=_implementation_sha256(),
                  checkpoint_hash_algorithm='sha256',
                  delivery_semantics='at_least_once_for_uncheckpointed_session')
    return config


def _safe_directory(path: str | Path) -> Path:
    directory = Path(path).absolute()
    require(not any(item.is_symlink() for item in (directory, *directory.parents)),
            'unsafe_directory_entry')
    return directory


def _acquire_lock(directory: Path):
    """Acquire an exclusive local writer lock without guessing whether one is stale."""
    lock = directory / LOCK_NAME
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        payload = json.dumps({'schema_version': 'patient-study-lock/v0.1',
                              'runner_version': RESUMABLE_RUNNER,
                              'pid_observation_only': os.getpid(),
                              'created_at': _now()}, sort_keys=True).encode('utf-8')
        os.write(fd, payload)
        os.fsync(fd)
        identity = os.fstat(fd).st_dev, os.fstat(fd).st_ino
    finally:
        os.close(fd)
    return lock, identity


def _release_lock(lock: Path, identity) -> None:
    """Do not unlink a path that was replaced after this process acquired it."""
    try:
        stat = lock.lstat()
        if (stat.st_dev, stat.st_ino) == identity and not lock.is_symlink():
            lock.unlink()
    except FileNotFoundError:
        pass


def _validate_resumable_checkpoint(suite: dict, client_config: dict, directory: Path,
                                   repeats: int, seed: int):
    """Validate v0.3 under the caller-held lock and return manifest plus sessions."""
    schedule = make_schedule(suite['scenarios'], repeats, seed)
    config = _resumable_config(client_config, repeats, seed)
    try:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        require(isinstance(manifest, dict), 'manifest_unreadable')
    except (OSError, ValueError, UnicodeError):
        raise ValueError('manifest_unreadable') from None
    require(manifest.get('schema_version') == RESUMABLE_SCHEMA
            and manifest.get('scope') == 'development_only'
            and manifest.get('source') == 'synthetic'
            and manifest.get('clinical_approval') is False
            and manifest.get('resume_supported') is True,
            'unsupported_manifest_contract')
    require(manifest.get('suite_sha256') == _digest(suite), 'suite_mismatch')
    require(manifest.get('config') == config
            and manifest.get('config_sha256') == _digest(config), 'config_mismatch')
    require(manifest.get('schedule') == schedule
            and manifest.get('planned_sessions') == len(schedule), 'schedule_mismatch')
    status = manifest.get('status')
    require(status in ('interrupted', 'completed'),
            'run_state_requires_operator_resolution')
    count, summaries = manifest.get('completed_sessions'), manifest.get('sessions')
    require(type(count) is int and 0 <= count <= len(schedule)
            and isinstance(summaries, list) and len(summaries) == count,
            'checkpoint_count_mismatch')
    expected = {'manifest.json', LOCK_NAME} | {f'session-{i+1:04d}.json' for i in range(count)}
    if status == 'completed':
        require(count == len(schedule), 'checkpoint_count_mismatch')
        expected.add('sessions.json')
    try:
        entries = list(directory.iterdir())
        require(all(not item.is_symlink() and item.is_file() for item in entries),
                'unsafe_directory_entry')
        require({item.name for item in entries} == expected, 'directory_inventory_mismatch')
    except OSError:
        raise ValueError('directory_unreadable') from None
    indexed = {scenario['scenario_id']: scenario for scenario in suite['scenarios']}
    sessions = []
    for index, summary in enumerate(summaries):
        item = schedule[index]
        filename = f'session-{index+1:04d}.json'
        require(isinstance(summary, dict) and summary.get('file') == filename
                and all(summary.get(key) == value for key, value in item.items()),
                'checkpoint_index_mismatch')
        path = directory / filename
        require(summary.get('sha256') == _file_sha256(path), 'checkpoint_digest_mismatch')
        try:
            session = json.loads(path.read_text(encoding='utf-8'))
            validate_session(session)
            scenario = indexed[item['scenario_id']]
            metadata = session['metadata']
            expected_id = (item['scenario_id'] + ':' + item['arm'] + ':'
                           + str(item['repeat_id']) + ':' + _digest(client_config)[:12])
            require(all(session.get(key) == scenario[key]
                        for key in ('scenario_id', 'family_id', 'variant'))
                    and session.get('session_id') == expected_id
                    and summary.get('session_id') == expected_id
                    and summary.get('status') == session['status']
                    and summary.get('termination_reason') == metadata.get('termination_reason')
                    and metadata.get('scenario_sha256') == _digest(scenario)
                    and metadata.get('target_config') == client_config
                    and metadata.get('system_policy_sha256') == config['system_policy_sha256']
                    and metadata.get('patient_classifier_version') == config['patient_classifier_version']
                    and metadata.get('session_protocol_id') == scenario['protocol_id']
                    and metadata.get('arm') == item['arm']
                    and metadata.get('repeat_id') == item['repeat_id']
                    and metadata.get('question_source') == 'synthetic'
                    and metadata.get('clinical_approval') is False,
                    'checkpoint_provenance_mismatch')
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ValueError('checkpoint_unreadable_or_invalid') from None
        sessions.append(session)
    if status == 'completed':
        aggregate = directory / 'sessions.json'
        require(manifest.get('aggregate_sha256') == _file_sha256(aggregate),
                'aggregate_digest_mismatch')
        try:
            require(json.loads(aggregate.read_text(encoding='utf-8')) == sessions,
                    'aggregate_mismatch')
        except (OSError, ValueError, UnicodeError):
            raise ValueError('aggregate_unreadable') from None
    return manifest, sessions, schedule, config


def run_resumable_study(suite: dict, client, out: str | Path, repeats: int = 1,
                        seed: int = 7, resume: bool = False) -> dict:
    """Start or explicitly resume a v0.3 synthetic study under a local lock.

    Completed checkpoints are digest-verified and never invoked again. An
    uncheckpointed request may already have reached a provider, so resumption is
    at-least-once for that one pending session, never an exactly-once claim.
    """
    require(isinstance(suite, dict) and suite.get('scope') == 'development_only',
            'formal admission is not implemented')
    require(callable(client), 'client must be callable')
    require(type(resume) is bool, 'resume must be boolean')
    scenarios = suite.get('scenarios')
    schedule = make_schedule(scenarios, repeats, seed)
    for scenario in scenarios:
        _validate_study_scenario(scenario)
    client_config = _client_config(client)
    config = _resumable_config(client_config, repeats, seed)
    directory = _safe_directory(out)
    if resume:
        require(directory.is_dir(), 'resume_directory_missing')
    else:
        directory.mkdir(parents=True, exist_ok=False)
    lock, lock_identity = _acquire_lock(directory)
    manifest = None
    attempt = None
    try:
        if resume:
            manifest, sessions, schedule, config = _validate_resumable_checkpoint(
                suite, client_config, directory, repeats, seed)
            if manifest['status'] == 'completed':
                return manifest
        else:
            sessions = []
            manifest = {
                'schema_version': RESUMABLE_SCHEMA, 'scope': 'development_only',
                'source': 'synthetic', 'suite_sha256': _digest(suite),
                'config_sha256': _digest(config), 'config': config,
                'schedule': schedule, 'started_at': _now(),
                'planned_sessions': len(schedule), 'completed_sessions': 0,
                'sessions': [], 'status': 'running', 'resume_supported': True,
                'clinical_approval': False, 'run_attempts': [],
                'uncheckpointed_call_replay_possible': False,
            }
        attempt = {
            'attempt_id': len(manifest['run_attempts']) + 1,
            'kind': 'resume' if resume else 'start', 'started_at': _now(),
            'starting_completed_sessions': manifest['completed_sessions'],
            'uncheckpointed_call_replay_possible': bool(resume),
            'outcome': 'running',
        }
        manifest['run_attempts'].append(attempt)
        manifest['status'] = 'running'
        manifest['uncheckpointed_call_replay_possible'] = bool(resume)
        _write_json(directory / 'manifest.json', manifest)
        indexed = {scenario['scenario_id']: scenario for scenario in scenarios}
        for index in range(manifest['completed_sessions'], len(schedule)):
            item = schedule[index]
            session = run_dialogue(indexed[item['scenario_id']], client,
                                   item['arm'], item['repeat_id'])
            filename = f'session-{index+1:04d}.json'
            path = directory / filename
            _write_json(path, session)
            sessions.append(session)
            manifest['sessions'].append({
                **item, 'session_id': session['session_id'], 'file': filename,
                'sha256': _file_sha256(path), 'status': session['status'],
                'termination_reason': session['metadata']['termination_reason'],
                'collected_in_attempt': attempt['attempt_id'],
            })
            manifest['completed_sessions'] = len(sessions)
            _write_json(directory / 'manifest.json', manifest)
        _write_json(directory / 'sessions.json', sessions)
        manifest['aggregate_sha256'] = _file_sha256(directory / 'sessions.json')
        manifest['status'] = 'completed'
        manifest['finished_at'] = _now()
        attempt['outcome'] = 'completed'
        attempt['finished_at'] = manifest['finished_at']
        _write_json(directory / 'manifest.json', manifest)
        return manifest
    except KeyboardInterrupt:
        if manifest is not None and attempt is not None:
            interrupted_at = _now()
            manifest['status'] = 'interrupted'
            manifest['last_interrupted_at'] = interrupted_at
            manifest['uncheckpointed_call_replay_possible'] = True
            attempt['outcome'] = 'interrupted'
            attempt['finished_at'] = interrupted_at
            _write_json(directory / 'manifest.json', manifest)
        raise
    finally:
        _release_lock(lock, lock_identity)


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
