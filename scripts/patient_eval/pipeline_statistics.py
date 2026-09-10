"""Convert explicitly authored R10 fixtures to R4 statistics with evidence links.

This adapter accepts one synthetic author, not independent human reviews or
real dynamic cases. Candidate discovery never supplies an opportunity judgment.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from .cli import evaluate_sessions
from .contracts import require
from .event_mapping import map_candidates, transcript_digest
from .import_batch import digest_bytes, scenario_digest, write_new_json
from .readiness_statistics import run_statistics, validate_statistics_bundle
from .review_contract import REVIEW_VERSION

AUTHOR = "SYNTHETIC-AUTHOR-NOT-A-HUMAN-REVIEW"
ABSENT_REVIEWER = "SYNTHETIC-REVIEWER-B-NO-RECORDS"
RUBRIC = "r10-fixture-draft/v1"


def convert_pipeline(suite_raw, sessions, plan):
    suite = json.loads(suite_raw)
    mapping = map_candidates(sessions, suite, digest_bytes(suite_raw), plan)
    by_id = {s["session_id"]: s for s in sessions}
    for session in sessions:
        meta = session["metadata"]
        require(meta.get("fixture_only") is True and meta.get("clinical_approval") is False
                and session["platform"] == "LOCAL-AUTHORED-FIXTURE-NO-MODEL",
                "statistics bridge requires explicit authored fixtures")
    bundle = {"schema_version": "readiness-statistics/v0.1", "scope": "development_only",
              "source": "synthetic", "fixture_only": True, "clinical_approval": False,
              "review_version": REVIEW_VERSION, "rubric_version": RUBRIC,
              "reviewers": [AUTHOR, ABSENT_REVIEWER],
              "cases": [{"case_id": s["scenario_id"], "family_id": s["family_id"]}
                        for s in suite["scenarios"]],
              "sessions": [], "opportunities": [], "ratings": []}
    # These serials label fixture variants; they are not repeated experiments.
    serials = Counter()
    for session in sorted(sessions, key=lambda s: s["session_id"]):
        case = session["scenario_id"]
        bundle["sessions"].append({"session_id": session["session_id"], "case_id": case,
            "platform": session["platform"], "arm": "baseline", "repeat_id": serials[case],
            "status": session["status"], "termination_reason": "fixture_status_" + session["status"],
            "invalid_component": session.get("invalid_component")})
        serials[case] += 1
    evidence = []
    for candidate in mapping["candidates"]:
        session = by_id[candidate["session_id"]]
        cid = candidate["criterion_id"]
        # A canonical tuple hash avoids ambiguous delimiter-based identities.
        item = scenario_digest([session["session_id"], cid])
        indexed = [(i, o) for i, o in enumerate(session["observations"]) if o["criterion_id"] == cid]
        recorded = "unassessed"
        observation_index = None
        if indexed:
            observation_index, obs = indexed[0]  # duplicate criteria rejected by map_candidates
            require(obs.get("fixture_only") is True and obs.get("independent_review") is False
                    and obs.get("source") == "human" and obs.get("reviewer_id") == AUTHOR
                    and obs.get("rubric_version") == RUBRIC and obs.get("review_version") == REVIEW_VERSION,
                    "only explicit R10 author mock reviews are supported")
            opportunity = obs["opportunity"]
            if opportunity["status"] == "occurred":
                require(candidate["candidate_status"] in {"ready_for_review", "response_missing"}
                        and opportunity["trigger_turn_id"] == candidate["trigger_turn_id"]
                        and opportunity["response_turn_id"] == candidate["response_turn_id"],
                        "review boundary does not match the mapped response")
            recorded = opportunity["status"]
            bundle["ratings"].append({"item_id": item, "reviewer_id": obs["reviewer_id"],
                "criterion_id": cid, "review_version": obs["review_version"],
                "rubric_version": obs["rubric_version"], "rating": obs["ordinal_rating"],
                "quality_status": obs["quality_status"], "opportunity_status": recorded,
                "serious_error": obs["serious_error"]})
        bundle["opportunities"].append({"item_id": item, "session_id": session["session_id"],
            "criterion_id": cid, "recorded_status": recorded})
        evidence.append({"item_id": item, "session_id": session["session_id"], "criterion_id": cid,
            "transcript_sha256": transcript_digest(session), "candidate_status": candidate["candidate_status"],
            "candidate_evidence_turn_ids": candidate["evidence_turn_ids"],
            "observation_index": observation_index,
            "review_evidence_turn_ids": indexed[0][1]["evidence_turn_ids"] if indexed else [],
            "review_sha256": scenario_digest(indexed[0][1]) if indexed else None})
    validate_statistics_bundle(bundle)
    return bundle, {"schema_version": "pipeline-statistics-links/v0.1",
        "scope": "synthetic_integration_only", "independent_reviewers": 0,
        "suite_file_sha256": digest_bytes(suite_raw), "plan_sha256": scenario_digest(plan),
        "sessions_sha256": scenario_digest(sessions), "statistics_bundle_sha256": scenario_digest(bundle),
        "rows": evidence,
        "limitations": ["Second reviewer is an empty planned slot; no row is fabricated.",
            "baseline is a fixture grouping, not a controlled experiment arm.",
            "repeat_id is a sorted fixture serial, not evidence of repeated model runs.",
            "Termination classes carry only supplied status, not an inferred cause.",
            "Candidate states are separate from reviewer opportunity judgments."]}


def run_bridge(suite_path, sessions_path, plan_path, out):
    suite_raw = Path(suite_path).read_bytes()
    sessions_raw, plan_raw = Path(sessions_path).read_bytes(), Path(plan_path).read_bytes()
    sessions, plan = json.loads(sessions_raw), json.loads(plan_raw)
    bundle, links = convert_pipeline(suite_raw, sessions, plan)
    evaluation = evaluate_sessions(json.loads(suite_raw), sessions)
    outcomes = {(s["session_id"], r["criterion_id"]): r
                for s in evaluation["scores"] for r in s["criterion_results"]}
    links.update(sessions_file_sha256=digest_bytes(sessions_raw), plan_file_sha256=digest_bytes(plan_raw))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    write_new_json(out / "bundle.json", bundle)
    write_new_json(out / "evidence-links.json", links)
    statistics = run_statistics(bundle, out / "statistics.sqlite")
    with sqlite3.connect(out / "statistics.sqlite") as db:
        rows = db.execute("SELECT o.item_id, o.session_id, o.criterion_id, r.rating "
                          "FROM opportunities o JOIN ratings r ON r.item_id=o.item_id "
                          "WHERE r.quality_status='assessed' ORDER BY o.item_id").fetchall()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    trail = [{"item_id": item, "session_id": sid, "criterion_id": cid, "rating": rating,
              "outcome": outcomes[(sid, cid)]["outcome"],
              "evidence_turn_ids": outcomes[(sid, cid)]["evidence_turn_ids"]}
             for item, sid, cid, rating in rows]
    # Behavior outcomes and ordinal quality are independent dimensions. A
    # documented behavior failure must survive even without a quality rating.
    failures = []
    for item in bundle["opportunities"]:
        result = outcomes[(item["session_id"], item["criterion_id"])]
        if result["outcome"] == "fail":
            failures.append({key: item[key] for key in ("item_id", "session_id", "criterion_id")})
            failures[-1].update(outcome="fail", rating=result.get("ordinal_rating"),
                                evidence_turn_ids=result["evidence_turn_ids"], reason=result["reason"],
                                attribution="visible_behavior_only; internal cause unverified")
    checks = {
        "database_integrity": integrity == "ok",
        "quality_count_matches_evaluator": len(trail) == sum(
            r.get("quality_status") == "assessed" for r in outcomes.values()),
        "ratings_match_evaluator": all(r["rating"] == outcomes[(r["session_id"], r["criterion_id"])]["ordinal_rating"]
                                       for r in trail),
        "all_planned_items_retained": len(bundle["opportunities"]) == len(outcomes),
        "no_second_reviewer_rows_fabricated": all(r["reviewer_id"] == AUTHOR for r in bundle["ratings"]),
    }
    report = {"schema_version": "pipeline-statistics-bridge/v0.1", "scope": "synthetic_integration_only",
        "clinical_approval": False, "model_calls": 0, "independent_reviewers": 0,
        "statistics": statistics, "quality_trace": trail,
        "failure_queue": failures,
        "outcome_counts": dict(sorted(Counter(r["outcome"] for r in outcomes.values()).items())),
        "checks": checks, "passed": sum(checks.values()), "total": len(checks)}
    write_new_json(out / "report.json", report)
    require(all(checks.values()), "statistics bridge mismatch; evidence preserved")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("suite", "sessions", "plan", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_bridge(args.suite, args.sessions, args.plan, args.out)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f"pipeline statistics failed: {error}\n")
    print(json.dumps({"checks": report["checks"], "outcomes": report["outcome_counts"]}))


if __name__ == "__main__":
    main()
