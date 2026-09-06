#!/usr/bin/env python3
"""Fail closed on S5 v0.9 fresh authoring until v0.8.1 is verifiably frozen."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "medical/stage-evals/S5/freeze-receipt-v0.8.1.json"
DEFAULT_FRESH_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.9"
ATTESTATION = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.8.1.json"
EXPECTED_ATTESTATION_BLOB = "f7ecf1663adebeb7b81eaa681ca142b1f749f833"
EXPECTED_RECEIPT_GENERATOR = "s5-freeze-receipt-v0.1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
APPROVAL_RE = re.compile(r"^user-approval:[A-Za-z0-9._:/#-]{8,}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )


def validate_receipt(receipt: dict[str, Any], attestation: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    freeze_commit = str(receipt.get("freeze_commit") or "")
    if receipt.get("stage") != "S5" or receipt.get("version") != "v0.8.1":
        failures.append("RECEIPT_SCOPE_INVALID")
    if receipt.get("receipt_type") != "canonical_freeze_receipt":
        failures.append("RECEIPT_TYPE_INVALID")
    if receipt.get("generator_version") != EXPECTED_RECEIPT_GENERATOR:
        failures.append("RECEIPT_GENERATOR_INVALID")
    if receipt.get("candidate_frozen") is not True:
        failures.append("CANDIDATE_NOT_FROZEN")
    if receipt.get("merged_pr") != 4:
        failures.append("MERGED_PR_MISMATCH")
    if receipt.get("explicit_merge_approval") is not True:
        failures.append("EXPLICIT_APPROVAL_MISSING")
    if not APPROVAL_RE.fullmatch(str(receipt.get("approval_reference") or "")):
        failures.append("APPROVAL_REFERENCE_INVALID")
    if receipt.get("attestation_git_blob_sha1") != EXPECTED_ATTESTATION_BLOB:
        failures.append("ATTESTATION_PIN_MISMATCH")
    if not COMMIT_RE.fullmatch(freeze_commit):
        failures.append("FREEZE_COMMIT_INVALID")
        return False, failures

    if git("cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
        failures.append("FREEZE_COMMIT_UNAVAILABLE")
        return False, failures
    if git("merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ANCESTOR")
    if git("merge-base", "--is-ancestor", freeze_commit, "origin/main").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN")
    observed_tree = git("show", "-s", "--format=%T", freeze_commit)
    if observed_tree.returncode != 0 or observed_tree.stdout.strip() != receipt.get("freeze_tree_sha"):
        failures.append("FREEZE_TREE_MISMATCH")

    # The canonical freeze commit must contain the exact pre-freeze candidate
    # bytes. Documentation/receipt files may be added later, but candidate
    # implementation or evidence cannot drift.
    for row in attestation.get("pinned_artifacts", []):
        rel = str(row.get("path") or "")
        observed = git("rev-parse", f"{freeze_commit}:{rel}")
        if observed.returncode != 0 or observed.stdout.strip() != row.get("git_blob_sha1"):
            failures.append(f"FREEZE_ARTIFACT_MISMATCH:{rel}")
    pinned_count = len(attestation.get("pinned_artifacts", []))
    if receipt.get("pinned_artifact_count") != pinned_count:
        failures.append("PINNED_ARTIFACT_COUNT_MISMATCH")
    if receipt.get("verified_artifact_count") != pinned_count:
        failures.append("VERIFIED_ARTIFACT_COUNT_MISMATCH")
    if receipt.get("fresh_evidence") is not False or receipt.get("gold_approved") is not False:
        failures.append("RECEIPT_EVIDENCE_BOUNDARY_INVALID")
    if (
        receipt.get("bounded_release") != "BLOCKED_NEXT_FRESH"
        or receipt.get("stage_release") != "BLOCKED_GOLD_REVIEW"
        or receipt.get("s6_automatic_trust") != "BLOCKED"
    ):
        failures.append("RECEIPT_RELEASE_BOUNDARY_INVALID")
    return not failures, failures


def evaluate(receipt_path: Path, fresh_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    attestation_bytes = ATTESTATION.read_bytes()
    observed_attestation_blob = git_blob_sha1(attestation_bytes)
    if observed_attestation_blob != EXPECTED_ATTESTATION_BLOB:
        failures.append("CURRENT_ATTESTATION_BLOB_MISMATCH")
    attestation = load_json(ATTESTATION)

    receipt_present = receipt_path.is_file()
    fresh_assets = sorted(
        path.relative_to(fresh_root).as_posix() for path in fresh_root.rglob("*") if path.is_file()
    ) if fresh_root.is_dir() else []
    fresh_assets_present = bool(fresh_assets)
    receipt_valid = False
    freeze_commit: str | None = None
    if receipt_present:
        try:
            receipt = load_json(receipt_path)
            freeze_commit = str(receipt.get("freeze_commit") or "") or None
            receipt_valid, receipt_failures = validate_receipt(receipt, attestation)
            failures.extend(receipt_failures)
        except (OSError, ValueError, json.JSONDecodeError):
            failures.append("RECEIPT_UNREADABLE")

    protocol_valid = False
    if fresh_assets_present:
        if not receipt_valid:
            failures.append("UNAUTHORIZED_FRESH_ASSETS_BEFORE_VERIFIED_FREEZE")
        protocol_path = fresh_root / "protocol-v0.9.json"
        if not protocol_path.is_file():
            failures.append("FRESH_PROTOCOL_MISSING")
        else:
            try:
                protocol = load_json(protocol_path)
                protocol_valid = bool(
                    protocol.get("stage") == "S5"
                    and protocol.get("version") == "v0.9"
                    and protocol.get("fresh_evidence") is True
                    and protocol.get("authored_after_freeze") is True
                    and protocol.get("target_implementation_freeze_commit") == freeze_commit
                )
            except (OSError, ValueError, json.JSONDecodeError):
                protocol_valid = False
            if not protocol_valid:
                failures.append("FRESH_PROTOCOL_INVALID")

    fresh_authoring_allowed = bool(receipt_valid and (not fresh_assets_present or protocol_valid))
    if failures:
        decision = "FAIL_CLOSED"
        guard_gate = "FAIL"
    elif fresh_authoring_allowed:
        decision = "ALLOW_AFTER_VERIFIED_FREEZE"
        guard_gate = "PASS"
    else:
        decision = "BLOCKED_NOT_FROZEN"
        guard_gate = "PASS"

    return {
        "stage": "S5",
        "version": "v0.9-admission-v0.1",
        "guard": "next-fresh-authoring-admission",
        "evidence_class": "development_process_guard",
        "fresh_evidence": False,
        "attestation_git_blob_sha1": observed_attestation_blob,
        "receipt_path": receipt_path.relative_to(ROOT).as_posix() if receipt_path.is_relative_to(ROOT) else str(receipt_path),
        "receipt_present": receipt_present,
        "receipt_valid": receipt_valid,
        "freeze_commit": freeze_commit,
        "fresh_root": fresh_root.relative_to(ROOT).as_posix() if fresh_root.is_relative_to(ROOT) else str(fresh_root),
        "fresh_assets_present": fresh_assets_present,
        "fresh_asset_count": len(fresh_assets),
        "fresh_assets": fresh_assets,
        "fresh_protocol_valid": protocol_valid,
        "fresh_authoring_allowed": fresh_authoring_allowed,
        "admission_decision": decision,
        "failures": failures,
        "guard_gate": guard_gate,
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "rule": "No S5 v0.9 fresh asset may exist before an explicit, verifiable v0.8.1 canonical freeze receipt; exposed v0.8/v0.8.1 cases never qualify as v0.9 fresh.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--fresh-root", type=Path, default=DEFAULT_FRESH_ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.receipt, args.fresh_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["guard_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
