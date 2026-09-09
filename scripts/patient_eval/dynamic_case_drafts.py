"""Build fail-closed, source-derived dynamic case authoring drafts.

The private bundle retains exact patient evidence fragments and review text only
under ``medical/patient-eval/local``.  The public artifact is a counts-only
projection.  Neither artifact grants clinical admission, and the generated
state machines require explicit operator confirmation rather than pretending
that draft natural-language triggers are validated executable rules.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .candidate_blockers import build_public_blocker_queue
from .candidate_review import LOCAL_ROOT, _read, validate_review
from .candidate_selection import build_development_selection


SCHEMA_VERSION = "dynamic-case-draft/v0.4"
AUDIT_VERSION = "dynamic-case-draft-audit/v0.1"
FSM_CONTRACT_VERSION = "dynamic-case-state-machine/v0.4"
_ADMISSION = {
    "gold_approved": False,
    "formal_approval": False,
    "clinical_gold": False,
    "dynamic_scenario_ready": False,
    "s6_automatic_trust": "BLOCKED",
}
_CASE_BLOCKERS = (
    "CLINICAL_RUBRIC_ADJUDICATION_REQUIRED",
    "INDEPENDENT_DUAL_REVIEW_REQUIRED",
    "NATURAL_LANGUAGE_RENDERING_REVIEW_REQUIRED",
    "SCORING_OPPORTUNITY_MAPPING_REQUIRED",
    "STOP_POLICY_AUTHORING_REQUIRED",
    "TRIGGER_SEMANTIC_REVIEW_REQUIRED",
)
_ID = re.compile(r"^C[0-9]{4}$")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _sha(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _new_local(path):
    path = Path(path)
    _require(path.resolve().is_relative_to(LOCAL_ROOT.resolve()),
             "private output must be under ignored medical/patient-eval/local/")
    _require(not path.exists(), "private output must be new; refusing overwrite")
    return path


def _new_public(path):
    path = Path(path)
    _require(not path.resolve().is_relative_to(LOCAL_ROOT.resolve()),
             "public audit must not be written into the private local directory")
    _require(not path.exists(), "public output must be new; refusing overwrite")
    return path


def _fact_fragments(fact):
    return [{
        "turn_id": span["turn_id"],
        "start": span["start"],
        "end": span["end"],
        "text": span["text"],
    } for span in fact["evidence_spans"]]


def _private_fact(fact, turns):
    source_turns = sorted({turns[span["turn_id"]]["source_turn_index"]
                           for span in fact["evidence_spans"]})
    return {
        "fact_id": fact["fact_id"],
        "slot_id": fact["fact_id"],
        "manual_groundsignal_slot": fact["manual_groundsignal_slot"],
        "polarity": fact["polarity"],
        "subject": fact["subject"],
        "time": fact["time"],
        "disclosure_policy": fact["disclosure_policy"],
        "correction_of_fact_id": fact["correction_of_candidate_id"],
        "source_turn_indices": source_turns,
        "evidence_fragments": _fact_fragments(fact),
        "review_status": "AI_ASSISTED_DRAFT_UNADJUDICATED",
    }


def _event(fact, rank):
    policy = fact["disclosure_policy"]
    if policy == "on_question":
        trigger_draft = deepcopy(fact["ask_patterns"])
        trigger_kind = "QUESTION_EXAMPLES"
    else:
        trigger_draft = [fact["disclosure_condition"]]
        trigger_kind = "SCHEDULE_CONDITION"
    return {
        "event_id": f"E{rank:03d}-{fact['fact_id']}",
        "slot_id": fact["fact_id"],
        "disclosure_policy": policy,
        "trigger": {
            "mode": "OPERATOR_CONFIRMATION_REQUIRED",
            "kind": trigger_kind,
            "authoring_draft": trigger_draft,
            "semantic_status": "UNADJUDICATED_NOT_EXECUTABLE",
        },
        "response": {
            "evidence_fragments": _fact_fragments(fact),
            "rendering_status": "AUTHORING_REVIEW_REQUIRED",
        },
        "one_shot": True,
    }


def _private_rubric(rubric):
    result = {
        "criterion_id": rubric["criterion_id"],
        "capability": rubric["capability"],
        "kind": rubric["kind"],
        "critical": rubric["critical"],
        "required": rubric["required"],
        "decision": rubric["decision"],
        "applicability": rubric["applicability"],
        "review_status": "AI_ASSISTED_DRAFT_UNADJUDICATED",
        "execution_state": "BLOCKED",
        "structured_opportunity": {
            "trigger_turn": None,
            "response_turn": None,
            "deadline": None,
            "mapping_status": "UNRESOLVED",
        },
    }
    if rubric["decision"] == "drafted":
        result.update({
            "description": rubric["description"],
            "anchors": deepcopy(rubric["anchors"]),
            "opportunity_authoring_draft": deepcopy(rubric["opportunity"]),
            "serious_error_definition": rubric["serious_error_definition"],
        })
    return result


def _build_case(item):
    candidate_id = item["candidate_id"]
    _require(_ID.fullmatch(candidate_id), "invalid candidate ID in frozen selection")
    turns = {turn["turn_id"]: turn for turn in item["turns"]}
    included = [fact for fact in item["review"]["facts"] if fact["decision"] == "include"]
    initial = [fact for fact in included if fact["disclosure_policy"] == "initial"]
    dynamic = [fact for fact in included if fact["disclosure_policy"] in {"on_question", "scheduled"}]
    never = [fact for fact in included if fact["disclosure_policy"] == "never"]
    drafted_rubrics = [row for row in item["review"]["rubrics"] if row["decision"] == "drafted"]
    _require(initial, "selected case has no included initial facts")
    _require(dynamic, "selected case has no included dynamic facts")
    _require(drafted_rubrics, "selected case has no drafted scoring rubric")

    events = [_event(fact, rank) for rank, fact in enumerate(dynamic, 1)]
    transitions = [{
        "transition_id": "T-OPEN",
        "from": "NOT_OPENED",
        "to": "ACTIVE",
        "event": "OPERATOR_OPEN",
        "guard": "ALWAYS",
        "effect": {"disclose_slots": [fact["fact_id"] for fact in initial],
                   "output_ref": "OPENING-EVIDENCE-FRAGMENTS"},
    }]
    transitions.extend({
        "transition_id": f"T-{event['event_id']}",
        "from": "ACTIVE",
        "to": "ACTIVE",
        "event": f"OPERATOR_CONFIRM:{event['event_id']}",
        "guard": "EVENT_NOT_PREVIOUSLY_DISCLOSED",
        "effect": {"disclose_slots": [event["slot_id"]],
                   "output_ref": event["event_id"]},
    } for event in events)
    transitions.append({
        "transition_id": "T-STOP",
        "from": "ACTIVE",
        "to": "CLOSED",
        "event": "OPERATOR_STOP",
        "guard": "ALWAYS",
        "effect": {"disclose_slots": [], "output_ref": None},
    })
    return {
        "case_id": f"DEV04-{candidate_id}",
        "candidate_id": candidate_id,
        "scope": "development_only",
        "development_exposed": True,
        "clinical_runnable": "BLOCKED",
        "execution_mode": "AUTHORING_DRAFT_OPERATOR_CONFIRMATION_ONLY",
        "facts": [_private_fact(fact, turns) for fact in included],
        "opening": {
            "slot_ids": [fact["fact_id"] for fact in initial],
            "evidence_fragments": [fragment for fact in initial for fragment in _fact_fragments(fact)],
            "rendering_status": "AUTHORING_REVIEW_REQUIRED",
        },
        "disclosure_events": events,
        "permanently_hidden_fact_ids": [fact["fact_id"] for fact in never],
        "finite_state_machine": {
            "contract_version": FSM_CONTRACT_VERSION,
            "initial_state": "NOT_OPENED",
            "terminal_states": ["CLOSED"],
            "states": ["NOT_OPENED", "ACTIVE", "CLOSED"],
            "transitions": transitions,
            "automatic_natural_language_matching": False,
        },
        "stop_conditions": [{
            "condition": "EXPLICIT_OPERATOR_STOP",
            "status": "DEFINED",
        }, {
            "condition": "TURN_BUDGET",
            "status": "AUTHORING_REQUIRED",
        }],
        "scoring_drafts": [_private_rubric(row) for row in item["review"]["rubrics"]],
        "task_completion": {
            "judgement": None,
            "status": "UNRESOLVED_REQUIRES_ADJUDICATED_RUBRIC_AND_OPPORTUNITY_MAPPING",
        },
        "execution_blockers": list(_CASE_BLOCKERS),
        "admission": deepcopy(_ADMISSION),
    }


def _validate_private_case(case):
    _require(case["admission"] == _ADMISSION, "case unexpectedly grants admission")
    _require(case["clinical_runnable"] == "BLOCKED", "case unexpectedly runnable")
    facts = {fact["fact_id"]: fact for fact in case["facts"]}
    _require(len(facts) == len(case["facts"]), "duplicate private fact ID")
    opening = set(case["opening"]["slot_ids"])
    _require(opening and all(facts[fact_id]["disclosure_policy"] == "initial" for fact_id in opening),
             "opening contains a future or unknown fact")
    disclosed = set(opening)
    for event in case["disclosure_events"]:
        fact_id = event["slot_id"]
        _require(fact_id in facts and fact_id not in disclosed, "invalid or duplicate disclosure event")
        _require(event["disclosure_policy"] == facts[fact_id]["disclosure_policy"]
                 and event["disclosure_policy"] in {"on_question", "scheduled"},
                 "event disclosure policy mismatch")
        _require(event["trigger"]["mode"] == "OPERATOR_CONFIRMATION_REQUIRED",
                 "unreviewed trigger cannot be automatic")
        disclosed.add(fact_id)
    _require(not (set(case["permanently_hidden_fact_ids"]) & disclosed),
             "never-disclose fact entered a visible transition")
    _require(case["finite_state_machine"]["automatic_natural_language_matching"] is False,
             "draft state machine cannot enable automatic language matching")
    _require(all(row["execution_state"] == "BLOCKED" for row in case["scoring_drafts"]),
             "unadjudicated scoring draft cannot be executable")


def _public_case_row(case):
    facts = case["facts"]
    policy_counts = Counter(row["disclosure_policy"] for row in facts)
    polarity_counts = Counter(row["polarity"] for row in facts)
    drafted = [row for row in case["scoring_drafts"] if row["decision"] == "drafted"]
    return {
        "case_id": case["case_id"],
        "candidate_id": case["candidate_id"],
        "development_exposed": True,
        "clinical_runnable": "BLOCKED",
        "included_fact_count": len(facts),
        "disclosure_policy_counts": dict(sorted(policy_counts.items())),
        "polarity_counts": dict(sorted(polarity_counts.items())),
        "correction_relation_count": sum(row["correction_of_fact_id"] is not None for row in facts),
        "fsm_transition_count": len(case["finite_state_machine"]["transitions"]),
        "drafted_rubric_count": len(drafted),
        "critical_drafted_rubric_count": sum(row["critical"] for row in drafted),
        "structured_scoring_opportunity_count": 0,
        "blockers": list(_CASE_BLOCKERS),
    }


def build_dynamic_case_drafts(original, review, blocker_queue, selection,
                              source_review_sha256, review_file_sha256):
    """Return a private authoring bundle and its text-free public audit."""
    validation = validate_review(original, review)
    expected_blockers = build_public_blocker_queue(
        original, review, source_review_sha256, review_file_sha256)
    _require(blocker_queue == expected_blockers,
             "blocker queue does not match validated private review")
    requested = selection.get("selection_config", {}).get("requested_count")
    expected_selection = build_development_selection(
        original, review, expected_blockers, source_review_sha256,
        review_file_sha256, requested_count=requested)
    _require(selection == expected_selection,
             "selection does not match deterministic recomputation")
    _require(selection["admission"] == {**_ADMISSION, "clinical_runnable_count": 0},
             "selection unexpectedly grants admission")

    item_by_id = {item["candidate_id"]: item for item in review["items"]}
    selected_ids = [row["candidate_id"] for row in selection["selected_candidates"]]
    cases = [_build_case(item_by_id[candidate_id]) for candidate_id in selected_ids]
    for case in cases:
        _validate_private_case(case)
    private_bundle = {
        "schema_version": SCHEMA_VERSION,
        "local_only": True,
        "scope": "development_only",
        "development_exposed": True,
        "source_review_sha256": source_review_sha256,
        "canonical_review_sha256": review_file_sha256,
        "packet_sha256": original["packet_sha256"],
        "selection_sha256": _sha(selection),
        "review_contract": {
            "status": "PASS",
            "candidate_count": validation["counts"]["candidates"],
            "interpretation": "Structural validity is not clinical correctness or reviewer credential proof.",
        },
        "cases": cases,
        "admission": deepcopy(_ADMISSION),
    }

    rows = [_public_case_row(case) for case in cases]
    policy_totals = Counter()
    polarity_totals = Counter()
    blocker_totals = Counter()
    for row in rows:
        policy_totals.update(row["disclosure_policy_counts"])
        polarity_totals.update(row["polarity_counts"])
        blocker_totals.update(row["blockers"])
    public_audit = {
        "schema_version": AUDIT_VERSION,
        "fsm_contract_version": FSM_CONTRACT_VERSION,
        "scope": "development_only",
        "development_exposed": True,
        "source_review_sha256": source_review_sha256,
        "canonical_review_sha256": review_file_sha256,
        "packet_sha256": original["packet_sha256"],
        "selection_sha256": _sha(selection),
        "private_bundle_sha256": _sha(private_bundle),
        "validation": {
            "official_review_contract": "PASS",
            "blocker_queue_exact_recomputation": "PASS",
            "selection_exact_recomputation": "PASS",
            "private_case_contract": f"{len(cases)}/{len(cases)} PASS",
            "automatic_natural_language_matching_enabled_count": 0,
            "model_answers_read": False,
        },
        "summary": {
            "selected_candidate_count": len(selected_ids),
            "private_case_draft_count": len(cases),
            "included_fact_count": sum(row["included_fact_count"] for row in rows),
            "disclosure_policy_counts": dict(sorted(policy_totals.items())),
            "polarity_counts": dict(sorted(polarity_totals.items())),
            "correction_relation_count": sum(row["correction_relation_count"] for row in rows),
            "fsm_transition_count": sum(row["fsm_transition_count"] for row in rows),
            "drafted_rubric_count": sum(row["drafted_rubric_count"] for row in rows),
            "critical_drafted_rubric_count": sum(row["critical_drafted_rubric_count"] for row in rows),
            "structured_scoring_opportunity_count": 0,
            "case_blocker_counts": dict(sorted(blocker_totals.items())),
            "clinical_runnable_count": 0,
        },
        "cases": rows,
        "admission": deepcopy(_ADMISSION),
        "privacy": {
            "contains_patient_text": False,
            "contains_evidence_spans": False,
            "contains_review_reason": False,
            "contains_reviewer_identity": False,
            "contains_source_dialogue_id": False,
            "contains_local_or_library_path": False,
        },
        "limitations": [
            "Evidence fragments and authoring text exist only in the ignored private bundle.",
            "Operator-confirmed transitions are authoring scaffolds, not validated language understanding.",
            "Structured trigger turns, response turns and deadlines remain unresolved rather than guessed.",
            "All source-derived cases are exposed development material and are not clinically runnable.",
        ],
    }
    return private_bundle, public_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--source-review", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--blockers", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--public-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        private_out = _new_local(args.private_out)
        public_out = _new_public(args.public_out)
        source_digest = hashlib.sha256(args.source_review.read_bytes()).hexdigest()
        _require(source_digest == args.expected_source_sha256,
                 "source review SHA-256 mismatch")
        review_bytes = args.review.read_bytes()
        private_bundle, public_audit = build_dynamic_case_drafts(
            _read(args.original), json.loads(review_bytes), _read(args.blockers),
            _read(args.selection), source_digest,
            hashlib.sha256(review_bytes).hexdigest())
        private_out.parent.mkdir(parents=True, exist_ok=True)
        private_out.write_text(_json(private_bundle), encoding="utf-8")
        public_out.parent.mkdir(parents=True, exist_ok=True)
        public_out.write_text(_json(public_audit), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"dynamic case draft generation failed: {exc}\n")
    print(_json({
        "completed": True,
        "private_case_draft_count": len(private_bundle["cases"]),
        "clinical_runnable_count": 0,
        "gold_approved": False,
        "clinical_gold": False,
        "s6_automatic_trust": "BLOCKED",
    }))


if __name__ == "__main__":
    main()
