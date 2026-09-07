#!/usr/bin/env python3
"""Generate the S5 v0.9.1 pre-freeze candidate attestation.

This records development/exposed evidence only. It never declares the candidate
frozen, creates fresh assets, or grants Gold/release status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_COMMIT = "1b722744545c9da34d086422be03489e35169548"
CANDIDATE_TREE = "63f984bb2b7738a98936dd0f34c65814527fdefe"
V09_FIRST_BLOB = "522c8f4ed39293d2ea01c81f48ffacc1d1ef4340"
V09_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.9"

PINNED_PATHS = (
    "requirements-s5-lineage-calibration.txt",
    "scripts/s5_lineage_detector_v073.py",
    "scripts/s5_lineage_detector_v081.py",
    "scripts/s5_lineage_detector_v091.py",
    "scripts/s5_trust_policy_v071.py",
    "scripts/s5_trust_policy_v091.py",
    "scripts/export_training_data_v061.py",
    "scripts/export_training_data_v091.py",
    "scripts/calibrate_s5_lineage_v073.py",
    "scripts/calibrate_s5_lineage_v081_matrix.py",
    "scripts/eval_s5_boundary_regression_v073.py",
    "scripts/eval_s5_boundary_regression_v081.py",
    "scripts/eval_s5_boundary_regression_v091.py",
    "scripts/eval_s5_fresh_lineage_v09.py",
    "scripts/s5_release_gate.py",
    "medical/configs/s5-trust-root-v0.4.1.json",
    "medical/configs/s5-trust-policy-registry-v0.4.1.json",
    "medical/stage-evals/S5/calibration-v0.7.3.json",
    "medical/stage-evals/S5/regression-v0.7.3.json",
    "medical/stage-evals/S5/calibration-matrix-v0.8.1.json",
    "medical/stage-evals/S5/regression-v0.8.1.json",
    "medical/stage-evals/S5/fresh-first-observation-v0.9.json",
    "medical/stage-evals/S5/receipt-publication-equivalence-v0.9.json",
    "medical/stage-evals/S5/regression-v0.9.1.json",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def pin(path: str) -> dict[str, Any]:
    data = (ROOT / path).read_bytes()
    return {
        "path": path,
        "size_bytes": len(data),
        "git_blob_sha1": git_blob_sha1(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def fresh_asset_contract(first: dict[str, Any]) -> dict[str, Any]:
    expected = first.get("fresh_asset_sha256") or {}
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in V09_ROOT.rglob("*.json")
    }
    if actual_paths != set(expected):
        raise ValueError("v0.9 fresh asset path set does not match immutable observation")
    rows: list[str] = []
    for rel, digest in sorted(expected.items()):
        observed = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if observed != digest:
            raise ValueError(f"v0.9 fresh asset drift: {rel}")
        rows.append(f"{rel}\0{digest}\n")
    aggregate = hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()
    return {
        "source": "medical/stage-evals/S5/fresh-first-observation-v0.9.json",
        "asset_count": len(rows),
        "path_sha256_aggregate": aggregate,
    }


def build() -> dict[str, Any]:
    first_path = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.9.json"
    first = load_json(first_path)
    first_blob = git_blob_sha1(first_path.read_bytes())
    if first_blob != V09_FIRST_BLOB:
        raise ValueError("immutable v0.9 first-observation blob drift")
    return {
        "stage": "S5",
        "version": "v0.9.1",
        "attestation_type": "pre_freeze_readiness",
        "evidence_class": "development_exposed_attestation",
        "fresh_evidence": False,
        "first_observation": False,
        "candidate_frozen": False,
        "freeze_commit": None,
        "candidate_implementation_commit": CANDIDATE_COMMIT,
        "candidate_implementation_tree": CANDIDATE_TREE,
        "candidate_status": "READY_FOR_EXPLICIT_FREEZE_DECISION",
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "immutable_history": {
            "v0.8.1_freeze_commit": "b5dffbe366904a46d3b6a44172a4f1626daa8924",
            "v0.9_receipt_commit": "ffe040b0295e666f96e7dac7099fdb6e5fe8d720",
            "v0.9_authoring_commit": "42f60341e6daf04196118b85ea6895434d2ec02e",
            "v0.9_first_observation_commit": "ebd036f5c2d683b29c8f306f76f5b2de920eaf87",
            "v0.9_first_observation_git_blob_sha1": first_blob,
            "v0.9_first_observation_result": "FAIL",
            "v0.9_hard_gate_failures": ["S5-F32"],
            "v0.9_clean_control_failures": ["CLEAN-NUMERIC-NEAR-NEIGHBOUR"],
        },
        "pinned_artifact_count": len(PINNED_PATHS),
        "pinned_artifacts": [pin(path) for path in PINNED_PATHS],
        "v0.9_fresh_asset_contract": fresh_asset_contract(first),
        "required_gates": {
            "v0.9_first_observation": "FAIL_PRESERVED",
            "v0.9.1_exposed_repair": "PASS_NOT_FRESH",
            "historical_regression": "PASS",
            "gold_review": "INCOMPLETE",
            "bounded_release": "NOT_ESTABLISHED",
            "s6_automatic_trust": "BLOCKED",
        },
        "next_step": "After dependency merges and explicit approval, freeze the exact candidate on canonical main; only then may an independent evaluator author a new fresh suite.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
