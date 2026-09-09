"""Versioned pilot loading, blind review packets and local manual collection.

Patient scripts are operator materials. Only the next patient message is copied
into a target application; scripts and scoring criteria never become prompts.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import random

from .contracts import require, validate_session
from .importers import import_blackbox
from .patient import PatientSimulator
from .runner import digest
from .scoring import aggregate_scores, score_session
from .diagnosis import diagnose
from .reporting import paired_family_comparison


DEFAULT_PILOT = Path(__file__).resolve().parents[2] / "medical/patient-eval/pilot/v0.2/suite.json"


def load_pilot_suite(path=DEFAULT_PILOT):
    suite = json.loads(Path(path).read_text(encoding="utf-8"))
    require(suite.get("schema_version") == "patient-pilot/v0.2", "unsupported pilot schema")
    require(suite.get("scope") == "development_only", "pilot cannot grant formal admission")
    scenarios = suite.get("scenarios")
    require(isinstance(scenarios, list) and bool(scenarios), "empty pilot suite")
    seen, families = set(), {}
    for scenario in scenarios:
        for field in ("scenario_id", "family_id", "variant", "protocol_id"):
            require(isinstance(scenario.get(field), str) and bool(scenario[field].strip()), f"missing {field}")
        require(scenario["scenario_id"] not in seen, "duplicate scenario_id")
        seen.add(scenario["scenario_id"])
        require(scenario.get("split") == "development", "pilot accepts development only")
        require(scenario.get("source") in {"synthetic", "deidentified_real"}, "unsupported question source")
        if scenario["source"] == "deidentified_real":
            require(scenario.get("use_authorized") is True and scenario.get("deidentification_confirmed") is True,
                    "real-derived pilot requires explicit operator declarations")
        PatientSimulator(scenario["patient"])
        criteria = scenario.get("criteria")
        require(isinstance(criteria, list) and bool(criteria), "empty criteria")
        criterion_ids = set()
        for criterion in criteria:
            require(isinstance(criterion.get("id"), str) and criterion["id"] not in criterion_ids, "duplicate/missing criterion id")
            criterion_ids.add(criterion["id"])
            require(criterion.get("module") in {f"C{i}" for i in range(1, 9)}, "invalid capability module")
            require(criterion.get("kind") in {"clinical", "mechanical"}, "invalid criterion kind")
            require(type(criterion.get("required")) is bool and type(criterion.get("critical")) is bool,
                    "required/critical must be boolean")
        families.setdefault(scenario["family_id"], []).append(scenario)
    # Paired variants are one family, never independent patient samples.
    for family in families.values():
        require(len({s["variant"] for s in family}) == len(family), "duplicate family variant")
        for other in family[1:]:
            require(other["criteria"] == family[0]["criteria"], "family variants must share scoring criteria")
            require(other["patient"]["facts"] == family[0]["patient"]["facts"], "family variants changed patient facts")
            require(other["protocol_id"] == family[0]["protocol_id"], "family protocol mismatch")
            allowed = family[0].get("pairing", {}).get("allowed_differences")
            require(allowed in [["initial_user_message"], ["events.pressure.content"]],
                    "pilot pairs must declare exactly one supported pressure manipulation")
            require(other.get("pairing", {}).get("allowed_differences") == allowed, "pairing declarations differ")
            def normalized_patient(s):
                patient = deepcopy(s["patient"])
                if allowed == ["initial_user_message"]:
                    patient["initial_user_message"] = "<declared expression manipulation>"
                else:
                    for event in patient["events"]:
                        if event["kind"] == "pressure":
                            event["content"] = "<declared pressure manipulation>"
                return patient
            require(normalized_patient(other) == normalized_patient(family[0]),
                    "undeclared patient-policy, event-trigger or budget change in paired variants")
            def resulting_facts(s):
                facts = {k: {"value": v["value"], "status": v["status"]} for k, v in s["patient"]["facts"].items()}
                for event in s["patient"]["events"]:
                    for update in event["updates"]:
                        facts[update["slot"]] = {"value": update["value"], "status": update["status"]}
                return facts
            require(resulting_facts(other) == resulting_facts(family[0]), "variants changed corrected patient facts")
    return suite


def score_pilot(suite, sessions):
    by_id = {s["scenario_id"]: s for s in suite["scenarios"]}
    require(isinstance(sessions, list) and bool(sessions), "sessions must be a nonempty list")
    seen, scores, diagnoses, normalized = set(), [], [], []
    for session in sessions:
        session = import_blackbox(session)
        validate_session(session)
        require(session["session_id"] not in seen, "duplicate session_id")
        seen.add(session["session_id"])
        require(session["scenario_id"] in by_id, "unknown scenario_id")
        scenario = by_id[session["scenario_id"]]
        metadata = session["metadata"]
        require(metadata["comparison_lane"] == "free_dialogue", "pilot score uses free-dialogue protocol")
        require(metadata["session_protocol_id"] == scenario["protocol_id"], "protocol mismatch")
        require(session["turns"][0]["content"] == scenario["patient"]["initial_user_message"], "initial patient question mismatch")
        require(metadata["question_source"] == scenario["source"], "source declaration mismatch")
        if "scenario_sha256" in metadata:
            require(metadata["scenario_sha256"] == digest(scenario), "scenario changed after collection")
        criteria = {c["id"]: c for c in scenario["criteria"]}
        for observation in session["observations"]:
            require(observation["criterion_id"] in criteria, "unknown observation criterion")
            ordinal = observation.get("ordinal_rating")
            require(ordinal is None or type(ordinal) is int and ordinal in {0, 1, 2}, "invalid ordinal rating")
            if observation["source"] != "human" or observation["outcome"] == "unassessed":
                continue
            require(observation["rubric_version"] == suite.get("rubric_version", "patient-pilot-rubric/v0.2"),
                    "pilot annotation rubric version mismatch")
            if criteria[observation["criterion_id"]]["critical"]:
                if observation["outcome"] == "fail":
                    require(observation.get("serious_error") is True, "critical failure requires an explicit serious-error judgment")
                elif observation["outcome"] == "pass":
                    require(observation.get("serious_error") is False, "critical pass requires an explicit no-serious-error judgment")
        score = score_session(session, scenario)
        scores.append(score)
        diagnoses.append(diagnose(session, score))
        normalized.append(session)
    transitions = [event for session in normalized if isinstance(session.get("harness_trace"), list)
                   for event in session["harness_trace"] if event.get("kind") == "patient_transition"]
    unmatched = sum(event.get("classification") == "unmatched" for event in transitions)
    event_records = [s for s in normalized if "planned_event_ids" in s["metadata"]]
    quality = {"automatic_patient_transitions": len(transitions), "unmatched_transitions": unmatched,
               "unmatched_rate": unmatched / len(transitions) if transitions else None,
               "sessions_with_event_audit": len(event_records),
               "planned_events": sum(len(s["metadata"]["planned_event_ids"]) for s in event_records),
               "unreached_events": sum(len(s["metadata"].get("unreached_event_ids", [])) for s in event_records),
               "incomplete_simulator_audits": sum(s["metadata"].get("simulator_audit_complete") is False for s in normalized),
               "sessions_with_complete_usage": sum(s["metadata"].get("usage_complete") is True for s in normalized),
               "unknown_usage_attempts": sum(s["metadata"].get("attempt_usage_unknown", 0) for s in normalized),
               "unparsed_user_clauses": sum(len(s.get("harness_state", {}).get("unparsed", [])) for s in normalized),
               "interpretation": "问句未匹配、未触发事件及未解析文字是测量与抽取审查线索，不能直接当成模型失分。"}
    return {"title": "GroundSignal 动态患者试评", "scope": "development_only", "sessions": normalized,
            "scores": scores, "diagnoses": diagnoses, "aggregate": aggregate_scores(scores),
            "measurement_quality": quality}


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def make_review_packet(suite, sessions, out, seed=7):
    """Separate reviewer materials from platform identities and hidden scripts."""
    score_pilot(suite, sessions)  # validate before exporting any clinical material
    out = Path(out)
    require(not out.exists(), "review output directory already exists")
    by_id = {s["scenario_id"]: s for s in suite["scenarios"]}
    ordered = deepcopy(sessions)
    random.Random(seed).shuffle(ordered)
    mapping, items, rating_rows = {}, [], []
    for index, session in enumerate(ordered, 1):
        blind_id = f"D{index:04d}"
        mapping[blind_id] = {key: session[key] for key in ("session_id", "scenario_id", "family_id", "platform")}
        scenario = by_id[session["scenario_id"]]
        for criterion in scenario["criteria"]:
            item_id = blind_id + ":" + criterion["id"]
            # Text can still reveal a brand. Metadata blinding is not guaranteed full blinding.
            items.append({"item_id": item_id, "criterion": deepcopy(criterion),
                          "turns": [{k: t[k] for k in ("turn_id", "role", "content")} for t in session["turns"]],
                          "session_status": session["status"], "rating": None, "outcome": "unassessed",
                          "evidence_turn_ids": [], "reason": "", "serious_error": None,
                          "reviewer_id": "", "rubric_version": suite.get("rubric_version", "patient-pilot-rubric/v0.2")})
            rating_rows.append({"item_id": item_id, "reviewer_id": "", "rubric_version": suite.get("rubric_version", "patient-pilot-rubric/v0.2"),
                                "rating": None, "serious_error": None})
    out.mkdir(parents=True)
    write_new_json(out / "reviewer-packet.json", {"scope": "development_only", "items": items,
                   "blinding_limit": "Only metadata is blinded; original response text may reveal the platform."})
    write_new_json(out / "ratings-template.json", {"template": True, "rows": rating_rows})
    write_new_json(out / "operator-key.json", {"seed": seed, "mapping": mapping,
                   "instruction": "Operator only. Do not give this key or patient scripts to blinded reviewers."})
    return {"sessions": len(ordered), "review_items": len(items), "out": str(out)}


def apply_review(suite, sessions, packet, operator_key):
    """Bind adjudicated judgments to original text, never infer them from 0–2."""
    score_pilot(suite, sessions)
    sessions = deepcopy(sessions)
    by_session = {s["session_id"]: s for s in sessions}
    scenarios = {s["scenario_id"]: s for s in suite["scenarios"]}
    mapping = operator_key.get("mapping", {})
    require(isinstance(packet.get("items"), list) and isinstance(mapping, dict), "invalid review packet/key")
    seen = set()
    for item in packet["items"]:
        item_id = item.get("item_id", "")
        require(isinstance(item_id, str) and ":" in item_id and item_id not in seen, "duplicate/invalid review item")
        seen.add(item_id)
        blind_id, criterion_id = item_id.split(":", 1)
        require(blind_id in mapping and mapping[blind_id].get("session_id") in by_session, "unknown blinded session")
        session = by_session[mapping[blind_id]["session_id"]]
        scenario = scenarios[session["scenario_id"]]
        criteria = {c["id"]: c for c in scenario["criteria"]}
        require(criterion_id in criteria and item.get("criterion") == criteria[criterion_id], "review criterion changed")
        visible = [{k: t[k] for k in ("turn_id", "role", "content")} for t in session["turns"]]
        require(item.get("turns") == visible, "reviewed text does not match the original session")
        rating = item.get("rating")
        require(rating is None or type(rating) is int and rating in {0, 1, 2}, "invalid ordinal rating")
        serious = item.get("serious_error")
        require(serious is None or type(serious) is bool, "invalid serious_error label")
        outcome = item.get("outcome", "unassessed")
        require(outcome in {"pass", "fail", "unassessed", "not_applicable"}, "invalid human outcome")
        if outcome == "unassessed":
            continue  # high ordinal ratings never imply a pass
        if criteria[criterion_id]["critical"]:
            require(outcome != "fail" or serious is True, "critical failure requires an explicit serious-error judgment")
            require(outcome != "pass" or serious is False, "critical pass requires an explicit no-serious-error judgment")
        require(item.get("rubric_version") == suite.get("rubric_version", "patient-pilot-rubric/v0.2"), "review rubric version mismatch")
        require(not any(o["criterion_id"] == criterion_id for o in session["observations"]),
                "existing annotation must be explicitly adjudicated, not silently overwritten")
        observation = {"criterion_id": criterion_id, "outcome": outcome, "source": "human",
                       "reviewer_id": item.get("reviewer_id"), "rubric_version": item.get("rubric_version"),
                       "reason": item.get("reason"), "evidence_turn_ids": item.get("evidence_turn_ids"),
                       "ordinal_rating": rating, "serious_error": serious}
        if item.get("applicability") == "legitimate_stop":
            observation["applicability"] = "legitimate_stop"
        session["observations"].append(observation)
        validate_session(session)
    score_pilot(suite, sessions)
    return sessions


def compare_intervention(suite, sessions, criterion_id, seed=7):
    """Compare adjudicated criterion completion; never fill missing reviews."""
    bundle = score_pilot(suite, sessions)
    scored = {s["session_id"]: s for s in bundle["scores"]}
    configs, policies, models, rows = set(), set(), set(), []
    for session in bundle["sessions"]:
        metadata = session["metadata"]
        arm = metadata.get("arm")
        require(arm in {"baseline", "state_augmented"}, "intervention comparison requires declared study arms")
        require(isinstance(metadata.get("target_config"), dict) and bool(metadata["target_config"]), "missing target configuration")
        require(isinstance(metadata.get("system_policy_sha256"), str), "missing fixed system policy identity")
        require(metadata.get("conversation_reset") is True, "comparison requires independently reset conversations")
        require(isinstance(metadata.get("scenario_sha256"), str), "comparison requires a frozen scenario identity")
        configs.add(digest(metadata["target_config"]))
        policies.add(metadata["system_policy_sha256"])
        models.add(session["platform"])
        result = next((r for r in scored[session["session_id"]]["criterion_results"] if r["criterion_id"] == criterion_id), None)
        require(result is not None, "selected criterion is not shared by every scenario")
        require(not scored[session["session_id"]]["excluded_from_target_metrics"],
                "resolve independent invalid measurements before comparing complete pairs")
        require(result["outcome"] in {"pass", "fail"},
                "selected criterion requires adjudication on every pair; unknown or inapplicable is not a score")
        rows.append({"family_id": session["family_id"], "scenario_id": session["scenario_id"],
                     "variant": session["variant"], "repeat_id": metadata.get("repeat_id"),
                     "platform": arm, "score": int(result["outcome"] == "pass"),
                     "comparison_lane": metadata["comparison_lane"], "protocol_id": metadata["session_protocol_id"]})
    require(len(configs) == len(policies) == len(models) == 1, "both arms must use the same model, configuration and fixed policy")
    comparison = paired_family_comparison(rows, "baseline", "state_augmented", seed=seed)
    comparison.update(criterion_id=criterion_id, target_platform=next(iter(models)),
                      target_quality_summary=bundle["aggregate"],
                      interpretation="判据完成率的家族配对差；服务失败计未完成。严重错误与未评临床项单列，不代表临床总体效果。")
    return comparison


def new_collection(scenario, metadata, platform, session_id):
    sim = PatientSimulator(scenario["patient"])
    opening = sim.opening()
    record = {"session_id": session_id, "scenario_id": scenario["scenario_id"], "family_id": scenario["family_id"],
              "variant": scenario["variant"], "platform": platform, "observability": "black_box",
              "status": "target_error", "turns": [{"turn_id": "u1", "role": "user", "content": opening["content"]}],
              "observations": [], "trace": [], "metadata": deepcopy(metadata)}
    # Validate supplied collection metadata now, before the operator starts the app.
    record = import_blackbox(record)
    record["status"] = "in_progress"  # journals are not completed evaluation records
    record["metadata"]["scenario_sha256"] = digest(scenario)
    require(metadata["session_protocol_id"] == scenario["protocol_id"] and metadata["comparison_lane"] == "free_dialogue",
            "manual collection protocol mismatch")
    require(metadata["question_source"] == scenario["source"], "question source mismatch")
    return {"schema_version": "patient-collection/v0.2", "scenario_sha256": digest(scenario),
            "session": record, "responses": [], "done": False, "next_patient_message": opening["content"],
            "notice": "Copy only next_patient_message. In-progress user messages are drafts until submitted to the app."}


def advance_collection(scenario, journal, assistant_text, finish=False, target_error=False,
                       requested_slots=None, classification_note=None, patient_submitted=None):
    require(journal.get("schema_version") == "patient-collection/v0.2", "unsupported collection journal")
    require(journal.get("scenario_sha256") == digest(scenario), "patient script changed during collection")
    require(journal.get("done") is False, "collection already ended")
    require(type(finish) is bool and type(target_error) is bool, "finish/error flags must be boolean")
    require(not target_error or not assistant_text, "record a target outage without inventing an assistant response")
    if target_error:
        require(type(patient_submitted) is bool,
                "on an outage record whether the pending patient message was actually submitted")
    require(target_error or isinstance(assistant_text, str) and bool(assistant_text.strip()), "empty assistant response")
    if requested_slots is not None:
        require(isinstance(classification_note, str) and bool(classification_note.strip()),
                "manual question classification requires an audit note")
    sim = PatientSimulator(scenario["patient"])
    turns = [{"turn_id": "u1", "role": "user", "content": sim.opening()["content"]}]
    for index, response in enumerate(journal["responses"], 1):
        turns.append({"turn_id": f"a{index}", "role": "assistant", "content": response["content"]})
        result = sim.respond(response["content"], requested_slots=response.get("requested_slots"), stop=response["finish"])
        require(not result["done"], "cannot advance an already ended transcript")
        turns.append({"turn_id": f"u{index+1}", "role": "user", "content": result["content"]})
    require(turns == journal["session"]["turns"], "journal transcript does not match deterministic replay")
    updated = deepcopy(journal)
    if target_error and not patient_submitted:
        updated.setdefault("collector_issues", []).append({
            "kind": "patient_input_not_submitted", "pending_turn_id": turns[-1]["turn_id"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "classification": "collection_failure_not_target_evidence"})
        updated["notice"] = "The input was not submitted. This remains an unfinished collection journal; no model session is exported."
        return updated
    if target_error:
        updated.update(done=True, next_patient_message=None)
        updated["session"]["status"] = "target_error"
        updated["session"]["metadata"]["stop_reason"] = "operator_recorded_target_error"
        updated["session"]["metadata"]["last_patient_input_submitted"] = True
    else:
        index = len(journal["responses"]) + 1
        turns.append({"turn_id": f"a{index}", "role": "assistant", "content": assistant_text})
        result = sim.respond(assistant_text, requested_slots=requested_slots, stop=finish)
        updated["responses"].append({"content": assistant_text, "finish": finish,
                                     "requested_slots": requested_slots, "classification_note": classification_note})
        updated["done"] = result["done"]
        updated["next_patient_message"] = None if result["done"] else result["content"]
        if not result["done"]:
            turns.append({"turn_id": f"u{index+1}", "role": "user", "content": result["content"]})
        updated["session"]["status"] = "completed" if result["done"] else "in_progress"
        updated["session"]["turns"] = turns
        updated["session"]["metadata"]["stop_reason"] = result["stop_reason"]
    updated["session"]["metadata"]["collected_at"] = datetime.now(timezone.utc).isoformat()
    updated["session"]["harness_trace"] = {"patient": sim.snapshot(), "collector": "manual-app/v0.2"}
    if updated["done"]:
        validate_session(updated["session"])
    return updated
