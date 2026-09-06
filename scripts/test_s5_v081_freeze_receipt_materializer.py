#!/usr/bin/env python3
"""Deterministic tests for the S5 v0.8.1 freeze-receipt materializer."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts/materialize_s5_v081_freeze_receipt.py"
ATTESTATION = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.8.1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("s5_freeze_materializer_under_test", MATERIALIZER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MATERIALIZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_git_factory(module, commit: str, tree: str, *, canonical: bool, drift_path: str | None = None):
    attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    pinned = {row["path"]: row["git_blob_sha1"] for row in attestation["pinned_artifacts"]}
    pinned[str(ATTESTATION.relative_to(ROOT))] = module.EXPECTED_ATTESTATION_BLOB

    def done(args: tuple[str, ...], code: int, stdout: str = ""):
        return module.subprocess.CompletedProcess(["git", *args], code, stdout, "")

    def fake_git(*args: str):
        if args[:2] == ("cat-file", "-e"):
            return done(args, 0)
        if args == ("rev-parse", "origin/main"):
            return done(args, 0, (commit if canonical else "9" * 40) + "\n")
        if args[:2] == ("merge-base", "--is-ancestor"):
            return done(args, 0 if canonical else 1)
        if args[:3] == ("show", "-s", "--format=%T"):
            return done(args, 0, tree + "\n")
        if args and args[0] == "rev-parse" and args[1].startswith(commit + ":"):
            path = args[1].split(":", 1)[1]
            sha = "0" * 40 if path == drift_path else pinned.get(path)
            return done(args, 0 if sha else 1, (sha + "\n") if sha else "")
        return done(args, 1)

    return fake_git


def run() -> dict:
    module = load_module()
    scenarios: list[dict] = []

    receipt, failures = module.build_receipt("bad", "TODO")
    assert receipt is None
    assert set(failures) == {"FREEZE_COMMIT_INVALID", "APPROVAL_REFERENCE_INVALID"}
    scenarios.append({"name": "invalid_authority_inputs_rejected", "result": "PASS", "failures": sorted(failures)})

    receipt, failures = module.build_receipt("a" * 40, "user-approval:fixture-0001")
    assert receipt is None and failures == ["FREEZE_COMMIT_UNAVAILABLE"]
    scenarios.append({"name": "unavailable_commit_rejected", "result": "PASS", "failures": failures})

    original_attestation = module.ATTESTATION
    with tempfile.TemporaryDirectory() as raw:
        module.ATTESTATION = Path(raw) / "drifted-attestation.json"
        module.ATTESTATION.write_text("{}\n", encoding="utf-8")
        receipt, failures = module.build_receipt("a" * 40, "user-approval:fixture-0001")
    module.ATTESTATION = original_attestation
    assert receipt is None and failures == ["CURRENT_ATTESTATION_BLOB_MISMATCH"]
    scenarios.append({"name": "working_attestation_drift_rejected", "result": "PASS", "failures": failures})

    commit, tree = "b" * 40, "c" * 40
    module.git = fake_git_factory(module, commit, tree, canonical=False)
    receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
    assert receipt is None
    assert {"FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP", "FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN"}.issubset(failures)
    scenarios.append({"name": "noncanonical_commit_rejected", "result": "PASS", "failures": sorted(failures)})

    drift_path = "scripts/s5_lineage_detector_v081.py"
    module.git = fake_git_factory(module, commit, tree, canonical=True, drift_path=drift_path)
    receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
    assert receipt is None and f"FREEZE_ARTIFACT_MISMATCH:{drift_path}" in failures
    scenarios.append({"name": "candidate_byte_drift_rejected", "result": "PASS", "failures": sorted(failures)})

    module.git = fake_git_factory(module, commit, tree, canonical=True)
    receipt, failures = module.build_receipt(commit, "user-approval:fixture-0001")
    assert failures == [] and receipt is not None
    assert receipt["candidate_frozen"] is True
    assert receipt["pinned_artifact_count"] == receipt["verified_artifact_count"] == 22
    assert receipt["fresh_evidence"] is False and receipt["gold_approved"] is False
    assert receipt["bounded_release"] == "BLOCKED_NEXT_FRESH"
    assert receipt["stage_release"] == "BLOCKED_GOLD_REVIEW"
    assert receipt["s6_automatic_trust"] == "BLOCKED"
    scenarios.append({"name": "canonical_exact_candidate_materializes_bounded_receipt", "result": "PASS", "failures": []})

    return {
        "stage": "S5",
        "version": "v0.8.1-freeze-receipt-tests-v0.1",
        "evidence_class": "development_process_guard_test",
        "fresh_evidence": False,
        "scenario_count": len(scenarios),
        "scenario_pass_count": len(scenarios),
        "test_gate": "PASS",
        "scenarios": scenarios,
        "receipt_materialized": False,
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "note": "The success path uses mocked Git history; no canonical freeze receipt is created by this test.",
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
