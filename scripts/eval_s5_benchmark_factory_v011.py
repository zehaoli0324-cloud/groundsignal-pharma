#!/usr/bin/env python3
"""S5 v0.1.1 exposed structural regression for the benchmark factory.

This is not fresh held-out evidence. It verifies that the v0.1 boundary failures
have been structurally repaired or safely contained without fabricating gold
approval.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "medical/stage-evals/S5/suite-p0-exposed-v0.1.1.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def approved_eval(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic structural probe response",
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--schema", type=Path, default=ROOT / "medical/schemas/clinical-case.schema.json")
    p.add_argument("--implementation-parent", default="811a755120210a14863a485e31c42ed5d3dd5f28")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    suite = load_json(args.suite)
    schema = load_json(args.schema)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    graph_schema = props.get("graph_eval") or {}
    graph_required = set(graph_schema.get("required") or [])
    decision_components = ("required_node_ids", "required_edge_ids", "expected_reasoning_path")
    provenance_schema = props.get("benchmark_provenance") or {}
    provenance_required = set(provenance_schema.get("required") or [])
    provenance_components = ("suite_id", "family_id", "split", "source_case_path", "source_manifest_path", "materializer_version", "training_eligible")

    schema_gate = {
        "graph_eval_required": "graph_eval" in required,
        "decision_components_required": {k: k in graph_required for k in decision_components},
        "benchmark_provenance_defined": bool(provenance_schema),
        "provenance_components_required": {k: k in provenance_required for k in provenance_components},
    }
    schema_gate["pass"] = bool(
        schema_gate["graph_eval_required"]
        and all(schema_gate["decision_components_required"].values())
        and schema_gate["benchmark_provenance_defined"]
        and all(schema_gate["provenance_components_required"].values())
    )

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v011")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v011")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_gate_v011")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v011")

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v011-") as td:
        out_dir = Path(td) / "materialized"
        summary = materializer.materialize(args.suite, ROOT / "medical/case-families", out_dir)
        manifest = load_json(out_dir / "materialization-manifest.json")
        case_paths = sorted(p for p in out_dir.rglob("*.json") if p.name != "materialization-manifest.json")
        cases = [load_json(p) for p in case_paths]

        split_counts = Counter()
        decision_contract_ok = 0
        provenance_ok = 0
        provenance_errors: list[str] = []
        by_split: dict[str, dict[str, Any]] = {}

        for case in cases:
            graph_eval = case.get("graph_eval") or {}
            if all(k in graph_eval for k in decision_components):
                decision_contract_ok += 1
            prov = case.get("benchmark_provenance") or {}
            split = str(prov.get("split") or "")
            split_counts[split] += 1
            by_split.setdefault(split, case)
            required_values = [prov.get(k) for k in provenance_components]
            eligible_expected = split == "dev"
            if all(v is not None and v != "" for v in required_values) and prov.get("training_eligible") is eligible_expected:
                provenance_ok += 1
            else:
                provenance_errors.append(str(case.get("case_id")))

        materialization_gate = {
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
            "decision_contract_cases": decision_contract_ok,
            "provenance_complete_cases": provenance_ok,
            "provenance_errors": provenance_errors,
            "manifest_roundtrip_equal": manifest == summary,
        }
        materialization_gate["pass"] = bool(
            materialization_gate["family_count"] == 12
            and materialization_gate["case_count"] == 60
            and materialization_gate["split_counts"] == {"dev": 36, "heldout": 12, "regression": 12}
            and materialization_gate["training_eligible_count"] == 36
            and materialization_gate["training_blocked_count"] == 24
            and materialization_gate["decision_contract_cases"] == 60
            and materialization_gate["provenance_complete_cases"] == 60
            and materialization_gate["manifest_roundtrip_equal"]
        )

        export_guard = {}
        for split in ("heldout", "regression"):
            case = by_split[split]
            blocked = False
            error_type = None
            try:
                exporter.export_row(approved_eval(str(case["case_id"])), case, None)
            except PermissionError as exc:
                blocked = True
                error_type = type(exc).__name__
            export_guard[split] = {"blocked": blocked, "error_type": error_type}

        dev_case = by_split["dev"]
        dev_result = exporter.export_row(approved_eval(str(dev_case["case_id"])), dev_case, None)
        export_guard["dev"] = {
            "exportable": dev_result is not None,
            "source_split_propagated": bool(dev_result and dev_result[1].get("source_split") == "dev"),
            "source_family_propagated": bool(dev_result and dev_result[1].get("source_family_id")),
            "source_suite_propagated": bool(dev_result and dev_result[1].get("source_suite_id") == suite.get("suite_id")),
        }
        export_guard["pass"] = bool(
            export_guard["heldout"]["blocked"]
            and export_guard["regression"]["blocked"]
            and all(export_guard["dev"].values())
        )

        gold = release_gate.evaluate(args.suite, ROOT / "medical/case-families")
        gold_containment = {
            "gold_approved_count": gold.get("gold_approved_count"),
            "pending_gold_count": gold.get("pending_gold_count"),
            "release_ready": gold.get("release_ready"),
            "decision": gold.get("decision"),
            "pass": bool(
                gold.get("gold_approved_count") == 0
                and gold.get("pending_gold_count") == 12
                and gold.get("release_ready") is False
                and gold.get("decision") == "BLOCKED_GOLD_REVIEW"
            ),
        }

        sentinel = "S5_V011_GOLD_SENTINEL_DO_NOT_EXPOSE"
        probe_case = {
            "case_id": "S5-V011-PROMPT-PROBE",
            "patient_context": {"chief_complaint": "synthetic audit probe"},
            "interaction": {"prompt": "Answer the synthetic audit task.", "prior_turns": []},
            "expected_behavior": {"must_include": [sentinel]},
            "graph_eval": {"required_node_ids": ["n"], "required_edge_ids": ["e"], "expected_reasoning_path": [sentinel]},
            "safety": {"critical_errors": [sentinel]},
            "scoring": {"rubric_version": "audit", "dimensions": [sentinel]},
        }
        rendered = harness.build_user_prompt(probe_case, "")
        prompt_leakage = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

    structural_pass = bool(schema_gate["pass"] and materialization_gate["pass"] and export_guard["pass"] and gold_containment["pass"] and prompt_leakage["pass"])
    result = {
        "stage": "S5",
        "version": "v0.1.1",
        "eval_name": "benchmark-factory-structural-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": True,
        "implementation_parent": args.implementation_parent,
        "suite_id": suite.get("suite_id"),
        "schema_contract_gate": schema_gate,
        "materialization_gate": materialization_gate,
        "training_export_partition_guard": export_guard,
        "gold_release_containment": gold_containment,
        "model_prompt_gold_leakage_regression": prompt_leakage,
        "historical_failure_disposition": {
            "S5-F1": "REPAIRED_EXPOSED_REGRESSION",
            "S5-F2": "CONTAINED_RELEASE_BLOCKED_NO_FAKE_APPROVAL",
            "S5-F3": "REPAIRED_EXPOSED_REGRESSION"
        },
        "structural_gate": "PASS" if structural_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "release_grade_heldout_trust": "BLOCKED_PENDING_FRESH_S5_AFTER_FREEZE",
        "hard_gate_failures": [] if structural_pass else ["S5-V011-STRUCTURAL-REGRESSION"],
        "notes": [
            "This reuses exposed P0 assets and is not fresh held-out evidence.",
            "0/12 gold approval is intentionally preserved; the repair is the machine-enforced block, not invented approval.",
            "A genuinely fresh S5 suite may only be created after this implementation is frozen."
        ]
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if structural_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
