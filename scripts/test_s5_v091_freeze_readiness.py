#!/usr/bin/env python3
"""Deterministic negative tests for the S5 v0.9.1 readiness verifier."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify_s5_v091_freeze_readiness.py"
MANIFEST = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.9.1.json"


def load_verifier():
    spec = importlib.util.spec_from_file_location("s5_v091_readiness_under_test", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {VERIFIER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run() -> dict:
    verifier = load_verifier()
    source = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scenarios: list[dict] = []

    baseline = verifier.verify(MANIFEST)
    assert baseline["verification_gate"] == "PASS"
    scenarios.append({"name": "exact_manifest_passes", "result": "PASS"})

    mutations = []
    missing = copy.deepcopy(source)
    missing["pinned_artifacts"].pop()
    mutations.append(("missing_pin_rejected", missing, "MISSING_REQUIRED_PIN:"))

    drifted = copy.deepcopy(source)
    drifted["pinned_artifacts"][0]["sha256"] = "0" * 64
    mutations.append(("hash_drift_rejected", drifted, "PIN_MISMATCH:"))

    duplicate = copy.deepcopy(source)
    duplicate["pinned_artifacts"].append(copy.deepcopy(duplicate["pinned_artifacts"][0]))
    mutations.append(("duplicate_pin_rejected", duplicate, "DUPLICATE_PINNED_PATH"))

    escalated = copy.deepcopy(source)
    escalated.update({"fresh_evidence": True, "candidate_frozen": True, "gold_approved": True, "s6_automatic_trust": "ALLOWED"})
    mutations.append(("privilege_escalation_rejected", escalated, "GATE_FAILURE:"))

    asset_drift = copy.deepcopy(source)
    asset_drift["v0.9_fresh_asset_contract"]["path_sha256_aggregate"] = "0" * 64
    mutations.append(("fresh_asset_contract_drift_rejected", asset_drift, "GATE_FAILURE:v09_assets_preserved"))

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for index, (name, payload, expected) in enumerate(mutations):
            path = root / f"manifest-{index}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = verifier.verify(path)
            assert result["verification_gate"] == "FAIL"
            assert any(failure.startswith(expected) for failure in result["failures"])
            scenarios.append({"name": name, "result": "PASS", "observed_gate": "FAIL"})

    return {
        "stage": "S5",
        "version": "v0.9.1-freeze-readiness-tests-v0.1",
        "evidence_class": "development_process_guard_test",
        "fresh_evidence": False,
        "first_observation": False,
        "scenario_count": len(scenarios),
        "scenario_pass_count": len(scenarios),
        "test_gate": "PASS",
        "scenarios": scenarios,
        "candidate_frozen": False,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
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
