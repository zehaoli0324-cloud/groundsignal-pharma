#!/usr/bin/env python3
"""Fail-closed validation for the interview-candidate stage promotion pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PILOT_IDS = ["INT-PM-04-02", "INT-PM-04-06", "INT-PM-04-09"]
FORBIDDEN_KEYS = {
    "answer",
    "source_answer",
    "gold_answer",
    "reference_answer",
    "expected_behavior",
    "clinical_advice",
    "scoring_rubric",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    return rows


def all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(all_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(all_keys(item))
    return keys


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    corpus = root / "medical/user-tasks/candidate-corpora/interview-material-v0.1"
    pilot = root / "medical/user-tasks/promotion-pilots/interview-pilot-v0.1"
    candidates = {row["candidate_id"]: row for row in read_jsonl(corpus / "user-question-candidates.jsonl")}
    queue = read_jsonl(corpus / "priority-review-queue.jsonl")
    records = read_jsonl(pilot / "promotion-records.jsonl")
    errors: list[str] = []

    require([row.get("candidate_id") for row in records] == PILOT_IDS, "pilot id/order mismatch", errors)
    require([row.get("candidate_id") for row in queue[:3]] == PILOT_IDS, "priority queue drift", errors)
    require(len(records) == len(PILOT_IDS), "pilot record count", errors)

    for row in records:
        candidate_id = str(row.get("candidate_id") or "")
        source = candidates.get(candidate_id)
        label = f"pilot/{candidate_id}"
        require(source is not None, f"{label}: missing quarantined source", errors)
        if source is not None:
            require(row.get("question") == source.get("question"), f"{label}: question drift", errors)
            require(source.get("trust", {}).get("status") == "UNVERIFIED_INTERVIEW_MATERIAL", f"{label}: source trust", errors)
        require(row.get("source_trust_status") == "UNVERIFIED_INTERVIEW_MATERIAL", f"{label}: pilot trust", errors)
        require(not (all_keys(row) & FORBIDDEN_KEYS), f"{label}: answer/eval payload present", errors)

        stages = row.get("stage_progress") or {}
        require(stages.get("S1", {}).get("status") == "CANDIDATE_ACCEPTED_FOR_DISCOVERY", f"{label}: S1", errors)
        require(stages.get("S1", {}).get("real_user_validation") is False, f"{label}: real-user claim", errors)
        require(stages.get("S2", {}).get("status") == "ROUTE_PLAN_DEFINED", f"{label}: S2", errors)
        require(stages.get("S2", {}).get("retrieval_completed") is False, f"{label}: retrieval claim", errors)
        require(len(stages.get("S2", {}).get("source_routes") or []) >= 4, f"{label}: source routes", errors)
        require(stages.get("S3", {}).get("status") == "BLOCKED_NO_FROZEN_EVIDENCE", f"{label}: S3", errors)
        require(stages.get("S3", {}).get("evidence_snapshot_frozen") is False, f"{label}: frozen evidence claim", errors)
        require(stages.get("S4", {}).get("eligible_for_knowledge_graph") is False, f"{label}: S4 eligibility", errors)
        require(stages.get("S5", {}).get("status") == "EVALUATION_DESIGN_DRAFT_ONLY", f"{label}: S5", errors)
        require(stages.get("S5", {}).get("benchmark_split") is None, f"{label}: benchmark split", errors)
        require(stages.get("S5", {}).get("gold_approved") is False, f"{label}: gold claim", errors)
        require(stages.get("S5", {}).get("training_export_eligible") is False, f"{label}: training export", errors)
        require(stages.get("S6_PLUS", {}).get("automatic_use") is False, f"{label}: downstream use", errors)

    markers = ["promotion-pilots/interview-pilot-v0.1", *PILOT_IDS]
    authority_paths = sorted((root / "medical/configs").glob("s5-trust-root*.json"))
    authority_paths += sorted((root / "medical/knowledge-base").glob("SOURCE_REGISTRY*.json"))
    for path in authority_paths:
        content = path.read_text(encoding="utf-8")
        for marker in markers:
            require(marker not in content, f"{path}: pilot entered authority via {marker}", errors)

    result = {
        "pilot_version": "interview-promotion-pilot-v0.1",
        "records": len(records),
        "candidate_links_verified": sum(row.get("candidate_id") in candidates for row in records),
        "route_plans_defined": sum(bool(row.get("stage_progress", {}).get("S2", {}).get("source_routes")) for row in records),
        "evidence_snapshots_frozen": 0,
        "gold_approved_count": 0,
        "knowledge_graph_eligible_count": 0,
        "training_export_eligible_count": sum(
            row.get("stage_progress", {}).get("S5", {}).get("training_export_eligible") is True
            for row in records
        ),
        "authority_files_checked": len(authority_paths),
        "validation_gate": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
