#!/usr/bin/env python3
"""S5 v0.2 first-use fresh adversarial boundary evaluation.

The target implementation was frozen before these fixtures were created.
This evaluator intentionally attacks generic benchmark-boundary invariants:
partition authority, fail-closed export, materialized-payload integrity,
decision-contract semantics, prompt leakage, and gold-release containment.

The first observation is immutable evidence. A FAIL must be reported before
any repair and this suite becomes exposed after first use.
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
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.2"
DEFAULT_PROTOCOL = DEFAULT_EVAL_ROOT / "protocol-v0.2.json"
DEFAULT_SUITE = DEFAULT_EVAL_ROOT / "suite-fresh-boundary-v0.2.json"
DEFAULT_FAMILY_ROOT = DEFAULT_EVAL_ROOT / "families"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"

PROVENANCE_REQUIRED = (
    "suite_id",
    "family_id",
    "split",
    "source_case_path",
    "source_manifest_path",
    "source_manifest_sha256",
    "source_case_sha256",
    "materializer_version",
    "training_eligible",
)
DECISION_REQUIRED = ("required_node_ids", "required_edge_ids", "expected_reasoning_path")


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
    return {
        "case_id": case_id,
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic first-use boundary probe response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {
            "blocked": False,
            "exported": result is not None,
            "error_type": None,
        }
    except PermissionError as exc:
        return {
            "blocked": True,
            "exported": False,
            "error_type": type(exc).__name__,
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    protocol = load_json(args.protocol)
    suite = load_json(args.suite)
    schema = load_json(args.schema)
    freeze = str(protocol["target_implementation_freeze_commit"])

    target_rows: dict[str, dict[str, Any]] = {}
    for rel, expected in protocol["target_blob_contract"].items():
        path = ROOT / rel
        observed = git_blob_sha(path)
        target_rows[rel] = {
            "expected_blob": expected,
            "observed_blob": observed,
            "match": observed == expected,
        }
    frozen_identity = {
        "freeze_commit": freeze,
        "suite_declares_same_freeze": suite.get("implementation_freeze_commit") == freeze,
        "target_blobs": target_rows,
    }
    frozen_identity["pass"] = bool(
        frozen_identity["suite_declares_same_freeze"]
        and all(x["match"] for x in target_rows.values())
    )

    validator = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_medical_case_families.py"),
            "--root",
            str(args.family_root),
            "--expect-families",
            "1",
            "--expect-cases",
            "5",
            "--expect-cases-per-family",
            "5",
            "--rubric-version",
            "medical-clinical-v0.2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    family_integrity = {
        "validator_exit_code": validator.returncode,
        "family_count_expected": 1,
        "case_count_expected": 5,
        "pass": validator.returncode == 0,
    }

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_frozen_v011")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_frozen_v011")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_gate_frozen_v011")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_frozen_v011")

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-fresh-v02-") as td:
        out_dir = Path(td) / "materialized"
        summary = materializer.materialize(args.suite, args.family_root, out_dir)
        materialized_paths = sorted(
            x for x in out_dir.rglob("*.json") if x.name != "materialization-manifest.json"
        )
        cases = [load_json(x) for x in materialized_paths]

        split_counts: Counter[str] = Counter()
        decision_ok = 0
        provenance_ok = 0
        by_split: dict[str, dict[str, Any]] = {}
        for case in cases:
            graph_eval = case.get("graph_eval") or {}
            if all(k in graph_eval for k in DECISION_REQUIRED):
                decision_ok += 1
            prov = case.get("benchmark_provenance") or {}
            split = str(prov.get("split") or "")
            split_counts[split] += 1
            by_split.setdefault(split, case)
            if all(prov.get(k) is not None and prov.get(k) != "" for k in PROVENANCE_REQUIRED):
                provenance_ok += 1

        materialization = {
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
            "decision_contract_cases": decision_ok,
            "provenance_complete_cases": provenance_ok,
        }
        materialization["pass"] = bool(
            materialization["family_count"] == 1
            and materialization["case_count"] == 5
            and materialization["split_counts"] == {"dev": 3, "heldout": 1, "regression": 1}
            and materialization["training_eligible_count"] == 3
            and materialization["training_blocked_count"] == 2
            and materialization["decision_contract_cases"] == 5
            and materialization["provenance_complete_cases"] == 5
        )

        baseline_dev = export_probe(exporter, by_split["dev"])
        baseline_reg = export_probe(exporter, by_split["regression"])
        baseline_heldout = export_probe(exporter, by_split["heldout"])
        baseline_export = {
            "dev": baseline_dev,
            "regression": baseline_reg,
            "heldout": baseline_heldout,
        }
        baseline_export["pass"] = bool(
            baseline_dev["exported"]
            and baseline_reg["blocked"]
            and baseline_heldout["blocked"]
        )

        forged = copy.deepcopy(by_split["heldout"])
        forged["benchmark_provenance"]["split"] = "dev"
        forged["benchmark_provenance"]["training_eligible"] = True
        forged_result = export_probe(exporter, forged)
        provenance_authority = {
            "probe": "heldout provenance relabeled to dev + training_eligible=true",
            "blocked": forged_result["blocked"],
            "exported": forged_result["exported"],
            "bypass_observed": forged_result["exported"],
            "pass": forged_result["blocked"],
        }

        stripped = copy.deepcopy(by_split["heldout"])
        stripped.pop("benchmark_provenance", None)
        stripped["split"] = "dev"
        stripped_result = export_probe(exporter, stripped)

        unknown = copy.deepcopy(by_split["heldout"])
        unknown["benchmark_provenance"]["split"] = "train"
        unknown["benchmark_provenance"]["training_eligible"] = True
        unknown_result = export_probe(exporter, unknown)

        eligible_flip = copy.deepcopy(by_split["heldout"])
        eligible_flip["benchmark_provenance"]["training_eligible"] = True
        eligible_flip_result = export_probe(exporter, eligible_flip)

        split_flip_ineligible = copy.deepcopy(by_split["heldout"])
        split_flip_ineligible["benchmark_provenance"]["split"] = "dev"
        split_flip_ineligible["benchmark_provenance"]["training_eligible"] = False
        split_flip_ineligible_result = export_probe(exporter, split_flip_ineligible)

        fail_closed = {
            "stripped_provenance_top_level_dev": {
                "blocked": stripped_result["blocked"],
                "exported": stripped_result["exported"],
                "bypass_observed": stripped_result["exported"],
            },
            "unknown_provenance_split_train": {
                "blocked": unknown_result["blocked"],
                "exported": unknown_result["exported"],
                "bypass_observed": unknown_result["exported"],
            },
            "heldout_with_eligible_true_control": {
                "blocked": eligible_flip_result["blocked"],
                "exported": eligible_flip_result["exported"],
            },
            "dev_with_eligible_false_control": {
                "blocked": split_flip_ineligible_result["blocked"],
                "exported": split_flip_ineligible_result["exported"],
            },
        }
        fail_closed["pass"] = bool(
            stripped_result["blocked"]
            and unknown_result["blocked"]
            and eligible_flip_result["blocked"]
            and split_flip_ineligible_result["blocked"]
        )

        mutated = copy.deepcopy(by_split["dev"])
        recorded_source_hash = mutated["benchmark_provenance"].get("source_case_sha256")
        mutated["interaction"]["prompt"] += " [TAMPERED_AFTER_MATERIALIZATION]"
        mutated_result = export_probe(exporter, mutated)
        payload_integrity = {
            "recorded_source_case_sha256_present": bool(recorded_source_hash),
            "materialized_payload_mutated_after_hash_binding": True,
            "tampered_payload_blocked": mutated_result["blocked"],
            "tampered_payload_exported": mutated_result["exported"],
            "integrity_enforced_before_export": mutated_result["blocked"],
            "pass": mutated_result["blocked"],
        }

        exemption_case = copy.deepcopy(by_split["dev"])
        exemption_case.pop("benchmark_provenance", None)
        exemption_case.pop("graph_eval", None)
        exemption_case["decision_contract_exemption"] = {
            "type": "NON_REASONING_CONTROL",
            "rationale": "Synthetic alignment probe.",
        }
        materializer_accepts = True
        try:
            materializer.validate_decision_contract(exemption_case)
        except ValueError:
            materializer_accepts = False
        root_required = set(schema.get("required") or [])
        schema_requires_graph = "graph_eval" in root_required
        schema_defines_exemption = "decision_contract_exemption" in (schema.get("properties") or {})
        schema_allows_exemption_without_graph = schema_defines_exemption and not schema_requires_graph
        decision_alignment = {
            "materializer_accepts_exemption_without_graph_eval": materializer_accepts,
            "schema_defines_typed_exemption": schema_defines_exemption,
            "schema_requires_graph_eval": schema_requires_graph,
            "schema_allows_exemption_without_graph_eval": schema_allows_exemption_without_graph,
            "pass": materializer_accepts == schema_allows_exemption_without_graph,
        }

        sentinel = "S5_FRESH_V02_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        prompt_case["scoring"]["dimensions"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {
            "sentinel_leaked": sentinel in rendered,
            "pass": sentinel not in rendered,
        }

    gold = release_gate.evaluate(args.suite, args.family_root)
    gold_containment = {
        "gold_approved_count": gold.get("gold_approved_count"),
        "pending_gold_count": gold.get("pending_gold_count"),
        "release_ready": gold.get("release_ready"),
        "decision": gold.get("decision"),
    }
    gold_containment["pass"] = bool(
        gold_containment["gold_approved_count"] == 0
        and gold_containment["pending_gold_count"] == 1
        and gold_containment["release_ready"] is False
        and gold_containment["decision"] == "BLOCKED_GOLD_REVIEW"
    )

    hard_failures: list[str] = []
    if not provenance_authority["pass"]:
        hard_failures.append("S5-F4")
    if not fail_closed["pass"]:
        hard_failures.append("S5-F5")
    if not payload_integrity["pass"]:
        hard_failures.append("S5-F6")
    if not decision_alignment["pass"]:
        hard_failures.append("S5-F7")
    precondition_failures = []
    for name, gate in (
        ("FROZEN_TARGET_IDENTITY", frozen_identity),
        ("FRESH_FAMILY_INTEGRITY", family_integrity),
        ("FRESH_MATERIALIZATION", materialization),
        ("BASELINE_PARTITION_EXPORT_GUARD", baseline_export),
        ("MODEL_PROMPT_GOLD_LEAKAGE", prompt_leakage),
        ("GOLD_RELEASE_CONTAINMENT", gold_containment),
    ):
        if not gate["pass"]:
            precondition_failures.append(name)

    fresh_pass = not hard_failures and not precondition_failures
    result = {
        "stage": "S5",
        "version": "v0.2",
        "eval_name": "fresh-boundary-adversarial-first-observation",
        "evidence_class": "independent_fresh_structural",
        "fresh_evidence": True,
        "first_observation": True,
        "target_implementation_freeze_commit": freeze,
        "suite_id": suite.get("suite_id"),
        "frozen_target_identity": frozen_identity,
        "fresh_family_integrity": family_integrity,
        "fresh_materialization": materialization,
        "baseline_partition_export_guard": baseline_export,
        "provenance_authority_tamper_resistance": provenance_authority,
        "unprovenanced_unknown_split_fail_closed": fail_closed,
        "materialized_payload_integrity_enforcement": payload_integrity,
        "decision_contract_exemption_alignment": decision_alignment,
        "model_prompt_gold_leakage": prompt_leakage,
        "gold_release_containment": gold_containment,
        "hard_gate_failures": hard_failures,
        "precondition_failures": precondition_failures,
        "fresh_structural_gate": "PASS" if fresh_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "notes": [
            "This is the first use of a new synthetic structural family created after the target implementation freeze.",
            "The suite becomes exposed after this first observation and must never be relabeled fresh.",
            "A structural fresh FAIL does not imply any clinical-performance conclusion.",
            "No expert or clinical gold approval is inferred."
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
