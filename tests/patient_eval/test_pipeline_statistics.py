from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.patient_eval.event_mapping import map_candidates, transcript_digest
from scripts.patient_eval.import_batch import digest_bytes, write_new_json
from scripts.patient_eval.pipeline_statistics import convert_pipeline, run_bridge
from scripts.patient_eval.readiness_pipeline import fixtures, mock_review_sessions


class PipelineStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.suite, self.sessions, self.plan = fixtures()
        self.raw = (json.dumps(self.suite, ensure_ascii=False, indent=2) + '\n').encode()
        mapping = map_candidates(self.sessions, self.suite, digest_bytes(self.raw), self.plan)
        self.reviewed = mock_review_sessions(self.sessions, mapping)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'suite.json').write_bytes(self.raw)
        write_new_json(self.root / 'plan.json', self.plan)

    def run_saved(self, sessions, name):
        source = self.root / (name + '-sessions.json')
        write_new_json(source, sessions)
        return run_bridge(self.root / 'suite.json', source, self.root / 'plan.json', self.root / name)

    def test_unreviewed_candidates_remain_unknown_with_empty_ratings(self):
        report = self.run_saved(self.sessions, 'before')
        stats = report['statistics']
        self.assertEqual(report['outcome_counts'], {'unassessed': 7})
        self.assertEqual(stats['denominators']['planned_opportunities'], 7)
        self.assertEqual(stats['denominators']['unassessed_opportunities'], 7)
        self.assertEqual(stats['denominators']['occurred_opportunities'], 0)
        self.assertEqual(stats['denominators']['opportunities_missing_both_reviewer_rows'], 7)
        self.assertIsNone(stats['agreement'])
        self.assertEqual(report['quality_trace'], [])
        self.assertEqual(report['failure_queue'], [])
        self.assertEqual(report['passed'], report['total'])

    def test_mock_reviews_join_to_statistics_and_failure_evidence(self):
        report = self.run_saved(self.reviewed, 'after')
        stats = report['statistics']
        self.assertEqual(report['outcome_counts'], {'fail': 1, 'pass': 2, 'unassessed': 4})
        expected = {'cases': 3, 'sessions': 7, 'target_metric_sessions': 6,
                    'measurement_invalid_sessions': 1, 'planned_opportunities': 7,
                    'occurred_opportunities': 3, 'unassessed_opportunities': 4,
                    'individual_quality_ratings': 3, 'opportunities_with_both_quality_ratings': 0,
                    'opportunities_missing_both_reviewer_rows': 4}
        for key, value in expected.items():
            self.assertEqual(stats['denominators'][key], value, key)
        self.assertEqual(stats['agreement']['paired_rated_items'], 0)
        self.assertIsNone(stats['agreement']['linear_weighted_cohen_kappa'])
        failure, = report['failure_queue']
        self.assertEqual(failure['evidence_turn_ids'], ['u2', 'a2'])
        links = json.loads((self.root / 'after/evidence-links.json').read_bytes())
        link = next(row for row in links['rows'] if row['item_id'] == failure['item_id'])
        original = next(s for s in self.reviewed if s['session_id'] == link['session_id'])
        self.assertEqual(original['observations'][link['observation_index']]['ordinal_rating'], 0)
        self.assertEqual(link['transcript_sha256'], transcript_digest(original))
        self.assertTrue(link['review_sha256'])
        with sqlite3.connect(self.root / 'after/statistics.sqlite') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ratings WHERE serious_error IS NOT NULL').fetchone()[0], 0)
        self.assertEqual(report['passed'], report['total'])

    def test_stale_transcript_rejected_before_any_output(self):
        self.reviewed[0]['turns'][-1]['content'] = 'changed answer'
        with self.assertRaisesRegex(ValueError, 'stale transcript'):
            self.run_saved(self.reviewed, 'stale')
        self.assertFalse((self.root / 'stale').exists())

    def test_behavior_failure_without_ordinal_rating_still_enters_failure_queue(self):
        for session in self.reviewed:
            for observation in session['observations']:
                if observation['outcome'] == 'fail':
                    observation.update(quality_status='unassessed', ordinal_rating=None)
        report = self.run_saved(self.reviewed, 'behavior-only')
        self.assertEqual(report['statistics']['denominators']['individual_quality_ratings'], 2)
        failure, = report['failure_queue']
        self.assertIsNone(failure['rating'])
        self.assertEqual(failure['evidence_turn_ids'], ['u2', 'a2'])

    def test_real_claims_legacy_reviews_and_second_reviewer_not_silently_converted(self):
        mutations = [lambda s: s[0]['metadata'].update(fixture_only=False),
                     lambda s: s[0]['metadata'].update(clinical_approval=True),
                     lambda s: s[0]['observations'][0].update(independent_review=True),
                     lambda s: s[0]['observations'][0].update(reviewer_id='ACTUAL-HUMAN'),
                     lambda s: s[0]['observations'][0].update(rubric_version='other')]
        for index, mutate in enumerate(mutations):
            sessions = deepcopy(self.reviewed)
            mutate(sessions)
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.run_saved(sessions, 'invalid-' + str(index))
            self.assertFalse((self.root / ('invalid-' + str(index))).exists())

    def test_later_answer_cannot_replace_mapped_answer_in_statistics(self):
        session = self.reviewed[0]
        session['turns'] += [{'turn_id': 'u3', 'role': 'user', 'content': '再核对一次'},
                             {'turn_id': 'a3', 'role': 'assistant', 'content': '后来修复'}]
        self.plan['session_events'][0]['transcript_sha256'] = transcript_digest(session)
        session['observations'][0]['opportunity']['response_turn_id'] = 'a3'
        session['observations'][0]['evidence_turn_ids'] = ['u2', 'a3']
        with self.assertRaisesRegex(ValueError, 'review boundary'):
            convert_pipeline(self.raw, self.reviewed, self.plan)

    def test_invalid_capture_cannot_carry_preexisting_score(self):
        self.reviewed[0].update(status='measurement_invalid', invalid_component='collector', invalid_reason='fixture')
        self.plan['session_events'][0]['transcript_sha256'] = transcript_digest(self.reviewed[0])
        with self.assertRaises(ValueError):
            convert_pipeline(self.raw, self.reviewed, self.plan)

    def test_inputs_unchanged_and_existing_output_preserved(self):
        original = deepcopy((self.reviewed, self.plan))
        first = self.run_saved(self.reviewed, 'saved')
        self.assertEqual(original, (self.reviewed, self.plan))
        path = self.root / 'saved/report.json'
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            run_bridge(self.root / 'suite.json', self.root / 'saved-sessions.json',
                       self.root / 'plan.json', self.root / 'saved')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(first, self.run_saved(self.reviewed, 'repeat'))


if __name__ == '__main__':
    unittest.main()
