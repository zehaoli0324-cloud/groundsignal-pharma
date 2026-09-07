#!/usr/bin/env python3
"""Deterministic state tests for v0.9.1 freeze and v0.10 admission controls."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "scripts/s5_v091_freeze_control.py"
ATTESTATION = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.9.1.json"
CONTROL_PLANE = ROOT / "medical/stage-evals/S5/control-plane-readiness-v0.9.1.json"


def load_library():
    spec = importlib.util.spec_from_file_location("s5_v091_freeze_control_under_test", LIBRARY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {LIBRARY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fake_git_factory(
    module,
    commit: str,
    tree: str,
    *,
    canonical: bool,
    candidate_drift: bool = False,
    control_drift: bool = False,
    preexisting_receipt: bool = False,
    preexisting_fresh: bool = False,
):
    attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PLANE.read_text(encoding="utf-8"))
    candidate_pins = {row["path"]: row["git_blob_sha1"] for row in attestation["pinned_artifacts"]}
    control_pins = {row["path"]: row["git_blob_sha1"] for row in control["pinned_control_plane_artifacts"]}
    candidate_drift_path = next(iter(candidate_pins))
    control_drift_path = next(iter(control_pins))
    pins = {**candidate_pins, **control_pins}
    pins[str(ATTESTATION.relative_to(ROOT))] = module.EXPECTED_ATTESTATION_BLOB
    pins[str(CONTROL_PLANE.relative_to(ROOT))] = module.git_blob_sha1(CONTROL_PLANE.read_bytes())

    def done(args: tuple[str, ...], code: int, stdout: str = ""):
        return module.subprocess.CompletedProcess(["git", *args], code, stdout, "")

    def fake_git(*args: str):
        if args[:2] == ("cat-file", "-e"):
            target = args[2]
            if target == f"{commit}^{{commit}}":
                return done(args, 0)
            if target == f"{commit}:{module.RECEIPT_REL}":
                return done(args, 0 if preexisting_receipt else 1)
            if target == f"{commit}:{module.NEXT_FRESH_ROOT_REL}":
                return done(args, 0 if preexisting_fresh else 1)
            return done(args, 1)
        if args == ("rev-parse", "origin/main"):
            return done(args, 0, (commit if canonical else "9" * 40) + "\n")
        if args[:2] == ("merge-base", "--is-ancestor"):
            if args[2] == commit and args[3] == "origin/main":
                return done(args, 0 if canonical else 1)
            if args[2] == commit and args[3] == "HEAD":
                return done(args, 0)
            return done(args, 1)
        if args[:3] == ("show", "-s", "--format=%T") and args[3] == commit:
            return done(args, 0, tree + "\n")
        if args and args[0] == "rev-parse" and args[1].startswith(commit + ":"):
            rel = args[1].split(":", 1)[1]
            sha = pins.get(rel)
            if candidate_drift and rel == candidate_drift_path:
                sha = "0" * 40
            if control_drift and rel == control_drift_path:
                sha = "0" * 40
            return done(args, 0 if sha else 1, (sha + "\n") if sha else "")
        return done(args, 1)

    return fake_git


def run() -> dict[str, Any]:
    module = load_library()
    scenarios: list[dict[str, Any]] = []

    def record(name: str, passed: bool, observed: str) -> None:
        assert passed, f"scenario failed: {name}: {observed}"
        scenarios.append({"name": name, "result": "PASS", "observed": observed})

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        missing_receipt = tmp / "missing-receipt.json"
        empty_root = tmp / "empty-fresh"

        current = module.evaluate_admission(missing_receipt, empty_root)
        record(
            "current_pre_freeze_state_blocks_cleanly",
            current["guard_gate"] == "PASS" and current["admission_decision"] == "BLOCKED_NOT_FROZEN",
            current["admission_decision"],
        )

        receipt, failures = module.build_receipt("bad", "TODO")
        record(
            "invalid_authority_inputs_rejected",
            receipt is None and set(failures) == {"FREEZE_COMMIT_INVALID", "APPROVAL_REFERENCE_INVALID"},
            ",".join(failures),
        )

        receipt, failures = module.build_receipt("a" * 40, "user-approval:fixture-0001")
        record("unavailable_commit_rejected", receipt is None and failures == ["FREEZE_COMMIT_UNAVAILABLE"], ",".join(failures))

        commit, tree = "b" * 40, "c" * 40
        module.git = fake_git_factory(module, commit, tree, canonical=False)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record("noncanonical_commit_rejected", receipt is None and "FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP" in failures, ",".join(failures))

        module.git = fake_git_factory(module, commit, tree, canonical=True, candidate_drift=True)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record("candidate_byte_drift_rejected", receipt is None and any(x.startswith("FREEZE_ARTIFACT_MISMATCH:") for x in failures), ",".join(failures))

        module.git = fake_git_factory(module, commit, tree, canonical=True, control_drift=True)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record("control_plane_byte_drift_rejected", receipt is None and any(x.startswith("FREEZE_CONTROL_PLANE_ARTIFACT_MISMATCH:") for x in failures), ",".join(failures))

        module.git = fake_git_factory(module, commit, tree, canonical=True, preexisting_receipt=True)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record("preseeded_receipt_rejected", receipt is None and "RECEIPT_PREEXISTED_AT_FREEZE" in failures, ",".join(failures))

        module.git = fake_git_factory(module, commit, tree, canonical=True, preexisting_fresh=True)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record("preseeded_fresh_root_rejected", receipt is None and "NEXT_FRESH_ASSETS_PREEXISTED_AT_FREEZE" in failures, ",".join(failures))

        module.git = fake_git_factory(module, commit, tree, canonical=True)
        receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
        record(
            "canonical_exact_candidate_materializes_bounded_receipt",
            not failures and receipt is not None and receipt["candidate_frozen"] is True and receipt["gold_approved"] is False and receipt["s6_automatic_trust"] == "BLOCKED",
            "receipt_built",
        )
        assert receipt is not None
        receipt_path = tmp / "valid-receipt.json"
        write_json(receipt_path, receipt)
        admitted = module.evaluate_admission(receipt_path, empty_root)
        record(
            "verified_receipt_opens_authoring_only",
            admitted["guard_gate"] == "PASS" and admitted["admission_decision"] == "ALLOW_AFTER_VERIFIED_FREEZE" and admitted["gold_approved"] is False,
            admitted["admission_decision"],
        )

        malformed = tmp / "malformed.json"
        malformed.write_text("{not-json", encoding="utf-8")
        failed = module.evaluate_admission(malformed, empty_root)
        record("malformed_receipt_fails_closed", failed["guard_gate"] == "FAIL" and "RECEIPT_UNREADABLE" in failed["failures"], failed["admission_decision"])

        unauthorized = tmp / "unauthorized-fresh"
        unauthorized.mkdir()
        (unauthorized / "case.json").write_text("{}\n", encoding="utf-8")
        failed = module.evaluate_admission(missing_receipt, unauthorized)
        record("fresh_before_receipt_fails_closed", failed["guard_gate"] == "FAIL" and "UNAUTHORIZED_FRESH_ASSETS_BEFORE_VERIFIED_FREEZE" in failed["failures"], failed["admission_decision"])

        no_protocol = tmp / "post-freeze-no-protocol"
        no_protocol.mkdir()
        (no_protocol / "case.json").write_text("{}\n", encoding="utf-8")
        failed = module.evaluate_admission(receipt_path, no_protocol)
        record("post_freeze_assets_without_protocol_rejected", failed["guard_gate"] == "FAIL" and "FRESH_PROTOCOL_MISSING" in failed["failures"], failed["admission_decision"])

        escalated = dict(receipt)
        escalated["gold_approved"] = True
        escalated_path = tmp / "escalated.json"
        write_json(escalated_path, escalated)
        failed = module.evaluate_admission(escalated_path, empty_root)
        record("gold_privilege_escalation_rejected", failed["guard_gate"] == "FAIL" and "RECEIPT_FIELD_INVALID:gold_approved" in failed["failures"], failed["admission_decision"])

    return {
        "stage": "S5",
        "version": "v0.9.1-freeze-control-tests-v0.1",
        "evidence_class": "development_process_guard_test",
        "fresh_evidence": False,
        "first_observation": False,
        "scenario_count": len(scenarios),
        "scenario_pass_count": len(scenarios),
        "test_gate": "PASS",
        "scenarios": scenarios,
        "receipt_materialized": False,
        "v0.10_assets_created": False,
        "candidate_frozen": False,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "note": "The positive path uses mocked canonical Git state; no real receipt or fresh asset is created.",
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
