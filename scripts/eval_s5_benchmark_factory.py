#!/usr/bin/env python3
"""S5 v0.1 development audit for the GroundSignal benchmark factory.

This is a structural/safety audit, not a fresh held-out evaluation and not a
clinical-validity claim. It deliberately tests whether benchmark split and gold
boundaries are machine-enforced rather than merely documented.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT / "medical/case-families")
    parser.add_argument("--schema", type=Path, default=ROOT / "medical/schemas/clinical-case.schema.json")
    parser.add_argument("--snapshot-commit", default="9e8aef6ee4e54dd6fe01eb6749368d2c15471762")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifests = []
    for p in sorted(args.root.glob("*/manifest.json")):
        manifests.append((p, load_json(p)))

    split_counts: Counter[str] = Counter()
    case_count = 0
    structure_pass = 0
    heldout_policy_pass = 0
    difficulty_metadata_pass = 0
    gold_approved = 0
    pending_gold = []

    for path, m in manifests:
        refs = m.get("cases", [])
        case_count += len(refs)
        splits = Counter(str(r.get("split")) for r in refs)
        split_counts.update(splits)
        if len(refs) == 5 and splits == Counter({"dev": 3, "regression": 1, "heldout": 1}):
            structure_pass += 1
        policy = m.get("split_policy") or {}
        if policy.get("leakage_rule") and policy.get("heldout_variables"):
            heldout_policy_pass += 1
        if len(m.get("target_capabilities") or []) >= 4 and len(m.get("failure_hypotheses") or []) >= 4:
            difficulty_metadata_pass += 1
        if m.get("status") == "gold_approved":
            gold_approved += 1
        else:
            pending_gold.append({"family_id": m.get("family_id"), "status": m.get("status")})

    # Reuse the existing materialization/referential-integrity validator.
    validator = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_medical_case_families.py"),
            "--expect-families", "12",
            "--expect-cases", "60",
            "--expect-cases-per-family", "5",
            "--rubric-version", "medical-clinical-v0.2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    schema = load_json(args.schema)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    split_binding = {
        "family_id_property": "family_id" in props,
        "family_id_required": "family_id" in required,
        "split_property": "split" in props,
        "split_required": "split" in required,
    }
    split_binding["pass"] = all(split_binding.values())

    graph_schema = props.get("graph_eval") or {}
    graph_required = set(graph_schema.get("required") or [])
    decision_components = ["required_node_ids", "required_edge_ids", "expected_reasoning_path"]
    decision_contract = {
        "graph_eval_required": "graph_eval" in required,
        "required_components": {k: k in graph_required for k in decision_components},
    }
    decision_contract["schema_enforced_component_count"] = sum(decision_contract["required_components"].values())
    decision_contract["schema_enforced_component_total"] = len(decision_components)
    decision_contract["pass"] = bool(
        decision_contract["graph_eval_required"]
        and decision_contract["schema_enforced_component_count"] == len(decision_components)
    )

    # Gold-leakage probe: expected behavior and scoring sentinels must not enter model prompt.
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_model_harness")
    sentinel = "S5_GOLD_SENTINEL_DO_NOT_EXPOSE"
    probe_case = {
        "case_id": "S5-PROMPT-PROBE",
        "patient_context": {"chief_complaint": "synthetic audit probe"},
        "interaction": {"prompt": "Answer the synthetic audit task.", "prior_turns": []},
        "expected_behavior": {"must_include": [sentinel]},
        "graph_eval": {"expected_reasoning_path": [sentinel]},
        "safety": {"critical_errors": [sentinel]},
        "scoring": {"rubric_version": "audit", "dimensions": [sentinel]},
    }
    rendered = harness.build_user_prompt(probe_case, "")
    prompt_probe = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

    # Split-contamination probe: an explicitly held-out synthetic case must never be exportable
    # merely because an evaluation row is approved. v0.1 intentionally observes current behavior.
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_export_training_data")
    heldout_case = {
        "case_id": "S5-SYNTHETIC-HELDOUT-PROBE",
        "split": "heldout",
        "interaction": {"prompt": "synthetic held-out export probe", "prior_turns": []},
        "patient_context": {"chief_complaint": "synthetic audit probe"},
        "evidence_snapshot": {},
    }
    approved_eval = {
        "case_id": heldout_case["case_id"],
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic ideal response",
        },
    }
    export_result = exporter.export_row(approved_eval, heldout_case, None)
    export_probe = {
        "approved_heldout_case_exportable": export_result is not None,
        "pass": export_result is None,
    }

    hard_failures = []
    if not split_binding["pass"] or not export_probe["pass"]:
        hard_failures.append("S5-F1")
    if gold_approved != len(manifests):
        hard_failures.append("S5-F2")
    if not decision_contract["pass"]:
        hard_failures.append("S5-F3")

    result = {
        "stage": "S5",
        "version": "v0.1",
        "eval_name": "benchmark-factory-development-boundary-audit",
        "evidence_class": "development",
        "fresh_evidence": False,
        "first_development_observation": True,
        "snapshot_commit": args.snapshot_commit,
        "family_count": len(manifests),
        "case_count": case_count,
        "split_counts": dict(sorted(split_counts.items())),
        "family_structure": {"passing": structure_pass, "total": len(manifests), "pass": structure_pass == len(manifests)},
        "heldout_policy_metadata": {"passing": heldout_policy_pass, "total": len(manifests), "pass": heldout_policy_pass == len(manifests)},
        "difficulty_metadata": {"passing": difficulty_metadata_pass, "total": len(manifests), "pass": difficulty_metadata_pass == len(manifests)},
        "materialization_referential_integrity": {"validator_exit_code": validator.returncode, "pass": validator.returncode == 0},
        "gold_readiness": {"gold_approved_families": gold_approved, "total": len(manifests), "pending": pending_gold, "pass": gold_approved == len(manifests)},
        "case_split_provenance_binding": split_binding,
        "decision_node_contract_schema": decision_contract,
        "model_prompt_gold_leakage_probe": prompt_probe,
        "training_export_heldout_guard_probe": export_probe,
        "hard_gate_failures": hard_failures,
        "release": "PASS" if not hard_failures else "FAIL",
        "notes": [
            "Existing P0 heldout-labelled cases are exposed repository assets and are not fresh evidence.",
            "This audit does not assert clinical validity or completed expert review.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["release"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
