from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.clinical_console import demo_packet
from scripts.patient_eval.choice_adjudication import (prepare_queue, decision_template,
                                                      apply_decisions, run_files)
from scripts.patient_eval.import_batch import scenario_digest
from tests.patient_eval.test_clinical_console_interactions import node


class ChoiceAdjudicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = demo_packet()
        cls.fixtures = node(cls.original)

    def setUp(self):
        self.left = deepcopy(self.fixtures['fixtures']['four_defaults'])
        self.right = deepcopy(self.left)
        self.right['answers']['reviewer_id'] = 'reviewer-B'
        self.right['answers']['items'][0]['facts'][0]['answer'] = 'uncertain'
        record = self.right['answers']['interaction']['records'][0]
        record['selection'] = 'uncertain'
        record['confirmation'].update(method='selection', answer='uncertain')

    def decision(self):
        queue = prepare_queue(self.original, self.left, self.right)
        draft = decision_template(queue)
        draft['adjudicator_id'] = 'SYNTHETIC-COORDINATOR-NOT-CLINICAL-REVIEW'
        row = next(r for r in queue['rows'] if r['status'] == 'disagreement')
        draft['decisions'] = [{'row_id': row['row_id'], 'answer': 'supported',
                               'reason': '合成教学：本题只判断原文语义支持，不补造事实配置。'}]
        return draft

    def test_confirmed_disagreement_missing_and_agreement_are_separate(self):
        q = prepare_queue(self.original, self.left, self.right)
        self.assertEqual(q['counts'], {'agreed': 3, 'disagreement': 1, 'missing_answer': 8})
        self.assertFalse(q['formal_approval'])
        self.assertFalse(q['independence_verified'])

    def test_matching_selections_without_confirmation_do_not_form_agreement(self):
        self.right = deepcopy(self.fixtures['fixtures']['selected'])
        self.right['answers']['reviewer_id'] = 'reviewer-B'
        self.left = deepcopy(self.right)
        self.left['answers']['reviewer_id'] = 'reviewer-A'
        q = prepare_queue(self.original, self.left, self.right)
        self.assertEqual(q['counts'], {'confirmation_required': 1, 'missing_answer': 11})

    def test_legacy_answers_need_reconfirmation(self):
        self.right['schema_version'] = 'clinical-console-choice-bundle/v0.2'
        self.right['answers']['schema_version'] = 'clinical-console-choices/v0.2'
        self.right['answers'].pop('interaction')
        q = prepare_queue(self.original, self.left, self.right)
        self.assertEqual(q['counts'], {'confirmation_required': 4, 'missing_answer': 8})

    def test_projection_keeps_originals_and_never_invents_fact_configuration(self):
        before = deepcopy((self.left, self.right))
        result, review = apply_decisions(self.original, self.left, self.right, self.decision())
        self.assertEqual(before, (self.left, self.right))
        self.assertEqual(result['counts'], {'adjudicated': 1, 'confirmed_agreement': 3, 'unresolved': 8})
        self.assertEqual(review['items'][0]['review']['facts'][0]['decision'], 'unreviewed')
        self.assertEqual(review['items'][0]['review']['rubrics'][0]['decision'], 'unreviewed')
        self.assertEqual(result['runtime_observations'], 0)
        self.assertFalse(result['clinical_gold'])
        self.assertEqual(result['review_sha256'], scenario_digest(review))
        self.assertTrue(review['reviewer_id'].startswith('adjudication:'))

    def test_partial_decisions_remain_unresolved(self):
        d = self.decision()
        d['decisions'] = []
        result, _ = apply_decisions(self.original, self.left, self.right, d)
        self.assertEqual(result['counts'], {'confirmed_agreement': 3, 'unresolved': 9})
        row = next(r for r in result['rows'] if r['status'] == 'disagreement')
        self.assertEqual(row['resolved_answer'], 'pending')

    def test_stale_review_same_packet_rejected(self):
        d = self.decision()
        self.left['answers']['profile']['background'] = 'researcher'
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply_decisions(self.original, self.left, self.right, d)

    def test_missing_rows_invalid_options_duplicates_and_promotion_rejected(self):
        q = prepare_queue(self.original, self.left, self.right)
        missing = next(r for r in q['rows'] if r['status'] == 'missing_answer')['row_id']
        mutations = [lambda d: d['decisions'][0].update(row_id=missing),
                     lambda d: d['decisions'][0].update(answer='pending'),
                     lambda d: d['decisions'][0].update(reason=' '),
                     lambda d: d['decisions'].append(deepcopy(d['decisions'][0])),
                     lambda d: d.update(formal_approval=True),
                     lambda d: d.update(clinical_gold=0),
                     lambda d: d.update(adjudicator_id=''),
                     lambda d: d.update(queue_sha256='0' * 64)]
        for i, mutate in enumerate(mutations):
            d = self.decision()
            mutate(d)
            with self.subTest(i=i), self.assertRaises(ValueError):
                apply_decisions(self.original, self.left, self.right, d)

    def test_same_seat_or_modified_source_rejected(self):
        with self.assertRaises(ValueError):
            prepare_queue(self.original, self.left, self.left)
        self.right['packet']['items'][0]['turns'][0]['content'] = 'tampered'
        with self.assertRaises(ValueError):
            prepare_queue(self.original, self.left, self.right)

    def test_file_roundtrip_preserves_inputs_and_refuses_overwrite_or_stale_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, value in [('original', self.original), ('left', self.left), ('right', self.right),
                                ('decisions', self.decision())]:
                (root / name).write_text(json.dumps(value))
            args = [root / k for k in ('original', 'left', 'right')]
            q = run_files(*args, root / 'queue')
            result = run_files(*args, root / 'result', root / 'decisions')
            self.assertEqual(result['queue_sha256'], scenario_digest(q))
            saved = (root / 'result/result.json').read_bytes()
            self.assertEqual(json.loads((root / 'result/reviewer-a.json').read_bytes()), self.left)
            with self.assertRaises(FileExistsError):
                run_files(*args, root / 'result', root / 'decisions')
            self.assertEqual(saved, (root / 'result/result.json').read_bytes())
            d = self.decision()
            d['queue_sha256'] = '0' * 64
            (root / 'decisions').write_text(json.dumps(d))
            with self.assertRaises(ValueError):
                run_files(*args, root / 'invalid', root / 'decisions')
            self.assertFalse((root / 'invalid').exists())


if __name__ == '__main__':
    unittest.main()
