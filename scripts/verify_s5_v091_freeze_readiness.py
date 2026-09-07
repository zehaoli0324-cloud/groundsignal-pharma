#!/usr/bin/env python3
"""Verify S5 v0.9.1 pre-freeze readiness without granting freeze or release."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.9.1.json"
GENERATOR = ROOT / "scripts/generate_s5_v091_freeze_readiness.py"
V09_FIRST_BLOB = "522c8f4ed39293d2ea01c81f48ffacc1d1ef4340"


def load_generator():
    spec = importlib.util.spec_from_file_location("s5_v091_readiness_contract", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)


def require(condition: bool, failure: str, failures: list[str]) -> None:
    if not condition:
        failures.append(failure)


def fresh_asset_aggregate(first: dict[str, Any], failures: list[str]) -> tuple[int, str]:
    expected = first.get("fresh_asset_sha256") or {}
    fresh_root = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.9"
    actual = {path.relative_to(ROOT).as_posix() for path in fresh_root.rglob("*.json")}
    require(actual == set(expected), "V09_FRESH_ASSET_PATH_SET_DRIFT", failures)
    rows: list[str] = []
    for rel, digest in sorted(expected.items()):
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"V09_FRESH_ASSET_MISSING:{rel}")
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        require(observed == digest, f"V09_FRESH_ASSET_SHA256_MISMATCH:{rel}", failures)
        rows.append(f"{rel}\0{digest}\n")
    return len(expected), hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def verify(manifest_path: Path) -> dict[str, Any]:
    generator = load_generator()
    expected_paths = set(generator.PINNED_PATHS)
    manifest = load_json(manifest_path)
    failures: list[str] = []
    rows = manifest.get("pinned_artifacts") or []
    paths = [str(row.get("path") or "") for row in rows]
    require(len(paths) == len(set(paths)), "DUPLICATE_PINNED_PATH", failures)
    missing = sorted(expected_paths - set(paths))
    extra = sorted(set(paths) - expected_paths)
    if missing:
        failures.append("MISSING_REQUIRED_PIN:" + ",".join(missing))
    if extra:
        failures.append("UNREVIEWED_EXTRA_PIN:" + ",".join(extra))
    require(manifest.get("pinned_artifact_count") == len(expected_paths), "PINNED_ARTIFACT_COUNT", failures)

    candidate = str(manifest.get("candidate_implementation_commit") or "")
    candidate_tree = str(manifest.get("candidate_implementation_tree") or "")
    commit_available = git("cat-file", "-e", f"{candidate}^{{commit}}").returncode == 0
    require(commit_available, "CANDIDATE_COMMIT_UNAVAILABLE", failures)
    observed_tree = git("rev-parse", f"{candidate}^{{tree}}").stdout.strip() if commit_available else ""
    require(observed_tree == candidate_tree == generator.CANDIDATE_TREE, "CANDIDATE_TREE_MISMATCH", failures)
    require(candidate == generator.CANDIDATE_COMMIT, "CANDIDATE_COMMIT_MISMATCH", failures)
    require(git("merge-base", "--is-ancestor", candidate, "HEAD").returncode == 0, "CANDIDATE_NOT_ANCESTOR_OF_HEAD", failures)

    verified = 0
    for row in rows:
        rel = str(row.get("path") or "")
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING_FILE:{rel}")
            continue
        data = path.read_bytes()
        observed = {
            "size_bytes": len(data),
            "git_blob_sha1": git_blob_sha1(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for key, value in observed.items():
            require(value == row.get(key), f"PIN_MISMATCH:{rel}:{key}", failures)
        if commit_available:
            candidate_blob = git("rev-parse", f"{candidate}:{rel}")
            require(
                candidate_blob.returncode == 0 and candidate_blob.stdout.strip() == row.get("git_blob_sha1"),
                f"CANDIDATE_BLOB_MISMATCH:{rel}",
                failures,
            )
        verified += 1

    first_path = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.9.json"
    first = load_json(first_path)
    regression = load_json(ROOT / "medical/stage-evals/S5/regression-v0.9.1.json")
    gold = load_json(ROOT / "medical/stage-evals/S5/release-gate-v0.1.1.json")
    asset_count, asset_aggregate = fresh_asset_aggregate(first, failures)
    asset_contract = manifest.get("v0.9_fresh_asset_contract") or {}

    checks = {
        "attestation_not_fresh": manifest.get("fresh_evidence") is False and manifest.get("first_observation") is False,
        "candidate_not_frozen": manifest.get("candidate_frozen") is False and manifest.get("freeze_commit") is None,
        "no_gold_claim": manifest.get("gold_approved") is False,
        "release_blocked": manifest.get("bounded_release") == "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW" and manifest.get("stage_release") == "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_blocked": manifest.get("s6_automatic_trust") == "BLOCKED",
        "v09_blob_preserved": git_blob_sha1(first_path.read_bytes()) == V09_FIRST_BLOB,
        "v09_fail_preserved": first.get("fresh_evidence") is True and first.get("first_observation") is True and first.get("fresh_structural_gate") == "FAIL" and first.get("hard_gate_failures") == ["S5-F32"] and first.get("clean_control_failures") == ["CLEAN-NUMERIC-NEAR-NEIGHBOUR"],
        "v09_assets_preserved": asset_count == 18 and asset_contract.get("asset_count") == asset_count and asset_contract.get("path_sha256_aggregate") == asset_aggregate,
        "v091_repair_pass_not_fresh": regression.get("repair_gate") == "PASS" and regression.get("failed_gates") == [] and regression.get("fresh_evidence") is False and regression.get("first_observation") is False,
        "v091_attack_clean_complete": all(row.get("pass") is True for row in regression.get("v09_exposed_attacks", {}).values()) and all(row.get("pass") is True for row in regression.get("v09_exposed_clean_controls", {}).values()),
        "v091_points_to_immutable_fail": regression.get("immutable_v09_first_observation", {}).get("expected_blob") == V09_FIRST_BLOB and regression.get("immutable_v09_first_observation", {}).get("observed_blob") == V09_FIRST_BLOB and regression.get("immutable_v09_first_observation", {}).get("preserved_result") == "FAIL",
        "gold_incomplete": regression.get("gold_approved_count") == 0 and gold.get("gold_approved_count") == 0 and gold.get("release_ready") is False,
        "regression_containment": regression.get("stage_release") == "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW" and regression.get("s6_automatic_trust") == "BLOCKED",
    }
    failures.extend(f"GATE_FAILURE:{name}" for name, passed in checks.items() if not passed)

    manifest_bytes = manifest_path.read_bytes()
    result = {
        "stage": "S5",
        "version": "v0.9.1",
        "verification": "pre-freeze-readiness",
        "evidence_class": "development_exposed_attestation_verification",
        "fresh_evidence": False,
        "first_observation": False,
        "manifest_git_blob_sha1": git_blob_sha1(manifest_bytes),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "required_path_count": len(expected_paths),
        "verified_path_count": verified,
        "v0.9_fresh_asset_count": asset_count,
        "checks": checks,
        "failures": failures,
        "verification_gate": "PASS" if not failures else "FAIL",
        "candidate_status": "READY_FOR_EXPLICIT_FREEZE_DECISION" if not failures else "NOT_READY",
        "candidate_frozen": False,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_step": "Merge dependencies only with explicit approval, then materialize a canonical freeze before any new fresh authoring.",
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
