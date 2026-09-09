"""Separate observed behavior from causal claims about hidden implementations.

An injected fault is not proof that it harmed an answer. A verified development
claim needs observed failure, a real restoration, and a successful matched replay.
Black-box transcripts never establish internal algorithm or engineering causes.
"""

import hashlib
import json

from .scoring import score_session
from .contracts import validate_session


COMPONENT_CATEGORIES = {
    "fact_state.correction": "engineering",  # runner dropped a correct update call
    "context_transport": "engineering",
    "tool_transport": "engineering",
    "state_update_policy": "algorithm_policy",
    "retrieval_ranker": "algorithm_policy",
    "evidence_version_filter": "algorithm_policy",
    "evidence_store": "data_knowledge",
}

CANDIDATES = {
    "C1": [("algorithm_policy", "Clarification or ambiguity handling may be insufficient."),
           ("engineering", "The visible question or context may not have reached the model intact.")],
    "C2": [("algorithm_policy", "Question selection or stopping policy may be insufficient.")],
    "C3": [("algorithm_policy", "The policy for revising conflicting patient facts may be insufficient."),
           ("engineering", "A correction may have been lost in context transport or state persistence.")],
    "C4": [("algorithm_policy", "Risk handling or decision boundaries may be insufficient."),
           ("data_knowledge", "Applicable safety evidence may be missing or outdated.")],
    "C5": [("data_knowledge", "Evidence coverage or population applicability may be insufficient."),
           ("algorithm_policy", "Evidence retrieval, ranking or use may be insufficient."),
           ("engineering", "Evidence may have been omitted or mapped incorrectly in delivery.")],
    "C6": [("engineering", "Tool delivery, timeout handling or schema mapping may be insufficient."),
           ("algorithm_policy", "Tool selection or recovery policy may be insufficient.")],
    "C7": [("algorithm_policy", "Explanation or misunderstanding repair policy may be insufficient."),
           ("engineering", "Presentation or response truncation may have removed useful explanation.")],
    "C8": [("algorithm_policy", "The response policy may be unstable under conversational pressure."),
           ("engineering", "Context limits or service failures may affect task completion.")],
}


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _one_event(session, kind, **matches):
    found = [event for event in session.get("trace", [])
             if event.get("kind") == kind
             and all(event.get(key) == value for key, value in matches.items())]
    return found[0] if len(found) == 1 else None


def _criteria_from_score(score):
    return [{"id": item["criterion_id"], **{key: item[key] for key in
             ("module", "kind", "critical", "required", "check", "fact_key", "expected", "expected_status")
             if key in item}}
            for item in score["criterion_results"]]


def _verify_correction_component(session, controlled, fault, criterion):
    """Bind the known fixture's transition, rendered answer and mechanical check."""
    if criterion.get("kind") != "mechanical" or criterion.get("check") != "state_value":
        return "The implemented component checker requires a mechanical state_value criterion."
    update = fault.get("before")
    if not isinstance(update, dict) or update.get("key") != criterion.get("fact_key"):
        return "The injected update must target the criterion's fact key."
    turn_id = fault.get("turn_id")
    if not turn_id or turn_id != session["turns"][-2].get("turn_id"):
        return "The implemented checker requires a correction at the final visible user turn."
    baseline_transition = _one_event(session, "state_transition", turn_id=turn_id)
    controlled_transition = _one_event(controlled, "state_transition", turn_id=turn_id)
    baseline_output = _one_event(session, "fixture_output")
    controlled_output = _one_event(controlled, "fixture_output")
    if not all((baseline_transition, controlled_transition, baseline_output, controlled_output)):
        return "Actual state transitions and fixture output snapshots are required."
    if baseline_transition.get("delivered") is not False or controlled_transition.get("delivered") is not True:
        return "The correction must be dropped in baseline and delivered in control."
    original = baseline_transition.get("before")
    if not isinstance(original, dict) or not isinstance(original.get("facts"), dict):
        return "A concrete state snapshot is required before the correction."
    if original != baseline_transition.get("after") or original != controlled_transition.get("before"):
        return "A dropped correction must leave state unchanged, with identical control starting state."
    if baseline_transition["after"] != baseline_output.get("fact_snapshot") or controlled_transition.get("after") != controlled_output.get("fact_snapshot"):
        return "Final fixture facts must equal the observed correction transition output."
    before_facts = original["facts"]
    corrected_snapshot = controlled_output.get("fact_snapshot")
    if not isinstance(corrected_snapshot, dict) or not isinstance(corrected_snapshot.get("facts"), dict):
        return "The corrected output requires concrete facts."
    after_facts = corrected_snapshot["facts"]
    key = criterion["fact_key"]
    if {k: v for k, v in before_facts.items() if k != key} != {k: v for k, v in after_facts.items() if k != key}:
        return "A correction replay must not change unrelated facts."
    actual = after_facts.get(key)
    if not isinstance(actual, dict) or actual.get("value") != update.get("value") or actual.get("status") != update.get("status") or actual.get("turn_id") != turn_id:
        return "Delivered state must contain the actual correction value, status and provenance."
    if baseline_output.get("selected_evidence_ids") != controlled_output.get("selected_evidence_ids"):
        return "Retrieved evidence changed during the correction replay."
    from .runner import render_fixture_answer
    for run, output in ((session, baseline_output), (controlled, controlled_output)):
        selected = output.get("selected_evidence_ids")
        if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
            return "Fixture output must record selected evidence IDs."
        try:
            expected_response = render_fixture_answer(output["fact_snapshot"]["facts"], selected)
        except (ValueError, KeyError, TypeError):
            return "Malformed output fact snapshot."
        if run["turns"][-1]["content"] != expected_response:
            return "Observed final answer does not match the actual fixture output snapshot."
    if "expected" not in criterion:
        return "The state criterion must record its expected value."
    expected_status = criterion.get("expected_status", "confirmed")
    def passes(facts):
        value = facts.get(key, {})
        return value.get("value") == criterion["expected"] and value.get("status") == expected_status
    if passes(before_facts) or not passes(after_facts):
        return "Recomputed mechanical state outcomes do not demonstrate fail-to-pass."
    return None


def _check_control(session, score, control):
    """Return grounded evidence or a rejection reason; declared hashes are unused."""
    if session.get("observability") != "instrumented":
        return None, "Black-box observations cannot verify an internal cause."
    controlled = control.get("controlled_session")
    if not isinstance(controlled, dict) or controlled.get("observability") != "instrumented":
        return None, "Both executions must contain instrumented sessions."
    try:
        validate_session(controlled)
    except (ValueError, KeyError, TypeError) as error:
        return None, "Controlled session validation failed: " + str(error)
    if not control.get("control_id") or not control.get("fault_event_id"):
        return None, "Missing control or fault event identity."
    for key in ("scenario_id", "family_id", "variant", "platform"):
        if session.get(key) != controlled.get(key):
            return None, "Replay changed the comparison stratum: " + key
    if session.get("session_id") == controlled.get("session_id"):
        return None, "A replay must have a distinct execution identity."
    if controlled.get("status") != "completed" or session.get("status") == "measurement_invalid":
        return None, "Measurement must be valid and the controlled execution complete."
    component = control.get("component")
    category = COMPONENT_CATEGORIES.get(component)
    if category is None or control.get("category") != category:
        return None, "Component/category is not registered for a controlled claim."
    if component != "fact_state.correction":
        return None, "No executable component checker is implemented for this intervention."
    baseline_context = _one_event(session, "evaluation_context")
    controlled_context = _one_event(controlled, "evaluation_context")
    if not baseline_context or not controlled_context:
        return None, "A unique input context snapshot is required for both executions."
    for run, context in ((session, baseline_context), (controlled, controlled_context)):
        if not isinstance(context.get("prefix"), list) or not context["prefix"]:
            return None, "A nonempty visible dialogue prefix is required."
        if not isinstance(context.get("config"), dict) or not context["config"]:
            return None, "A nonempty frozen execution configuration is required."
        if context["prefix"] != run.get("turns", [])[:-1]:
            return None, "Snapshot is not the actual prefix preceding the observed final answer."
        if run["turns"][-1].get("role") != "assistant":
            return None, "The controlled decision must have an observed assistant answer."
    if _canonical(baseline_context["prefix"]) != _canonical(controlled_context["prefix"]):
        return None, "Visible dialogue prefixes differ."
    if _canonical(baseline_context["config"]) != _canonical(controlled_context["config"]):
        return None, "Execution configurations differ."
    fault = _one_event(session, "fault_injected", event_id=control["fault_event_id"], component=component)
    restored = _one_event(controlled, "component_restored", control_id=control["control_id"], component=component)
    if not fault or not restored or fault.get("applied") is not True or restored.get("applied") is not True:
        return None, "Actual injection and restoration events are required."
    if any(key not in event for event in (fault, restored) for key in ("before", "after")):
        return None, "Component snapshots are missing."
    if fault["before"] == fault["after"]:
        return None, "The purported fault did not change the component."
    if fault["after"] != restored["before"] or fault["before"] != restored["after"]:
        return None, "Restoration does not reverse the recorded fault."
    scenario = {key: session[key] for key in ("scenario_id", "family_id", "variant")}
    scenario["criteria"] = _criteria_from_score(score)
    try:
        baseline_score = score_session(session, scenario)
        controlled_score = score_session(controlled, scenario)
    except (ValueError, KeyError, TypeError) as error:
        return None, "Replay observation validation failed: " + str(error)
    criterion_id = control.get("criterion_id")
    baseline_items = {item["criterion_id"]: item for item in baseline_score["criterion_results"]}
    controlled_items = {item["criterion_id"]: item for item in controlled_score["criterion_results"]}
    before, after = baseline_items.get(criterion_id), controlled_items.get(criterion_id)
    if not before or not after or before["outcome"] != "fail" or after["outcome"] != "pass":
        return None, "The same criterion must have an observed fail-to-pass change."
    if before["operational_unmet"] or after["operational_unmet"]:
        return None, "Unreached probes do not establish an observed corrected answer."
    if session["turns"][-1]["turn_id"] not in before["evidence_turn_ids"] or controlled["turns"][-1]["turn_id"] not in after["evidence_turn_ids"]:
        return None, "Both judgments must cite the decision after the matched prefix."
    component_error = _verify_correction_component(session, controlled, fault, before)
    if component_error:
        return None, component_error
    return {
        "control_id": control["control_id"], "criterion_id": criterion_id,
        "fault_event_id": control["fault_event_id"], "component": component,
        "baseline_session_id": session["session_id"],
        "controlled_session_id": controlled["session_id"],
        "prefix_sha256": _digest(baseline_context["prefix"]),
        "config_sha256": _digest(baseline_context["config"]),
        "observed_change": "fail_to_pass",
        "baseline_evidence_turn_ids": before["evidence_turn_ids"],
        "controlled_evidence_turn_ids": after["evidence_turn_ids"],
    }, None


def _check_behavior_control(session, score, control):
    """Validate one changed visible user turn without inferring a hidden cause."""
    controlled = control.get("controlled_session")
    if session.get("observability") != "black_box" or not isinstance(controlled, dict) or controlled.get("observability") != "black_box":
        return None, "A behavior probe requires two black-box sessions."
    try:
        validate_session(controlled)
    except (ValueError, KeyError, TypeError) as error:
        return None, "Controlled session validation failed: " + str(error)
    if not control.get("control_id") or control.get("factor") not in {
        "correction_restated", "ambiguity_clarified", "evidence_supplied", "pressure_removed"
    }:
        return None, "Missing control identity or unsupported behavior factor."
    for key in ("scenario_id", "family_id", "variant", "platform"):
        if session.get(key) != controlled.get(key):
            return None, "Behavior probe changed the comparison stratum: " + key
    if session.get("session_id") == controlled.get("session_id"):
        return None, "A behavior probe requires distinct execution identities."
    if session.get("status") != "completed" or controlled.get("status") != "completed":
        return None, "Both behavior probe sessions must have observed completed answers."
    baseline_metadata = session.get("metadata", {})
    controlled_metadata = controlled.get("metadata", {})
    if not isinstance(baseline_metadata, dict) or not isinstance(controlled_metadata, dict):
        return None, "Behavior probe metadata must be objects."
    matched_settings = {}
    for key in ("app_version", "platform_mode", "input_mode", "session_protocol_id"):
        value = baseline_metadata.get(key)
        if not isinstance(value, str) or not value.strip() or value != controlled_metadata.get(key):
            return None, "Missing or mismatched behavior probe setting: " + key
        matched_settings[key] = value
    if baseline_metadata.get("conversation_reset") is not True or controlled_metadata.get("conversation_reset") is not True:
        return None, "Both executions require a recorded conversation reset."
    baseline_prefix, controlled_prefix = session["turns"][:-1], controlled["turns"][:-1]
    if len(baseline_prefix) != len(controlled_prefix):
        return None, "A behavior probe must preserve prefix turn count."
    changed = []
    for before, after in zip(baseline_prefix, controlled_prefix):
        if {key: value for key, value in before.items() if key != "content"} != {
            key: value for key, value in after.items() if key != "content"
        }:
            return None, "A behavior probe must preserve turn identities, roles and other fields."
        if before["content"] != after["content"]:
            if before["role"] != "user":
                return None, "Only one user message may change in this behavior probe."
            changed.append(before["turn_id"])
    if changed != [control.get("changed_turn_id")]:
        return None, "Exactly the declared user message must differ."
    scenario = {key: session[key] for key in ("scenario_id", "family_id", "variant")}
    scenario["criteria"] = _criteria_from_score(score)
    try:
        baseline_score = score_session(session, scenario)
        controlled_score = score_session(controlled, scenario)
    except (ValueError, KeyError, TypeError) as error:
        return None, "Behavior probe observation validation failed: " + str(error)
    criterion_id = control.get("criterion_id")
    baseline_items = {item["criterion_id"]: item for item in baseline_score["criterion_results"]}
    controlled_items = {item["criterion_id"]: item for item in controlled_score["criterion_results"]}
    before, after = baseline_items.get(criterion_id), controlled_items.get(criterion_id)
    if not before or not after or before["outcome"] != "fail" or after["outcome"] != "pass":
        return None, "The same criterion must have an observed fail-to-pass change."
    if before["operational_unmet"] or after["operational_unmet"]:
        return None, "Unreached probes cannot establish improved answer behavior."
    if session["turns"][-1]["turn_id"] not in before["evidence_turn_ids"] or controlled["turns"][-1]["turn_id"] not in after["evidence_turn_ids"]:
        return None, "Both behavior judgments must cite the final observed answer."
    return {
        "control_id": control["control_id"], "criterion_id": criterion_id,
        "factor": control["factor"], "changed_turn_id": control["changed_turn_id"],
        "baseline_session_id": session["session_id"], "controlled_session_id": controlled["session_id"],
        "baseline_prefix_sha256": _digest(baseline_prefix),
        "controlled_prefix_sha256": _digest(controlled_prefix),
        "matched_settings_sha256": _digest(matched_settings),
        "observed_change": "fail_to_pass",
        "baseline_evidence_turn_ids": before["evidence_turn_ids"],
        "controlled_evidence_turn_ids": after["evidence_turn_ids"],
    }, None


def diagnose(session, score, controls=None):
    """Produce evidence-graded hypotheses, never guess a proprietary architecture."""
    validate_session(session)
    if score.get("session_id") != session.get("session_id"):
        raise ValueError("score belongs to a different session")
    observability = session.get("observability")
    if observability not in {"instrumented", "black_box"}:
        raise ValueError("unknown observability")
    observed = [{key: item[key] for key in (
        "criterion_id", "module", "kind", "critical", "reason", "evidence_turn_ids", "operational_unmet",
        "reviewer_id", "rubric_version"
    )} for item in score["criterion_results"] if item["outcome"] == "fail"]
    hypotheses = []
    control_reviews = []
    for control in controls or []:
        if not isinstance(control, dict):
            raise ValueError("control must be an object")
        behavior_probe = control.get("kind") == "blackbox_behavior_probe"
        checker = _check_behavior_control if behavior_probe else _check_control
        evidence, rejection = checker(session, score, control)
        control_reviews.append({"control_id": control.get("control_id"), "accepted": evidence is not None,
                                "reason": rejection})
        if evidence and behavior_probe:
            hypotheses.append({
                "category": "behavioral_sensitivity", "evidence_level": "supported_hypothesis",
                "claim": "The controlled input change accompanied improved behavior, consistent with sensitivity to the declared factor.",
                "evidence": evidence,
                "limitations": [
                    "This result cannot identify an internal algorithm or engineering mechanism.",
                    "One pair does not exclude sampling variation; repeated preregistered comparisons are still required.",
                    "Factor interpretation and operator-reported platform settings require independent review.",
                ],
            })
        elif evidence:
            hypotheses.append({
                "category": control["category"], "evidence_level": "verified_under_test",
                "claim": "Restoring the recorded component reversed this observed failure in a matched development replay.",
                "evidence": evidence,
                "limitations": [
                    "Causal claim is restricted to this recorded intervention and execution.",
                    "It does not establish clinical benefit or a cause in another platform.",
                    "Broader claims require independent families and repeated controlled runs.",
                ],
            })
    seen = set()
    for defect in observed:
        for category, claim in CANDIDATES.get(defect["module"], []):
            key = (defect["module"], category)
            if key in seen:
                continue
            seen.add(key)
            hypotheses.append({
                "category": category, "evidence_level": "needs_investigation", "claim": claim,
                "evidence": {"criterion_id": defect["criterion_id"], "module": defect["module"],
                             "evidence_turn_ids": defect["evidence_turn_ids"]},
                "limitations": [
                    "The failed behavior is observed; this internal explanation is a candidate only.",
                    "The same output can result from data, policy, engineering or evaluator problems.",
                    "Black-box outputs cannot identify internal causes." if observability == "black_box"
                    else "A matched replay is required before attributing the failure to this component.",
                ],
            })
    if score.get("excluded_from_target_metrics"):
        hypotheses.append({
            "category": "evaluator_simulator", "evidence_level": "needs_investigation",
            "claim": "The measurement was invalid; target quality cannot be concluded from this run.",
            "evidence": {"status": session["status"]},
            "limitations": ["Inspect independent harness failure records before repeating the run."],
        })
    unassessed = [item["criterion_id"] for item in score["criterion_results"]
                  if item["outcome"] == "unassessed" or (item["kind"] == "clinical" and item["operational_unmet"])]
    return {
        "session_id": session["session_id"], "observability": observability,
        "observed_defects": observed, "hypotheses": hypotheses,
        "control_reviews": control_reviews, "unassessed_criteria": unassessed,
        "internal_cause_confirmed": any(item["evidence_level"] == "verified_under_test" for item in hypotheses),
        "clinical_readiness": "not_established",
    }
