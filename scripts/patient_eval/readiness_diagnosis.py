"""Record a fixed synthetic event-loss investigation using existing components.

This is a teaching replay of an existing injected fault, not a newly discovered
production defect, model evaluation, language extractor, or independent test set.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from .contracts import load_suite
from .diagnosis import diagnose
from .runner import replay_control, run_fixture
from .scoring import score_session

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'medical/patient-eval/development/scenarios.json'
CASE_IDS = ('medication-time.pressure', 'symptom-presence.pressure', 'report-date.pressure')


def investigate(scenario):
    baseline = run_fixture(scenario, drop_correction=True)
    restored = run_fixture(scenario, drop_correction=False)
    before = score_session(baseline, scenario)
    after = score_session(restored, scenario)
    diagnosis = diagnose(baseline, before, replay_control(scenario, baseline, restored))
    def outcome(score):
        return next(r['outcome'] for r in score['criterion_results'] if r['criterion_id'] == 'state.latest')
    return {'scenario': scenario, 'baseline': baseline, 'restored': restored,
            'baseline_score': before, 'restored_score': after, 'diagnosis': diagnosis,
            'state_outcomes': [outcome(before), outcome(after)]}


def negative_controls(pair):
    """Alter recorded evidence to verify that unsupported attribution is refused."""
    case, baseline, restored = (pair[k] for k in ('scenario', 'baseline', 'restored'))
    results = []
    for name in ('no_restoration', 'answer_only', 'missing_transition', 'changed_config', 'black_box'):
        before, after = copy.deepcopy(baseline), copy.deepcopy(restored)
        if name == 'no_restoration':
            after = copy.deepcopy(baseline)
            after['session_id'] += ':no-restoration'
        elif name == 'answer_only':
            # A claimed passing grade and a good answer do not repair stale state.
            after = copy.deepcopy(baseline)
            after['session_id'] += ':answer-only'
            after['turns'][-1] = copy.deepcopy(restored['turns'][-1])
            after['observations'] = copy.deepcopy(restored['observations'])
            after['trace'].extend(copy.deepcopy(e) for e in restored['trace']
                                  if e['kind'] == 'component_restored')
        elif name == 'missing_transition':
            after['trace'] = [e for e in after['trace'] if e['kind'] != 'state_transition']
        elif name == 'changed_config':
            for event in after['trace']:
                if event['kind'] == 'evaluation_context':
                    event['config']['state_policy'] = 'different_policy'
        controls = replay_control(case, before, after)
        if name == 'black_box':
            # Keep the same visible answers, remove privileged internal evidence.
            for session in (before, after):
                session['observability'] = 'black_box'
                session['trace'] = []
        result = diagnose(before, score_session(before, case), controls)
        refused = (bool(result['control_reviews'])
                   and all(not review['accepted'] for review in result['control_reviews'])
                   and not result['internal_cause_confirmed'])
        results.append({'name': name, 'rejected': refused,
                        'control_reviews': result['control_reviews'],
                        'internal_cause_confirmed': result['internal_cause_confirmed']})
    without_control = diagnose(baseline, pair['baseline_score'])
    results.append({'name': 'symptom_without_replay',
                    'rejected': not without_control['internal_cause_confirmed'],
                    'control_reviews': without_control['control_reviews'],
                    'internal_cause_confirmed': without_control['internal_cause_confirmed']})
    return results


def build_report():
    # No path or endpoint arguments: this entry is fixed to public synthetic data.
    suite = load_suite(SUITE)
    cases = {case['scenario_id']: case for case in suite['scenarios']}
    pairs = [investigate(cases[case_id]) for case_id in CASE_IDS]
    negatives = negative_controls(pairs[0])
    checks = {}
    for pair in pairs:
        prefix = pair['scenario']['scenario_id']
        checks[prefix + ':state_fail_to_pass'] = pair['state_outcomes'] == ['fail', 'pass']
        checks[prefix + ':matched_cause_verified'] = pair['diagnosis']['internal_cause_confirmed']
        checks[prefix + ':clinical_stays_unassessed'] = all(
            r['outcome'] == 'unassessed' for key in ('baseline_score', 'restored_score')
            for r in pair[key]['criterion_results'] if r['kind'] == 'clinical')
    for result in negatives:
        checks['negative:' + result['name']] = result['rejected']
    code_paths = ['contracts.py', 'diagnosis.py', 'runner.py', 'state.py',
                  'scoring.py', 'retrieval.py', 'readiness_diagnosis.py']
    paths = [SUITE] + [ROOT / 'scripts/patient_eval' / name for name in code_paths]
    return {
        'schema_version': 'readiness-diagnosis-report/v0.1',
        'source': 'synthetic', 'split': 'development',
        'fault_origin': 'existing_explicit_injection_not_new_product_bug',
        'primary_scenario_id': CASE_IDS[0],
        'regression_scope': 'two_existing_public_variants_not_independent_held_out',
        'intervention': 'restore_delivery_of_one_structured_correction',
        'checks': checks, 'checks_passed': sum(checks.values()),
        'checks_total': len(checks), 'passed': all(checks.values()),
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'pairs': pairs, 'negative_controls': negatives,
        'external_model_calls': 0, 'real_source_sessions': 0,
        'independent_raters': 0, 'model_quality_assessed': False,
        'clinical_validity_assessed': False, 'personal_skill_verified': False,
        's6_automatic_trust': 'BLOCKED',
        'limitations': [
            'Structured updates are author annotations; extraction accuracy is not evaluated.',
            'Restoration disables the existing injection; no production bug was repaired.',
            'Only deterministic local outputs are tested; no proprietary model mechanism is established.',
            'Source digests detect local changes; they are not an external trust root.',
            'Collection timestamps vary across runs; compare checks and evidence, not whole-file equality.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    # Exclusive creation preserves earlier successful or failed observations.
    with args.out.open('x', encoding='utf-8') as handle:
        report = build_report()
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({k: report[k] for k in ('passed', 'checks_passed', 'checks_total',
                                           'external_model_calls', 'real_source_sessions')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
