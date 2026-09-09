"""Build a text-free blocker queue from a validated private candidate review.

The input review may contain patient text and reviewer-authored prose. This
module deliberately exports only bounded identifiers, enumerated blocker codes
and aggregate counts. It never grants case admission or clinical approval.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from .candidate_review import _read, validate_review


SCHEMA_VERSION = "candidate-blocker-queue/v0.1"
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SELECTION_BLOCKERS = {
    "PRIVACY_REVIEW_REQUIRED",
    "COMPLETENESS_NOT_USABLE",
    "NO_INCLUDED_FACTS",
    "FACT_DECISION_UNCERTAIN",
    "FACT_POLARITY_CONFLICT",
}
_AUTHORING_BLOCKERS = _SELECTION_BLOCKERS | {"CORRECTION_RELATION_ADJUDICATION"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _safe_id(value, label):
    _require(isinstance(value, str) and _SAFE_ID.fullmatch(value), label + " is not a bounded public identifier")
    return value


def _blocker(code, entry_id, field, resolution_class, required_role, blocks):
    return {
        "code": code,
        "evidence_location": {"entry_id": _safe_id(entry_id, "entry_id"), "field": field},
        "automatic_fix": False,
        "resolution_class": resolution_class,
        "required_role": required_role,
        "blocks": blocks,
    }


def _candidate_blockers(item):
    review = item["review"]
    blockers = []
    privacy = review["privacy"]["decision"]
    if privacy != "reviewed_no_identifiers":
        blockers.append(_blocker(
            "PRIVACY_REVIEW_REQUIRED", "privacy", "review.privacy.decision",
            "human_privacy_review", "privacy_reviewer",
            ["candidate_selection", "dynamic_authoring", "clinical_runnable"],
        ))
    completeness = review["completeness"]["decision"]
    if completeness != "usable":
        blockers.append(_blocker(
            "COMPLETENESS_NOT_USABLE", "completeness", "review.completeness.decision",
            "human_source_review", "source_data_reviewer",
            ["candidate_selection", "dynamic_authoring", "clinical_runnable"],
        ))
    included = [fact for fact in review["facts"] if fact["decision"] == "include"]
    if not included:
        blockers.append(_blocker(
            "NO_INCLUDED_FACTS", "facts", "review.facts.decision",
            "human_source_review", "source_data_reviewer",
            ["candidate_selection", "dynamic_authoring", "clinical_runnable"],
        ))
    for fact in review["facts"]:
        fact_id = _safe_id(fact["fact_id"], "fact_id")
        if fact["decision"] == "uncertain":
            blockers.append(_blocker(
                "FACT_DECISION_UNCERTAIN", fact_id, "review.facts.decision",
                "clinical_semantic_adjudication", "qualified_clinical_reviewer",
                ["candidate_selection", "dynamic_authoring", "clinical_runnable"],
            ))
        if fact["decision"] == "include" and fact["polarity"] == "conflict":
            blockers.append(_blocker(
                "FACT_POLARITY_CONFLICT", fact_id, "review.facts.polarity",
                "clinical_semantic_adjudication", "qualified_clinical_reviewer",
                ["candidate_selection", "dynamic_authoring", "clinical_runnable"],
            ))
        if fact["correction_of_candidate_id"] is not None:
            blockers.append(_blocker(
                "CORRECTION_RELATION_ADJUDICATION", fact_id,
                "review.facts.correction_of_candidate_id",
                "clinical_semantic_adjudication", "qualified_clinical_reviewer",
                ["dynamic_authoring", "clinical_runnable"],
            ))
    for rubric in review["rubrics"]:
        if rubric["kind"] != "clinical" or not rubric["critical"]:
            continue
        criterion_id = _safe_id(rubric["criterion_id"], "criterion_id")
        suffix = {
            "drafted": "ADJUDICATION",
            "excluded": "EXCLUSION_ADJUDICATION",
            "unreviewed": "UNREVIEWED",
        }[rubric["decision"]]
        blockers.append(_blocker(
            "CLINICAL_RUBRIC_" + suffix, criterion_id, "review.rubrics.decision",
            "qualified_clinical_adjudication", "qualified_clinical_reviewer",
            ["clinical_runnable"],
        ))
    return blockers


def build_public_blocker_queue(original, review, source_review_sha256, review_file_sha256):
    """Validate private inputs and return only a bounded public projection."""
    _require(re.fullmatch(r"[0-9a-f]{64}", source_review_sha256 or ""), "invalid source review SHA-256")
    _require(re.fullmatch(r"[0-9a-f]{64}", review_file_sha256 or ""), "invalid canonical review SHA-256")
    validation = validate_review(original, review)
    _require(validation["structurally_valid"] is True, "review is not structurally valid")
    _require(all(review.get(flag) is False for flag in (
        "formal_approval", "clinical_gold", "dynamic_scenario_ready")),
        "review unexpectedly claims admission")

    candidates = []
    codes = Counter()
    resolution_classes = Counter()
    candidate_ids = set()
    for item in review["items"]:
        candidate_id = _safe_id(item["candidate_id"], "candidate_id")
        _require(candidate_id not in candidate_ids, "duplicate candidate_id")
        candidate_ids.add(candidate_id)
        blockers = _candidate_blockers(item)
        codes.update(row["code"] for row in blockers)
        resolution_classes.update(row["resolution_class"] for row in blockers)
        blocker_codes = {row["code"] for row in blockers}
        candidates.append({
            "candidate_id": candidate_id,
            "development_exposed": True,
            "states": {
                "candidate_selection": "BLOCKED" if blocker_codes & _SELECTION_BLOCKERS else "READY",
                "dynamic_authoring": "BLOCKED" if blocker_codes & _AUTHORING_BLOCKERS else "READY",
                "clinical_runnable": "BLOCKED",
            },
            "blockers": blockers,
        })

    state_counts = {}
    for stage in ("candidate_selection", "dynamic_authoring", "clinical_runnable"):
        state_counts[stage] = dict(Counter(row["states"][stage] for row in candidates))
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "development_only",
        "development_exposed": True,
        "source_review_sha256": source_review_sha256,
        "canonical_review_sha256": review_file_sha256,
        "packet_sha256": original["packet_sha256"],
        "validation": {
            "official_contract": "PASS",
            "candidate_count": validation["counts"]["candidates"],
            "facts_decided": validation["counts"]["facts_decided"],
            "facts_missing": validation["counts"]["facts_missing"],
            "rubrics_decided": validation["counts"]["rubrics_decided"],
            "rubrics_missing": validation["counts"]["rubrics_missing"],
        },
        "admission": {
            "gold_approved": False,
            "formal_approval": False,
            "clinical_gold": False,
            "dynamic_scenario_ready": False,
            "s6_automatic_trust": "BLOCKED",
        },
        "global_blockers": [
            {
                "code": "AI_REVIEW_NOT_CLINICAL_TRUTH",
                "automatic_fix": False,
                "required_role": "independent_human_and_qualified_clinical_review",
                "blocks": ["clinical_runnable"],
            },
            {
                "code": "FORMAL_ADMISSION_NOT_GRANTED",
                "automatic_fix": False,
                "required_role": "authorized_case_admission_workflow",
                "blocks": ["clinical_runnable", "s6_automatic_trust"],
            },
        ],
        "summary": {
            "candidate_count": len(candidates),
            "candidate_state_counts": state_counts,
            "candidate_blocker_count": sum(codes.values()),
            "blocker_code_counts": dict(sorted(codes.items())),
            "observed_feature_counts": {
                "privacy_review_required_candidates": codes.get("PRIVACY_REVIEW_REQUIRED", 0),
                "no_included_fact_candidates": codes.get("NO_INCLUDED_FACTS", 0),
                "uncertain_facts": codes.get("FACT_DECISION_UNCERTAIN", 0),
                "included_conflict_polarities": codes.get("FACT_POLARITY_CONFLICT", 0),
                "correction_relations": codes.get("CORRECTION_RELATION_ADJUDICATION", 0),
                "critical_clinical_rubrics": sum(
                    count for code, count in codes.items() if code.startswith("CLINICAL_RUBRIC_")
                ),
            },
            "resolution_class_counts": dict(sorted(resolution_classes.items())),
            "mechanical_auto_fixable_count": 0,
            "human_or_clinical_resolution_count": sum(codes.values()),
        },
        "candidates": candidates,
        "privacy": {
            "contains_patient_text": False,
            "contains_review_reason": False,
            "contains_reviewer_identity": False,
            "contains_source_dialogue_id": False,
            "contains_local_or_library_path": False,
        },
        "limitations": [
            "Blocker detection is deterministic workflow triage, not medical adjudication.",
            "READY means eligible for the named development step only; it does not mean clinically runnable.",
            "Exposed source-derived candidates are development material, not fresh held-out evidence.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--source-review", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        _require(not args.out.exists(), "output must be new; refusing overwrite")
        source_digest = hashlib.sha256(args.source_review.read_bytes()).hexdigest()
        _require(source_digest == args.expected_source_sha256, "source review SHA-256 mismatch")
        review_bytes = args.review.read_bytes()
        result = build_public_blocker_queue(
            _read(args.original), json.loads(review_bytes), source_digest,
            hashlib.sha256(review_bytes).hexdigest(),
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(_json(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"candidate blocker queue failed: {exc}\n")
    print(_json({
        "completed": True,
        "candidate_count": result["summary"]["candidate_count"],
        "candidate_blocker_count": result["summary"]["candidate_blocker_count"],
        "gold_approved": False,
        "clinical_gold": False,
        "s6_automatic_trust": "BLOCKED",
    }))


if __name__ == "__main__":
    main()
