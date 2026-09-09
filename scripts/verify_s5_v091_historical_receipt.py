#!/usr/bin/env python3
"""Verify an already published S5 receipt without materializing a new freeze.

The pins below come from the existing receipt publication commit on canonical
main. They identify historical evidence, not an alternative authoring authority.
The frozen materializer and admission policy remain unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import s5_v091_freeze_control as frozen

ROOT = frozen.ROOT
PUBLICATION_COMMIT = "31c94deded224d54a7e2f0e977ebe458e9b6c16e"
FREEZE_COMMIT = "cdc89298693aa9c5222f15ed9bd62a57e140fbc6"
RECEIPT_BLOB = "9fb59ab6205b8b37a1574988d386980c953a0839"
git = frozen.git


def verify(receipt_path: Path = ROOT / frozen.RECEIPT_REL) -> dict[str, Any]:
    failures: list[str] = []
    result: dict[str, Any] = {
        "stage": "S5",
        "verification": "v0.9.1-immutable-historical-receipt",
        "evidence_class": "development_process_integrity_attestation_verification",
        "freeze_commit": FREEZE_COMMIT,
        "receipt_publication_commit": PUBLICATION_COMMIT,
        "expected_receipt_git_blob_sha1": RECEIPT_BLOB,
        "fresh_evidence": False,
        "first_observation": False,
        "receipt_materialized": False,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
    }

    def finish() -> dict[str, Any]:
        result["failures"] = failures
        result["verification_gate"] = "FAIL" if failures else "PASS"
        return result

    history = git("rev-parse", "--is-shallow-repository")
    if history.returncode != 0 or history.stdout.strip() != "false":
        failures.append("COMPLETE_GIT_HISTORY_REQUIRED")
        return finish()
    for commit in (FREEZE_COMMIT, PUBLICATION_COMMIT):
        if git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            failures.append(f"HISTORICAL_COMMIT_UNAVAILABLE:{commit}")
    if failures:
        return finish()
    if git("rev-parse", "origin/main").returncode != 0:
        failures.append("CANONICAL_MAIN_UNAVAILABLE")
    for ref in ("origin/main", "HEAD"):
        if git("merge-base", "--is-ancestor", PUBLICATION_COMMIT, ref).returncode != 0:
            failures.append(f"RECEIPT_PUBLICATION_NOT_ANCESTOR:{ref}")
    parents = git("rev-list", "--parents", "-n", "1", PUBLICATION_COMMIT)
    if parents.returncode != 0 or parents.stdout.split() != [PUBLICATION_COMMIT, FREEZE_COMMIT]:
        failures.append("RECEIPT_PUBLICATION_PARENT_MISMATCH")
    published_blob = git("rev-parse", f"{PUBLICATION_COMMIT}:{frozen.RECEIPT_REL}")
    if published_blob.returncode != 0 or published_blob.stdout.strip() != RECEIPT_BLOB:
        failures.append("PUBLISHED_RECEIPT_BLOB_MISMATCH")
    if git("cat-file", "-e", f"{PUBLICATION_COMMIT}:{frozen.NEXT_FRESH_ROOT_REL}").returncode == 0:
        failures.append("FRESH_ASSETS_PREEXISTED_AT_RECEIPT_PUBLICATION")

    try:
        data = receipt_path.read_bytes()
        receipt = json.loads(data)
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be an object")
    except (OSError, ValueError):
        failures.append("RECEIPT_UNREADABLE")
        return finish()
    if frozen.git_blob_sha1(data) != RECEIPT_BLOB:
        failures.append("CURRENT_RECEIPT_BLOB_MISMATCH")
    if receipt.get("freeze_commit") != FREEZE_COMMIT:
        failures.append("HISTORICAL_FREEZE_COMMIT_MISMATCH")

    attestation, attestation_check, attestation_blob = frozen.verify_current_attestation()
    control_plane, control_check, control_blob = frozen.verify_current_control_plane()
    if (
        attestation is None or attestation_check is None
        or attestation_blob != frozen.EXPECTED_ATTESTATION_BLOB
        or attestation_check.get("verification_gate") != "PASS"
    ):
        failures.append("CURRENT_ATTESTATION_NOT_READY")
    if control_plane is None or control_check is None or control_check.get("verification_gate") != "PASS":
        failures.append("CURRENT_CONTROL_PLANE_NOT_READY")
    if failures:
        return finish()

    # This is the unchanged frozen validator: historical ancestry, tree,
    # 24 implementation pins, 8 control-plane pins and release boundaries.
    valid, receipt_failures = frozen.validate_receipt(receipt, attestation, control_plane, control_blob)
    failures.extend(receipt_failures)
    if not valid and not receipt_failures:
        failures.append("FROZEN_RECEIPT_VALIDATOR_REJECTED")
    return finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=ROOT / frozen.RECEIPT_REL)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.receipt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verification_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
