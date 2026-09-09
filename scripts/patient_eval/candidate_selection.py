"""Freeze a deterministic, text-free development candidate selection.

Selection uses structural review features only. It does not inspect model
answers, infer clinical truth, create case families or grant runnable status.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .candidate_blockers import build_public_blocker_queue
from .candidate_review import _read, validate_review


SCHEMA_VERSION = "candidate-development-selection/v0.1"
FEATURE_NAMES = (
    "turn_count",
    "included_fact_count",
    "initial_fact_count",
    "on_question_fact_count",
    "scheduled_fact_count",
    "absent_fact_count",
    "unknown_fact_count",
    "drafted_behavioral_rubric_count",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _features(item):
    review = item["review"]
    included = [fact for fact in review["facts"] if fact["decision"] == "include"]
    return {
        "turn_count": len(item["turns"]),
        "included_fact_count": len(included),
        "initial_fact_count": sum(fact["disclosure_policy"] == "initial" for fact in included),
        "on_question_fact_count": sum(fact["disclosure_policy"] == "on_question" for fact in included),
        "scheduled_fact_count": sum(fact["disclosure_policy"] == "scheduled" for fact in included),
        "absent_fact_count": sum(fact["polarity"] == "absent" for fact in included),
        "unknown_fact_count": sum(fact["polarity"] == "unknown" for fact in included),
        "drafted_behavioral_rubric_count": sum(
            rubric["kind"] == "behavioral" and rubric["decision"] == "drafted"
            for rubric in review["rubrics"]
        ),
    }


def _tags(features):
    tags = []
    for field, tag in (
        ("initial_fact_count", "HAS_INITIAL"),
        ("on_question_fact_count", "HAS_ON_QUESTION"),
        ("scheduled_fact_count", "HAS_SCHEDULED"),
        ("absent_fact_count", "HAS_ABSENT"),
        ("unknown_fact_count", "HAS_EXPLICIT_UNKNOWN"),
    ):
        if features[field] > 0:
            tags.append(tag)
    if features["turn_count"] >= 20:
        tags.append("AT_LEAST_20_TURNS")
    if features["on_question_fact_count"] + features["scheduled_fact_count"] >= 5:
        tags.append("AT_LEAST_5_DYNAMIC_FACTS")
    return tags


def _normalise(features_by_id):
    ranges = {}
    for name in FEATURE_NAMES:
        values = [features[name] for features in features_by_id.values()]
        ranges[name] = (min(values), max(values))
    normalised = {}
    for candidate_id, features in features_by_id.items():
        row = {}
        for name, value in features.items():
            low, high = ranges[name]
            row[name] = 0.0 if high == low else (value - low) / (high - low)
        normalised[candidate_id] = row
    return normalised, ranges


def _distance(left, right):
    return sum(abs(left[name] - right[name]) for name in FEATURE_NAMES) / len(FEATURE_NAMES)


def _tie_digest(packet_sha256, candidate_id):
    return hashlib.sha256(f"{packet_sha256}:{candidate_id}".encode()).hexdigest()


def _similarity_groups(review):
    groups = {}
    for group in review["similarity"]["source_group_suggestions"]:
        group_id = group["group_id"]
        for candidate_id in group["candidate_ids"]:
            _require(candidate_id not in groups, "candidate occurs in multiple similarity groups")
            groups[candidate_id] = group_id
    return groups


def _source_identity(item):
    value = item["source_dialogue_id"]
    return type(value).__name__, str(value)


def build_development_selection(
        original, review, blocker_queue, source_review_sha256, review_file_sha256,
        requested_count=12):
    """Return a deterministic selection manifest without source or patient text."""
    _require(type(requested_count) is int and requested_count > 0, "requested_count must be a positive integer")
    validation = validate_review(original, review)
    expected_blockers = build_public_blocker_queue(
        original, review, source_review_sha256, review_file_sha256)
    _require(blocker_queue == expected_blockers, "blocker queue does not match validated private review")
    _require(blocker_queue["admission"] == {
        "gold_approved": False,
        "formal_approval": False,
        "clinical_gold": False,
        "dynamic_scenario_ready": False,
        "s6_automatic_trust": "BLOCKED",
    }, "blocker queue unexpectedly grants admission")

    items = {item["candidate_id"]: item for item in review["items"]}
    gate_rows = {row["candidate_id"]: row for row in blocker_queue["candidates"]}
    _require(set(items) == set(gate_rows), "candidate identity mismatch between review and blockers")
    authoring_ready_ids = sorted(
        candidate_id for candidate_id, row in gate_rows.items()
        if row["states"]["dynamic_authoring"] == "READY"
    )
    _require(authoring_ready_ids, "no dynamic-authoring candidates are ready")
    ready_features = {candidate_id: _features(items[candidate_id]) for candidate_id in authoring_ready_ids}
    eligible_ids = sorted(candidate_id for candidate_id, row in ready_features.items()
                          if row["initial_fact_count"] > 0
                          and row["on_question_fact_count"] + row["scheduled_fact_count"] > 0)
    _require(eligible_ids, "no candidates satisfy initial and dynamic disclosure requirements")
    features_by_id = {candidate_id: ready_features[candidate_id] for candidate_id in eligible_ids}
    normalised, ranges = _normalise(features_by_id)
    tags_by_id = {candidate_id: set(_tags(features)) for candidate_id, features in features_by_id.items()}
    similarity_groups = _similarity_groups(review)
    source_identity = {candidate_id: _source_identity(items[candidate_id]) for candidate_id in eligible_ids}

    selected = []
    traces = {}
    covered_tags = set()
    selected_similarity_groups = set()
    selected_sources = set()
    while len(selected) < min(requested_count, len(eligible_ids)):
        feasible = []
        for candidate_id in eligible_ids:
            if candidate_id in selected:
                continue
            group = similarity_groups.get(candidate_id)
            if group is not None and group in selected_similarity_groups:
                continue
            if source_identity[candidate_id] in selected_sources:
                continue
            new_tags = len(tags_by_id[candidate_id] - covered_tags)
            complexity = sum(normalised[candidate_id].values()) / len(FEATURE_NAMES)
            minimum_distance = (
                min(_distance(normalised[candidate_id], normalised[chosen]) for chosen in selected)
                if selected else complexity
            )
            feasible.append((
                -new_tags,
                -minimum_distance,
                -complexity,
                _tie_digest(original["packet_sha256"], candidate_id),
                candidate_id,
                new_tags,
                minimum_distance,
                complexity,
            ))
        if not feasible:
            break
        chosen = min(feasible)
        candidate_id = chosen[4]
        selected.append(candidate_id)
        traces[candidate_id] = {
            "new_structural_tag_count": chosen[5],
            "minimum_normalised_distance": round(chosen[6], 12),
            "normalised_complexity": round(chosen[7], 12),
        }
        covered_tags.update(tags_by_id[candidate_id])
        if candidate_id in similarity_groups:
            selected_similarity_groups.add(similarity_groups[candidate_id])
        selected_sources.add(source_identity[candidate_id])

    selection_config = {
        "requested_count": requested_count,
        "eligibility_gate": [
            "dynamic_authoring=READY from exact recomputed blocker queue",
            "at least one included initial-disclosure fact",
            "at least one included on-question or scheduled fact",
        ],
        "feature_names": list(FEATURE_NAMES),
        "selection_order": [
            "maximise new structural tags",
            "maximise minimum normalised L1 distance to selected candidates",
            "maximise mean normalised structural complexity",
            "SHA-256(packet_sha256:candidate_id) ascending tie-break",
        ],
        "similarity_guard": "at most one candidate per uncalibrated similarity component",
        "source_guard": "at most one candidate per exact private source dialogue identity",
        "model_answers_used": False,
    }
    selection_set = set(selected)
    decisions = []
    reasons = Counter()
    for candidate_id in sorted(items):
        if candidate_id in selection_set:
            decision, reason = "SELECTED", "STRUCTURAL_DIVERSITY_SELECTION"
        elif candidate_id not in authoring_ready_ids:
            decision, reason = "NOT_SELECTED", "DYNAMIC_AUTHORING_BLOCKED"
        elif ready_features[candidate_id]["initial_fact_count"] == 0:
            decision, reason = "NOT_SELECTED", "INITIAL_DISCLOSURE_MISSING"
        elif (ready_features[candidate_id]["on_question_fact_count"]
              + ready_features[candidate_id]["scheduled_fact_count"] == 0):
            decision, reason = "NOT_SELECTED", "DYNAMIC_DISCLOSURE_MISSING"
        elif (similarity_groups.get(candidate_id) is not None
              and similarity_groups[candidate_id] in selected_similarity_groups):
            decision, reason = "NOT_SELECTED", "SIMILARITY_GROUP_CAP"
        elif source_identity[candidate_id] in selected_sources:
            decision, reason = "NOT_SELECTED", "SOURCE_DIALOGUE_CAP"
        else:
            decision, reason = "NOT_SELECTED", "FIXED_SELECTION_CAP"
        reasons[reason] += 1
        decisions.append({"candidate_id": candidate_id, "decision": decision, "reason": reason})

    selected_rows = []
    for rank, candidate_id in enumerate(selected, 1):
        selected_rows.append({
            "selection_rank": rank,
            "candidate_id": candidate_id,
            "development_exposed": True,
            "clinical_runnable": "BLOCKED",
            "features": features_by_id[candidate_id],
            "structural_tags": sorted(tags_by_id[candidate_id]),
            "selection_trace": traces[candidate_id],
        })
    coverage = {}
    for name in FEATURE_NAMES:
        values = [features_by_id[candidate_id][name] for candidate_id in selected]
        coverage[name] = {"minimum": min(values), "maximum": max(values), "sum": sum(values)}
    similarity = review["similarity"]
    source_identities = [_source_identity(item) for item in review["items"]]
    selected_source_identities = [_source_identity(items[candidate_id]) for candidate_id in selected]
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "development_only",
        "selection_status": "FROZEN_DEVELOPMENT_IDS" if len(selected) == requested_count else "PARTIAL",
        "development_exposed": True,
        "source_review_sha256": source_review_sha256,
        "canonical_review_sha256": review_file_sha256,
        "packet_sha256": original["packet_sha256"],
        "blocker_queue_sha256": hashlib.sha256(_json(blocker_queue).encode()).hexdigest(),
        "selection_rule_sha256": hashlib.sha256(_json(selection_config).encode()).hexdigest(),
        "selection_config": selection_config,
        "validation": {
            "official_review_contract": "PASS",
            "blocker_queue_exact_recomputation": "PASS",
            "candidate_count": validation["counts"]["candidates"],
            "dynamic_authoring_gate_ready_count": len(authoring_ready_ids),
            "eligible_selection_count": len(eligible_ids),
            "requested_count": requested_count,
            "selected_count": len(selected),
            "model_answers_read": False,
        },
        "source_and_similarity_audit": {
            "private_source_dialogue_count": len(source_identities),
            "private_unique_source_dialogue_count": len(set(source_identities)),
            "selected_unique_source_dialogue_count": len(set(selected_source_identities)),
            "similarity_threshold": similarity["threshold"],
            "similarity_threshold_status": similarity["threshold_status"],
            "compared_pair_count": similarity["compared_pair_count"],
            "exact_pair_count": similarity["exact_pair_count"],
            "near_pair_count": similarity["near_pair_count"],
            "source_group_suggestion_count": len(similarity["source_group_suggestions"]),
            "family_pair_design": "UNSUPPORTED_DO_NOT_INVENT",
        },
        "eligible_feature_ranges": {
            name: {"minimum": low, "maximum": high} for name, (low, high) in ranges.items()
        },
        "selected_feature_coverage": coverage,
        "selected_candidates": selected_rows,
        "candidate_decisions": decisions,
        "decision_reason_counts": dict(sorted(reasons.items())),
        "admission": {
            "gold_approved": False,
            "formal_approval": False,
            "clinical_gold": False,
            "dynamic_scenario_ready": False,
            "clinical_runnable_count": 0,
            "s6_automatic_trust": "BLOCKED",
        },
        "privacy": {
            "contains_patient_text": False,
            "contains_review_reason": False,
            "contains_reviewer_identity": False,
            "contains_source_dialogue_id": False,
            "contains_local_or_library_path": False,
        },
        "limitations": [
            "Structural diversity is not clinical diversity or medical representativeness.",
            "Zero lexical near-duplicate cues at an uncalibrated threshold does not establish independence.",
            "No verified source families or controlled variants are available; none are invented.",
            "Selected exposed candidates remain development material and are not clinically runnable.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--source-review", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--blockers", type=Path, required=True)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        _require(not args.out.exists(), "output must be new; refusing overwrite")
        source_digest = hashlib.sha256(args.source_review.read_bytes()).hexdigest()
        _require(source_digest == args.expected_source_sha256, "source review SHA-256 mismatch")
        review_bytes = args.review.read_bytes()
        result = build_development_selection(
            _read(args.original), json.loads(review_bytes), _read(args.blockers),
            source_digest, hashlib.sha256(review_bytes).hexdigest(), args.count,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(_json(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"candidate selection failed: {exc}\n")
    print(_json({
        "completed": True,
        "selected_count": result["validation"]["selected_count"],
        "clinical_runnable_count": 0,
        "gold_approved": False,
        "clinical_gold": False,
        "s6_automatic_trust": "BLOCKED",
    }))


if __name__ == "__main__":
    main()
