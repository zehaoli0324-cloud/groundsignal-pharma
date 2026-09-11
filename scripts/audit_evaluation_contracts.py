#!/usr/bin/env python3
"""A1 batch 3 synthetic invariants. Exit 2 preserves observed defects.

No production fixes, real patient data, network calls or clinical judgments.
The statistics duplicate probes copy the SAME opportunity, not a new occurrence.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.patient_eval.cli import evaluate_sessions
from scripts.patient_eval.runner import digest, run_fixture
from scripts.patient_eval.readiness_statistics import DEFAULT_FIXTURE, load_statistics_bundle, run_statistics


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def probes():
    rows = []

    def record(pid, finding, expected, actual, passed):
        rows.append(dict(probe_id=pid, finding_id=finding, expected=expected,
                         actual=actual, invariant_pass=bool(passed)))

    case = dict(scenario_id='audit-synthetic-marker', family_id='audit-marker', variant='clear',
                protocol_id='audit-fixed/v1', source='synthetic', split='development',
                prefix=[dict(turn_id='u1', role='user', content='Record marker alpha.')],
                visible_updates={'u1': [dict(key='marker', value='alpha', status='confirmed')]},
                criteria=[dict(id='marker', module='C3', kind='mechanical', critical=False,
                               required=True, check='state_value', fact_key='marker',
                               expected='alpha', expected_status='confirmed')])
    suite = dict(schema_version='patient-eval/v0.1', scope='development_only', scenarios=[case])
    original = run_fixture(case)
    result = evaluate_sessions(suite, [original])
    record('matching_scenario_passes', None, 'Unchanged synthetic marker satisfies original rule',
           result['scores'][0]['counts'], result['scores'][0]['fully_passed'])

    for pid in ('changed_rule_old_result', 'explicit_wrong_scenario_digest'):
        changed_suite, run = deepcopy(suite), deepcopy(original)
        if pid == 'changed_rule_old_result':
            changed_suite['scenarios'][0]['criteria'][0]['expected'] = 'beta'
        else:
            run['metadata']['scenario_sha256'] = '0' * 64
        error, scored = None, None
        try:
            scored = evaluate_sessions(changed_suite, [run])['scores'][0]
        except ValueError as exc:
            error = str(exc)
        actual = dict(error=error, stored_digest=run['metadata']['scenario_sha256'],
                      expected_digest=digest(changed_suite['scenarios'][0]),
                      current_expected=changed_suite['scenarios'][0]['criteria'][0]['expected'],
                      retained_observation=run['observations'][0],
                      fully_passed=scored['fully_passed'] if scored else None)
        record(pid, 'A1-011', 'Reject an explicitly mismatched scenario binding before scoring', actual, error is not None)

    for pid, mutation in (
        ('duplicate_session_rejected', lambda r: [r, deepcopy(r)]),
        ('wrong_protocol_rejected', lambda r: (r['metadata'].update(session_protocol_id='other') or [r]))):
        error = None
        try:
            evaluate_sessions(suite, mutation(deepcopy(original)))
        except ValueError as exc:
            error = str(exc)
        record(pid, None, 'Invalid identity rejected', dict(error=error), error is not None)

    missing = deepcopy(original)
    missing['observations'] = []
    scored = evaluate_sessions(suite, [missing])['scores'][0]
    record('missing_observation_not_pass', None, 'Missing review stays unassessed and cannot pass',
           dict(counts=scored['counts'], fully_passed=scored['fully_passed']),
           scored['counts']['unassessed'] == 1 and not scored['fully_passed'])
    invalid = deepcopy(original)
    invalid.update(status='measurement_invalid', invalid_component='collector', invalid_reason='Synthetic capture failure')
    invalid['metadata']['comparison_lane'] = 'free_dialogue'
    result = evaluate_sessions(suite, [invalid])
    record('invalid_measurement_excluded', None, 'Previously passing observation cannot certify invalid capture',
           dict(counts=result['scores'][0]['counts'], aggregate=result['aggregate']),
           not result['scores'][0]['fully_passed'] and result['aggregate']['valid_sessions'] == 0)

    bundle = load_statistics_bundle(DEFAULT_FIXTURE)
    with tempfile.TemporaryDirectory(prefix='a1-statistics-synthetic-') as tmp:
        root = Path(tmp)
        base = run_statistics(bundle, root / 'baseline.sqlite')
        record('statistics_baseline', None, 'Known fixture retains hand-checked units and denominators',
               base['denominators'], base['denominators']['planned_opportunities'] == 7
               and base['denominators']['individual_quality_ratings'] == 4
               and base['service_completion']['denominator'] == 6)
        for copy_ratings in (False, True):
            changed = deepcopy(bundle)
            item_id = base['queries']['both_reviewers_assessed'][0]['item_id']
            item = next(o for o in changed['opportunities'] if o['item_id'] == item_id)
            alias = item_id + ':copied-same-occurrence'
            changed['opportunities'].append({**item, 'item_id': alias})
            if copy_ratings:
                changed['ratings'] += [{**r, 'item_id': alias} for r in bundle['ratings'] if r['item_id'] == item_id]
            report, error = None, None
            try:
                report = run_statistics(changed, root / f'duplicate-{copy_ratings}.sqlite')
            except ValueError as exc:
                error = str(exc)
            record('duplicate_opportunity_with_ratings' if copy_ratings else 'duplicate_opportunity_alias',
                   'A1-012', 'Same occurrence copied under another item ID cannot increase sample counts',
                   dict(error=error, original_item=item, duplicate_id=alias,
                        denominators=report['denominators'] if report else None),
                   error is not None or report['denominators'] == base['denominators'])
        empty = deepcopy(bundle)
        empty['ratings'] = []
        report = run_statistics(empty, root / 'empty.sqlite')
        record('empty_ratings_stay_missing', None, 'No reviewer rows create no paired rating or agreement',
               dict(denominators=report['denominators'], agreement=report['agreement']),
               report['agreement'] is None and report['denominators']['individual_quality_ratings'] == 0
               and report['denominators']['opportunities_missing_both_reviewer_rows'] == 7)
        duplicate = deepcopy(bundle)
        duplicate['opportunities'].append(deepcopy(duplicate['opportunities'][0]))
        error = None
        try:
            run_statistics(duplicate, root / 'same-id.sqlite')
        except ValueError as exc:
            error = str(exc)
        record('duplicate_item_id_rejected', None, 'Exact item-ID duplicate rejected before creating database',
               dict(error=error, database_exists=(root / 'same-id.sqlite').exists()),
               error is not None and not (root / 'same-id.sqlite').exists())
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with patch.object(socket, 'connect', create=True, side_effect=AssertionError('network forbidden')), \
         patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')), \
         patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
        rows = probes()
    failures = sum(not row['invariant_pass'] for row in rows)
    result = dict(scope='synthetic_contract_audit', total=len(rows), passed=len(rows)-failures,
                  failed=failures, rows=rows, production_fixes=0, external_model_calls=0,
                  private_patient_reads=0, clinical_approval=False)
    dump(args.out / 'observations.json', result)
    paths = ['scripts/audit_evaluation_contracts.py', 'scripts/patient_eval/cli.py',
             'scripts/patient_eval/scoring.py', 'scripts/patient_eval/runner.py',
             'scripts/patient_eval/contracts.py', 'scripts/patient_eval/readiness_statistics.py',
             str(DEFAULT_FIXTURE.relative_to(ROOT))]
    dump(args.out / 'run-manifest.json', dict(argv=[sys.executable, *sys.argv], cwd=str(Path.cwd()),
         python=platform.python_version(),
         input_git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         input_git_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
         file_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
         probe_script_uncommitted_at_first_execution=True, network='blocked in process',
         input_scope='authored synthetic marker plus existing synthetic statistics fixture',
         output=str(args.out), expected_exit_code_at_audit_baseline=2,
         actual_exit_code=2 if failures else 0, result='FAIL' if failures else 'PASS'))
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
    return 2 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
