"""Negative contract tests for teaching examples, not a natural-language judge."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.readiness_rules import DEFAULT_PACK, validate_pack, validate_rule


class ReadinessRulesTests(unittest.TestCase):
    def setUp(self):
        self.rule = json.loads((DEFAULT_PACK.parent / 'correction-opportunity-v0.1.json').read_text())

    def test_three_rules_preserve_unvalidated_status(self):
        report = validate_pack(DEFAULT_PACK)
        self.assertEqual((report['rules_validated'], report['author_examples']), (3, 9))
        self.assertEqual(report['independent_rater_count'], 0)
        self.assertEqual(report['real_v04_opportunities_mapped'], 0)
        self.assertFalse(report['semantic_scoring_validated'])

    def test_trigger_and_response_cannot_reference_wrong_turns(self):
        for field, turn in [('trigger', 'a1'), ('trigger', 'u1'), ('response', 'a1'), ('response', 'a3')]:
            with self.subTest(field=field, turn=turn):
                r = deepcopy(self.rule)
                r['opportunity'][field]['turn_id'] = turn
                with self.assertRaises(ValueError):
                    validate_rule(r)

    def test_flags_and_example_grade_types_cannot_promote_trust(self):
        for key, value in [('clinical_gold', True), ('formal_approval', 0), ('clinical_rule', True),
                           ('source', 'real'), ('mapping_to_real_v04_rules', True)]:
            r = deepcopy(self.rule)
            r[key] = value
            with self.assertRaises(ValueError):
                validate_rule(r)
        self.rule['author_examples'][0]['illustrative_rating'] = True
        with self.assertRaises(ValueError):
            validate_rule(self.rule)

    def test_status_definitions_and_grade_coverage_are_required(self):
        for field in ['not_reached', 'not_applicable', 'unassessed', 'deadline']:
            r = deepcopy(self.rule)
            r['opportunity'][field] = ''
            with self.assertRaises(ValueError):
                validate_rule(r)
        self.rule['author_examples'][0]['illustrative_rating'] = 1
        with self.assertRaises(ValueError):
            validate_rule(self.rule)

    def test_pack_rejects_path_escape_and_duplicate_criteria(self):
        pack = json.loads(DEFAULT_PACK.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'pack.json'
            for names in [['../outside.json'], ['one.json', './one.json'], ['one.json', 'two.json']]:
                pack['rules'] = names
                path.write_text(json.dumps(pack))
                for name in ['one.json', 'two.json']:
                    (root / name).write_text(json.dumps(self.rule))
                with self.assertRaises(ValueError):
                    validate_pack(path)


if __name__ == '__main__':
    unittest.main()
