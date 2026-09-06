#!/usr/bin/env python3
"""S5 v0.4 third genuinely fresh policy-root first observation.

Target implementation is frozen at 64cd9288... before all v0.4 fixtures/evaluator
exist. This evaluator attacks the trust-policy root itself, not the already-exposed
F8-F11 paths.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4"
DEFAULT_PROTOCOL = EVAL_ROOT / "protocol-v0.4.json"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.4.json"
DEFAULT_FAMILY_ROOT = EVAL_ROOT / "families"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"
LAUNDERED = EVAL_ROOT / "attack-sources/laundered-heldout.json"
COLLISION_SUITE = EVAL_ROOT / "collision-authority/suite-collision-v0.4.json"
COLLISION_ROOT = EVAL_ROOT / "collision-authority/families"
REPLAY_SUITE = EVAL_ROOT / "replay-authority/suite-copy-v0.4.json"
REPLAY_ROOT = EVAL_ROOT / "replay-authority/families"
HO_CASE_ID = "S5FRESH-BND4-HO-001"

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()

def approved_eval(case_id: str) -> dict[str, Any]:
    return {"case_id": case_id, "training_candidate": {"review_status": "approved", "type": "sft", "ideal_response": "synthetic v0.4 policy-root probe response"}}

def export_probe(exporter: Any, case: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None, policy)
        return {"blocked": False, "exported": result is not None}
    except PermissionError:
        return {"blocked": True, "exported": False}

def materialized_cases(materializer: Any, suite: Path, root: Path, out: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = materializer.materialize(suite, root, out)
    paths = sorted(x for x in out.rglob("*.json") if x.name != "materialization-manifest.json")
    return summary, [load_json(x) for x in paths]

def schema_exemption_aligned(schema: dict[str, Any]) -> bool:
    if "graph_eval" in set(schema.get("required") or []):
        return False
    for block in schema.get("allOf") or []:
        for alt in block.get("anyOf") or []:
            if "decision_contract_exemption" in set(alt.get("required") or []):
                return True
    return False

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    protocol, suite, schema = load_json(args.protocol), load_json(args.suite), load_json(args.schema)
    freeze = str(protocol["target_implementation_freeze_commit"])

    target_rows = {}
    for rel, expected in protocol["target_blob_contract"].items():
        observed = git_blob_sha(ROOT / rel)
        target_rows[rel] = {"expected_blob": expected, "observed_blob": observed, "match": observed == expected}
    frozen_identity = {"freeze_commit": freeze, "suite_declares_same_freeze": suite.get("implementation_freeze_commit") == freeze, "target_blobs": target_rows}
    frozen_identity["pass"] = bool(frozen_identity["suite_declares_same_freeze"] and all(x["match"] for x in target_rows.values()))

    validator = subprocess.run([sys.executable, str(ROOT / "scripts/validate_medical_case_families.py"), "--root", str(args.family_root), "--expect-families", "1", "--expect-cases", "5", "--expect-cases-per-family", "5", "--rubric-version", "medical-clinical-v0.2"], cwd=ROOT, capture_output=True, text=True)
    family_integrity = {"validator_exit_code": validator.returncode, "pass": validator.returncode == 0}

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v04_frozen")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v04_frozen")
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v04_frozen")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v04_frozen")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v04_frozen")

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v04-") as td:
        td = Path(td)
        fresh_policy = trust.build_policy([(args.suite, args.family_root)])
        summary, cases = materialized_cases(materializer, args.suite, args.family_root, td / "fresh")
        by_split = {}
        split_counts = {}
        for case in cases:
            split = str(case["benchmark_provenance"]["split"])
            by_split.setdefault(split, case)
            split_counts[split] = split_counts.get(split, 0) + 1
        materialization = {"family_count": summary.get("family_count"), "case_count": summary.get("case_count"), "split_counts": dict(sorted(split_counts.items())), "training_eligible_count": summary.get("training_eligible_count"), "training_blocked_count": summary.get("training_blocked_count")}
        materialization["pass"] = materialization == {"family_count": 1, "case_count": 5, "split_counts": {"dev": 3, "heldout": 1, "regression": 1}, "training_eligible_count": 3, "training_blocked_count": 2}

        bdev = export_probe(exporter, by_split["dev"], fresh_policy)
        breg = export_probe(exporter, by_split["regression"], fresh_policy)
        bho = export_probe(exporter, by_split["heldout"], fresh_policy)
        baseline = {"dev": bdev, "regression": breg, "heldout": bho}
        baseline["pass"] = bool(bdev["exported"] and breg["blocked"] and bho["blocked"])

        ordinary_policy = trust.build_policy(ordinary_sources=[LAUNDERED])
        laundered_case = exporter.load_cases(LAUNDERED, ordinary_policy)[HO_CASE_ID]
        r12 = export_probe(exporter, laundered_case, ordinary_policy)
        f12 = {"probe": "caller-built policy allowlists copied heldout as ordinary source", **r12, "pass": r12["blocked"]}

        off_policy_path = td / "attacker-policy.json"
        off_policy_path.write_text(json.dumps(ordinary_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        off_policy = exporter.load_trust_policy(off_policy_path)
        off_case = exporter.load_cases(LAUNDERED, off_policy)[HO_CASE_ID]
        r13 = export_probe(exporter, off_case, off_policy)
        f13 = {"probe": "off-repository policy file becomes root authority", "policy_path_outside_repo": True, **r13, "pass": r13["blocked"]}

        collision_rejected = False
        collision_policy = None
        try:
            collision_policy = trust.build_policy([(args.suite, args.family_root), (COLLISION_SUITE, COLLISION_ROOT)])
        except ValueError:
            collision_rejected = True
        collision_result = {"blocked": True, "exported": False}
        if not collision_rejected:
            _, collision_cases = materialized_cases(materializer, COLLISION_SUITE, COLLISION_ROOT, td / "collision")
            collision_result = export_probe(exporter, collision_cases[0], collision_policy)
        f14 = {"probe": "same case_id trusted in two suites with heldout vs dev split", "policy_builder_rejected_collision": collision_rejected, **collision_result, "pass": collision_rejected or collision_result["blocked"]}

        replay_policy = trust.build_policy([(REPLAY_SUITE, REPLAY_ROOT)])
        _, replay_cases = materialized_cases(materializer, REPLAY_SUITE, REPLAY_ROOT, td / "replay")
        replay_result = export_probe(exporter, replay_cases[0], replay_policy)
        f15 = {"probe": "same suite blob replayed at alternate path/family root with heldout case declared dev", "same_suite_blob_as_genuine": git_blob_sha(REPLAY_SUITE) == git_blob_sha(args.suite), **replay_result, "pass": replay_result["blocked"]}

        bad_policy = copy.deepcopy(fresh_policy)
        suite_entry = bad_policy["benchmark_suites"][suite["suite_id"]]
        family_entry = suite_entry["families"]["S5FRESH-BOUNDARY-003"]
        family_entry["cases"]["S5FRESH-BND4-DEV-001"]["source_case_git_blob_sha1"] = "0" * 40
        source_mismatch = export_probe(exporter, by_split["dev"], bad_policy)
        source_blob_control = {**source_mismatch, "pass": source_mismatch["blocked"]}

        exemption = copy.deepcopy(by_split["dev"])
        exemption.pop("benchmark_provenance", None)
        exemption.pop("graph_eval", None)
        exemption["decision_contract_exemption"] = {"type": "NON_REASONING_CONTROL", "rationale": "v0.4 alignment control"}
        mat_accepts = True
        try:
            materializer.validate_decision_contract(exemption)
        except ValueError:
            mat_accepts = False
        decision_alignment = {"materializer_accepts_exemption": mat_accepts, "schema_accepts_exemption_shape": schema_exemption_aligned(schema)}
        decision_alignment["pass"] = bool(decision_alignment["materializer_accepts_exemption"] and decision_alignment["schema_accepts_exemption_shape"])

        sentinel = "S5_FRESH_V04_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

    gold = release_gate.evaluate(args.suite, args.family_root)
    gold_containment = {"gold_approved_count": gold.get("gold_approved_count"), "pending_gold_count": gold.get("pending_gold_count"), "release_ready": gold.get("release_ready"), "decision": gold.get("decision")}
    gold_containment["pass"] = bool(gold_containment["gold_approved_count"] == 0 and gold_containment["pending_gold_count"] == 1 and gold_containment["release_ready"] is False and gold_containment["decision"] == "BLOCKED_GOLD_REVIEW")

    hard = {"S5-F12": f12, "S5-F13": f13, "S5-F14": f14, "S5-F15": f15}
    hard_failures = [name for name, gate in hard.items() if not gate["pass"]]
    preconditions = {"FROZEN_TARGET_IDENTITY": frozen_identity, "FRESH_FAMILY_INTEGRITY": family_integrity, "FRESH_MATERIALIZATION": materialization, "BASELINE_PARTITION_EXPORT_GUARD": baseline, "SOURCE_BLOB_MISMATCH_CONTROL": source_blob_control, "DECISION_CONTRACT_ALIGNMENT": decision_alignment, "MODEL_PROMPT_GOLD_LEAKAGE": prompt_leakage, "GOLD_RELEASE_CONTAINMENT": gold_containment}
    precondition_failures = [name for name, gate in preconditions.items() if not gate["pass"]]
    fresh_pass = not hard_failures and not precondition_failures

    result = {"stage": "S5", "version": "v0.4", "eval_name": "third-fresh-policy-root-first-observation", "evidence_class": "independent_fresh_structural", "fresh_evidence": True, "first_observation": True, "target_implementation_freeze_commit": freeze, "suite_id": suite.get("suite_id"), **preconditions, **hard, "hard_gate_failures": hard_failures, "precondition_failures": precondition_failures, "fresh_structural_gate": "PASS" if fresh_pass else "FAIL", "stage_release": "BLOCKED_GOLD_REVIEW", "s6_automatic_trust": "BLOCKED", "notes": ["The trust policy is treated as a security root; this fresh evaluation asks whether callers can redefine that root without independent authentication.", "All v0.4 fixtures and attack authorities were authored after the v0.3.1 target implementation freeze.", "No clinical gold approval, real-patient validation, or model-training gain is inferred."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1

if __name__ == "__main__":
    raise SystemExit(main())
