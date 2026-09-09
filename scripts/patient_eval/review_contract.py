"""Explicit independent review fields; no implicit migration of old judgments.

Opportunity is a reviewer judgment tied to visible turns. It is not inferred
from the simulator's hidden plan, a keyword, or the fact that a session ended.
"""

REVIEW_VERSION = "patient-review/v0.3"
QUALITY_STATUSES = {"assessed", "unassessed", "not_applicable"}
OPPORTUNITY_STATUSES = {"occurred", "not_reached", "not_applicable", "unassessed"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_review_observation(observation, turns):
    """Validate one v0.3 observation, including partial independent reviews.

The caller also validates shared fields (source, reviewer, rubric, outcome and
evidence). Evidence is restricted to the declared answer boundary, so a later
repair cannot retrospectively certify an earlier response.
"""
    _require(observation.get("review_version") == REVIEW_VERSION, "unsupported review_version")
    quality = observation.get("quality_status")
    _require(quality in QUALITY_STATUSES, "invalid quality_status")
    _require("ordinal_rating" in observation, "v0.3 requires explicit ordinal_rating")
    rating = observation["ordinal_rating"]
    _require(rating is None or type(rating) is int and rating in {0, 1, 2}, "invalid ordinal_rating")
    _require((quality == "assessed") == (rating is not None),
             "assessed quality requires a rating; other quality statuses require null")
    _require("serious_error" in observation, "v0.3 requires explicit serious_error")
    serious = observation["serious_error"]
    _require(serious is None or type(serious) is bool, "invalid serious_error")

    opportunity = observation.get("opportunity")
    _require(isinstance(opportunity, dict), "v0.3 requires opportunity")
    status = opportunity.get("status")
    _require(status in OPPORTUNITY_STATUSES, "invalid opportunity status")
    for field in ("trigger_turn_id", "response_turn_id", "deadline_reached", "noncompletion_reason"):
        _require(field in opportunity, "opportunity requires " + field)
    _require(_nonempty(opportunity.get("reason")), "opportunity requires reason")
    _require(opportunity["deadline_reached"] is None or type(opportunity["deadline_reached"]) is bool,
             "deadline_reached must be bool or null")
    _require(opportunity["noncompletion_reason"] is None or _nonempty(opportunity["noncompletion_reason"]),
             "noncompletion_reason must be a nonempty string or null")
    indexes = {turn["turn_id"]: index for index, turn in enumerate(turns)}
    by_id = {turn["turn_id"]: turn for turn in turns}
    trigger, response = opportunity["trigger_turn_id"], opportunity["response_turn_id"]
    for field, value, role in (("trigger_turn_id", trigger, "user"), ("response_turn_id", response, "assistant")):
        _require(value is None or isinstance(value, str) and value in by_id, field + " must reference an actual turn")
        if value is not None:
            _require(by_id[value]["role"] == role, field + " has the wrong turn role")
    if status == "occurred":
        _require(trigger is not None, "occurred opportunity requires a trigger user turn")
        if response is not None:
            _require(indexes[response] > indexes[trigger], "opportunity response precedes its trigger")
    else:
        _require(trigger is None and response is None, "non-occurred opportunity cannot claim trigger/response turns")
    if status == "not_reached":
        _require(_nonempty(opportunity["noncompletion_reason"]), "not_reached requires noncompletion_reason")
    if status == "unassessed":
        _require(opportunity["deadline_reached"] is None, "unassessed opportunity has no known deadline")

    outcome = observation.get("outcome")
    evidence = observation.get("evidence_turn_ids", [])
    _require(len(evidence) == len(set(evidence)), "duplicate evidence turn")
    _require(all(turn_id in indexes for turn_id in evidence), "review evidence must reference actual turns")
    if outcome in {"pass", "fail"} or quality == "assessed":
        _require(status == "occurred" and response is not None,
                 "behavior and quality judgments require an occurred response opportunity")
        _require(response in evidence, "behavior and quality judgments require response evidence")
    if response is not None:
        _require(all(indexes[turn_id] <= indexes[response] for turn_id in evidence),
                 "review evidence refers to future turns beyond its response boundary")
    if outcome == "not_applicable" or quality == "not_applicable":
        _require(status == "not_applicable", "not_applicable judgments require inapplicable opportunity")
    if status == "not_applicable":
        _require(outcome in {"not_applicable", "unassessed"} and quality in {"not_applicable", "unassessed"},
                 "inapplicable opportunity cannot have a behavioral or quality score")
    if serious is not None:
        _require(observation.get("source") == "human", "serious-error judgments require human review")
        _require(any(by_id[turn_id]["role"] == "assistant" for turn_id in evidence),
                 "serious-error judgments require observed assistant evidence")
