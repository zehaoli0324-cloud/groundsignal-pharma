"""Build a local SQLite denominator drill from metadata-only synthetic rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from copy import deepcopy
from pathlib import Path

from .agreement import rater_agreement
from .contracts import require
from .study import _write_json


DEFAULT_FIXTURE = (Path(__file__).resolve().parents[2] / 'medical/patient-eval/readiness'
                   / 'statistics-fixture-v0.1.json')
STATUSES = {'completed', 'target_error', 'measurement_invalid'}
OPPORTUNITY_STATUSES = {'occurred', 'not_reached', 'not_applicable', 'unassessed'}
QUALITY_STATUSES = {'assessed', 'unassessed', 'not_applicable'}

CASE_COMPLETION_SQL = """
WITH base_units AS (
  SELECT case_id, COUNT(*) AS units
  FROM (SELECT DISTINCT case_id, platform, arm FROM sessions)
  GROUP BY case_id
)
SELECT c.case_id, c.family_id, COUNT(s.session_id) AS sessions,
       COUNT(s.session_id) - COALESCE(b.units, 0) AS repeat_sessions,
       COALESCE(SUM(s.status = 'completed'), 0) AS completed_sessions,
       COALESCE(SUM(s.status = 'target_error'), 0) AS target_error_sessions,
       COALESCE(SUM(s.status = 'measurement_invalid'), 0) AS measurement_invalid_sessions,
       COALESCE(SUM(s.status IN ('completed', 'target_error')), 0) AS target_metric_sessions
FROM cases c LEFT JOIN sessions s ON s.case_id = c.case_id
LEFT JOIN base_units b ON b.case_id = c.case_id
GROUP BY c.case_id, c.family_id, b.units ORDER BY c.case_id
"""
ERROR_DISTRIBUTION_SQL = """
SELECT status AS session_status,
       CASE WHEN status = 'measurement_invalid' THEN invalid_component
            ELSE termination_reason END AS error_class,
       COUNT(*) AS sessions
FROM sessions WHERE status != 'completed'
GROUP BY session_status, error_class ORDER BY session_status, error_class
"""
BOTH_REVIEWERS_SQL = """
SELECT o.item_id, s.case_id, o.session_id, o.criterion_id,
       MAX(CASE WHEN r.reviewer_id = :reviewer_a THEN r.rating END) AS reviewer_a_rating,
       MAX(CASE WHEN r.reviewer_id = :reviewer_b THEN r.rating END) AS reviewer_b_rating
FROM opportunities o JOIN sessions s ON s.session_id = o.session_id
LEFT JOIN ratings r ON r.item_id = o.item_id
GROUP BY o.item_id, s.case_id, o.session_id, o.criterion_id
HAVING SUM(r.reviewer_id = :reviewer_a AND r.quality_status = 'assessed' AND r.rating IS NOT NULL) > 0
   AND SUM(r.reviewer_id = :reviewer_b AND r.quality_status = 'assessed' AND r.rating IS NOT NULL) > 0
ORDER BY o.item_id
"""

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE cases (case_id TEXT PRIMARY KEY, family_id TEXT NOT NULL);
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
  platform TEXT NOT NULL, arm TEXT NOT NULL, repeat_id INTEGER NOT NULL CHECK(repeat_id >= 0),
  status TEXT NOT NULL CHECK(status IN ('completed','target_error','measurement_invalid')),
  termination_reason TEXT NOT NULL, invalid_component TEXT,
  UNIQUE(case_id, platform, arm, repeat_id),
  CHECK((status = 'measurement_invalid' AND invalid_component IS NOT NULL)
        OR (status != 'measurement_invalid' AND invalid_component IS NULL))
);
CREATE TABLE opportunities (
  item_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id),
  criterion_id TEXT NOT NULL,
  recorded_status TEXT NOT NULL CHECK(recorded_status IN ('occurred','not_reached','not_applicable','unassessed'))
);
CREATE TABLE ratings (
  item_id TEXT NOT NULL REFERENCES opportunities(item_id), reviewer_id TEXT NOT NULL,
  criterion_id TEXT NOT NULL, review_version TEXT NOT NULL, rubric_version TEXT NOT NULL,
  rating INTEGER CHECK(rating IN (0,1,2)),
  quality_status TEXT NOT NULL CHECK(quality_status IN ('assessed','unassessed','not_applicable')),
  opportunity_status TEXT NOT NULL CHECK(opportunity_status IN ('occurred','not_reached','not_applicable','unassessed')),
  serious_error INTEGER CHECK(serious_error IN (0,1)), PRIMARY KEY(item_id, reviewer_id),
  CHECK((quality_status = 'assessed' AND rating IS NOT NULL AND opportunity_status = 'occurred')
        OR (quality_status != 'assessed' AND rating IS NULL))
);
"""


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _canonical_sha256(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(row, keys, label):
    require(isinstance(row, dict) and set(row) == set(keys), label + ' fields mismatch')


def validate_statistics_bundle(bundle):
    """Validate all relations before creating a database file."""
    require(isinstance(bundle, dict), 'bundle must be an object')
    _exact_keys(bundle, ('schema_version', 'scope', 'source', 'fixture_only',
                         'clinical_approval', 'review_version', 'rubric_version',
                         'reviewers', 'cases', 'sessions', 'opportunities', 'ratings'),
                'bundle')
    require(bundle.get('schema_version') == 'readiness-statistics/v0.1', 'unsupported schema')
    require(bundle.get('scope') == 'development_only' and bundle.get('source') == 'synthetic'
            and bundle.get('fixture_only') is True and bundle.get('clinical_approval') is False,
            'only non-clinical synthetic fixtures are accepted')
    require(bundle.get('review_version') == 'patient-review/v0.3', 'unsupported review version')
    rubric = bundle.get('rubric_version')
    require(_nonempty(rubric), 'rubric version is required')
    reviewers = bundle.get('reviewers')
    require(isinstance(reviewers, list) and len(reviewers) == 2
            and all(_nonempty(item) for item in reviewers)
            and reviewers[0] != reviewers[1], 'two distinct reviewers are required')

    cases = bundle.get('cases')
    require(isinstance(cases, list) and bool(cases), 'cases must be nonempty')
    case_ids = set()
    for row in cases:
        _exact_keys(row, ('case_id', 'family_id'), 'case')
        require(all(_nonempty(row[key]) for key in row), 'case fields must be nonempty')
        require(row['case_id'] not in case_ids, 'duplicate case_id')
        case_ids.add(row['case_id'])

    sessions = bundle.get('sessions')
    require(isinstance(sessions, list) and bool(sessions), 'sessions must be nonempty')
    session_ids, session_keys, session_statuses = set(), set(), {}
    session_fields = ('session_id', 'case_id', 'platform', 'arm', 'repeat_id', 'status',
                      'termination_reason', 'invalid_component')
    for row in sessions:
        _exact_keys(row, session_fields, 'session')
        require(all(_nonempty(row[key]) for key in ('session_id', 'case_id', 'platform', 'arm',
                                                     'termination_reason')), 'session fields missing')
        require(row['arm'] in {'baseline', 'state_augmented'}, 'invalid study arm')
        require(row['case_id'] in case_ids, 'session refers to unknown case')
        require(type(row['repeat_id']) is int and row['repeat_id'] >= 0, 'invalid repeat_id')
        require(row['status'] in STATUSES, 'invalid session status')
        require((row['status'] == 'measurement_invalid' and _nonempty(row['invalid_component']))
                or (row['status'] != 'measurement_invalid' and row['invalid_component'] is None),
                'invalid component/status combination')
        key = (row['case_id'], row['platform'], row['arm'], row['repeat_id'])
        require(row['session_id'] not in session_ids and key not in session_keys,
                'duplicate session identity')
        session_ids.add(row['session_id'])
        session_keys.add(key)
        session_statuses[row['session_id']] = row['status']

    opportunities = bundle.get('opportunities')
    require(isinstance(opportunities, list) and bool(opportunities),
            'opportunities must be nonempty')
    item_ids, item_criteria, item_session_statuses = set(), {}, {}
    for row in opportunities:
        _exact_keys(row, ('item_id', 'session_id', 'criterion_id', 'recorded_status'), 'opportunity')
        require(all(_nonempty(row[key]) for key in ('item_id', 'session_id', 'criterion_id')),
                'opportunity fields missing')
        require(row['item_id'] not in item_ids and row['session_id'] in session_ids,
                'duplicate item or unknown session')
        require(row['recorded_status'] in OPPORTUNITY_STATUSES, 'invalid opportunity status')
        if session_statuses[row['session_id']] == 'measurement_invalid':
            require(row['recorded_status'] == 'unassessed',
                    'invalid measurements cannot claim an opportunity state')
        item_ids.add(row['item_id'])
        item_criteria[row['item_id']] = row['criterion_id']
        item_session_statuses[row['item_id']] = session_statuses[row['session_id']]

    ratings = bundle.get('ratings')
    require(isinstance(ratings, list) and bool(ratings), 'ratings must be nonempty')
    pairs = set()
    fields = ('item_id', 'reviewer_id', 'criterion_id', 'review_version', 'rubric_version',
              'rating', 'quality_status', 'opportunity_status', 'serious_error')
    for row in ratings:
        _exact_keys(row, fields, 'rating')
        require(row['item_id'] in item_ids and row['reviewer_id'] in reviewers,
                'rating refers to unknown item or reviewer')
        require(row['criterion_id'] == item_criteria[row['item_id']],
                'rating criterion mismatch')
        require(row['review_version'] == bundle['review_version']
                and row['rubric_version'] == rubric, 'rating version mismatch')
        if item_session_statuses[row['item_id']] == 'measurement_invalid':
            require(row['quality_status'] == 'unassessed' and row['rating'] is None
                    and row['opportunity_status'] == 'unassessed' and row['serious_error'] is None,
                    'invalid measurement cannot contribute quality, opportunity or safety judgments')
        pair = row['item_id'], row['reviewer_id']
        require(pair not in pairs, 'duplicate reviewer/item rating')
        pairs.add(pair)
    # Reuse the established validator and agreement arithmetic; do not implement
    # a second interpretation of missing ratings or weighted kappa here.
    agreement = rater_agreement(deepcopy(ratings), reviewers[0], reviewers[1])
    return agreement


def load_statistics_bundle(path: str | Path):
    try:
        bundle = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        raise ValueError('statistics bundle is unreadable') from None
    validate_statistics_bundle(bundle)
    return bundle


def build_statistics_database(bundle: dict, path: str | Path) -> Path:
    agreement = validate_statistics_bundle(bundle)
    del agreement
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with sqlite3.connect(destination) as db:
        db.executescript(SCHEMA)
        db.executemany('INSERT INTO metadata VALUES (?,?)', [
            ('schema_version', bundle['schema_version']),
            ('bundle_sha256', _canonical_sha256(bundle)),
            ('scope', bundle['scope']), ('source', bundle['source']),
        ])
        db.executemany('INSERT INTO cases VALUES (?,?)',
                       [(row['case_id'], row['family_id']) for row in bundle['cases']])
        db.executemany('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', [
            tuple(row[key] for key in ('session_id', 'case_id', 'platform', 'arm', 'repeat_id',
                                       'status', 'termination_reason', 'invalid_component'))
            for row in bundle['sessions']])
        db.executemany('INSERT INTO opportunities VALUES (?,?,?,?)', [
            tuple(row[key] for key in ('item_id', 'session_id', 'criterion_id', 'recorded_status'))
            for row in bundle['opportunities']])
        db.executemany('INSERT INTO ratings VALUES (?,?,?,?,?,?,?,?,?)', [
            tuple(row[key] for key in ('item_id', 'reviewer_id', 'criterion_id', 'review_version',
                                       'rubric_version', 'rating', 'quality_status',
                                       'opportunity_status', 'serious_error'))
            for row in bundle['ratings']])
    return destination


def _rows(db, sql, parameters=None):
    db.row_factory = sqlite3.Row
    return [dict(row) for row in db.execute(sql, parameters or {})]


def _scalar(db, sql):
    return db.execute(sql).fetchone()[0]


def run_statistics(bundle: dict, database_path: str | Path) -> dict:
    agreement = validate_statistics_bundle(bundle)
    database = build_statistics_database(bundle, database_path)
    reviewer_a, reviewer_b = bundle['reviewers']
    with sqlite3.connect(database) as db:
        queries = {
            'case_completion': _rows(db, CASE_COMPLETION_SQL),
            'error_distribution': _rows(db, ERROR_DISTRIBUTION_SQL),
            'both_reviewers_assessed': _rows(
                db, BOTH_REVIEWERS_SQL,
                {'reviewer_a': reviewer_a, 'reviewer_b': reviewer_b}),
        }
        status = dict(db.execute('SELECT status, COUNT(*) FROM sessions GROUP BY status'))
        opportunity = dict(db.execute(
            'SELECT recorded_status, COUNT(*) FROM opportunities GROUP BY recorded_status'))
        repeat_sessions = _scalar(db, 'SELECT COALESCE(SUM(n - 1), 0) FROM '
                                      '(SELECT COUNT(*) AS n FROM sessions '
                                      'GROUP BY case_id, platform, arm)')
        any_rated = _scalar(db, "SELECT COUNT(DISTINCT item_id) FROM ratings "
                                "WHERE quality_status='assessed' AND rating IS NOT NULL")
        individual = _scalar(db, "SELECT COUNT(*) FROM ratings "
                                 "WHERE quality_status='assessed' AND rating IS NOT NULL")
        missing_both = _scalar(db, 'SELECT COUNT(*) FROM opportunities o WHERE NOT EXISTS '
                                  '(SELECT 1 FROM ratings r WHERE r.item_id=o.item_id)')
        review_union = _scalar(db, 'SELECT COUNT(DISTINCT item_id) FROM ratings')
        invalid_opportunities = _scalar(
            db, "SELECT COUNT(*) FROM opportunities o JOIN sessions s ON s.session_id=o.session_id "
                "WHERE s.status='measurement_invalid'")
    cases, sessions = len(bundle['cases']), len(bundle['sessions'])
    completed = status.get('completed', 0)
    target_errors = status.get('target_error', 0)
    invalid = status.get('measurement_invalid', 0)
    denominator = completed + target_errors
    denominators = {
        'cases': cases, 'sessions': sessions, 'repeat_sessions': repeat_sessions,
        'completed_sessions': completed, 'target_error_sessions': target_errors,
        'measurement_invalid_sessions': invalid, 'target_metric_sessions': denominator,
        'planned_opportunities': len(bundle['opportunities']),
        'occurred_opportunities': opportunity.get('occurred', 0),
        'not_reached_opportunities': opportunity.get('not_reached', 0),
        'unassessed_opportunities': opportunity.get('unassessed', 0),
        'not_applicable_opportunities': opportunity.get('not_applicable', 0),
        'opportunities_on_measurement_invalid_sessions': invalid_opportunities,
        'opportunities_with_any_quality_rating': any_rated,
        'opportunities_with_both_quality_ratings': len(queries['both_reviewers_assessed']),
        'individual_quality_ratings': individual,
        'opportunities_missing_both_reviewer_rows': missing_both,
    }
    return {
        'schema_version': 'readiness-statistics-report/v0.1',
        'scope': 'development_only', 'source': 'synthetic',
        'input_bundle_sha256': _canonical_sha256(bundle),
        'denominators': denominators,
        'service_completion': {
            'numerator': completed, 'denominator': denominator,
            'rate': completed / denominator if denominator else None,
            'excluded_measurement_invalid': invalid,
            'definition': ('完成会话 /（完成会话 + 目标接口失败）；测量无效单独报告，'
                           '因为这类会话没有形成对被测系统的有效测量'),
        },
        'queries': queries,
        'agreement_input': {
            'expected_opportunities': len(bundle['opportunities']),
            'items_present_in_either_reviewer_input': review_union,
            'items_missing_both_reviewers': missing_both,
        },
        'agreement': agreement,
        'limitations': [
            '重复会话不是新的独立病例。',
            '未评分、未到达、不适用和缺少评审记录都不能填成零分。',
            '加权科恩一致性系数只衡量两位评审的一致程度，不能证明医学正确性或评审资质。',
            '本小表为作者构造的合成材料，只用于核对分母和查询。',
        ],
        'external_model_calls': 0, 'real_source_sessions': 0,
        'clinical_approval': False, 'personal_skill_verified': False,
        'human_handoff_verified': False, 'training_data_generated': False,
        's6_automatic_trust': 'BLOCKED',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError(args.report)
    bundle = load_statistics_bundle(args.input)
    report = run_statistics(bundle, args.db)
    _write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
