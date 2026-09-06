#!/usr/bin/env python3
"""S5 v0.3.1 external trust-root repair exposed regression.

Reuses the already-observed v0.3 family only as exposed regression evidence.
The immutable v0.3 fresh FAIL remains the historical first observation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.3"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.3.json"
DEFAULT_FAMILY_ROOT = EVAL_ROOT / "families"
FIRST_OBSERVATION = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.3.json"
EXPECTED_FIRST_OBSERVATION_BLOB = "47e1669f724f8b2cab285ec0f689cb3819e068e2"
DECOY_MANIFEST = EVAL_ROOT / "decoy-authority/manifest.json"
DECOY_CASE = EVAL_ROOT / "decoy-authority/cases/S5FRESH-BND3-HO-001.json"
DEFAULT_POLICY = ROOT / "medical/configs/s5-trust-root-v0.3.1.json"


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
            "ideal_response": "synthetic v0.3.1 exposed-regression response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None, policy)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    p.add_argument("--trust-policy", type=Path, default=DEFAULT_POLICY)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    first = load_json(FIRST_OBSERVATION)
    preservation = {
        "expected_git_blob_sha": EXPECTED_FIRST_OBSERVATION_BLOB,
        "observed_git_blob_sha": git_blob_sha(FIRST_OBSERVATION),
        "historical_gate": first.get("fresh_structural_gate"),
        "historical_failures": first.get("hard_gate_failures"),
    }
    preservation["pass"] = bool(
        preservation["observed_git_blob_sha"] == EXPECTED_FIRST_OBSERVATION_BLOB
        and preservation["historical_gate"] == "FAIL"
        and preservation["historical_failures"] == ["S5-F8", "S5-F9", "S5-F10", "S5-F11"]
    )

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v031")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v031")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_gate_v031")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v031")
    policy = exporter.load_trust_policy(args.trust_policy)

    trusted_suite = (policy.get("benchmark_suites") or {}).get("S5-FRESH-BOUNDARY-v0.3") or {}
    trust_root = {
        "policy_version": policy.get("policy_version"),
        "suite_registered": bool(trusted_suite),
        "family_registered": "S5FRESH-BOUNDARY-002" in (trusted_suite.get("families") or {}),
        "ordinary_fixture_registered": "medical/examples/clinical-medication-safety-001.json" in (policy.get("ordinary_training_sources") or {}),
    }
    trust_root["pass"] = all(bool(trust_root[k]) for k in ("suite_registered", "family_registered", "ordinary_fixture_registered"))

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v031-") as td:
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
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
        }
        materialization["pass"] = bool(
            materialization["family_count"] == 1
            and materialization["case_count"] == 5
            and materialization["split_counts"] == {"dev": 3, "heldout": 1, "regression": 1}
            and materialization["training_eligible_count"] == 3
            and materialization["training_blocked_count"] == 2
        )

        baseline_dev = export_probe(exporter, by_split["dev"], policy)
        baseline_reg = export_probe(exporter, by_split["regression"], policy)
        baseline_ho = export_probe(exporter, by_split["heldout"], policy)
        baseline = {"dev": baseline_dev, "regression": baseline_reg, "heldout": baseline_ho}
        baseline["pass"] = bool(baseline_dev["exported"] and baseline_reg["blocked"] and baseline_ho["blocked"])

        raw_heldout = args.family_root / "S5FRESH-BOUNDARY-002/cases/S5FRESH-BND3-HO-001.json"
        laundered_path = td_path / "ordinary-training-source.json"
        shutil.copyfile(raw_heldout, laundered_path)
        f8_blocked = False
        try:
            loaded = exporter.load_cases(laundered_path, policy)["S5FRESH-BND3-HO-001"]
            f8_probe = export_probe(exporter, loaded, policy)
            f8_blocked = bool(f8_probe["blocked"])
        except PermissionError:
            f8_blocked = True
        f8 = {"blocked": f8_blocked, "pass": f8_blocked}

        recomputed = copy.deepcopy(by_split["dev"])
        recomputed["interaction"]["prompt"] += " [ATTACKER_MUTATION_WITH_RECOMPUTED_DIGEST]"
        recomputed["benchmark_provenance"]["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(recomputed)
        f9_probe = export_probe(exporter, recomputed, policy)
        f9 = {"blocked": f9_probe["blocked"], "pass": f9_probe["blocked"]}

        suite_forged = copy.deepcopy(by_split["dev"])
        suite_forged["benchmark_provenance"]["suite_id"] = "S5-ATTACKER-FORGED-SUITE"
        suite_forged["benchmark_provenance"]["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(suite_forged)
        f10_probe = export_probe(exporter, suite_forged, policy)
        f10 = {"blocked": f10_probe["blocked"], "pass": f10_probe["blocked"]}

        foreign = copy.deepcopy(by_split["heldout"])
        prov = foreign["benchmark_provenance"]
        prov["family_id"] = "S5FRESH-DECOY-AUTHORITY-001"
        prov["split"] = "dev"
        prov["training_eligible"] = True
        prov["source_manifest_path"] = DECOY_MANIFEST.relative_to(ROOT).as_posix()
        prov["source_case_path"] = DECOY_CASE.relative_to(ROOT).as_posix()
        prov["source_manifest_sha256"] = exporter.sha256_file(DECOY_MANIFEST)
        prov["source_case_sha256"] = exporter.sha256_file(DECOY_CASE)
        prov["materialized_payload_sha256"] = exporter.canonical_materialized_sha256(foreign)
        f11_probe = export_probe(exporter, foreign, policy)
        f11 = {"blocked": f11_probe["blocked"], "pass": f11_probe["blocked"]}

        ordinary_path = ROOT / "medical/examples/clinical-medication-safety-001.json"
        ordinary_case = exporter.load_cases(ordinary_path, policy)["clinical-medication-safety-001"]
        ordinary_probe = export_probe(exporter, ordinary_case, policy)
        ordinary_control = {"exported": ordinary_probe["exported"], "blocked": ordinary_probe["blocked"], "pass": ordinary_probe["exported"]}

        sentinel = "S5_V031_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        prompt_case["scoring"]["dimensions"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

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
        "external_trust_root": trust_root,
        "materialization": materialization,
        "baseline_partition_export": baseline,
        "S5-F8": f8,
        "S5-F9": f9,
        "S5-F10": f10,
        "S5-F11": f11,
        "ordinary_source_allowlist_control": ordinary_control,
        "model_prompt_gold_leakage": prompt_leakage,
        "gold_release_containment": gold_containment,
    }
    failed = [name for name, gate in gates.items() if not gate.get("pass")]
    passed = not failed
    result = {
        "stage": "S5",
        "version": "v0.3.1",
        "eval_name": "external-trust-root-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "source_fresh_suite": "S5 v0.3 first observation; now exposed",
        **gates,
        "historical_failure_disposition": {
            "S5-F8": "REPAIRED_EXPOSED_REGRESSION" if f8["pass"] else "OPEN",
            "S5-F9": "REPAIRED_EXPOSED_REGRESSION" if f9["pass"] else "OPEN",
            "S5-F10": "REPAIRED_EXPOSED_REGRESSION" if f10["pass"] else "OPEN",
            "S5-F11": "REPAIRED_EXPOSED_REGRESSION" if f11["pass"] else "OPEN",
        },
        "failed_gates": failed,
        "regression_gate": "PASS" if passed else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_fresh_requirement": "freeze v0.3.1, then author a new trust-root fresh suite; v0.3 is exposed forever",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
