#!/usr/bin/env python3
"""Fail-closed validation for quarantined interview-derived candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_TRUST_STATUS = "UNVERIFIED_INTERVIEW_MATERIAL"
EXPECTED_RELEASE_STATUS = "QUARANTINED_CANDIDATE_ONLY"
REQUIRED_PROHIBITIONS = {
    "medical_truth",
    "gold_answer",
    "knowledge_graph_ingest",
    "training_export",
    "clinical_advice",
    "heldout_or_regression_split",
}
FORBIDDEN_PAYLOAD_KEYS = {
    "answer",
    "source_answer",
    "gold_answer",
    "reference_answer",
    "expected_behavior",
    "evidence_snapshot",
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(payload)
    return rows


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(walk_keys(item))
    return keys


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_candidate(row: dict[str, Any], errors: list[str], label: str) -> None:
    trust = row.get("trust") or {}
    triage = row.get("triage") or {}
    require(row.get("release_status") == EXPECTED_RELEASE_STATUS, f"{label}: release status", errors)
    require(trust.get("status") == EXPECTED_TRUST_STATUS, f"{label}: trust status", errors)
    for field in (
        "externally_verified",
        "eligible_for_trust_root",
        "eligible_for_knowledge_graph",
        "eligible_for_training_export",
    ):
        require(trust.get(field) is False, f"{label}: {field} must be false", errors)
    require(bool(str(row.get("question") or "").strip()), f"{label}: empty question", errors)
    require(triage.get("premise_verification_required") is True, f"{label}: premise verification", errors)
    require(
        REQUIRED_PROHIBITIONS.issubset(set(row.get("prohibited_uses") or [])),
        f"{label}: missing prohibition",
        errors,
    )
    forbidden = walk_keys(row) & FORBIDDEN_PAYLOAD_KEYS
    require(not forbidden, f"{label}: forbidden payload keys {sorted(forbidden)}", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("medical/user-tasks/candidate-corpora/interview-material-v0.1"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    corpus = args.corpus_dir.resolve()
    repo_root = args.repo_root.resolve()
    errors: list[str] = []

    manifest = read_json(corpus / "source-manifest.json")
    inventory = read_jsonl(corpus / "all-question-inventory.jsonl")
    candidates = read_jsonl(corpus / "user-question-candidates.jsonl")
    eval_seeds = read_jsonl(corpus / "evaluation-seeds.jsonl")
    risk_seeds = read_jsonl(corpus / "unsafe-answer-risk-seeds.jsonl")
    priority_queue = read_jsonl(corpus / "priority-review-queue.jsonl")

    for field in (
        "source_files_committed",
        "answer_text_committed",
        "eligible_for_trust_root",
        "eligible_for_knowledge_graph",
        "eligible_for_training_export",
    ):
        require(manifest.get(field) is False, f"manifest: {field} must be false", errors)
    require(manifest.get("trust_status") == EXPECTED_TRUST_STATUS, "manifest: trust status", errors)
    require(not list(corpus.glob("*.docx")), "raw DOCX source must not be committed", errors)

    ids = [str(row.get("candidate_id") or "") for row in inventory]
    require(len(ids) == len(set(ids)), "inventory: duplicate candidate_id", errors)
    questions = [str(row.get("question") or "") for row in inventory]
    require(len(questions) == len(set(questions)), "inventory: duplicate question text", errors)
    for row in inventory:
        validate_candidate(row, errors, f"inventory/{row.get('candidate_id')}")

    candidate_ids = {row["candidate_id"] for row in candidates}
    inventory_ids = {row["candidate_id"] for row in inventory}
    retained_ids = {
        row["candidate_id"]
        for row in inventory
        if row.get("triage", {}).get("disposition") == "retain_as_candidate"
    }
    require(candidate_ids == retained_ids, "candidate output does not match retained inventory", errors)

    for row in candidates:
        require(row["candidate_id"] in inventory_ids, f"orphan candidate {row['candidate_id']}", errors)
        validate_candidate(row, errors, f"candidate/{row['candidate_id']}")

    eval_refs = [str(row.get("derived_from_candidate_id") or "") for row in eval_seeds]
    require(len(eval_refs) == len(set(eval_refs)), "evaluation seeds: duplicate candidate reference", errors)
    require(set(eval_refs) == candidate_ids, "evaluation seeds do not map one-to-one to candidates", errors)
    for row in eval_seeds:
        label = f"eval/{row.get('seed_id')}"
        require(row.get("source_trust_status") == EXPECTED_TRUST_STATUS, f"{label}: trust status", errors)
        require(row.get("release_status") == EXPECTED_RELEASE_STATUS, f"{label}: release status", errors)
        require(row.get("split") is None, f"{label}: split must remain unassigned", errors)
        require(
            REQUIRED_PROHIBITIONS.issubset(set(row.get("prohibited_uses") or [])),
            f"{label}: missing prohibition",
            errors,
        )
        forbidden = walk_keys(row) & FORBIDDEN_PAYLOAD_KEYS
        require(not forbidden, f"{label}: forbidden payload keys {sorted(forbidden)}", errors)

    for row in risk_seeds:
        require(
            row.get("candidate_id") in inventory_ids,
            f"orphan risk seed {row.get('risk_seed_id')}",
            errors,
        )
        require(
            "unsafe_answer_text" not in row,
            f"{row.get('risk_seed_id')}: source answer text imported",
            errors,
        )

    priority_ids = [str(row.get("candidate_id") or "") for row in priority_queue]
    require(len(priority_ids) == len(set(priority_ids)), "priority queue: duplicate candidate", errors)
    require(set(priority_ids).issubset(candidate_ids), "priority queue: non-retained candidate", errors)
    for row in priority_queue:
        require(row.get("release_status") == EXPECTED_RELEASE_STATUS, f"priority/{row.get('candidate_id')}: release status", errors)
        require(row.get("next_action") == "verify_premise_and_attach_authoritative_evidence", f"priority/{row.get('candidate_id')}: unsafe next action", errors)

    expected = manifest.get("outputs") or {}
    require(expected.get("inventory_count") == len(inventory), "manifest inventory count mismatch", errors)
    require(
        expected.get("retained_user_question_candidates") == len(candidates),
        "manifest candidate count mismatch",
        errors,
    )
    require(expected.get("evaluation_seed_count") == len(eval_seeds), "manifest eval count mismatch", errors)
    require(expected.get("risk_seed_count") == len(risk_seeds), "manifest risk count mismatch", errors)
    require(expected.get("priority_review_count") == len(priority_queue), "manifest priority count mismatch", errors)

    quarantine_markers = [
        "candidate-corpora/interview-material-v0.1",
        *(str(source.get("source_id") or "") for source in manifest.get("sources") or []),
    ]
    authority_paths = sorted((repo_root / "medical" / "configs").glob("s5-trust-root*.json"))
    authority_paths += sorted((repo_root / "medical" / "knowledge-base").glob("SOURCE_REGISTRY*.json"))
    for path in authority_paths:
        text = path.read_text(encoding="utf-8")
        for marker in quarantine_markers:
            require(
                marker not in text,
                f"{path}: quarantined corpus entered authority file via {marker}",
                errors,
            )

    summary = {
        "inventory": len(inventory),
        "retained_candidates": len(candidates),
        "evaluation_seeds": len(eval_seeds),
        "unsafe_answer_risk_seeds": len(risk_seeds),
        "priority_review_queue": len(priority_queue),
        "authority_files_checked": len(authority_paths),
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for error in errors:
        print("ERROR", error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
