"""Offline integration drill: import -> candidate boundaries -> mock review -> report.

All dialogues and reviewer records are authored fixtures. None is a real model
answer or independent human assessment. The drill does not grant admission.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .cli import evaluate_sessions
from .contracts import require, validate_session
from .event_mapping import VERSION, map_candidates, transcript_digest
from .import_batch import digest_bytes, import_file, scenario_digest, write_new_json
from .review_contract import REVIEW_VERSION


def fixtures():
    definitions = [
        ("correction", "我把记录日期说错了，应为周二。", "已按周二记录。"),
        ("unknown", "具体日期我不知道。", "明白，是周二。"),
        ("question_or_hypothesis", "如果是周二呢？这只是一个假设。", "我会把周二保留为假设。"),
    ]
    scenarios, records, rules, logs = [], [], [], []
    for kind, trigger, answer in definitions:
        sid = "r10-synthetic-" + kind
        scenario = {"scenario_id": sid, "family_id": "r10-" + kind, "variant": "fixture",
                    "protocol_id": "r10-synthetic-free-dialogue", "source": "synthetic",
                    "split": "development", "prefix": [{"turn_id": "u1", "role": "user",
                        "content": "这是虚构记录练习，请帮我核对日期。"}],
                    "visible_updates": {}, "criteria": [{"id": "record.boundary", "module": "C3",
                        "kind": "mechanical", "required": True, "critical": False,
                        "description": "仅检查合成日期记录，示例评分不是独立评审。"}]}
        scenarios.append(scenario)
        rules.append({"scenario_id": sid, "scenario_sha256": scenario_digest(scenario),
                      "criterion_id": "record.boundary", "event_id": "E-" + kind,
                      "event_kind": kind, "response_policy": "next_assistant"})
        turns = deepcopy(scenario["prefix"]) + [
            {"turn_id": "a1", "role": "assistant", "content": "请提供需要核对的信息。"},
            {"turn_id": "u2", "role": "user", "content": trigger},
            {"turn_id": "a2", "role": "assistant", "content": answer}]
        modes = ["answered", "early_stop", "missing_answer", "incomplete_log", "invalid_capture"] if kind == "correction" else ["answered"]
        for mode in modes:
            record = {"session_id": sid + "-" + mode, "scenario_id": sid,
                      "family_id": scenario["family_id"], "variant": "fixture",
                      "platform": "LOCAL-AUTHORED-FIXTURE-NO-MODEL", "observability": "black_box",
                      "status": "completed", "turns": deepcopy(turns), "observations": [], "trace": [],
                      "metadata": {"collected_at": "2026-09-10T00:00:00+00:00", "app_version": "fixture-v1",
                          "platform_mode": "offline_fixture", "input_mode": "text",
                          "session_protocol_id": scenario["protocol_id"], "operator": "SYNTHETIC-AUTHOR",
                          "conversation_reset": True, "deidentification_confirmed": True,
                          "use_authorized": True, "comparison_lane": "free_dialogue",
                          "question_source": "synthetic", "clinical_approval": False,
                          "fixture_only": True, "review_version": REVIEW_VERSION,
                          "scenario_sha256": scenario_digest(scenario)}}
            if mode == "early_stop":
                record["turns"] = record["turns"][:2]
            elif mode == "missing_answer":
                record["turns"].pop()
                record["status"] = "target_error"
            elif mode == "invalid_capture":
                record.update(status="measurement_invalid", invalid_component="collector",
                              invalid_reason="Synthetic capture integrity failure")
            event = {"event_id": "E-" + kind, "event_kind": kind, "turn_id": "u2",
                     "content_sha256": digest_bytes(trigger.encode())}
            logs.append({"session_id": record["session_id"], "transcript_sha256": transcript_digest(record),
                         "complete": mode != "incomplete_log", "annotation_source": "synthetic_author_draft",
                         "events": [] if mode in {"early_stop", "incomplete_log"} else [event]})
            records.append(record)
    suite = {"schema_version": "patient-eval/v0.1", "scope": "development_only", "scenarios": scenarios}
    suite_raw = (json.dumps(suite, ensure_ascii=False, indent=2) + "\n").encode()
    sha = digest_bytes(suite_raw)
    for record in records:
        record["metadata"]["suite_sha256"] = sha
    plan = {"schema_version": VERSION, "source": "synthetic", "fixture_only": True,
            "clinical_approval": False, "suite_sha256": sha, "rules": rules, "session_events": logs}
    return suite, records, plan


def mock_review_sessions(sessions, mapping):
    """Explicit fixture-only reviews, added separately from the mapper."""
    result = deepcopy(sessions)
    by_id = {s["session_id"]: s for s in result}
    for row in mapping["candidates"]:
        session = by_id[row["session_id"]]
        require(session["metadata"].get("fixture_only") is True
                and session["platform"] == "LOCAL-AUTHORED-FIXTURE-NO-MODEL",
                "mock reviews require authored fixtures")
        require(row["transcript_sha256"] == transcript_digest(session), "stale review transcript")
        if row["candidate_status"] != "ready_for_review":
            continue
        rating = 0 if row["event_kind"] == "unknown" else 2
        session["observations"].append({"criterion_id": row["criterion_id"],
            "review_version": REVIEW_VERSION, "source": "human",
            "reviewer_id": "SYNTHETIC-AUTHOR-NOT-A-HUMAN-REVIEW", "rubric_version": "r10-fixture-draft/v1",
            "fixture_only": True, "independent_review": False,
            "outcome": "pass" if rating == 2 else "fail", "ordinal_rating": rating,
            "quality_status": "assessed", "serious_error": None,
            "reason": "Authored mock review for integration only; no human reviewed this session.",
            "evidence_turn_ids": row["evidence_turn_ids"],
            "opportunity": {"status": "occurred", "trigger_turn_id": row["trigger_turn_id"],
                "response_turn_id": row["response_turn_id"], "deadline_reached": True,
                "noncompletion_reason": None, "reason": "Synthetic author accepts candidate boundary for this fixture."}})
        validate_session(session)
    return result


def run_drill(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    suite, records, plan = fixtures()
    for name, value in (("suite.json", suite), ("records.json", records), ("plan.json", plan)):
        write_new_json(out / name, value)
    import_summary = import_file(out / "records.json", out / "suite.json", out / "imported.json")
    sessions = json.loads((out / "imported.json").read_bytes())
    mapping = map_candidates(sessions, suite, digest_bytes((out / "suite.json").read_bytes()), plan)
    before = evaluate_sessions(suite, sessions)
    reviewed = mock_review_sessions(sessions, mapping)
    after = evaluate_sessions(suite, reviewed)
    failures = [{"session_id": score["session_id"], "criterion_id": r["criterion_id"],
                 "evidence_turn_ids": r["evidence_turn_ids"], "reason": r["reason"],
                 "attribution": "visible_behavior_only; internal cause unverified"}
                for score in after["scores"] for r in score["criterion_results"] if r["outcome"] == "fail"]
    before_rows = [r for s in before["scores"] for r in s["criterion_results"]]
    after_rows = [r for s in after["scores"] for r in s["criterion_results"]]
    statuses = mapping["summary"]["statuses"]
    planned = mapping["summary"]["planned_items"]
    invalid = statuses.get("measurement_invalid", 0)
    ready = statuses.get("ready_for_review", 0)
    rated = sum(r.get("quality_status") == "assessed" for r in after_rows)
    checks = {
        "seven_sessions_imported": import_summary["sessions"] == 7,
        "no_observations_created_by_import_or_mapper": all(not s["observations"] for s in sessions),
        "all_seven_unassessed_before_mock_review": sum(r["outcome"] == "unassessed" for r in before_rows) == 7,
        "candidate_partition": statuses == {"ready_for_review": 3, "event_not_reached": 1,
            "response_missing": 1, "event_log_unknown": 1, "measurement_invalid": 1},
        "three_mock_ratings_only": sum(r.get("quality_status") == "assessed" for r in after_rows) == 3,
        "four_unassessed_retained": sum(r["outcome"] == "unassessed" for r in after_rows) == 4,
        "one_evidence_linked_failure": len(failures) == 1 and failures[0]["evidence_turn_ids"] == ["u2", "a2"],
        "no_safety_judgment_inferred": all(r.get("serious_error") is None for r in after_rows),
    }
    report = {"scope": "synthetic_integration_only", "clinical_approval": False,
              "real_sessions": 0, "model_calls": 0, "independent_reviewers": 0,
              "import": import_summary, "mapping": mapping["summary"],
              "denominators": {"planned": planned, "measurement_invalid": invalid, "valid_planned": planned - invalid,
                  "ready_candidate_answers": ready, "mock_rated": rated,
                  "mock_rated_over_valid_planned": f"{rated}/{planned - invalid}",
                  "mock_rated_over_ready_candidates": f"{rated}/{ready}",
                  "note": "Candidate presence is not an independent opportunity judgment."},
              "checks": checks, "passed": sum(checks.values()), "total": len(checks),
              "failure_queue": failures,
              "limitations": ["Explicit event annotations, no automatic semantic extraction.",
                  "Mock human-format records are authored fixtures, not actual human review.",
                  "Real dynamic v0.4 admission and 57 rule mappings remain incomplete."]}
    for name, value in (("candidates.json", mapping), ("before-review.json", before),
                        ("mock-reviewed-sessions.json", reviewed), ("after-mock-review.json", after),
                        ("report.json", report)):
        write_new_json(out / name, value)
    require(all(checks.values()), "integration drill failed; evidence preserved at output")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        report = run_drill(args.out)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f"synthetic pipeline drill failed: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
