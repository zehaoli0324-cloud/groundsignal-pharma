"""Choice roundtrip, non-promotion, privacy and comparison regressions; synthetic only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from scripts.patient_eval.clinical_console import demo_packet, render_console
from scripts.patient_eval.clinical_console_choices import OPTIONS, validate_choices, compare_choices


class ClinicalConsoleChoicesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = demo_packet()
        proc = subprocess.run(['node', 'tests/patient_eval/clinical_console_choices.cjs'],
            cwd=Path(__file__).resolve().parents[2], input=json.dumps(cls.original),
            text=True, capture_output=True, check=True)
        cls.data = json.loads(proc.stdout)

    def setUp(self):
        self.bundle = deepcopy(self.data['bundle'])

    def test_choice_roundtrip_does_not_invent_fact_admission_or_scores(self):
        report, review = validate_choices(self.original, self.bundle)
        facts = review['items'][0]['review']['facts']
        self.assertEqual(facts[0]['decision'], 'unreviewed')
        self.assertEqual(facts[1]['decision'], 'uncertain')
        self.assertEqual(report['counts']['supported_semantics'], 1)
        self.assertEqual(report['counts']['answered'], 8)
        self.assertEqual(report['counts']['total'], 12)
        self.assertEqual(review['items'][0]['review']['rubrics'][0]['applicability'], 'applicable')
        self.assertEqual(review['items'][0]['review']['rubrics'][0]['decision'], 'unreviewed')
        self.assertFalse(report['clinical_gold'])

    def test_all_frontend_options_are_accepted_and_match_backend(self):
        for key in OPTIONS:
            self.assertEqual(set(self.data['options'][key]), OPTIONS[key])
        for section, id_key in [('facts', 'fact_id'), ('privacy', 'turn_id'), ('rubrics', 'criterion_id')]:
            for value in OPTIONS[section]:
                with self.subTest(section=section, value=value):
                    b = deepcopy(self.bundle)
                    b['answers']['items'][0][section][0]['answer'] = value
                    validate_choices(self.original, b)
        for value in OPTIONS['completeness']:
            self.bundle['answers']['items'][0]['completeness'] = value
            validate_choices(self.original, self.bundle)

    def test_privacy_clearance_requires_every_turn_clear(self):
        _, full = validate_choices(self.original, self.bundle)
        self.assertEqual(full['items'][0]['review']['privacy']['decision'], 'reviewed_no_identifiers')
        for value in ('pending', 'risk', 'uncertain'):
            self.bundle['answers']['items'][0]['privacy'][0]['answer'] = value
            _, review = validate_choices(self.original, self.bundle)
            self.assertEqual(review['items'][0]['review']['privacy']['decision'], 'unreviewed')
            self.assertEqual(review['items'][0]['review']['privacy']['additional_spans'], [])

    def test_changed_source_flags_ids_and_invalid_choices_are_rejected(self):
        mutations = [lambda b: b['packet']['items'][0]['turns'][0].update(content='tampered'),
                     lambda b: b['answers'].update(formal_approval=True),
                     lambda b: b['answers'].update(clinical_gold=0),
                     lambda b: b['answers']['items'][0]['facts'][0].update(answer='approved'),
                     lambda b: b['answers']['items'][0]['facts'][0].update(fact_id='wrong'),
                     lambda b: b['answers']['items'][0]['privacy'].pop(),
                     lambda b: b['answers']['profile'].update(background='verified_doctor')]
        for mutate in mutations:
            b = deepcopy(self.bundle)
            mutate(b)
            with self.assertRaises(ValueError):
                validate_choices(self.original, b)

    def test_comparison_preserves_support_and_pending_without_claiming_independence(self):
        b = deepcopy(self.bundle)
        b['answers']['reviewer_id'] = 'reviewer-B'
        b['answers']['items'][0]['facts'][0]['answer'] = 'uncertain'
        result = compare_choices(self.original, self.bundle, b)
        self.assertEqual(len(result['differences']), 1)
        self.assertEqual(len(result['missing']), 4)
        self.assertEqual(result['both_answered'], 8)
        self.assertFalse(result['independence_verified'])
        with self.assertRaises(ValueError):
            compare_choices(self.original, self.bundle, self.bundle)

    def test_question_exclusion_is_explicit_and_pending_remains_unreviewed(self):
        a = self.bundle['answers']['items'][0]
        a['facts'][0]['answer'] = 'question'
        a['facts'][1]['answer'] = 'pending'
        _, review = validate_choices(self.original, self.bundle)
        f = review['items'][0]['review']['facts']
        self.assertEqual(f[0]['decision'], 'exclude')
        self.assertFalse(f[0]['is_patient_assertion'])
        self.assertEqual(f[1]['decision'], 'unreviewed')
        self.assertIsNone(f[1]['reason'])

    def test_render_includes_default_choice_mode_and_embedded_script(self):
        html = render_console()
        self.assertIn('<body class="quick-mode">', html)
        self.assertIn('医生点选', html)
        self.assertNotIn('/* CONSOLE_CHOICES */', html)
        self.assertIn('clinical-console-choice-bundle/v0.2', html)
        js = Path('scripts/patient_eval/clinical_console_assets/choices.js').read_text()
        for forbidden in ('fetch(', 'localStorage', 'sessionStorage', 'innerHTML', "el('textarea'", "type='text'"):
            self.assertNotIn(forbidden, js)


if __name__ == '__main__':
    unittest.main()
