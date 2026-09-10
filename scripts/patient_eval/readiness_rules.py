"""Structural validation for synthetic teaching rubrics, never semantic scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_PACK = Path(__file__).resolve().parents[2] / 'medical/patient-eval/readiness/scoring-rule-pack-v0.1.json'
FLAGS = {'clinical_gold': False, 'formal_approval': False,
         'dynamic_scenario_ready': False, 's6_automatic_trust': 'BLOCKED'}
RULE_FIELDS = {'schema_version', 'source', 'split', 'author', *FLAGS, 'criterion_id', 'capability',
               'clinical_rule', 'description', 'source_turns', 'opportunity', 'anchors',
               'serious_error', 'author_examples', 'validation_status', 'automation_status',
               'mapping_to_real_v04_rules'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, fields, label):
    require(isinstance(value, dict) and set(value) == set(fields), label + ' fields mismatch')


def text(value):
    return isinstance(value, str) and bool(value.strip())


def constants(value, expected):
    for key, wanted in expected.items():
        require(type(value.get(key)) is type(wanted) and value[key] == wanted,
                'unsupported or promoted field: ' + key)


def validate_rule(rule):
    keys(rule, RULE_FIELDS, 'rule')
    constants(rule, {**FLAGS, 'schema_version': 'readiness-scoring-opportunity/v0.1',
                    'source': 'synthetic', 'split': 'development',
                    'author': 'assistant_draft_for_human_review', 'clinical_rule': False,
                    'validation_status': 'draft_only_no_independent_raters',
                    'automation_status': 'no_natural_language_scorer_implemented',
                    'mapping_to_real_v04_rules': 0})
    require(all(text(rule[k]) for k in ('criterion_id', 'capability', 'description')), 'missing rule description')
    turns = rule['source_turns']
    require(isinstance(turns, list) and len(turns) > 0 and len(turns) % 2 == 1,
            'source prefix must end with a user turn')
    for n, turn in enumerate(turns):
        keys(turn, {'turn_id', 'role', 'content'}, 'turn')
        expected_role = 'user' if n % 2 == 0 else 'assistant'
        expected_id = ('u' if n % 2 == 0 else 'a') + str(n // 2 + 1)
        require(turn['role'] == expected_role and turn['turn_id'] == expected_id and text(turn['content']),
                'prefix role/order/id invalid')
    op = rule['opportunity']
    keys(op, {'trigger', 'response', 'deadline', 'not_reached', 'not_applicable', 'unassessed'}, 'opportunity')
    for key in ('trigger', 'response'):
        keys(op[key], {'turn_id', 'condition'}, key)
        require(text(op[key]['condition']), 'missing condition')
    require(op['trigger']['turn_id'] == turns[-1]['turn_id'], 'trigger must be last visible user turn')
    require(op['response']['turn_id'] == 'a' + str((len(turns) + 1) // 2),
            'response must be first assistant turn after trigger')
    require(all(text(op[k]) for k in ('deadline', 'not_reached', 'not_applicable', 'unassessed')),
            'missing opportunity status/deadline definition')
    keys(rule['anchors'], {'0', '1', '2'}, 'anchors')
    require(all(text(v) for v in rule['anchors'].values()), 'empty anchor')
    keys(rule['serious_error'], {'status', 'reason'}, 'serious error')
    require(rule['serious_error']['status'] == 'not_assessed_by_this_rule' and text(rule['serious_error']['reason']),
            'teaching rule cannot assess clinical severity')
    examples = rule['author_examples']
    require(isinstance(examples, list) and len(examples) == 3, 'requires three author examples')
    grades, contents = [], []
    for e in examples:
        keys(e, {'content', 'illustrative_rating', 'reason'}, 'author example')
        require(text(e['content']) and text(e['reason']), 'empty author example')
        require(type(e['illustrative_rating']) is int and e['illustrative_rating'] in (0, 1, 2), 'invalid example grade')
        grades.append(e['illustrative_rating'])
        contents.append(e['content'])
    require(set(grades) == {0, 1, 2} and len(set(contents)) == 3, 'author examples must cover distinct grades/texts')
    return {'criterion_id': rule['criterion_id'], 'trigger_turn_id': op['trigger']['turn_id'],
            'response_turn_id': op['response']['turn_id'], 'author_examples': len(examples)}


def validate_pack(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    pack = json.loads(raw)
    keys(pack, {'schema_version', 'source', 'split', *FLAGS, 'rules', 'purpose'}, 'pack')
    constants(pack, {**FLAGS, 'schema_version': 'readiness-rule-pack/v0.1', 'source': 'synthetic', 'split': 'development'})
    require(text(pack['purpose']), 'missing purpose')
    files = pack['rules']
    require(isinstance(files, list) and files and all(text(p) for p in files) and len(set(files)) == len(files),
            'invalid or duplicate rule paths')
    results, seen_paths, seen_ids = [], set(), set()
    for filename in files:
        entry = (path.parent / filename).resolve()
        require(entry.is_relative_to(path.parent) and entry.suffix == '.json' and entry not in seen_paths,
                'rule path escapes pack or aliases another rule')
        data = entry.read_bytes()
        result = validate_rule(json.loads(data))
        require(result['criterion_id'] not in seen_ids, 'duplicate criterion')
        seen_paths.add(entry)
        seen_ids.add(result['criterion_id'])
        results.append({**result, 'file': filename, 'sha256': hashlib.sha256(data).hexdigest()})
    return {'schema_version': 'readiness-rule-validation/v0.1', 'structurally_valid': True,
            'source': 'synthetic', 'pack_sha256': hashlib.sha256(raw).hexdigest(),
            'rules_validated': len(results), 'rules_total': len(files),
            'author_examples': sum(r['author_examples'] for r in results), 'rules': results,
            'independent_rater_count': 0, 'real_v04_opportunities_mapped': 0,
            'semantic_scoring_validated': False, 'clinical_validity_assessed': False, **FLAGS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=DEFAULT_PACK)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = validate_pack(args.pack)
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as handle:
            handle.write(content)
    print(content, end='')


if __name__ == '__main__':
    main()
