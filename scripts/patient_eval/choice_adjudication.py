"""Confirmation-aware choice reconciliation; never grants clinical admission.

Original choice bundles stay intact. A separate conservative review projection
can enter the existing candidate-review validator, not the model scoring lane.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from .candidate_review import validate_review
from .clinical_console import FLAGS
from .clinical_console_choices import OPTIONS, _keys, _require, validate_choices
from .clinical_console_interactions import ANSWER_VERSION, LEGACY_VERSION, answer_rows
from .import_batch import scenario_digest, write_new_json

QUEUE_VERSION = 'choice-adjudication-queue/v0.1'
DECISION_VERSION = 'choice-adjudication-decisions/v0.1'


def _rows(bundle):
    answers = bundle['answers']
    records = answers['interaction']['records'] if answers['schema_version'] == ANSWER_VERSION else None
    for i, (candidate, section, item, value) in enumerate(answer_rows(answers)):
        confirmed = records is not None and records[i]['confirmation'] is not None
        yield {'candidate_id': candidate, 'section': section, 'item_id': item,
               'answer': value, 'confirmation': ('confirmed' if confirmed else
                   'missing' if value == 'pending' else 'legacy_unknown' if records is None
                   or records[i]['last_action'] == 'legacy_unknown' else 'unconfirmed')}


def prepare_queue(original, left, right):
    for bundle in (left, right):
        validate_choices(original, bundle)
    reviewers = [b['answers']['reviewer_id'] for b in (left, right)]
    _require(reviewers[0] != reviewers[1], 'two distinct reviewer seats required')
    rows = []
    for a, b in zip(_rows(left), _rows(right)):
        identity = [a[k] for k in ('candidate_id', 'section', 'item_id')]
        if a['answer'] == 'pending' or b['answer'] == 'pending':
            status = 'missing_answer'
        elif any(r['confirmation'] != 'confirmed' for r in (a, b)):
            status = 'confirmation_required'
        else:
            status = 'agreed' if a['answer'] == b['answer'] else 'disagreement'
        rows.append({'row_id': scenario_digest(identity),
            **{k: a[k] for k in ('candidate_id', 'section', 'item_id')},
            'left': {k: a[k] for k in ('answer', 'confirmation')},
            'right': {k: b[k] for k in ('answer', 'confirmation')}, 'status': status})
    return {'schema_version': QUEUE_VERSION, 'packet_sha256': original['packet_sha256'],
        'input_sha256': [scenario_digest(b) for b in (left, right)], 'reviewer_ids': reviewers,
        'rows': rows, 'counts': dict(sorted(Counter(r['status'] for r in rows).items())),
        'independence_verified': False, 'interaction_authenticity_verified': False, **FLAGS}


def decision_template(queue):
    return {'schema_version': DECISION_VERSION, 'queue_sha256': scenario_digest(queue),
            'adjudicator_id': '', 'authority': 'self_declared_unsigned_not_approval',
            'decisions': [], **FLAGS}


def apply_decisions(original, left, right, decisions):
    queue = prepare_queue(original, left, right)  # recompute; never trust edited queue rows
    template = decision_template(queue)
    _keys(decisions, set(template), 'adjudication')
    for key in ('schema_version', 'queue_sha256', 'authority', *FLAGS):
        _require(decisions[key] == template[key] and type(decisions[key]) is type(template[key]),
                 'stale adjudication or invalid authority flags')
    actor = decisions['adjudicator_id']
    _require(isinstance(actor, str) and bool(actor.strip()), 'adjudicator identity required')
    _require(isinstance(decisions['decisions'], list), 'decisions must be a list')
    by_id = {r['row_id']: r for r in queue['rows']}
    selected = {}
    for decision in decisions['decisions']:
        _keys(decision, {'row_id', 'answer', 'reason'}, 'decision')
        rid = decision['row_id']
        _require(isinstance(rid, str) and rid in by_id and rid not in selected,
                 'unknown or duplicate adjudication row')
        row = by_id[rid]
        _require(row['status'] == 'disagreement', 'only confirmed disagreements can be adjudicated')
        _require(isinstance(decision['answer'], str) and decision['answer'] in OPTIONS[row['section']]
                 and decision['answer'] != 'pending', 'invalid adjudicated answer')
        _require(isinstance(decision['reason'], str) and bool(decision['reason'].strip()),
                 'adjudication reason required')
        selected[rid] = decision
    # Internal legacy-format projection only. Never export a forged reviewer
    # choice bundle or fabricated UI confirmation records.
    internal = deepcopy(left)
    internal['schema_version'] = 'clinical-console-choice-bundle/v0.2'
    answers = internal['answers']
    answers['schema_version'] = LEGACY_VERSION
    answers.pop('interaction', None)
    answers['reviewer_id'] = 'reviewer-C'
    answers['profile'] = {key: 'pending' for key in answers['profile']}
    resolutions = []
    for row in queue['rows']:
        decision = selected.get(row['row_id'])
        value = decision['answer'] if decision else row['left']['answer'] if row['status'] == 'agreed' else 'pending'
        source = 'adjudicated' if decision else 'confirmed_agreement' if row['status'] == 'agreed' else 'unresolved'
        resolutions.append({**deepcopy(row), 'resolved_answer': value, 'resolution_source': source,
                            'reason': decision['reason'] if decision else None})
        item = next(i for i in answers['items'] if i['candidate_id'] == row['candidate_id'])
        if row['section'] == 'completeness':
            item['completeness'] = value
        else:
            key = {'facts': 'fact_id', 'privacy': 'turn_id', 'rubrics': 'criterion_id'}[row['section']]
            next(r for r in item[row['section']] if r[key] == row['item_id'])['answer'] = value
    _, review = validate_choices(original, internal)
    review['reviewer_id'] = 'adjudication:' + actor.strip()
    validation = validate_review(original, review)
    result = {'schema_version': 'choice-adjudication-result/v0.1',
        'packet_sha256': original['packet_sha256'], 'queue_sha256': scenario_digest(queue),
        'input_sha256': queue['input_sha256'], 'decisions_sha256': scenario_digest(decisions),
        'adjudicator_id': actor, 'authority': template['authority'], 'rows': resolutions,
        'counts': dict(sorted(Counter(r['resolution_source'] for r in resolutions).items())),
        'review_sha256': scenario_digest(review), 'projection_validation': validation,
        'independence_verified': False, 'clinical_credentials_verified': False,
        'runtime_observations': 0, **FLAGS}
    return result, review


def run_files(original_path, left_path, right_path, out, decisions_path=None):
    original, left, right = [json.loads(Path(p).read_bytes()) for p in (original_path, left_path, right_path)]
    queue = prepare_queue(original, left, right)
    decisions = json.loads(Path(decisions_path).read_bytes()) if decisions_path else None
    resolved = apply_decisions(original, left, right, decisions) if decisions is not None else None
    destination = Path(out)
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in [('original.json', original), ('reviewer-a.json', left), ('reviewer-b.json', right),
                        ('queue.json', queue)]:
        write_new_json(destination / name, value)
    if resolved is None:
        write_new_json(destination / 'decisions-template.json', decision_template(queue))
    else:
        for name, value in [('decisions.json', decisions), ('result.json', resolved[0]), ('review.json', resolved[1])]:
            write_new_json(destination / name, value)
    return queue if resolved is None else resolved[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'left', 'right', 'out'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--decisions')
    args = parser.parse_args(argv)
    try:
        result = run_files(args.original, args.left, args.right, args.out, args.decisions)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f'choice adjudication failed: {error}\n')
    print(json.dumps(result['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
