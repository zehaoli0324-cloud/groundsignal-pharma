"""Validate unsigned UI observations without claiming attention or old provenance."""
from __future__ import annotations

UI_VERSION = '0.2.2'
ANSWER_VERSION = 'clinical-console-choices/v0.3'
LEGACY_VERSION = 'clinical-console-choices/v0.2'
SUGGESTED = {'facts': 'supported', 'privacy': 'clear', 'rubrics': 'applicable', 'completeness': 'usable'}


def answer_rows(answers):
    for item in answers['items']:
        for section, key in (('facts', 'fact_id'), ('privacy', 'turn_id'), ('rubrics', 'criterion_id')):
            for row in item[section]:
                yield item['candidate_id'], section, row[key], row['answer']
        yield item['candidate_id'], 'completeness', 'completeness', item['completeness']


def validate_interactions(answers):
    # Imported here because the outer validator first checks answer identities/options.
    from .clinical_console_choices import OPTIONS, _keys, _require
    meta = answers['interaction']
    _keys(meta, {'schema_version', 'export_ui_version', 'origin_answers_version', 'records'}, 'interaction')
    _require(meta['schema_version'] == 'clinical-console-interaction/v0.1'
             and meta['export_ui_version'] == UI_VERSION, 'unsupported interaction version')
    _require(meta['origin_answers_version'] in (LEGACY_VERSION, ANSWER_VERSION), 'unsupported origin')
    legacy = meta['origin_answers_version'] == LEGACY_VERSION
    rows = list(answer_rows(answers))
    _require(isinstance(meta['records'], list) and len(meta['records']) == len(rows), 'interaction coverage mismatch')
    for record, (candidate, section, item_id, value) in zip(meta['records'], rows):
        def check(ok):
            _require(ok, 'interaction inconsistent with answer: ' + candidate + '.' + section + '.' + item_id)
        def valid(v):
            return isinstance(v, str) and v in OPTIONS[section]
        _keys(record, {'candidate_id', 'section', 'item_id', 'origin', 'display', 'selection',
                       'confirmation', 'last_action'}, 'interaction record')
        check((record['candidate_id'], record['section'], record['item_id']) == (candidate, section, item_id))
        origin, display, selection, confirmation, action = (record[k] for k in
            ('origin', 'display', 'selection', 'confirmation', 'last_action'))
        _keys(origin, {'answers_version', 'answer', 'ui_version'}, 'origin')
        check(origin['answers_version'] == meta['origin_answers_version'] and valid(origin['answer']))
        check(origin['ui_version'] == (None if legacy else UI_VERSION))
        if not legacy:
            check(origin['answer'] == 'pending')
        if display is not None:
            _keys(display, {'ui_version', 'preset_shown', 'answer'}, 'display')
            check(display['ui_version'] == UI_VERSION and type(display['preset_shown']) is bool
                  and valid(display['answer']) and display['answer'] != 'pending')
            if display['preset_shown']:
                check(display['answer'] == SUGGESTED[section])
        check(selection is None or (valid(selection) and selection != 'pending'))
        if confirmation is not None:
            _keys(confirmation, {'ui_version', 'method', 'answer', 'preset_shown'}, 'confirmation')
            check(confirmation['ui_version'] == UI_VERSION
                  and confirmation['method'] in ('preset', 'selection', 'existing_answer')
                  and type(confirmation['preset_shown']) is bool
                  and confirmation['answer'] == value and value != 'pending')
            if confirmation['method'] == 'preset':
                check(selection is None and confirmation['preset_shown'] and value == SUGGESTED[section])
            elif confirmation['method'] == 'selection':
                check(selection == value)
            else:
                check(legacy and selection is None and value == origin['answer']
                      and not confirmation['preset_shown'])
        check(isinstance(action, str) and action in
              {'unseen', 'viewed', 'selected', 'confirmed', 'skipped', 'legacy_unknown'})
        check((confirmation is not None and display is not None) if action == 'confirmed'
              else confirmation is None)
        if action == 'selected':
            check(selection == value and value != 'pending' and display is not None)
        if action in {'unseen', 'viewed', 'skipped'}:
            check(value == 'pending' and selection is None)
        if action == 'unseen':
            check(not legacy and display is None)
        if action == 'viewed':
            check(not legacy and display is not None)
        if action == 'legacy_unknown':
            check(legacy and value == origin['answer'] and selection is None)
    return summarize_interactions(answers)


def summarize_interactions(answers):
    rows = list(answer_rows(answers))
    summary = {'records': len(rows), 'preset_confirmed': 0, 'selection_confirmed': 0,
               'existing_answer_confirmed': 0, 'selected_unconfirmed': 0,
               'legacy_confirmation_unknown': 0, 'pending': sum(r[3] == 'pending' for r in rows),
               'latest_display_preset': 0, 'display_unknown': 0,
               'attention_verified': False, 'interaction_authenticity_verified': False}
    if answers['schema_version'] == LEGACY_VERSION:
        summary['legacy_confirmation_unknown'] = sum(r[3] != 'pending' for r in rows)
        summary['display_unknown'] = len(rows)
        return summary
    for record, row in zip(answers['interaction']['records'], rows):
        display, confirmation = record['display'], record['confirmation']
        summary['display_unknown'] += display is None
        summary['latest_display_preset'] += display is not None and display['preset_shown']
        if confirmation is not None:
            summary[confirmation['method'] + '_confirmed'] += 1
        elif record['last_action'] == 'selected':
            summary['selected_unconfirmed'] += 1
        elif row[3] != 'pending':
            summary['legacy_confirmation_unknown'] += 1
    return summary
