#!/usr/bin/env python3
"""Verify the S5 v0.8.1 pre-freeze control-plane attestation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "medical/stage-evals/S5/control-plane-readiness-v0.8.1.json"

EXPECTED_PATHS = {
    "scripts/check_s5_next_fresh_admission.py",
    "scripts/test_s5_next_fresh_admission.py",
    "scripts/materialize_s5_v081_freeze_receipt.py",
    "scripts/test_s5_v081_freeze_receipt_materializer.py",
    "scripts/verify_s5_v081_control_plane_readiness.py",
    "medical/stage-evals/S5/next-fresh-admission-v0.9.json",
    "medical/stage-evals/S5/next-fresh-admission-adversarial-tests-v0.9.json",
    "medical/stage-evals/S5/freeze-receipt-materializer-tests-v0.8.1.json",
    "medical/stage-evals/S5/freeze-readiness-v0.8.1.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def verify(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    failures: list[str] = []
    rows = manifest.get("pinned_control_plane_artifacts", [])
    paths = [str(row.get("path") or "") for row in rows]
    if len(paths) != len(set(paths)):
        failures.append("DUPLICATE_PINNED_PATH")
    missing = sorted(EXPECTED_PATHS - set(paths))
    extra = sorted(set(paths) - EXPECTED_PATHS)
    if missing:
        failures.append("MISSING_REQUIRED_PIN:" + ",".join(missing))
    if extra:
        failures.append("UNREVIEWED_EXTRA_PIN:" + ",".join(extra))

    verified: list[dict[str, Any]] = []
    for row in rows:
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

    boundary_checks = {
        "scope_is_s5_v081": manifest.get("stage") == "S5" and manifest.get("version") == "v0.8.1",
        "not_fresh_evidence": manifest.get("fresh_evidence") is False,
        "control_plane_not_frozen": (
            manifest.get("control_plane_frozen") is False
            and manifest.get("freeze_commit") is None
        ),
        "candidate_not_frozen": manifest.get("candidate_frozen") is False,
        "canonical_receipt_absent": manifest.get("canonical_freeze_receipt_present") is False,
        "next_fresh_blocked": manifest.get("next_fresh_authoring") == "BLOCKED_NOT_FROZEN",
        "gold_not_approved": manifest.get("gold_approved") is False,
        "bounded_release_blocked": manifest.get("bounded_release") == "BLOCKED_NEXT_FRESH",
        "stage_release_blocked": manifest.get("stage_release") == "BLOCKED_GOLD_REVIEW",
        "s6_blocked": manifest.get("s6_automatic_trust") == "BLOCKED",
    }
    failures.extend(f"BOUNDARY_FAILURE:{name}" for name, passed in boundary_checks.items() if not passed)

    manifest_bytes = manifest_path.read_bytes()
    return {
        "stage": "S5",
        "version": "v0.8.1",
        "verification": "pre-freeze-control-plane-readiness",
        "evidence_class": "development_process_integrity_attestation",
        "fresh_evidence": False,
        "manifest_git_blob_sha1": git_blob_sha1(manifest_bytes),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "required_path_count": len(EXPECTED_PATHS),
        "verified_path_count": len(verified),
        "boundary_checks": boundary_checks,
        "failures": failures,
        "verification_gate": "PASS" if not failures else "FAIL",
        "control_plane_status": "READY_FOR_EXPLICIT_FREEZE_DECISION" if not failures else "NOT_READY",
        "control_plane_frozen": False,
        "candidate_frozen": False,
        "canonical_freeze_receipt_present": False,
        "bounded_release": "BLOCKED_NEXT_FRESH",
        "stage_release": "BLOCKED_GOLD_REVIEW",
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
