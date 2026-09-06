#!/usr/bin/env python3
"""S5 v0.2.1 generic boundary repair exposed regression.

This evaluator reuses the already-exposed v0.2 fresh family only as regression
evidence. It does not create or relabel fresh evidence. The immutable v0.2 first
observation remains the historical record of S5-F4..F7.
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
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.2"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.2.json"
DEFAULT_FAMILY_ROOT = EVAL_ROOT / "families"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"
FIRST_OBSERVATION = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.2.json"
EXPECTED_FIRST_OBSERVATION_BLOB = "3de2ebfb66dcf46ff204c8dcfe08cb29b0b0f695"


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
            "ideal_response": "synthetic exposed-regression boundary probe response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}


def schema_exemption_contract(schema: dict[str, Any]) -> dict[str, Any]:
    root_required = set(schema.get("required") or [])
    properties = schema.get("properties") or {}
    exemption_defined = "decision_contract_exemption" in properties
    graph_defined = "graph_eval" in properties
    graph_unconditionally_required = "graph_eval" in root_required
    alternative_declared = False
    for block in schema.get("allOf") or []:
        for alt in block.get("anyOf") or []:
            req = set(alt.get("required") or [])
            if "decision_contract_exemption" in req:
                alternative_declared = True
    allows_exemption_without_graph = bool(
        exemption_defined and graph_defined and not graph_unconditionally_required and alternative_declared
    )
    return {
        "graph_defined": graph_defined,
        "exemption_defined": exemption_defined,
        "graph_unconditionally_required": graph_unconditionally_required,
        "decision_alternative_declared": alternative_declared,
        "allows_exemption_without_graph_eval": allows_exemption_without_graph,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    suite = load_json(args.suite)
    schema = load_json(args.schema)
    first_observation = load_json(FIRST_OBSERVATION)

    preservation = {
        "path": FIRST_OBSERVATION.relative_to(ROOT).as_posix(),
        "expected_git_blob_sha": EXPECTED_FIRST_OBSERVATION_BLOB,
        "observed_git_blob_sha": git_blob_sha(FIRST_OBSERVATION),
        "historical_gate": first_observation.get("fresh_structural_gate"),
        "historical_failures": first_observation.get("hard_gate_failures"),
    }
    preservation["pass"] = bool(
        preservation["observed_git_blob_sha"] == EXPECTED_FIRST_OBSERVATION_BLOB
        and preservation["historical_gate"] == "FAIL"
        and preservation["historical_failures"] == ["S5-F4", "S5-F5", "S5-F6", "S5-F7"]
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

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v021")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v021")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_gate_v021")

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v021-") as td:
        out_dir = Path(td) / "materialized"
        summary = materializer.materialize(args.suite, args.family_root, out_dir)
        materialized_paths = sorted(
            x for x in out_dir.rglob("*.json") if x.name != "materialization-manifest.json"
        )
        cases = [load_json(x) for x in materialized_paths]

        split_counts: Counter[str] = Counter()
        by_split: dict[str, dict[str, Any]] = {}
        digest_complete = 0
        digest_self_consistent = 0
        decision_contracts = 0
        for case in cases:
            prov = case.get("benchmark_provenance") or {}
            split = str(prov.get("split") or "")
            split_counts[split] += 1
            by_split.setdefault(split, case)
            if prov.get("materialized_payload_sha256"):
                digest_complete += 1
                if materializer.canonical_materialized_sha256(case) == prov.get("materialized_payload_sha256"):
                    digest_self_consistent += 1
            graph = case.get("graph_eval") or {}
            if all(k in graph for k in ("required_node_ids", "required_edge_ids", "expected_reasoning_path")):
                decision_contracts += 1

        materialization = {
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
            "decision_contract_cases": decision_contracts,
            "payload_digest_present_cases": digest_complete,
            "payload_digest_self_consistent_cases": digest_self_consistent,
        }
        materialization["pass"] = bool(
            materialization["family_count"] == 1
            and materialization["case_count"] == 5
            and materialization["split_counts"] == {"dev": 3, "heldout": 1, "regression": 1}
            and materialization["training_eligible_count"] == 3
            and materialization["training_blocked_count"] == 2
            and materialization["decision_contract_cases"] == 5
            and materialization["payload_digest_present_cases"] == 5
            and materialization["payload_digest_self_consistent_cases"] == 5
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
            baseline_dev["exported"] and baseline_reg["blocked"] and baseline_heldout["blocked"]
        )

        forged = copy.deepcopy(by_split["heldout"])
        forged["benchmark_provenance"]["split"] = "dev"
        forged["benchmark_provenance"]["training_eligible"] = True
        forged_result = export_probe(exporter, forged)
        f4 = {
            "probe": "heldout provenance relabeled to dev + training_eligible=true",
            "blocked": forged_result["blocked"],
            "exported": forged_result["exported"],
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

        f5 = {
            "stripped_provenance_top_level_dev": stripped_result,
            "unknown_provenance_split_train": unknown_result,
            "heldout_with_eligible_true_control": eligible_flip_result,
            "dev_with_eligible_false_control": split_flip_ineligible_result,
        }
        f5["pass"] = bool(
            stripped_result["blocked"]
            and unknown_result["blocked"]
            and eligible_flip_result["blocked"]
            and split_flip_ineligible_result["blocked"]
        )

        mutated = copy.deepcopy(by_split["dev"])
        recorded_digest = mutated["benchmark_provenance"].get("materialized_payload_sha256")
        mutated["interaction"]["prompt"] += " [TAMPERED_AFTER_MATERIALIZATION]"
        mutated_result = export_probe(exporter, mutated)
        f6 = {
            "recorded_materialized_payload_sha256_present": bool(recorded_digest),
            "tampered_payload_blocked": mutated_result["blocked"],
            "tampered_payload_exported": mutated_result["exported"],
            "pass": bool(recorded_digest) and mutated_result["blocked"],
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
        schema_contract = schema_exemption_contract(schema)
        f7 = {
            "materializer_accepts_exemption_without_graph_eval": materializer_accepts,
            **schema_contract,
        }
        f7["pass"] = bool(
            materializer_accepts and schema_contract["allows_exemption_without_graph_eval"]
        )

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

    gates = {
        "historical_first_observation_preservation": preservation,
        "exposed_family_integrity": family_integrity,
        "materialization_integrity": materialization,
        "baseline_partition_export_guard": baseline_export,
        "S5-F4": f4,
        "S5-F5": f5,
        "S5-F6": f6,
        "S5-F7": f7,
        "gold_release_containment": gold_containment,
    }
    hard_failures = [name for name in ("S5-F4", "S5-F5", "S5-F6", "S5-F7") if not gates[name]["pass"]]
    precondition_failures = [
        name for name in (
            "historical_first_observation_preservation",
            "exposed_family_integrity",
            "materialization_integrity",
            "baseline_partition_export_guard",
            "gold_release_containment",
        ) if not gates[name]["pass"]
    ]
    regression_pass = not hard_failures and not precondition_failures

    result = {
        "stage": "S5",
        "version": "v0.2.1",
        "eval_name": "generic-boundary-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "source_fresh_suite": "S5 v0.2 first observation; now exposed",
        "suite_id": suite.get("suite_id"),
        **gates,
        "historical_failure_disposition": {
            "S5-F4": "REPAIRED_EXPOSED_REGRESSION" if f4["pass"] else "OPEN",
            "S5-F5": "REPAIRED_EXPOSED_REGRESSION" if f5["pass"] else "OPEN",
            "S5-F6": "REPAIRED_EXPOSED_REGRESSION" if f6["pass"] else "OPEN",
            "S5-F7": "REPAIRED_EXPOSED_REGRESSION" if f7["pass"] else "OPEN",
        },
        "regression_gate": "PASS" if regression_pass else "FAIL",
        "hard_gate_failures": hard_failures,
        "precondition_failures": precondition_failures,
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_fresh_requirement": "freeze v0.2.1 implementation, then create a genuinely new boundary suite before bounded S5 structural release",
        "notes": [
            "The v0.2 suite is exposed regression evidence only and is not relabeled fresh.",
            "No gold approval, clinical validation, real-user evidence, or training gain is inferred.",
            "Regression PASS repairs F4-F7 but does not satisfy the independent gold-review release gate."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if regression_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
