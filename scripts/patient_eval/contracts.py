"""Small, dependency-free validation at the evaluation trust boundary.

Only explicitly selected visible turns are sent to a target. Scenario labels,
expected values, structured annotations and patient hidden state stay local.
This release deliberately admits development data only; it does not implement
or replace GroundSignal's independent S5/S6 admission process.
"""

from __future__ import annotations

import json
from pathlib import Path

from .review_contract import REVIEW_VERSION, validate_review_observation


MODULES = {f"C{i}" for i in range(1, 9)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_turns(turns: list, completed: bool = True) -> None:
    require(isinstance(turns, list) and bool(turns), "turns must be nonempty")
    seen = set()
    for index, turn in enumerate(turns):
        require(isinstance(turn, dict), "turn must be an object")
        require(nonempty(turn.get("turn_id")), "missing turn_id")
        require(turn["turn_id"] not in seen, "duplicate turn_id")
        seen.add(turn["turn_id"])
        require(turn.get("role") == ("user" if index % 2 == 0 else "assistant"),
                "turns must alternate user/assistant, starting with user")
        require(nonempty(turn.get("content")), "empty turn content")
    if completed:
        require(turns[-1]["role"] == "assistant", "completed session must end with assistant")


def validate_scenario(scenario: dict) -> None:
    require(isinstance(scenario, dict), "scenario must be an object")
    for field in ("scenario_id", "family_id", "variant", "protocol_id"):
        require(nonempty(scenario.get(field)), f"missing {field}")
    require(scenario.get("split") == "development", "v0.1 admits development split only")
    require(scenario.get("source") in {"synthetic", "deidentified_real"}, "unsupported question source")
    if scenario["source"] == "deidentified_real":
        require(scenario.get("use_authorized") is True and scenario.get("deidentification_confirmed") is True,
                "real-derived scenarios require operator authorization/deidentification declarations")
    prefix = scenario.get("prefix")
    validate_turns(prefix, completed=False)
    require(prefix[-1]["role"] == "user", "fixed prefix must end with user")
    require(all(turn["turn_id"] != "answer" for turn in prefix), "answer is reserved for target completion")
    ids = {turn["turn_id"] for turn in prefix if turn["role"] == "user"}
    updates = scenario.get("visible_updates", {})
    require(isinstance(updates, dict) and set(updates) <= ids, "updates must refer to visible user turns")
    for turn_updates in updates.values():
        require(isinstance(turn_updates, list), "visible updates must be lists")
        for update in turn_updates:
            require(isinstance(update, dict) and nonempty(update.get("key")), "invalid visible update")
            require(update.get("status") in {"confirmed", "unknown", "conflict"}, "invalid fact status")
            require("value" in update, "missing fact value")
    criteria = scenario.get("criteria")
    require(isinstance(criteria, list) and bool(criteria), "criteria must be nonempty")
    seen = set()
    for criterion in criteria:
        require(isinstance(criterion, dict) and nonempty(criterion.get("id")), "invalid criterion")
        require(criterion["id"] not in seen, "duplicate criterion id")
        seen.add(criterion["id"])
        require(criterion.get("module") in MODULES, "unknown module")
        require(criterion.get("kind") in {"mechanical", "clinical"}, "unknown criterion kind")
        require(type(criterion.get("required")) is bool and type(criterion.get("critical")) is bool,
                "criterion required/critical must be booleans")


def validate_session(session: dict) -> None:
    require(isinstance(session, dict), "session must be an object")
    for field in ("session_id", "scenario_id", "family_id", "variant", "platform"):
        require(nonempty(session.get(field)), f"missing {field}")
    require(session.get("observability") in {"instrumented", "black_box"}, "invalid observability")
    status = session.get("status")
    require(status in {"completed", "target_error", "measurement_invalid"}, "invalid session status")
    metadata = session.get("metadata", {})
    require(isinstance(metadata, dict), "metadata must be an object")
    if "review_version" in metadata:
        require(metadata["review_version"] == REVIEW_VERSION, "unsupported session review_version")
    validate_turns(session.get("turns"), completed=status == "completed")
    require(isinstance(session.get("trace"), list), "trace must be a list")
    if session["observability"] == "black_box":
        require(not session["trace"], "black-box sessions cannot claim internal traces")
    if status == "measurement_invalid":
        require(nonempty(session.get("invalid_reason")), "measurement invalid requires an independent reason")
        require(session.get("invalid_component") in {"simulator", "evaluator", "collector"},
                "target outages are target_error, not measurement_invalid")
    observations = session.get("observations")
    require(isinstance(observations, list), "observations must be a list")
    seen = set()
    turn_ids = {turn["turn_id"] for turn in session["turns"]}
    for observation in observations:
        require(isinstance(observation, dict), "invalid observation")
        cid = observation.get("criterion_id")
        require(nonempty(cid) and cid not in seen, "missing or duplicate observation criterion")
        seen.add(cid)
        require(observation.get("outcome") in {"pass", "fail", "not_applicable", "unassessed"},
                "invalid outcome")
        require(observation.get("source") in {"human", "deterministic"}, "invalid observation source")
        evidence = observation.get("evidence_turn_ids")
        require(isinstance(evidence, list) and all(isinstance(t, str) and t in turn_ids for t in evidence),
                "observation evidence must reference actual turns")
        require(nonempty(observation.get("reason")), "observation requires reason")
        if observation["outcome"] in {"pass", "fail", "not_applicable"}:
            require(bool(evidence), "decided observations require evidence")
        if observation["source"] == "human":
            require(nonempty(observation.get("reviewer_id")), "human annotation requires reviewer_id")
            require(nonempty(observation.get("rubric_version")), "human annotation requires rubric_version")
        if "review_version" in observation:
            require(observation["review_version"] == REVIEW_VERSION, "unsupported review_version")
            validate_review_observation(observation, session["turns"])
        else:
            require(not ({"quality_status", "opportunity"} & set(observation)),
                    "independent review fields require explicit review_version; legacy is not auto-upgraded")


def visible_prefix(scenario: dict) -> list[dict]:
    """Allowlist only role/content; never serialize an entire scenario to a model."""
    validate_scenario(scenario)
    return [{"role": turn["role"], "content": turn["content"]} for turn in scenario["prefix"]]


def load_suite(path: str | Path) -> dict:
    suite = json.loads(Path(path).read_text(encoding="utf-8"))
    require(suite.get("schema_version") == "patient-eval/v0.1", "unsupported schema version")
    require(suite.get("scope") == "development_only", "formal admission is not implemented")
    require(isinstance(suite.get("scenarios"), list) and bool(suite["scenarios"]), "empty suite")
    seen = set()
    family_splits = {}
    for scenario in suite["scenarios"]:
        validate_scenario(scenario)
        require(scenario["scenario_id"] not in seen, "duplicate scenario id")
        seen.add(scenario["scenario_id"])
        family = scenario["family_id"]
        require(family not in family_splits or family_splits[family] == scenario["split"], "family split leakage")
        family_splits[family] = scenario["split"]
    return suite
