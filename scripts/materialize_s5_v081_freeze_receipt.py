#!/usr/bin/env python3
"""Materialize the S5 v0.8.1 freeze receipt only from canonical main.

The script validates authority and candidate bytes before writing a receipt. It
does not grant gold approval, release S5, or create any next-fresh assets.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ATTESTATION = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.8.1.json"
CONTROL_PLANE = ROOT / "medical/stage-evals/S5/control-plane-readiness-v0.8.1.json"
CONTROL_PLANE_VERIFIER = ROOT / "scripts/verify_s5_v081_control_plane_readiness.py"
RECEIPT_REL = "medical/stage-evals/S5/freeze-receipt-v0.8.1.json"
NEXT_FRESH_ROOT_REL = "medical/stage-evals/S5/fresh-lineage-v0.9"
EXPECTED_ATTESTATION_BLOB = "f7ecf1663adebeb7b81eaa681ca142b1f749f833"
GENERATOR_VERSION = "s5-freeze-receipt-v0.3"
EXPECTED_PR = 4
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
APPROVAL_RE = re.compile(r"^user-approval:[A-Za-z0-9._:/#-]{8,}$")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def verify_current_control_plane() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        spec = importlib.util.spec_from_file_location("s5_control_plane_verifier", CONTROL_PLANE_VERIFIER)
        if spec is None or spec.loader is None:
            return None, None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = load_json(CONTROL_PLANE)
        result = module.verify(CONTROL_PLANE)
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None
    return manifest, result


def build_receipt(freeze_commit: str, approval_reference: str) -> tuple[dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    if not COMMIT_RE.fullmatch(freeze_commit):
        failures.append("FREEZE_COMMIT_INVALID")
    if not APPROVAL_RE.fullmatch(approval_reference):
        failures.append("APPROVAL_REFERENCE_INVALID")
    if failures:
        return None, failures

    try:
        attestation_bytes = ATTESTATION.read_bytes()
    except OSError:
        return None, ["CURRENT_ATTESTATION_UNAVAILABLE"]
    if git_blob_sha1(attestation_bytes) != EXPECTED_ATTESTATION_BLOB:
        return None, ["CURRENT_ATTESTATION_BLOB_MISMATCH"]

    control_plane, control_check = verify_current_control_plane()
    if control_plane is None or control_check is None:
        return None, ["CURRENT_CONTROL_PLANE_UNAVAILABLE"]
    if control_check.get("verification_gate") != "PASS":
        return None, ["CURRENT_CONTROL_PLANE_NOT_READY"]
    control_plane_blob = str(control_check["manifest_git_blob_sha1"])

    if git("cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
        return None, ["FREEZE_COMMIT_UNAVAILABLE"]
    canonical = git("rev-parse", "origin/main")
    if canonical.returncode != 0:
        return None, ["CANONICAL_MAIN_UNAVAILABLE"]
    canonical_sha = canonical.stdout.strip()
    if freeze_commit != canonical_sha:
        failures.append("FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP")
    if git("merge-base", "--is-ancestor", freeze_commit, "origin/main").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN")
    if git("cat-file", "-e", f"{freeze_commit}:{RECEIPT_REL}").returncode == 0:
        failures.append("RECEIPT_PREEXISTED_AT_FREEZE")
    if git("cat-file", "-e", f"{freeze_commit}:{NEXT_FRESH_ROOT_REL}").returncode == 0:
        failures.append("NEXT_FRESH_ASSETS_PREEXISTED_AT_FREEZE")

    observed_attestation = git("rev-parse", f"{freeze_commit}:{ATTESTATION.relative_to(ROOT)}")
    if observed_attestation.returncode != 0 or observed_attestation.stdout.strip() != EXPECTED_ATTESTATION_BLOB:
        failures.append("ATTESTATION_PIN_MISMATCH")

    observed_control_plane = git("rev-parse", f"{freeze_commit}:{CONTROL_PLANE.relative_to(ROOT)}")
    if observed_control_plane.returncode != 0 or observed_control_plane.stdout.strip() != control_plane_blob:
        failures.append("CONTROL_PLANE_ATTESTATION_PIN_MISMATCH")

    attestation = json.loads(attestation_bytes.decode("utf-8"))
    verified_count = 0
    for row in attestation.get("pinned_artifacts", []):
        rel = str(row.get("path") or "")
        observed = git("rev-parse", f"{freeze_commit}:{rel}")
        if observed.returncode != 0 or observed.stdout.strip() != row.get("git_blob_sha1"):
            failures.append(f"FREEZE_ARTIFACT_MISMATCH:{rel}")
        else:
            verified_count += 1

    control_verified_count = 0
    for row in control_plane.get("pinned_control_plane_artifacts", []):
        rel = str(row.get("path") or "")
        observed = git("rev-parse", f"{freeze_commit}:{rel}")
        if observed.returncode != 0 or observed.stdout.strip() != row.get("git_blob_sha1"):
            failures.append(f"FREEZE_CONTROL_PLANE_ARTIFACT_MISMATCH:{rel}")
        else:
            control_verified_count += 1

    tree = git("show", "-s", "--format=%T", freeze_commit)
    if tree.returncode != 0:
        failures.append("FREEZE_TREE_UNAVAILABLE")
    if failures:
        return None, failures

    pinned_count = len(attestation.get("pinned_artifacts", []))
    control_pinned_count = len(control_plane.get("pinned_control_plane_artifacts", []))
    return {
        "stage": "S5",
        "version": "v0.8.1",
        "receipt_type": "canonical_freeze_receipt",
        "generator_version": GENERATOR_VERSION,
        "candidate_frozen": True,
        "control_plane_frozen": True,
        "merged_pr": EXPECTED_PR,
        "explicit_merge_approval": True,
        "approval_reference": approval_reference,
        "attestation_git_blob_sha1": EXPECTED_ATTESTATION_BLOB,
        "control_plane_attestation_git_blob_sha1": control_plane_blob,
        "freeze_commit": freeze_commit,
        "freeze_tree_sha": tree.stdout.strip(),
        "pinned_artifact_count": pinned_count,
        "verified_artifact_count": verified_count,
        "control_plane_pinned_artifact_count": control_pinned_count,
        "control_plane_verified_artifact_count": control_verified_count,
        "freeze_receipt_absent_at_freeze": True,
        "next_fresh_assets_absent_at_freeze": True,
        "fresh_evidence": False,
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_step": "Run the next-fresh admission guard, then author v0.9 only after it allows authoring.",
    }, []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt, failures = build_receipt(args.freeze_commit, args.approval_reference)
    if failures:
        print(json.dumps({
            "receipt_written": False,
            "failures": failures,
            "bounded_release": "BLOCKED_NEXT_FRESH",
            "stage_release": "BLOCKED_GOLD_REVIEW",
            "s6_automatic_trust": "BLOCKED",
        }, ensure_ascii=False, indent=2))
        return 1
    assert receipt is not None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
