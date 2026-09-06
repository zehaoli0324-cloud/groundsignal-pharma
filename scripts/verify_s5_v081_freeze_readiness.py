#!/usr/bin/env python3
"""Verify the S5 v0.8.1 pre-freeze attestation without granting release."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.8.1.json"

EXPECTED_PATHS = {
    "requirements-s5-lineage-calibration.txt",
    "scripts/s5_lineage_detector_v073.py",
    "scripts/s5_lineage_detector_v081.py",
    "scripts/s5_trust_policy_v071.py",
    "scripts/s5_trust_policy_v073.py",
    "scripts/s5_trust_policy.py",
    "scripts/export_training_data_v061.py",
    "scripts/export_training_data_v073.py",
    "scripts/export_training_data.py",
    "scripts/calibrate_s5_lineage_v073.py",
    "scripts/calibrate_s5_lineage_v081.py",
    "scripts/calibrate_s5_lineage_v081_matrix.py",
    "scripts/eval_s5_boundary_regression_v073.py",
    "scripts/eval_s5_boundary_regression_v081.py",
    "scripts/s5_release_gate.py",
    "medical/stage-evals/S5/calibration-v0.7.3.json",
    "medical/stage-evals/S5/regression-v0.7.3.json",
    "medical/stage-evals/S5/calibration-v0.8.1.json",
    "medical/stage-evals/S5/calibration-matrix-v0.8.1.json",
    "medical/stage-evals/S5/regression-v0.8.1.json",
    "medical/stage-evals/S5/fresh-first-observation-v0.8.json",
    "medical/stage-evals/S5/release-gate-v0.1.1.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def verify(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    failures: list[str] = []
    paths = [str(row.get("path")) for row in manifest.get("pinned_artifacts", [])]
    if len(paths) != len(set(paths)):
        failures.append("DUPLICATE_PINNED_PATH")
    missing_contract = sorted(EXPECTED_PATHS - set(paths))
    extra_contract = sorted(set(paths) - EXPECTED_PATHS)
    if missing_contract:
        failures.append("MISSING_REQUIRED_PIN:" + ",".join(missing_contract))
    if extra_contract:
        failures.append("UNREVIEWED_EXTRA_PIN:" + ",".join(extra_contract))

    verified: list[dict[str, Any]] = []
    for row in manifest.get("pinned_artifacts", []):
        rel = str(row.get("path") or "")
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING_FILE:{rel}")
            continue
        data = path.read_bytes()
        observed = {
            "path": rel,
            "size_bytes": len(data),
            "git_blob_sha1": git_blob_sha1(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        verified.append(observed)
        for key in ("size_bytes", "git_blob_sha1", "sha256"):
            if observed[key] != row.get(key):
                failures.append(f"PIN_MISMATCH:{rel}:{key}")

    calibration = load_json(ROOT / "medical/stage-evals/S5/calibration-v0.8.1.json")
    matrix = load_json(ROOT / "medical/stage-evals/S5/calibration-matrix-v0.8.1.json")
    regression = load_json(ROOT / "medical/stage-evals/S5/regression-v0.8.1.json")
    first_obs = load_json(ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.8.json")
    gold = load_json(ROOT / "medical/stage-evals/S5/release-gate-v0.1.1.json")

    checks = {
        "attestation_is_not_fresh": manifest.get("fresh_evidence") is False,
        "candidate_not_yet_frozen": manifest.get("candidate_frozen") is False and manifest.get("freeze_commit") is None,
        "calibration_pass_not_fresh": calibration.get("selection_gate") == "PASS" and calibration.get("fresh_evidence") is False,
        "matrix_pass_not_fresh": matrix.get("selection_gate") == "PASS" and matrix.get("fresh_evidence") is False,
        "matrix_attack_rate": matrix.get("metrics", {}).get("cross_language_block_rate") == 1.0,
        "matrix_mosaic_rate": matrix.get("metrics", {}).get("mosaic_reasoned_block_rate") == 1.0,
        "matrix_clean_false_block_rate": matrix.get("metrics", {}).get("clean_false_block_rate") == 0.0,
        "matrix_clean_review_rate": matrix.get("metrics", {}).get("clean_review_rate") == 0.0,
        "regression_pass_not_fresh": regression.get("regression_gate") == "PASS" and regression.get("fresh_evidence") is False,
        "v08_fresh_fail_preserved": first_obs.get("fresh_evidence") is True and first_obs.get("first_observation") is True and first_obs.get("hard_gate_failures") == ["S5-F28", "S5-F31"],
        "gold_incomplete": gold.get("gold_approved_count") == 0 and gold.get("pending_gold_count") == 12 and gold.get("release_ready") is False,
        "release_blocked": all(item.get("stage_release") == "BLOCKED_GOLD_REVIEW" for item in (manifest, calibration, matrix, regression, first_obs)),
        "s6_blocked": all(item.get("s6_automatic_trust") == "BLOCKED" for item in (manifest, calibration, matrix, regression, first_obs)),
    }
    failures.extend(f"GATE_FAILURE:{name}" for name, passed in checks.items() if not passed)

    manifest_bytes = manifest_path.read_bytes()
    result = {
        "stage": "S5",
        "version": "v0.8.1",
        "verification": "pre-freeze-readiness",
        "evidence_class": "development_exposed_attestation_verification",
        "fresh_evidence": False,
        "manifest_git_blob_sha1": git_blob_sha1(manifest_bytes),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "required_path_count": len(EXPECTED_PATHS),
        "verified_path_count": len(verified),
        "checks": checks,
        "failures": failures,
        "verification_gate": "PASS" if not failures else "FAIL",
        "candidate_status": "READY_FOR_EXPLICIT_FREEZE_DECISION" if not failures else "NOT_READY",
        "candidate_frozen": False,
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_step": "Materialize a freeze commit only after explicit merge approval; then author a new independent fresh suite.",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verification_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
