"""Validate selection-only semantic reviews and project conservative legacy drafts.

Supported source semantics do not establish subject, polarity, disclosure, clinical
score anchors or admission. Keep the choice bundle alongside the legacy projection.
"""
from __future__ import annotations

from copy import deepcopy

from .candidate_review import validate_review
from .clinical_console import FLAGS, independent_packet

OPTIONS = {
    'facts': {'pending', 'supported', 'issue', 'question', 'subject', 'time', 'polarity',
              'correction', 'span', 'other', 'uncertain'},
    'privacy': {'pending', 'clear', 'risk', 'uncertain'},
    'rubrics': {'pending', 'applicable', 'not_applicable', 'clinical', 'uncertain'},
    'completeness': {'pending', 'usable', 'insufficient', 'exclude', 'uncertain'},
    'background': {'pending', 'clinician', 'researcher', 'other'},
    'independence': {'pending', 'independent', 'not_independent'},
    'conflicts': {'pending', 'none', 'present'},
}
FACT_REASONS = {
    'supported': '点选：原文支持该信息；主体、极性、字段和披露配置尚待完成，不代表已纳入。',
    'issue': '点选：有问题，具体原因待选择。',
    'question': '点选：这是提问或假设，不是患者事实。',
    'subject': '点选：人物归属有问题。', 'time': '点选：时间理解有问题。',
    'polarity': '点选：肯定、否定或未知有问题。',
    'correction': '点选：纠正或冲突关系需要处理。',
    'span': '点选：摘录不准确或缺少上下文。',
    'other': '点选：其他问题，交研究人员处理。',
    'uncertain': '点选：无法判断，交他人复核。',
}


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _keys(value, expected, label):
    _require(isinstance(value, dict) and set(value) == set(expected), label + ' fields changed')


def _validate_legacy_choices(original: dict, bundle: dict) -> tuple[dict, dict]:
    _keys(bundle, {'schema_version', 'packet', 'answers'}, 'choice bundle')
    _require(bundle['schema_version'] == 'clinical-console-choice-bundle/v0.2', 'unsupported choice bundle')
    validate_review(original, bundle['packet'])  # authenticates original digest and immutable evidence
    a = bundle['answers']
    expected = {'schema_version', 'local_only', 'packet_sha256', 'reviewer_id', 'authority',
                'profile', 'items', *FLAGS}
    _keys(a, expected, 'answers')
    constants = {'schema_version': 'clinical-console-choices/v0.2', 'local_only': True,
                 'packet_sha256': original['packet_sha256'],
                 'authority': 'self_declared_unsigned_not_approval', **FLAGS}
    for key, value in constants.items():
        _require(a[key] == value and type(a[key]) is type(value), 'answer source/status mismatch')
    _require(a['reviewer_id'] in ('reviewer-A', 'reviewer-B', 'reviewer-C'), 'invalid reviewer seat')
    _keys(a['profile'], {'background', 'independence', 'conflicts'}, 'profile')
    for key, value in a['profile'].items():
        _require(isinstance(value, str) and value in OPTIONS[key], 'invalid declaration')
    _require(isinstance(a['items'], list) and len(a['items']) == len(original['items']), 'case count mismatch')
    result = independent_packet(original)
    result['reviewer_id'] = a['reviewer_id']
    counts = {'answered': 0, 'total': 0, 'supported_semantics': 0, 'formal_included_facts': 0,
              'drafted_scoring_rules': 0, 'pending': 0}
    for item, answer, projected in zip(original['items'], a['items'], result['items']):
        _keys(answer, {'candidate_id', 'facts', 'privacy', 'rubrics', 'completeness'}, 'case answers')
        _require(answer['candidate_id'] == item['candidate_id'], 'case identity/order mismatch')
        for section, id_key, rows in (
            ('facts', 'fact_id', item['review']['facts']),
            ('privacy', 'turn_id', item['turns']),
            ('rubrics', 'criterion_id', item['review']['rubrics']),
        ):
            _require(isinstance(answer[section], list) and len(answer[section]) == len(rows), 'row count mismatch')
            for entry, row in zip(answer[section], rows):
                _keys(entry, {id_key, 'answer'}, section)
                _require(entry[id_key] == row[id_key], 'row identity/order mismatch')
                _require(isinstance(entry['answer'], str) and entry['answer'] in OPTIONS[section], 'invalid choice')
        _require(isinstance(answer['completeness'], str) and answer['completeness'] in OPTIONS['completeness'], 'invalid completeness')
        values = [r['answer'] for s in ('facts', 'privacy', 'rubrics') for r in answer[s]] + [answer['completeness']]
        counts['total'] += len(values)
        counts['answered'] += sum(v != 'pending' for v in values)
        r = projected['review']
        for f, choice in zip(r['facts'], answer['facts']):
            value = choice['answer']
            if value == 'pending':
                continue
            f['reason'] = FACT_REASONS[value]
            if value == 'supported':
                # Only semantic support was asked; never silently invent required facts/configuration.
                counts['supported_semantics'] += 1
            else:
                f['decision'] = 'exclude' if value == 'question' else 'uncertain'
                if value == 'question':
                    f['is_patient_assertion'] = False
        privacy = answer['privacy']
        r['privacy']['checked_turn_ids'] = [x['turn_id'] for x in privacy if x['answer'] != 'pending']
        if all(x['answer'] == 'clear' for x in privacy):
            r['privacy'].update(decision='reviewed_no_identifiers', reason='点选：逐轮检查后均未发现身份信息。')
        elif any(x['answer'] == 'risk' for x in privacy):
            r['privacy']['reason'] = '点选：存在或疑似身份信息；具体片段待定位，未完成隐私准入。'
        elif any(x['answer'] == 'uncertain' for x in privacy):
            r['privacy']['reason'] = '点选：部分话轮无法判断，待复核。'
        complete = answer['completeness']
        if complete in ('usable', 'insufficient', 'exclude'):
            r['completeness'].update(decision={'exclude': 'excluded'}.get(complete, complete),
                reason={'usable': '点选：本段材料足够理解情况。', 'insufficient': '点选：缺少关键信息。',
                        'exclude': '点选：材料不适合使用。'}[complete],
                evidence_turn_ids=[t['turn_id'] for t in item['turns']])
        elif complete == 'uncertain':
            r['completeness']['reason'] = '点选：无法判断材料完整性，待复核。'
        for rule, choice in zip(r['rubrics'], answer['rubrics']):
            value = choice['answer']
            if value == 'applicable':
                rule.update(applicability='applicable', reason='点选：适合考察，具体评分标准和机会待补充。')
            elif value == 'not_applicable':
                rule.update(decision='excluded', applicability='not_applicable', reason='点选：本例不适合考察此项。')
            elif value in ('clinical', 'uncertain'):
                rule['reason'] = '点选：需要相关专科人员裁决。' if value == 'clinical' else '点选：无法判断，待复核。'
    validate_review(original, result)
    counts['pending'] = counts['total'] - counts['answered']
    report = {'schema_version': 'clinical-console-choices-validation/v0.2', 'structurally_valid': True,
              'packet_sha256': a['packet_sha256'], 'reviewer_id': a['reviewer_id'], 'counts': counts,
              'clinical_credentials_verified': False, 'independence_verified': False, **FLAGS,
              'interpretation': '点选答卷是语义与适用性复核；须保留原答卷。派生草稿不补造事实配置或评分标准。'}
    return report, result



def validate_choices(original: dict, bundle: dict) -> tuple[dict, dict]:
    from .clinical_console_interactions import ANSWER_VERSION, LEGACY_VERSION, validate_interactions, summarize_interactions
    _keys(bundle, {'schema_version', 'packet', 'answers'}, 'choice bundle')
    if bundle['schema_version'] == 'clinical-console-choice-bundle/v0.2':
        report, review = _validate_legacy_choices(original, bundle)
        report['interaction_summary'] = summarize_interactions(bundle['answers'])
        return report, review
    _require(bundle['schema_version'] == 'clinical-console-choice-bundle/v0.3', 'unsupported choice bundle')
    _require(isinstance(bundle['answers'], dict) and bundle['answers'].get('schema_version') == ANSWER_VERSION,
             'answer/bundle version mismatch')
    _require('interaction' in bundle['answers'], 'missing interaction records')
    legacy = deepcopy(bundle)
    legacy['schema_version'] = 'clinical-console-choice-bundle/v0.2'
    legacy['answers'].pop('interaction')
    legacy['answers']['schema_version'] = LEGACY_VERSION
    report, review = _validate_legacy_choices(original, legacy)
    report['interaction_summary'] = validate_interactions(bundle['answers'])
    report['schema_version'] = 'clinical-console-choices-validation/v0.3'
    report['interpretation'] += ' 操作记录区分展示、改选和确认；不证明阅读、身份或临床正确。旧记录缺失不回填。'
    return report, review


def compare_choices(original: dict, a: dict, b: dict) -> dict:
    validate_choices(original, a)
    validate_choices(original, b)
    left, right = a['answers'], b['answers']
    _require(left['reviewer_id'] != right['reviewer_id'], 'two different reviewer seats required')
    differences, missing = [], []
    compared = 0
    def compare(path, x, y):
        nonlocal compared
        if x == 'pending' or y == 'pending':
            missing.append(path)
        else:
            compared += 1
            if x != y:
                differences.append({'path': path, 'a': x, 'b': y})
    for x, y in zip(left['items'], right['items']):
        for section, key in [('facts', 'fact_id'), ('privacy', 'turn_id'), ('rubrics', 'criterion_id')]:
            for p, q in zip(x[section], y[section]):
                compare(x['candidate_id'] + '.' + section + '.' + p[key], p['answer'], q['answer'])
        compare(x['candidate_id'] + '.completeness', x['completeness'], y['completeness'])
    return {'schema_version': 'clinical-console-choices-comparison/v0.2', 'packet_sha256': original['packet_sha256'],
            'reviewer_ids': [left['reviewer_id'], right['reviewer_id']], 'both_answered': compared,
            'differences': differences, 'missing': missing, 'independence_verified': False, **FLAGS}
