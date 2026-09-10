"""Candidate answer boundaries from explicit synthetic event annotations.

No language matching, clinical admission, or automatic review. A complete event
log is an operator declaration, not proof that every semantic event was found.
Source-derived v0.4 cases remain outside this prototype's accepted contract.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .contracts import nonempty, require
from .import_batch import digest_bytes, scenario_digest, validate_batch, write_new_json


VERSION = "synthetic-event-mapping/v0.1"
KINDS = {"correction", "unknown", "question_or_hypothesis"}


def transcript_digest(session):
    return scenario_digest({key: session.get(key) for key in (
        "session_id", "scenario_id", "family_id", "variant", "platform", "status",
        "turns", "invalid_component", "invalid_reason")})


def map_candidates(records, suite, suite_sha256, plan):
    """Return sidecar candidates; never add observations to imported sessions."""
    require(isinstance(plan, dict) and plan.get("schema_version") == VERSION,
            "unsupported mapping plan")
    require(plan.get("source") == "synthetic" and plan.get("fixture_only") is True
            and plan.get("clinical_approval") is False, "synthetic fixture plan required")
    require(isinstance(suite, dict), "suite must be an object")
    require(all(s.get("source") == "synthetic" for s in suite.get("scenarios", [])),
            "event mapping prototype accepts synthetic scenarios only")
    require(plan.get("suite_sha256") == suite_sha256, "mapping suite digest mismatch")
    sessions = validate_batch(records, suite, suite_sha256)
    scenarios = {s["scenario_id"]: s for s in suite["scenarios"]}
    rules = plan.get("rules")
    require(isinstance(rules, list) and bool(rules), "mapping rules required")
    indexed_rules = {}
    event_kinds = {}
    for rule in rules:
        require(isinstance(rule, dict), "rule must be an object")
        sid, cid = rule.get("scenario_id"), rule.get("criterion_id")
        require(nonempty(sid) and sid in scenarios, "unknown mapping scenario")
        require(nonempty(cid) and cid in {c["id"] for c in scenarios[sid]["criteria"]},
                "unknown mapping criterion")
        require((sid, cid) not in indexed_rules, "duplicate mapping criterion")
        require(rule.get("scenario_sha256") == scenario_digest(scenarios[sid]),
                "mapping scenario digest mismatch")
        event = rule.get("event_id")
        require(nonempty(event) and rule.get("event_kind") in KINDS, "invalid event definition")
        require(rule.get("response_policy") == "next_assistant", "unsupported response policy")
        key = (sid, event)
        require(key not in event_kinds or event_kinds[key] == rule["event_kind"],
                "conflicting event kind")
        event_kinds[key] = rule["event_kind"]
        indexed_rules[(sid, cid)] = rule
    logs = plan.get("session_events")
    require(isinstance(logs, list), "session event logs required")
    indexed_logs = {}
    for log in logs:
        require(isinstance(log, dict) and nonempty(log.get("session_id")), "invalid event log")
        require(log["session_id"] not in indexed_logs, "duplicate session event log")
        indexed_logs[log["session_id"]] = log
    require(set(indexed_logs) == {s["session_id"] for s in sessions},
            "event logs must bind exactly the imported sessions")
    rows = []
    for session in sessions:
        sid = session["scenario_id"]
        log = indexed_logs[session["session_id"]]
        require(log.get("transcript_sha256") == transcript_digest(session), "stale transcript binding")
        require(type(log.get("complete")) is bool, "event log completeness must be explicit")
        require(nonempty(log.get("annotation_source")), "event annotation source required")
        require(isinstance(log.get("events"), list), "events must be a list")
        turns = session["turns"]
        indexes = {t["turn_id"]: i for i, t in enumerate(turns)}
        events = {}
        for event in log["events"]:
            require(isinstance(event, dict), "event must be an object")
            eid, tid = event.get("event_id"), event.get("turn_id")
            require(nonempty(eid) and (sid, eid) in event_kinds, "unknown event ID")
            require(eid not in events, "duplicate event; split repeated probes into separate rules")
            require(event.get("event_kind") == event_kinds[(sid, eid)], "event kind mismatch")
            require(nonempty(tid) and tid in indexes, "event references missing turn")
            turn = turns[indexes[tid]]
            require(turn["role"] == "user", "event trigger must be a user turn")
            require(event.get("content_sha256") == digest_bytes(turn["content"].encode()),
                    "event content binding mismatch")
            events[eid] = event
        for criterion in scenarios[sid]["criteria"]:
            rule = indexed_rules.get((sid, criterion["id"]))
            row = {"session_id": session["session_id"], "scenario_id": sid,
                   "criterion_id": criterion["id"], "session_status": session["status"],
                   "event_id": rule["event_id"] if rule else None,
                   "event_kind": rule["event_kind"] if rule else None,
                   "candidate_status": "unmapped", "trigger_turn_id": None,
                   "response_turn_id": None, "evidence_turn_ids": [],
                   "review_status": "pending", "ordinal_rating": None,
                   "serious_error": None, "is_review": False,
                   "transcript_sha256": log["transcript_sha256"]}
            if session["status"] == "measurement_invalid":
                row["candidate_status"] = "measurement_invalid"
            elif rule:
                event = events.get(rule["event_id"])
                if event is None:
                    row["candidate_status"] = "event_not_reached" if log["complete"] else "event_log_unknown"
                else:
                    tid = event["turn_id"]
                    i = indexes[tid] + 1
                    response = turns[i]["turn_id"] if i < len(turns) else None
                    row.update(candidate_status="ready_for_review" if response else "response_missing",
                               trigger_turn_id=tid, response_turn_id=response,
                               evidence_turn_ids=[tid] + ([response] if response else []))
            rows.append(row)
    counts = Counter(r["candidate_status"] for r in rows)
    return {"schema_version": VERSION, "source": "synthetic", "fixture_only": True,
            "clinical_approval": False, "plan_sha256": scenario_digest(plan),
            "automatic_language_matching": False, "independent_reviewers": 0,
            "summary": {"planned_items": len(rows), "statuses": dict(sorted(counts.items())),
                        "scored_by_mapper": 0}, "candidates": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "suite", "plan", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        require(not Path(args.out).exists(), "refusing to overwrite mapping")
        suite_raw = Path(args.suite).read_bytes()
        result = map_candidates(json.loads(Path(args.input).read_bytes()), json.loads(suite_raw),
                                digest_bytes(suite_raw), json.loads(Path(args.plan).read_bytes()))
        write_new_json(args.out, result)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f"event mapping failed: {error}\n")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
