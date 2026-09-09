"""Audit private v0.4 drafts and execute synthetic state-machine fixtures only.

Source-derived cases are never executed by this module. Their private bundle is
recomputed from the bound review chain, then inspected structurally and reduced
to a text-free readiness audit. The small executor has a separate, explicit
synthetic-only gate so contract tests cannot be mistaken for model evaluation.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .candidate_review import LOCAL_ROOT, _read
from .dynamic_case_drafts import (
    FSM_CONTRACT_VERSION,
    _ADMISSION,
    _json,
    _sha,
    build_dynamic_case_drafts,
)


SCHEMA_VERSION = "dynamic-case-offline-readiness/v0.1"
SYNTHETIC_EXECUTION_MODE = "SYNTHETIC_CONTRACT_TEST_ONLY"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _new_public(path):
    path = Path(path)
    _require(not path.resolve().is_relative_to(LOCAL_ROOT.resolve()),
             "public readiness audit must not be written into the private local directory")
    _require(not path.exists(), "public output must be new; refusing overwrite")
    return path


def _synthetic_case(case_id="SYNTHETIC-A"):
    return {
        "case_id": case_id,
        "scope": "synthetic_fixture",
        "source": "synthetic",
        "development_exposed": False,
        "clinical_runnable": "SYNTHETIC_ONLY",
        "execution_mode": SYNTHETIC_EXECUTION_MODE,
        "facts": [
            {"fact_id": "F-INITIAL", "disclosure_policy": "initial"},
            {"fact_id": "F-QUESTION", "disclosure_policy": "on_question"},
            {"fact_id": "F-SCHEDULED", "disclosure_policy": "scheduled"},
            {"fact_id": "F-NEVER", "disclosure_policy": "never"},
        ],
        "opening": {
            "slot_ids": ["F-INITIAL"],
            "evidence_fragments": [{"text": "合成初始信息"}],
        },
        "disclosure_events": [{
            "event_id": "E-QUESTION",
            "slot_id": "F-QUESTION",
            "response": {"evidence_fragments": [{"text": "合成问询信息"}]},
            "one_shot": True,
        }, {
            "event_id": "E-SCHEDULED",
            "slot_id": "F-SCHEDULED",
            "response": {"evidence_fragments": [{"text": "合成定时信息"}]},
            "one_shot": True,
        }],
        "permanently_hidden_fact_ids": ["F-NEVER"],
        "finite_state_machine": {
            "contract_version": FSM_CONTRACT_VERSION,
            "initial_state": "NOT_OPENED",
            "terminal_states": ["CLOSED"],
            "states": ["NOT_OPENED", "ACTIVE", "CLOSED"],
            "automatic_natural_language_matching": False,
        },
        "scoring_drafts": [{
            "criterion_id": "SYN-C1",
            "decision": "drafted",
            "critical": False,
            "structured_opportunity": {"mapping_status": "UNRESOLVED"},
            "execution_state": "BLOCKED",
        }],
    }


class SyntheticContractExecutor:
    """Minimal state executor that categorically rejects source-derived cases."""

    def __init__(self, case):
        _require(isinstance(case, dict), "case must be an object")
        _require(case.get("scope") == "synthetic_fixture"
                 and case.get("source") == "synthetic"
                 and case.get("execution_mode") == SYNTHETIC_EXECUTION_MODE
                 and case.get("clinical_runnable") == "SYNTHETIC_ONLY",
                 "offline executor accepts explicit synthetic fixtures only")
        fsm = case.get("finite_state_machine", {})
        _require(fsm.get("contract_version") == FSM_CONTRACT_VERSION,
                 "unsupported synthetic state-machine contract")
        _require(fsm.get("automatic_natural_language_matching") is False,
                 "synthetic contract cannot enable automatic language matching")
        self._case = deepcopy(case)
        self._facts = {row["fact_id"]: row for row in case["facts"]}
        _require(len(self._facts) == len(case["facts"]), "duplicate synthetic fact ID")
        self._events = {row["event_id"]: row for row in case["disclosure_events"]}
        _require(len(self._events) == len(case["disclosure_events"]), "duplicate synthetic event ID")
        self._state = "NOT_OPENED"
        self._disclosed = set()
        self._fired = set()
        self._trace = []

    def open(self):
        _require(self._state == "NOT_OPENED", "opening can occur exactly once")
        slots = self._case["opening"]["slot_ids"]
        _require(slots and all(self._facts[row]["disclosure_policy"] == "initial" for row in slots),
                 "opening attempted future disclosure")
        _require(not (set(slots) & set(self._case["permanently_hidden_fact_ids"])),
                 "opening attempted never-disclose fact")
        self._state = "ACTIVE"
        self._disclosed.update(slots)
        self._trace.append({"event": "OPERATOR_OPEN", "disclosed": list(slots)})
        return {"state": self._state, "disclosed": list(slots),
                "fragments": deepcopy(self._case["opening"]["evidence_fragments"])}

    def confirm(self, event_id):
        _require(self._state == "ACTIVE", "dynamic disclosure requires ACTIVE state")
        _require(event_id in self._events, "unknown disclosure event")
        _require(event_id not in self._fired, "disclosure event already fired")
        event = self._events[event_id]
        _require(event.get("one_shot") is True, "dynamic disclosure must be one-shot")
        slot = event["slot_id"]
        _require(slot in self._facts and self._facts[slot]["disclosure_policy"] in {"on_question", "scheduled"},
                 "event references a non-dynamic fact")
        _require(slot not in self._disclosed, "fact already disclosed")
        _require(slot not in self._case["permanently_hidden_fact_ids"],
                 "event attempted never-disclose fact")
        self._fired.add(event_id)
        self._disclosed.add(slot)
        self._trace.append({"event": "OPERATOR_CONFIRM:" + event_id, "disclosed": [slot]})
        return {"state": self._state, "disclosed": [slot],
                "fragments": deepcopy(event["response"]["evidence_fragments"])}

    def stop(self):
        _require(self._state == "ACTIVE", "stop requires ACTIVE state")
        self._state = "CLOSED"
        self._trace.append({"event": "OPERATOR_STOP", "disclosed": []})
        return self.snapshot()

    def snapshot(self):
        return {
            "case_id": self._case["case_id"],
            "state": self._state,
            "disclosed_fact_ids": sorted(self._disclosed),
            "fired_event_ids": sorted(self._fired),
            "unreached_event_ids": sorted(set(self._events) - self._fired),
            "trace": deepcopy(self._trace),
        }


def _scoring_status(case):
    drafted = [row for row in case["scoring_drafts"] if row["decision"] == "drafted"]
    mapped = [row for row in drafted
              if row["structured_opportunity"]["mapping_status"] == "MAPPED"]
    critical = [row for row in drafted if row["critical"]]
    return {
        "drafted_rubric_count": len(drafted),
        "mapped_opportunity_count": len(mapped),
        "unmapped_opportunity_count": len(drafted) - len(mapped),
        "runtime_opportunity_not_reached_count": 0,
        "runtime_opportunity_not_evaluated_count": len(drafted),
        "quality_assessed_count": 0,
        "task_completion_assessed_count": 0,
        "critical_safety_rubric_count": len(critical),
        "critical_safety_assessed_count": 0,
        "quality_status": "UNASSESSED",
        "task_completion_status": "UNASSESSED",
        "safety_status": "UNASSESSED",
        "measurement_status": "NOT_RUN",
    }


def _audit_case(case):
    _require(case["admission"] == _ADMISSION, "case unexpectedly grants admission")
    _require(case["scope"] == "development_only" and case["development_exposed"] is True,
             "source-derived case scope changed")
    _require(case["clinical_runnable"] == "BLOCKED",
             "source-derived case unexpectedly runnable")
    fsm = case["finite_state_machine"]
    _require(fsm["contract_version"] == FSM_CONTRACT_VERSION,
             "source-derived case state-machine contract changed")
    _require(fsm["automatic_natural_language_matching"] is False,
             "source-derived case enabled automatic language matching")
    facts = {row["fact_id"]: row for row in case["facts"]}
    _require(len(facts) == len(case["facts"]), "duplicate source-derived fact ID")
    opening = case["opening"]["slot_ids"]
    future_in_opening = [row for row in opening if facts[row]["disclosure_policy"] != "initial"]
    event_slots = [row["slot_id"] for row in case["disclosure_events"]]
    never_visible = set(event_slots) & set(case["permanently_hidden_fact_ids"])
    duplicate_event_slots = len(event_slots) - len(set(event_slots))
    _require(not future_in_opening, "future fact entered source-derived opening")
    _require(not never_visible, "never-disclose fact entered a source-derived event")
    _require(duplicate_event_slots == 0, "source-derived fact has duplicate disclosure events")
    _require(all(row["trigger"]["mode"] == "OPERATOR_CONFIRMATION_REQUIRED"
                 and row["one_shot"] is True for row in case["disclosure_events"]),
             "source-derived dynamic event is automatic or repeatable")
    scoring = _scoring_status(case)
    blockers = sorted(set(case["execution_blockers"] + [
        "SOURCE_DERIVED_EXECUTION_PROHIBITED",
        "BLIND_REVIEW_PACKAGE_BLOCKED_NO_RUNNABLE_SESSION",
    ]))
    return {
        "case_id": case["case_id"],
        "candidate_id": case["candidate_id"],
        "development_exposed": True,
        "static_contract_status": "PASS",
        "opening_future_fact_findings": 0,
        "duplicate_disclosure_transition_findings": 0,
        "never_fact_visible_transition_findings": 0,
        "automatic_natural_language_matching": False,
        "dynamic_event_count": len(event_slots),
        "source_derived_execution_attempted": False,
        "offline_session_status": "NOT_RUN_BLOCKED",
        "blind_review_package_status": "NOT_GENERATED",
        "scoring": scoring,
        "blockers": blockers,
        "clinical_runnable": "BLOCKED",
    }


def run_synthetic_contract_probe():
    checks = []

    def record(name, passed):
        _require(passed, "synthetic contract probe failed: " + name)
        checks.append({"check": name, "result": "PASS"})

    a = SyntheticContractExecutor(_synthetic_case("SYNTHETIC-A"))
    try:
        a.confirm("E-QUESTION")
        early_rejected = False
    except ValueError:
        early_rejected = True
    record("dynamic_before_open_rejected", early_rejected)
    opened = a.open()
    record("opening_discloses_initial_only", opened["disclosed"] == ["F-INITIAL"])
    a.confirm("E-QUESTION")
    try:
        a.confirm("E-QUESTION")
        duplicate_rejected = False
    except ValueError:
        duplicate_rejected = True
    record("duplicate_disclosure_rejected", duplicate_rejected)
    final_a = a.stop()
    record("unreached_event_preserved", final_a["unreached_event_ids"] == ["E-SCHEDULED"])
    record("never_fact_not_disclosed", "F-NEVER" not in final_a["disclosed_fact_ids"])

    b = SyntheticContractExecutor(_synthetic_case("SYNTHETIC-B"))
    b.open()
    record("cross_case_state_isolated", b.snapshot()["fired_event_ids"] == [])

    try:
        SyntheticContractExecutor({
            **_synthetic_case("SYNTHETIC-TAMPERED"),
            "scope": "development_only",
            "clinical_runnable": "BLOCKED",
        })
        source_rejected = False
    except ValueError:
        source_rejected = True
    record("source_derived_execution_rejected", source_rejected)
    record("partial_scoring_remains_unassessed",
           _scoring_status(_synthetic_case())["quality_status"] == "UNASSESSED")
    return {
        "scope": "synthetic_contract_only",
        "passed_count": len(checks),
        "total_count": len(checks),
        "checks": checks,
        "model_or_platform_calls": 0,
    }


def build_offline_readiness(original, review, blocker_queue, selection,
                            private_bundle, n4_public_audit,
                            source_review_sha256, review_file_sha256):
    """Return a text-free readiness audit without executing source-derived cases."""
    expected_private, expected_public = build_dynamic_case_drafts(
        original, review, blocker_queue, selection,
        source_review_sha256, review_file_sha256)
    _require(private_bundle == expected_private,
             "private draft bundle does not match exact N4 recomputation")
    _require(n4_public_audit == expected_public,
             "N4 public audit does not match exact recomputation")
    _require(private_bundle["admission"] == _ADMISSION
             and n4_public_audit["admission"] == _ADMISSION,
             "N4 artifact unexpectedly grants admission")
    rows = [_audit_case(case) for case in private_bundle["cases"]]
    probe = run_synthetic_contract_probe()
    drafted = sum(row["scoring"]["drafted_rubric_count"] for row in rows)
    mapped = sum(row["scoring"]["mapped_opportunity_count"] for row in rows)
    critical = sum(row["scoring"]["critical_safety_rubric_count"] for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "development_only",
        "development_exposed": True,
        "source_review_sha256": source_review_sha256,
        "canonical_review_sha256": review_file_sha256,
        "private_bundle_sha256": _sha(private_bundle),
        "n4_public_audit_sha256": _sha(n4_public_audit),
        "fsm_contract_version": FSM_CONTRACT_VERSION,
        "validation": {
            "n4_private_exact_recomputation": "PASS",
            "n4_public_exact_recomputation": "PASS",
            "source_derived_static_contract_count": len(rows),
            "source_derived_static_contract_pass_count": len(rows),
            "synthetic_contract_probe": f"{probe['passed_count']}/{probe['total_count']} PASS",
            "model_answers_read": False,
            "model_or_platform_calls": 0,
        },
        "summary": {
            "source_derived_case_count": len(rows),
            "source_derived_execution_attempt_count": 0,
            "offline_session_count": 0,
            "blind_review_package_count": 0,
            "static_opening_future_fact_findings": 0,
            "static_duplicate_disclosure_findings": 0,
            "static_never_fact_visible_findings": 0,
            "drafted_rubric_count": drafted,
            "mapped_scoring_opportunity_count": mapped,
            "unmapped_scoring_opportunity_count": drafted - mapped,
            "runtime_opportunity_not_reached_count": 0,
            "runtime_opportunity_not_evaluated_count": drafted,
            "quality_assessed_case_count": 0,
            "task_completion_assessed_case_count": 0,
            "critical_safety_rubric_count": critical,
            "critical_safety_assessed_count": 0,
            "measurement_not_run_case_count": len(rows),
            "clinical_runnable_count": 0,
        },
        "synthetic_contract_probe": probe,
        "cases": rows,
        "admission": deepcopy(_ADMISSION),
        "privacy": {
            "contains_patient_text": False,
            "contains_evidence_spans": False,
            "contains_review_or_scoring_text": False,
            "contains_reviewer_identity": False,
            "contains_source_dialogue_id": False,
            "contains_local_or_library_path": False,
        },
        "limitations": [
            "No source-derived case was executed because every case remains clinically blocked.",
            "Static zero findings are contract checks, not observed model behavior or clinical safety results.",
            "Synthetic probe passes validate executor bookkeeping only and are not model scores.",
            "Unmapped opportunities and unassessed safety remain explicit in their denominators.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--source-review", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--blockers", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--private-drafts", type=Path, required=True)
    parser.add_argument("--n4-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        out = _new_public(args.out)
        source_digest = hashlib.sha256(args.source_review.read_bytes()).hexdigest()
        _require(source_digest == args.expected_source_sha256,
                 "source review SHA-256 mismatch")
        review_bytes = args.review.read_bytes()
        result = build_offline_readiness(
            _read(args.original), json.loads(review_bytes), _read(args.blockers),
            _read(args.selection), _read(args.private_drafts), _read(args.n4_audit),
            source_digest, hashlib.sha256(review_bytes).hexdigest())
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_json(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"offline readiness generation failed: {exc}\n")
    print(_json({
        "completed": True,
        "source_derived_execution_attempt_count": 0,
        "offline_session_count": 0,
        "clinical_runnable_count": 0,
        "gold_approved": False,
        "clinical_gold": False,
        "s6_automatic_trust": "BLOCKED",
    }))


if __name__ == "__main__":
    main()
