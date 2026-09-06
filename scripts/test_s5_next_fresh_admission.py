#!/usr/bin/env python3
"""Adversarial contract tests for the S5 v0.9 fresh-authoring guard.

These are development process tests. They do not create or evaluate fresh cases.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts/check_s5_next_fresh_admission.py"
ATTESTATION_PATH = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.8.1.json"


def load_guard():
    spec = importlib.util.spec_from_file_location("s5_next_fresh_guard_under_test", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GUARD_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def receipt(*, commit: str, tree: str, **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "stage": "S5",
        "version": "v0.8.1",
        "receipt_type": "canonical_freeze_receipt",
        "generator_version": "s5-freeze-receipt-v0.1",
        "candidate_frozen": True,
        "merged_pr": 4,
        "explicit_merge_approval": True,
        "approval_reference": "user-approval:fixture-0001",
        "attestation_git_blob_sha1": "f7ecf1663adebeb7b81eaa681ca142b1f749f833",
        "freeze_commit": commit,
        "freeze_tree_sha": tree,
        "pinned_artifact_count": 22,
        "verified_artifact_count": 22,
        "fresh_evidence": False,
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
    }
    value.update(overrides)
    return value


def fake_git_factory(module, commit: str, tree: str, *, on_main: bool):
    attestation = json.loads(ATTESTATION_PATH.read_text(encoding="utf-8"))
    pinned = {row["path"]: row["git_blob_sha1"] for row in attestation["pinned_artifacts"]}

    def fake_git(*args: str):
        if args[:2] == ("cat-file", "-e") and args[2] == f"{commit}^{{commit}}":
            return module.subprocess.CompletedProcess(["git", *args], 0, "", "")
        if args[:2] == ("merge-base", "--is-ancestor") and args[2] == commit:
            is_canonical_check = args[3] == "origin/main"
            return module.subprocess.CompletedProcess(
                ["git", *args], 0 if (on_main or not is_canonical_check) else 1, "", ""
            )
        if args[:3] == ("show", "-s", "--format=%T") and args[3] == commit:
            return module.subprocess.CompletedProcess(["git", *args], 0, tree + "\n", "")
        if args and args[0] == "rev-parse" and args[1].startswith(commit + ":"):
            path = args[1].split(":", 1)[1]
            sha = pinned.get(path)
            return module.subprocess.CompletedProcess(
                ["git", *args], 0 if sha else 1, (sha + "\n") if sha else "", ""
            )
        return module.subprocess.CompletedProcess(["git", *args], 1, "", "unexpected fake git call")

    return fake_git


def require(result: dict[str, Any], *, gate: str, decision: str, failures: set[str]) -> None:
    assert result["guard_gate"] == gate, result
    assert result["admission_decision"] == decision, result
    assert result["fresh_authoring_allowed"] is (decision == "ALLOW_AFTER_VERIFIED_FREEZE"), result
    assert failures.issubset(set(result["failures"])), result
    assert result["fresh_evidence"] is False, result
    assert result["stage_release"] == "BLOCKED_GOLD_REVIEW", result
    assert result["s6_automatic_trust"] == "BLOCKED", result


def run() -> dict[str, Any]:
    module = load_guard()
    scenarios: list[dict[str, Any]] = []

    def record(name: str, result: dict[str, Any]) -> None:
        scenarios.append({
            "name": name,
            "guard_gate": result["guard_gate"],
            "admission_decision": result["admission_decision"],
            "fresh_authoring_allowed": result["fresh_authoring_allowed"],
            "expected_failures_observed": sorted(result["failures"]),
        })

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)

        result = module.evaluate(tmp / "missing.json", tmp / "empty-fresh")
        require(result, gate="PASS", decision="BLOCKED_NOT_FROZEN", failures=set())
        record("missing_receipt_no_assets_blocks_cleanly", result)

        malformed = tmp / "malformed.json"
        malformed.write_text("{not-json", encoding="utf-8")
        result = module.evaluate(malformed, tmp / "empty-fresh")
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={"RECEIPT_UNREADABLE"})
        record("malformed_receipt_fails_closed", result)

        invalid = tmp / "invalid-authority.json"
        write_json(invalid, receipt(
            commit="not-a-commit",
            tree="not-a-tree",
            stage="S6",
            receipt_type="self_asserted",
            generator_version="unknown-generator",
            candidate_frozen=False,
            merged_pr=999,
            explicit_merge_approval=False,
            approval_reference="TODO",
            attestation_git_blob_sha1="0" * 40,
        ))
        result = module.evaluate(invalid, tmp / "empty-fresh")
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={
            "RECEIPT_SCOPE_INVALID", "RECEIPT_TYPE_INVALID", "CANDIDATE_NOT_FROZEN",
            "MERGED_PR_MISMATCH", "EXPLICIT_APPROVAL_MISSING", "ATTESTATION_PIN_MISMATCH",
            "FREEZE_COMMIT_INVALID", "RECEIPT_GENERATOR_INVALID", "APPROVAL_REFERENCE_INVALID",
        })
        record("self_asserted_authority_is_rejected", result)

        unavailable = tmp / "unavailable.json"
        write_json(unavailable, receipt(commit="a" * 40, tree="b" * 40))
        result = module.evaluate(unavailable, tmp / "empty-fresh")
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={"FREEZE_COMMIT_UNAVAILABLE"})
        record("unavailable_commit_is_rejected", result)

        simulated_unmerged_commit = "b" * 40
        simulated_unmerged_tree = "c" * 40
        module.git = fake_git_factory(
            module, simulated_unmerged_commit, simulated_unmerged_tree, on_main=False
        )
        unmerged = tmp / "unmerged.json"
        write_json(unmerged, receipt(commit=simulated_unmerged_commit, tree=simulated_unmerged_tree))
        result = module.evaluate(unmerged, tmp / "empty-fresh")
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={"FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN"})
        record("unmerged_pr_head_is_rejected", result)

        unauthorized_root = tmp / "unauthorized-fresh"
        unauthorized_root.mkdir()
        (unauthorized_root / "case.json").write_text("{}\n", encoding="utf-8")
        result = module.evaluate(tmp / "missing.json", unauthorized_root)
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={
            "UNAUTHORIZED_FRESH_ASSETS_BEFORE_VERIFIED_FREEZE", "FRESH_PROTOCOL_MISSING",
        })
        record("fresh_asset_before_freeze_is_rejected", result)

        simulated_commit = "d" * 40
        simulated_tree = "e" * 40
        module.git = fake_git_factory(module, simulated_commit, simulated_tree, on_main=True)
        valid_receipt = tmp / "valid-simulated.json"
        write_json(valid_receipt, receipt(commit=simulated_commit, tree=simulated_tree))

        result = module.evaluate(valid_receipt, tmp / "empty-fresh")
        require(result, gate="PASS", decision="ALLOW_AFTER_VERIFIED_FREEZE", failures=set())
        record("verified_canonical_freeze_opens_authoring", result)

        missing_protocol_root = tmp / "missing-protocol"
        missing_protocol_root.mkdir()
        (missing_protocol_root / "case.json").write_text("{}\n", encoding="utf-8")
        result = module.evaluate(valid_receipt, missing_protocol_root)
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={"FRESH_PROTOCOL_MISSING"})
        record("post_freeze_assets_without_protocol_are_rejected", result)

        mismatch_root = tmp / "mismatch-protocol"
        mismatch_root.mkdir()
        write_json(mismatch_root / "protocol-v0.9.json", {
            "stage": "S5", "version": "v0.9", "fresh_evidence": True,
            "authored_after_freeze": True, "target_implementation_freeze_commit": "f" * 40,
        })
        result = module.evaluate(valid_receipt, mismatch_root)
        require(result, gate="FAIL", decision="FAIL_CLOSED", failures={"FRESH_PROTOCOL_INVALID"})
        record("protocol_target_mismatch_is_rejected", result)

        valid_root = tmp / "valid-protocol"
        valid_root.mkdir()
        write_json(valid_root / "protocol-v0.9.json", {
            "stage": "S5", "version": "v0.9", "fresh_evidence": True,
            "authored_after_freeze": True,
            "target_implementation_freeze_commit": simulated_commit,
        })
        result = module.evaluate(valid_receipt, valid_root)
        require(result, gate="PASS", decision="ALLOW_AFTER_VERIFIED_FREEZE", failures=set())
        record("matching_post_freeze_protocol_is_admitted", result)

    return {
        "stage": "S5",
        "version": "v0.9-admission-tests-v0.1",
        "evidence_class": "development_process_guard_test",
        "fresh_evidence": False,
        "scenario_count": len(scenarios),
        "scenario_pass_count": len(scenarios),
        "test_gate": "PASS",
        "scenarios": scenarios,
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "note": "The positive path uses a deterministic mocked canonical Git history; it is not a real freeze receipt or fresh evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
