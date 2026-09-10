import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.patient_eval.readiness_statistics import (BOTH_REVIEWERS_SQL,
    CASE_COMPLETION_SQL, DEFAULT_FIXTURE, ERROR_DISTRIBUTION_SQL,
    build_statistics_database, load_statistics_bundle, run_statistics)


class ReadinessStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = load_statistics_bundle(DEFAULT_FIXTURE)

    def analyze(self, bundle=None, name='result'):
        return run_statistics(bundle or self.bundle, self.root / f'{name}.sqlite')

    def test_hand_checkable_denominators_and_three_queries(self):
        report = self.analyze()
        self.assertEqual(report['denominators'], {
            'cases': 3, 'sessions': 7, 'repeat_sessions': 1,
            'completed_sessions': 5, 'target_error_sessions': 1,
            'measurement_invalid_sessions': 1, 'target_metric_sessions': 6,
            'planned_opportunities': 7, 'occurred_opportunities': 3,
            'not_reached_opportunities': 1, 'unassessed_opportunities': 2,
            'not_applicable_opportunities': 1,
            'opportunities_on_measurement_invalid_sessions': 1,
            'opportunities_with_any_quality_rating': 3,
            'opportunities_with_both_quality_ratings': 1,
            'individual_quality_ratings': 4,
            'opportunities_missing_both_reviewer_rows': 1,
        })
        self.assertEqual(len(report['queries']['case_completion']), 3)
        self.assertEqual(sum(row['sessions'] for row in report['queries']['case_completion']), 7)
        self.assertEqual(report['queries']['both_reviewers_assessed'], [{
            'item_id': 'case-a:baseline:r0:correction', 'case_id': 'case-a',
            'session_id': 'case-a:baseline:r0', 'criterion_id': 'correction',
            'reviewer_a_rating': 1, 'reviewer_b_rating': 2,
        }])
        errors = {(row['session_status'], row['error_class']): row['sessions']
                  for row in report['queries']['error_distribution']}
        self.assertEqual(errors[('target_error', 'transport_error')], 1)
        self.assertEqual(errors[('measurement_invalid', 'collector')], 1)

    def test_service_completion_keeps_target_error_and_excludes_invalid_measurement(self):
        report = self.analyze()
        self.assertEqual(report['service_completion']['numerator'], 5)
        self.assertEqual(report['service_completion']['denominator'], 6)
        self.assertAlmostEqual(report['service_completion']['rate'], 5 / 6)
        self.assertEqual(report['service_completion']['excluded_measurement_invalid'], 1)

    def test_unassessed_not_reached_and_missing_rows_never_become_zero(self):
        report = self.analyze()
        self.assertEqual(report['queries']['both_reviewers_assessed'][0]['item_id'],
                         'case-a:baseline:r0:correction')
        with sqlite3.connect(self.root / 'result.sqlite') as db:
            values = db.execute(
                "SELECT rating FROM ratings WHERE quality_status != 'assessed'"
            ).fetchall()
        self.assertTrue(values)
        self.assertTrue(all(value[0] is None for value in values))
        self.assertEqual(report['agreement']['total_items'], 6)
        self.assertEqual(report['agreement_input']['expected_opportunities'], 7)
        self.assertEqual(report['agreement_input']['items_missing_both_reviewers'], 1)

    def test_case_session_and_repeat_units_are_not_interchangeable(self):
        report = self.analyze()
        self.assertEqual(report['denominators']['cases'], 3)
        self.assertEqual(report['denominators']['sessions'], 7)
        self.assertEqual(report['denominators']['repeat_sessions'], 1)
        case_a = next(row for row in report['queries']['case_completion']
                      if row['case_id'] == 'case-a')
        self.assertEqual((case_a['sessions'], case_a['repeat_sessions']), (3, 1))

    def test_invalid_source_and_relations_fail_before_database_creation(self):
        mutations = {
            'real_source': lambda b: b.update(source='deidentified_real'),
            'unknown_session': lambda b: b['opportunities'][0].update(session_id='missing'),
            'unknown_item': lambda b: b['ratings'][0].update(item_id='missing'),
            'duplicate_session': lambda b: b['sessions'].append(copy.deepcopy(b['sessions'][0])),
            'invalid_null': lambda b: b['ratings'][3].update(rating=0),
            'invalid_reviewers': lambda b: b.update(reviewers=['same', 'same']),
        }
        for label, mutation in mutations.items():
            bundle = copy.deepcopy(self.bundle)
            mutation(bundle)
            path = self.root / f'{label}.sqlite'
            with self.subTest(label=label), self.assertRaises(ValueError):
                run_statistics(bundle, path)
            self.assertFalse(path.exists())

    def test_case_with_no_session_remains_visible_with_zero_counts(self):
        self.bundle['cases'].append({'case_id': 'case-not-run', 'family_id': 'not-run'})
        report = self.analyze()
        row = next(item for item in report['queries']['case_completion']
                   if item['case_id'] == 'case-not-run')
        self.assertEqual(row, {
            'case_id': 'case-not-run', 'family_id': 'not-run', 'sessions': 0,
            'repeat_sessions': 0, 'completed_sessions': 0,
            'target_error_sessions': 0, 'measurement_invalid_sessions': 0,
            'target_metric_sessions': 0,
        })
        self.assertEqual(report['denominators']['cases'], 4)

    def test_existing_database_is_not_overwritten(self):
        path = self.root / 'existing.sqlite'
        path.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            build_statistics_database(self.bundle, path)
        self.assertEqual(path.read_bytes(), b'keep')

    def test_published_sql_matches_executed_queries(self):
        path = DEFAULT_FIXTURE.with_name('statistics-queries-v0.1.sql')
        statements = []
        for statement in path.read_text(encoding='utf-8').split(';'):
            lines = [line for line in statement.splitlines()
                     if line.strip() and not line.lstrip().startswith('--')]
            if lines:
                statements.append(' '.join(' '.join(lines).split()))
        executed = [' '.join(query.split()) for query in
                    (CASE_COMPLETION_SQL, ERROR_DISTRIBUTION_SQL, BOTH_REVIEWERS_SQL)]
        self.assertEqual(statements, executed)

    def test_input_bundle_is_unchanged_and_report_is_deterministic(self):
        original = copy.deepcopy(self.bundle)
        first = self.analyze(name='first')
        second = self.analyze(name='second')
        self.assertEqual(self.bundle, original)
        self.assertEqual(first, second)
        self.assertFalse(first['clinical_approval'])
        self.assertEqual(first['external_model_calls'], 0)
        self.assertFalse(first['personal_skill_verified'])


if __name__ == '__main__':
    unittest.main()
