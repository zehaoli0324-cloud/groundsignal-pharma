#!/usr/bin/env python3
"""Generate the pre-freeze v0.9.1 control-plane attestation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED_PATHS = (
    "scripts/s5_v091_freeze_control.py",
    "scripts/materialize_s5_v091_freeze_receipt.py",
    "scripts/check_s5_v10_fresh_admission.py",
    "scripts/test_s5_v091_freeze_control.py",
    "scripts/generate_s5_v091_control_plane_readiness.py",
    "scripts/verify_s5_v091_control_plane_readiness.py",
    "medical/stage-evals/S5/freeze-readiness-v0.9.1.json",
    "medical/stage-evals/S5/freeze-readiness-check-v0.9.1.json",
)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def pin(rel: str) -> dict:
    data = (ROOT / rel).read_bytes()
    return {"path": rel, "size_bytes": len(data), "git_blob_sha1": git_blob_sha1(data), "sha256": hashlib.sha256(data).hexdigest()}


def build() -> dict:
    return {
        "stage": "S5",
        "version": "v0.9.1",
        "attestation": "pre-freeze-control-plane-readiness",
        "evidence_class": "development_process_integrity_attestation",
        "fresh_evidence": False,
        "first_observation": False,
        "control_plane_frozen": False,
        "candidate_frozen": False,
        "freeze_commit": None,
        "canonical_freeze_receipt_present": False,
        "next_fresh_authoring": "BLOCKED_NOT_FROZEN",
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "pinned_control_plane_artifact_count": len(PINNED_PATHS),
        "pinned_control_plane_artifacts": [pin(path) for path in PINNED_PATHS],
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
