#!/usr/bin/env python3
"""S5 v0.3 second genuinely fresh trust-boundary first observation.

The target implementation is frozen at c938dc86... before this evaluator and all
v0.3 fixtures existed. This suite attacks new trust-root compositions rather than
replaying the v0.2 F4-F7 probes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.3"
DEFAULT_PROTOCOL = EVAL_ROOT / "protocol-v0.3.json"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.3.json"
DEFAULT_FAMILY_ROOT = EVAL_ROOT / "families"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"
DECOY_MANIFEST = EVAL_ROOT / "decoy-authority/manifest.json"
DECOY_CASE = EVAL_ROOT / "decoy-authority/cases/S5FRESH-BND3-HO-001.json"


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_eval(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic v0.3 trust-boundary probe response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}
    except Exception as exc:
        return {"blocked": False, "exported": False, "error_type": type(exc).__name__, "unexpected_error": str(exc)}


def schema_exemption_aligned(schema: dict[str, Any]) -> bool:
    required = set(schema.get("required") or [])
    if "graph_eval" in required:
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

    protocol = load_json(args.protocol)
    suite = load_json(args.suite)
    schema = load_json(args.schema)
    freeze = str(protocol["target_implementation_freeze_commit"])

    target_rows: dict[str, dict[str, Any]] = {}
    for rel, expected in protocol["target_blob_contract"].items():
        observed = git_blob_sha(ROOT / rel)
        target_rows[rel] = {"expected_blob": expected, "observed_blob": observed, "match": observed == expected}
    frozen_identity = {
        "freeze_commit": freeze,
        "suite_declares_same_freeze": suite.get("implementation_freeze_commit") == freeze,
        "target_blobs": target_rows,
    }
    frozen_identity["pass"] = bool(frozen_identity["suite_declares_same_freeze"] and all(x["match"] for x in target_rows.values()))

    validator = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_medical_case_families.py"), "--root", str(args.family_root),
         "--expect-families", "1", "--expect-cases", "5", "--expect-cases-per-family", "5",
         "--rubric-version", "medical-clinical-v0.2"],
        cwd=ROOT, capture_output=True, text=True,
    )
    family_integrity = {"validator_exit_code": validator.returncode, "pass": validator.returncode == 0}

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_frozen_v021")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_frozen_v021")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_gate_frozen_v021")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_frozen_v021")

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-fresh-v03-") as td:
        td_path = Path(td)
        out_dir = td_path / "materialized"
        summary = materializer.materialize(args.suite, args.family_root, out_dir)
        paths = sorted(x for x in out_dir.rglob("*.json") if x.name != "materialization-manifest.json")
        cases = [load_json(x) for x in paths]
        split_counts: Counter[str] = Counter()
        by_split: dict[str, dict[str, Any]] = {}
        for case in cases:
            split = str((case.get("benchmark_provenance") or {}).get("split") or "")
            split_counts[split] += 1
            by_split.setdefault(split, case)
        materialization = {
            "family_count": summary.get("family_count"), "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
        }
        materialization["pass"] = bool(materialization == {
            "family_count": 1, "case_count": 5,
            "split_counts": {"dev": 3, "heldout": 1, "regression": 1},
            "training_eligible_count": 3, "training_blocked_count": 2,
        })

        baseline_dev = export_probe(exporter, by_split["dev"])
        baseline_reg = export_probe(exporter, by_split["regression"])
        baseline_ho = export_probe(exporter, by_split["heldout"])
        baseline_export = {"dev": baseline_dev, "regression": baseline_reg, "heldout": baseline_ho}
        baseline_export["pass"] = bool(baseline_dev["exported"] and baseline_reg["blocked"] and baseline_ho["blocked"])

        # F8: copy a raw benchmark heldout case outside a path containing "case-families".
        raw_heldout = args.family_root / "S5FRESH-BOUNDARY-002/cases/S5FRESH-BND3-HO-001.json"
        laundered_path = td_path / "ordinary-training-source.json"
        shutil.copyfile(raw_heldout, laundered_path)
        laundered_loaded = exporter.load_cases(laundered_path)["S5FRESH-BND3-HO-001"]
        laundered_result = export_probe(exporter, laundered_loaded)
        f8 = {
            "probe": "copy raw heldout benchmark case to ordinary path then load through trusted loader",
            "blocked": laundered_result["blocked"], "exported": laundered_result["exported"],
            "pass": laundered_result["blocked"],
        }

        # F9: mutate a materialized dev payload and recompute the self-contained digest.
        recomputed = copy.deepcopy(by_split["dev"])
        recomputed["interaction"]["prompt"] += " [ATTACKER_MUTATION_WITH_RECOMPUTED_DIGEST]"
        recomputed["benchmark_provenance"]["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(recomputed)
        recomputed_result = export_probe(exporter, recomputed)
        f9 = {
            "probe": "mutate materialized payload then recompute embedded SHA-256",
            "blocked": recomputed_result["blocked"], "exported": recomputed_result["exported"],
            "pass": recomputed_result["blocked"],
        }

        # F10: suite identity is case-local; forge it and recompute the embedded digest.
        suite_forged = copy.deepcopy(by_split["dev"])
        suite_forged["benchmark_provenance"]["suite_id"] = "S5-ATTACKER-FORGED-SUITE"
        suite_forged["benchmark_provenance"]["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(suite_forged)
        suite_forged_result = export_probe(exporter, suite_forged)
        f10 = {
            "probe": "forge suite_id while keeping family manifest authority unchanged",
            "blocked": suite_forged_result["blocked"], "exported": suite_forged_result["exported"],
            "pass": suite_forged_result["blocked"],
        }

        # F11: replace intended heldout family authority with a foreign repo-local manifest not listed by the suite.
        foreign = copy.deepcopy(by_split["heldout"])
        prov = foreign["benchmark_provenance"]
        prov["family_id"] = "S5FRESH-DECOY-AUTHORITY-001"
        prov["split"] = "dev"
        prov["training_eligible"] = True
        prov["source_manifest_path"] = DECOY_MANIFEST.relative_to(ROOT).as_posix()
        prov["source_case_path"] = DECOY_CASE.relative_to(ROOT).as_posix()
        prov["source_manifest_sha256"] = sha256_file(DECOY_MANIFEST)
        prov["source_case_sha256"] = sha256_file(DECOY_CASE)
        prov["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(foreign)
        foreign_result = export_probe(exporter, foreign)
        f11 = {
            "probe": "substitute foreign repo-local dev manifest not listed in frozen suite",
            "blocked": foreign_result["blocked"], "exported": foreign_result["exported"],
            "pass": foreign_result["blocked"],
        }

        exemption_case = copy.deepcopy(by_split["dev"])
        exemption_case.pop("benchmark_provenance", None)
        exemption_case.pop("graph_eval", None)
        exemption_case["decision_contract_exemption"] = {"type": "NON_REASONING_CONTROL", "rationale": "v0.3 alignment control"}
        materializer_accepts_exemption = True
        try:
            materializer.validate_decision_contract(exemption_case)
        except ValueError:
            materializer_accepts_exemption = False
        decision_alignment = {
            "materializer_accepts_exemption": materializer_accepts_exemption,
            "schema_accepts_exemption_shape": schema_exemption_aligned(schema),
        }
        decision_alignment["pass"] = bool(decision_alignment["materializer_accepts_exemption"] and decision_alignment["schema_accepts_exemption_shape"])

        sentinel = "S5_FRESH_V03_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        prompt_case["scoring"]["dimensions"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

    gold = release_gate.evaluate(args.suite, args.family_root)
    gold_containment = {
        "gold_approved_count": gold.get("gold_approved_count"), "pending_gold_count": gold.get("pending_gold_count"),
        "release_ready": gold.get("release_ready"), "decision": gold.get("decision"),
    }
    gold_containment["pass"] = bool(gold_containment["gold_approved_count"] == 0 and gold_containment["pending_gold_count"] == 1 and gold_containment["release_ready"] is False and gold_containment["decision"] == "BLOCKED_GOLD_REVIEW")

    hard_gates = {"S5-F8": f8, "S5-F9": f9, "S5-F10": f10, "S5-F11": f11}
    hard_failures = [name for name, gate in hard_gates.items() if not gate["pass"]]
    preconditions = {
        "FROZEN_TARGET_IDENTITY": frozen_identity,
        "FRESH_FAMILY_INTEGRITY": family_integrity,
        "FRESH_MATERIALIZATION": materialization,
        "BASELINE_PARTITION_EXPORT_GUARD": baseline_export,
        "DECISION_CONTRACT_ALIGNMENT": decision_alignment,
        "MODEL_PROMPT_GOLD_LEAKAGE": prompt_leakage,
        "GOLD_RELEASE_CONTAINMENT": gold_containment,
    }
    precondition_failures = [name for name, gate in preconditions.items() if not gate["pass"]]
    fresh_pass = not hard_failures and not precondition_failures

    result = {
        "stage": "S5", "version": "v0.3",
        "eval_name": "second-fresh-boundary-adversarial-first-observation",
        "evidence_class": "independent_fresh_structural", "fresh_evidence": True, "first_observation": True,
        "target_implementation_freeze_commit": freeze, "suite_id": suite.get("suite_id"),
        **preconditions, **hard_gates,
        "hard_gate_failures": hard_failures, "precondition_failures": precondition_failures,
        "fresh_structural_gate": "PASS" if fresh_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "notes": [
            "This is the first observation of a suite authored after the v0.2.1 implementation freeze.",
            "No implementation repair is applied before this observation is recorded.",
            "A structural PASS would still not create gold approval or clinical validation."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
