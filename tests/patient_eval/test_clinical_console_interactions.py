"""New/legacy choice files and cross-language interaction validation; synthetic only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from scripts.patient_eval.clinical_console import demo_packet, render_console
from scripts.patient_eval.clinical_console_choices import validate_choices, compare_choices


def node(payload, *args):
    result = subprocess.run(['node', 'tests/patient_eval/clinical_console_interactions.cjs', *args],
                            input=json.dumps(payload), text=True, capture_output=True,
                            cwd=Path(__file__).resolve().parents[2], check=True)
    return json.loads(result.stdout)


class ClinicalConsoleInteractionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = demo_packet()
        cls.data = node(cls.original)

    def test_all_frontend_roundtrips_pass_authoritative_validator(self):
        self.assertEqual(self.data['checks'], 10)
        for name, bundle in self.data['fixtures'].items():
            with self.subTest(name=name):
                before = deepcopy(bundle)
                report, _ = validate_choices(self.original, bundle)
                self.assertTrue(report['structurally_valid'])
                self.assertEqual(bundle, before)
                self.assertFalse(report['formal_approval'])
                self.assertFalse(report['interaction_summary']['attention_verified'])

    def test_presets_are_displayed_without_answering_and_four_confirmations_recorded(self):
        report, _ = validate_choices(self.original, self.data['fixtures']['viewed'])
        self.assertEqual(report['counts']['answered'], 0)
        self.assertEqual(report['interaction_summary']['latest_display_preset'], 1)
        report, _ = validate_choices(self.original, self.data['fixtures']['four_defaults'])
        self.assertEqual(report['counts']['answered'], 4)
        self.assertEqual(report['interaction_summary']['preset_confirmed'], 4)
        self.assertEqual(report['interaction_summary']['pending'], 8)

    def test_edit_confirm_and_skip_have_distinct_states(self):
        for name, field in [('selected', 'selected_unconfirmed'),
                            ('selection_confirmed', 'selection_confirmed'),
                            ('changed_back_to_default', 'selection_confirmed'),
                            ('edited_after_confirm', 'selected_unconfirmed')]:
            report, _ = validate_choices(self.original, self.data['fixtures'][name])
            self.assertEqual(report['interaction_summary'][field], 1)
            self.assertEqual(report['interaction_summary']['preset_confirmed'], 0)
        report, _ = validate_choices(self.original, self.data['fixtures']['skipped'])
        self.assertEqual(report['counts']['answered'], 0)

    def test_legacy_unknown_is_not_retroactively_upgraded(self):
        for bundle in [self.data['legacy'], self.data['fixtures']['legacy_migrated']]:
            report, _ = validate_choices(self.original, bundle)
            self.assertEqual(report['interaction_summary']['legacy_confirmation_unknown'], 2)
            self.assertEqual(report['interaction_summary']['preset_confirmed'], 0)
        report, _ = validate_choices(self.original, self.data['fixtures']['legacy_reconfirmed'])
        self.assertEqual(report['interaction_summary']['existing_answer_confirmed'], 1)
        self.assertEqual(report['interaction_summary']['legacy_confirmation_unknown'], 1)

    def test_versions_mix_without_changing_answer_comparison_or_projection(self):
        new = self.data['fixtures']['four_defaults']
        old = deepcopy(new)
        old['schema_version'] = 'clinical-console-choice-bundle/v0.2'
        old['answers']['schema_version'] = 'clinical-console-choices/v0.2'
        old['answers'].pop('interaction')
        self.assertEqual(validate_choices(self.original, new)[1], validate_choices(self.original, old)[1])
        old['answers']['reviewer_id'] = 'reviewer-B'
        comparison = compare_choices(self.original, new, old)
        self.assertEqual(comparison['both_answered'], 4)
        self.assertEqual(comparison['differences'], [])

    def test_invalid_records_rejected_in_both_languages(self):
        base = self.data['fixtures']['four_defaults']
        mutations = [lambda a: a['interaction']['records'].pop(),
                     lambda a: a['interaction']['records'].reverse(),
                     lambda a: a['interaction'].update(export_ui_version='future'),
                     lambda a: a['interaction']['records'][0]['display'].update(preset_shown=1),
                     lambda a: a['interaction']['records'][0]['confirmation'].update(answer='uncertain'),
                     lambda a: a['interaction']['records'][0]['confirmation'].update(method='selection'),
                     lambda a: a['interaction']['records'][0].update(last_action='viewed'),
                     lambda a: a['interaction']['records'][0]['origin'].update(ui_version=None),
                     lambda a: a['interaction']['records'][0].update(extra='unrecognized'),
                     lambda a: a.pop('interaction'),
                     lambda a: a.update(schema_version='clinical-console-choices/v0.2')]
        bad = []
        for mutate in mutations:
            bundle = deepcopy(base)
            mutate(bundle['answers'])
            with self.assertRaises(ValueError):
                validate_choices(self.original, bundle)
            bad.append(bundle)
        self.assertEqual(node(bad, '--validate'), [False] * len(bad))

    def test_built_page_wires_recording_to_existing_actions(self):
        html = render_console()
        self.assertIn('默认勾选版 0.2.2', html)
        for function in ('recordDisplay(answers,caseIndex,stage,rowIndex)',
                         'recordSelection(answers,caseIndex,stage,rowIndex,v)',
                         'recordConfirmation(answers,caseIndex,stage,rowIndex)',
                         'recordSkip(answers,caseIndex,stage,rowIndex)', 'restoreBundle(b)'):
            self.assertIn(function, html)
        self.assertIn("facts:'supported',privacy:'clear',rubrics:'applicable',completeness:'usable'", html)


if __name__ == '__main__':
    unittest.main()
