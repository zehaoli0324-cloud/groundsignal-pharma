"""Validate operator-recorded conversations from an externally visible app.

No network calls, automatic de-identification, consent adjudication, or access to
the target's internal state occurs here. Keep real transcripts outside git.
"""

from copy import deepcopy
from datetime import datetime


_ROLES = {"user", "assistant"}
_OUTCOMES = {"pass", "fail", "not_applicable", "unassessed"}
_STATUSES = {"completed", "target_error", "measurement_invalid"}


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def import_blackbox(record: dict) -> dict:
    """Return a validated copy labelled as black-box, or raise ``ValueError``.

    The two real-question flags are operator declarations, not proof of an
    independent review. Clinical semantic assessments remain the scorer's job.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    result = deepcopy(record)
    for field in ("session_id", "scenario_id", "family_id", "variant", "platform"):
        _nonempty(result.get(field), field)
    if result.get("observability", "black_box") != "black_box":
        raise ValueError("app imports cannot claim instrumented observability")
    if result.get("trace", []) != []:
        raise ValueError("black-box imports must not contain internal traces")
    if result.get("status") not in _STATUSES:
        raise ValueError("invalid session status")

    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    for field in (
        "collected_at", "app_version", "platform_mode", "input_mode",
        "session_protocol_id", "operator",
    ):
        _nonempty(metadata.get(field), f"metadata.{field}")
    try:
        collected = datetime.fromisoformat(metadata["collected_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("collected_at must be an ISO timestamp") from error
    if collected.tzinfo is None or collected.utcoffset() is None:
        raise ValueError("collected_at must include a timezone")
    for field in ("conversation_reset", "deidentification_confirmed", "use_authorized"):
        if type(metadata.get(field)) is not bool:
            raise ValueError(f"metadata.{field} must be a boolean")
    if metadata.get("comparison_lane") not in {"fixed_prefix", "free_dialogue"}:
        raise ValueError("invalid comparison_lane")
    if metadata.get("question_source") not in {"synthetic", "deidentified_real"}:
        raise ValueError("invalid question_source")
    if metadata["question_source"] == "deidentified_real" and not (
        metadata["deidentification_confirmed"] and metadata["use_authorized"]
    ):
        raise ValueError("real-question import requires both operator declarations")

    turns = result.get("turns")
    if not isinstance(turns, list) or not turns:
        raise ValueError("turns must be a non-empty list")
    turn_ids = set()
    expected_role = "user"
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("each turn must be an object")
        turn_id = _nonempty(turn.get("turn_id"), "turn_id")
        if turn_id in turn_ids:
            raise ValueError("turn_id must be unique within a session")
        turn_ids.add(turn_id)
        if turn.get("role") not in _ROLES or turn["role"] != expected_role:
            raise ValueError("turns must alternate user/assistant, beginning with user")
        expected_role = "assistant" if expected_role == "user" else "user"
        _nonempty(turn.get("content"), "turn.content")
    if result["status"] == "completed" and turns[-1]["role"] != "assistant":
        raise ValueError("completed sessions must end with an assistant turn")

    observations = result.get("observations", [])
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    seen_criteria = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError("each observation must be an object")
        criterion = _nonempty(observation.get("criterion_id"), "criterion_id")
        if criterion in seen_criteria:
            raise ValueError("a criterion may be observed only once per session")
        seen_criteria.add(criterion)
        if observation.get("outcome") not in _OUTCOMES:
            raise ValueError("invalid observation outcome")
        if observation.get("source") not in {"deterministic", "human"}:
            raise ValueError("invalid observation source")
        _nonempty(observation.get("reason"), "observation.reason")
        refs = observation.get("evidence_turn_ids")
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ValueError("evidence_turn_ids must be a list of turn IDs")
        if len(set(refs)) != len(refs) or any(ref not in turn_ids for ref in refs):
            raise ValueError("evidence_turn_ids must be unique and refer to visible turns")
        if observation["outcome"] in {"pass", "fail"} and not refs:
            raise ValueError("assessed observations need visible evidence")

    result["observability"] = "black_box"
    result["trace"] = []
    result["observations"] = observations
    metadata["internal_access_verified"] = False
    metadata["declarations_are_review_approval"] = False
    metadata["attribution_limit"] = "behavioral_hypotheses_only"
    metadata["observability_note"] = "仅有用户输入与平台回答；无法核验内部算法、检索、状态或服务日志。"
    return result
