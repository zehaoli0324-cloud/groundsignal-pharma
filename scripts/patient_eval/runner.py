"""Reproducible prefix replay with an observed event-loss intervention.

The fixture is an engineering subject, not a medical model or patient simulator.
Fact extraction is a supplied visible annotation and is NOT evaluated here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone

from .contracts import require, validate_scenario, validate_session
from .retrieval import rank_evidence
from .state import FactState


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def render_fixture_answer(facts: dict, selected_ids: list) -> str:
    """The fixture's entire visible answer is deterministically reconstructable."""
    rendered = "；".join(f"{key}={fact['value']}（{fact['status']}）" for key, fact in facts.items())
    return "工程测试：当前记录为 " + rendered + "。检索记录=" + str(selected_ids) + "。此输出只演示事实记录，不提供医疗判断。"


def run_fixture(scenario: dict, drop_correction: bool = False) -> dict:
    validate_scenario(scenario)
    require(scenario["source"] == "synthetic", "fixture is restricted to synthetic development data")
    correction_turns = [turn_id for turn_id, updates in scenario.get("visible_updates", {}).items()
                        for update in updates if update.get("supersedes")]
    require(len(correction_turns) <= 1, "v0.1 fixture supports a single correction intervention")
    require(not correction_turns or correction_turns[0] == scenario["prefix"][-1]["turn_id"],
            "v0.1 intervention must target the final visible user turn")
    state = FactState()
    trace = []
    for turn in scenario["prefix"]:
        for update in scenario.get("visible_updates", {}).get(turn["turn_id"], []):
            before = state.snapshot()
            if drop_correction and update.get("supersedes"):
                trace.append({"kind": "fault_injected", "event_id": "F04:" + turn["turn_id"],
                              "component": "fact_state.correction", "before": copy.deepcopy(update),
                              "after": None, "applied": True, "turn_id": turn["turn_id"]})
                trace.append({"kind": "state_transition", "delivered": False, "turn_id": turn["turn_id"],
                              "before": before, "after": state.snapshot()})
                continue
            state.apply(update, turn["turn_id"])
            trace.append({"kind": "state_transition", "delivered": True, "turn_id": turn["turn_id"],
                          "before": before, "after": state.snapshot()})
            if update.get("supersedes"):
                trace.append({"kind": "component_restored", "control_id": "restore:" + turn["turn_id"],
                              "component": "fact_state.correction", "before": None,
                              "after": copy.deepcopy(update), "applied": True})
    trace.append({"kind": "evaluation_context", "prefix": copy.deepcopy(scenario["prefix"]),
                  "config": {"adapter": "fixture", "fixture_version": "0.1",
                             "state_policy": "explicit_visible_updates",
                             "scenario_sha256": digest(scenario)}})
    retrieval = scenario.get("retrieval", {})
    passages = rank_evidence(retrieval.get("query", ""), retrieval.get("passages", []),
                             top_k=3, as_of=retrieval.get("as_of"), population=retrieval.get("population"))
    trace.append({"kind": "retrieval", "query": retrieval.get("query", ""),
                  "selected_ids": [p["id"] for p in passages], "ranked": passages})
    facts = state.snapshot()["facts"]
    selected_ids = [p["id"] for p in passages]
    trace.append({"kind": "fixture_output", "fact_snapshot": state.snapshot(),
                  "selected_evidence_ids": selected_ids})
    response = render_fixture_answer(facts, selected_ids)
    turns = copy.deepcopy(scenario["prefix"]) + [{"turn_id": "answer", "role": "assistant", "content": response}]
    observations = []
    for criterion in scenario["criteria"]:
        if criterion["kind"] != "mechanical":
            continue
        if criterion.get("check") == "state_value":
            expected = criterion["expected"]
            actual = facts.get(criterion["fact_key"], {})
            passed = actual.get("value") == expected and actual.get("status") == criterion.get("expected_status", "confirmed")
            reason = f"显式输出事实 {criterion['fact_key']}: observed={actual.get('value')!r}, expected={expected!r}。只检查状态记录。"
        elif criterion.get("check") == "selected_evidence":
            selected = [p["id"] for p in passages]
            passed = bool(selected) and selected[0] == criterion["expected"]
            reason = f"合成证据排序首位={selected[:1]}；不代表医学内容支持关系通过。"
        else:
            continue
        observations.append({"criterion_id": criterion["id"], "outcome": "pass" if passed else "fail",
                             "evidence_turn_ids": ["answer"], "source": "deterministic", "reason": reason})
    session = {
        "session_id": scenario["scenario_id"] + (":fault" if drop_correction else ":restored"),
        "scenario_id": scenario["scenario_id"], "family_id": scenario["family_id"], "variant": scenario["variant"],
        "platform": "development_fixture", "observability": "instrumented", "status": "completed",
        "turns": turns, "observations": observations, "trace": trace,
        "metadata": {"adapter": "fixture", "arm": "fault" if drop_correction else "restored",
                     "comparison_lane": "fixed_prefix", "session_protocol_id": scenario["protocol_id"],
                     "collected_at": datetime.now(timezone.utc).isoformat(), "synthetic": True,
                     "scenario_sha256": digest(scenario), "prefix_sha256": digest(scenario["prefix"]),
                     "clinical_approval": False},
    }
    validate_session(session)
    return session


def replay_control(scenario: dict, baseline: dict, restored: dict) -> list[dict]:
    """Pair an actually dropped visible correction with its observed delivery."""
    controls = []
    for event in baseline["trace"]:
        if event.get("kind") != "fault_injected":
            continue
        for criterion in scenario["criteria"]:
            if criterion.get("check") == "state_value" and criterion.get("fact_key") == event["before"]["key"]:
                controls.append({"control_id": "restore:" + event["turn_id"], "criterion_id": criterion["id"],
                                 "category": "engineering", "component": event["component"],
                                 "fault_event_id": event["event_id"], "controlled_session": restored})
    return controls
