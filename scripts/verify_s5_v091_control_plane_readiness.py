#!/usr/bin/env python3
"""Verify the v0.9.1 pre-freeze control-plane attestation."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "medical/stage-evals/S5/control-plane-readiness-v0.9.1.json"
GENERATOR = ROOT / "scripts/generate_s5_v091_control_plane_readiness.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def expected_paths() -> set[str]:
    spec = importlib.util.spec_from_file_location("s5_v091_control_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.PINNED_PATHS)


def verify(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    expected = expected_paths()
    rows = manifest.get("pinned_control_plane_artifacts") or []
    paths = [str(row.get("path") or "") for row in rows]
    failures: list[str] = []
    if len(paths) != len(set(paths)):
        failures.append("DUPLICATE_PINNED_PATH")
    if expected - set(paths):
        failures.append("MISSING_REQUIRED_PIN:" + ",".join(sorted(expected - set(paths))))
    if set(paths) - expected:
        failures.append("UNREVIEWED_EXTRA_PIN:" + ",".join(sorted(set(paths) - expected)))
    if manifest.get("pinned_control_plane_artifact_count") != len(expected):
        failures.append("PINNED_ARTIFACT_COUNT_MISMATCH")
    verified = 0
    for row in rows:
        rel = str(row.get("path") or "")
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING_FILE:{rel}")
            continue
        data = path.read_bytes()
        observed = {"size_bytes": len(data), "git_blob_sha1": git_blob_sha1(data), "sha256": hashlib.sha256(data).hexdigest()}
        for key, value in observed.items():
            if row.get(key) != value:
                failures.append(f"PIN_MISMATCH:{rel}:{key}")
        verified += 1
    checks = {
        "scope": manifest.get("stage") == "S5" and manifest.get("version") == "v0.9.1",
        "not_fresh": manifest.get("fresh_evidence") is False and manifest.get("first_observation") is False,
        "not_frozen": manifest.get("candidate_frozen") is False and manifest.get("control_plane_frozen") is False and manifest.get("freeze_commit") is None,
        "receipt_absent": manifest.get("canonical_freeze_receipt_present") is False,
        "authoring_blocked": manifest.get("next_fresh_authoring") == "BLOCKED_NOT_FROZEN",
        "gold_false": manifest.get("gold_approved") is False,
        "release_blocked": manifest.get("bounded_release") == "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW" and manifest.get("stage_release") == "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_blocked": manifest.get("s6_automatic_trust") == "BLOCKED",
    }
    failures.extend(f"BOUNDARY_FAILURE:{key}" for key, passed in checks.items() if not passed)
    data = manifest_path.read_bytes()
    return {
        "stage": "S5",
        "version": "v0.9.1",
        "verification": "pre-freeze-control-plane-readiness",
        "evidence_class": "development_process_integrity_attestation_verification",
        "fresh_evidence": False,
        "first_observation": False,
        "manifest_git_blob_sha1": git_blob_sha1(data),
        "manifest_sha256": hashlib.sha256(data).hexdigest(),
        "required_path_count": len(expected),
        "verified_path_count": verified,
        "boundary_checks": checks,
        "failures": failures,
        "verification_gate": "PASS" if not failures else "FAIL",
        "control_plane_status": "READY_FOR_EXPLICIT_FREEZE_DECISION" if not failures else "NOT_READY",
        "control_plane_frozen": False,
        "candidate_frozen": False,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
    }


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
