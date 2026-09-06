#!/usr/bin/env python3
"""S5 v0.4.1 policy-root repair exposed regression.

The v0.4 suite is already exposed. This evaluator preserves its immutable first
fresh FAIL and uses it only as regression evidence for F12-F15.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.4.json"
DEFAULT_FAMILY_ROOT = EVAL_ROOT / "families"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"
FIRST_OBSERVATION = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.4.json"
EXPECTED_FIRST_OBSERVATION_BLOB = "45a10ed2cc522b555a3f3eecf785dffedf8cd4c3"
LAUNDERED = EVAL_ROOT / "attack-sources/laundered-heldout.json"
COLLISION_SUITE = EVAL_ROOT / "collision-authority/suite-collision-v0.4.json"
COLLISION_ROOT = EVAL_ROOT / "collision-authority/families"
REPLAY_SUITE = EVAL_ROOT / "replay-authority/suite-copy-v0.4.json"
REPLAY_ROOT = EVAL_ROOT / "replay-authority/families"
V02_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.2/suite-fresh-boundary-v0.2.json"
V02_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.2/families"
V03_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.3/suite-fresh-boundary-v0.3.json"
V03_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.3/families"
ORDINARY = ROOT / "medical/examples/clinical-medication-safety-001.json"
DEFAULT_POLICY = ROOT / "medical/configs/s5-trust-root-v0.4.1.json"


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
            "ideal_response": "synthetic v0.4.1 exposed-regression response",
        },
    }


def export_probe(
    exporter: Any, case: dict[str, Any], policy: dict[str, Any] | Path | None = None
) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None, policy)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}


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
    p.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    p.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
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
        and preservation["historical_failures"] == ["S5-F12", "S5-F13", "S5-F14", "S5-F15"]
    )

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v041")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v041")
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v041")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v041")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v041")
    schema = load_json(args.schema)

    trust_root = exporter.trust_root_status()
    policy = exporter.load_trust_policy(args.trust_policy)

    rebuilt = trust.build_policy(
        [
            (V02_SUITE, V02_ROOT),
            (V03_SUITE, V03_ROOT),
            (args.suite, args.family_root),
        ],
        [ORDINARY],
        policy_version="s5-trust-root-v0.4.1",
    )
    canonical_policy_rebuild = {
        "match": rebuilt == load_json(args.trust_policy),
        "pass": rebuilt == load_json(args.trust_policy),
    }

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v041-") as td_raw:
        td = Path(td_raw)
        out_dir = td / "materialized"
        summary = materializer.materialize(args.suite, args.family_root, out_dir)
        paths = sorted(x for x in out_dir.rglob("*.json") if x.name != "materialization-manifest.json")
        cases = [load_json(x) for x in paths]
        by_split: dict[str, dict[str, Any]] = {}
        split_counts: dict[str, int] = {}
        for case in cases:
            split = str(case["benchmark_provenance"]["split"])
            by_split.setdefault(split, case)
            split_counts[split] = split_counts.get(split, 0) + 1

        materialization = {
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
        }
        materialization["pass"] = materialization == {
            "family_count": 1,
            "case_count": 5,
            "split_counts": {"dev": 3, "heldout": 1, "regression": 1},
            "training_eligible_count": 3,
            "training_blocked_count": 2,
        }

        dev = export_probe(exporter, by_split["dev"], policy)
        reg = export_probe(exporter, by_split["regression"], policy)
        heldout = export_probe(exporter, by_split["heldout"], policy)
        baseline = {
            "dev": "EXPORTABLE" if dev["exported"] else "BLOCKED",
            "regression": "BLOCKED" if reg["blocked"] else "EXPORTABLE",
            "heldout": "BLOCKED" if heldout["blocked"] else "EXPORTABLE",
        }
        baseline["pass"] = bool(dev["exported"] and reg["blocked"] and heldout["blocked"])

        caller_policy = trust.build_policy(ordinary_sources=[LAUNDERED])
        f12_blocked = False
        try:
            laundered_case = exporter.load_cases(LAUNDERED, caller_policy)
            only_case = next(iter(laundered_case.values()))
            f12_blocked = export_probe(exporter, only_case, caller_policy)["blocked"]
        except PermissionError:
            f12_blocked = True
        f12 = {"blocked": f12_blocked, "pass": f12_blocked}

        off_policy_path = td / "attacker-policy.json"
        off_policy_path.write_text(
            json.dumps(caller_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        f13_blocked = False
        try:
            exporter.load_trust_policy(off_policy_path)
        except PermissionError:
            f13_blocked = True
        f13 = {"policy_path_outside_repo": True, "blocked": f13_blocked, "pass": f13_blocked}

        collision_rejected = False
        try:
            trust.build_policy(
                [(args.suite, args.family_root), (COLLISION_SUITE, COLLISION_ROOT)]
            )
        except ValueError:
            collision_rejected = True
        f14 = {
            "policy_builder_rejected_collision": collision_rejected,
            "blocked": collision_rejected,
            "pass": collision_rejected,
        }

        replay_policy = trust.build_policy([(REPLAY_SUITE, REPLAY_ROOT)])
        replay_out = td / "replay-materialized"
        materializer.materialize(REPLAY_SUITE, REPLAY_ROOT, replay_out)
        replay_paths = sorted(
            x for x in replay_out.rglob("*.json") if x.name != "materialization-manifest.json"
        )
        replay_case = load_json(replay_paths[0])
        replay_probe = export_probe(exporter, replay_case, replay_policy)
        f15 = {
            "same_suite_blob_as_genuine": git_blob_sha(REPLAY_SUITE) == git_blob_sha(args.suite),
            "blocked": replay_probe["blocked"],
            "pass": replay_probe["blocked"],
        }

        ordinary_case = exporter.load_cases(ORDINARY, policy)["clinical-medication-safety-001"]
        ordinary_probe = export_probe(exporter, ordinary_case, policy)
        ordinary_control = {
            "exported": ordinary_probe["exported"],
            "blocked": ordinary_probe["blocked"],
            "pass": ordinary_probe["exported"],
        }

        exemption = copy.deepcopy(by_split["dev"])
        exemption.pop("benchmark_provenance", None)
        exemption.pop("graph_eval", None)
        exemption["decision_contract_exemption"] = {
            "type": "NON_REASONING_CONTROL",
            "rationale": "v0.4.1 alignment control",
        }
        materializer_accepts = True
        try:
            materializer.validate_decision_contract(exemption)
        except ValueError:
            materializer_accepts = False
        decision_alignment = {
            "materializer_accepts_exemption": materializer_accepts,
            "schema_accepts_exemption_shape": schema_exemption_aligned(schema),
        }
        decision_alignment["pass"] = bool(
            decision_alignment["materializer_accepts_exemption"]
            and decision_alignment["schema_accepts_exemption_shape"]
        )

        sentinel = "S5_V041_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
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
        "trust_root": trust_root,
        "canonical_policy_rebuild": canonical_policy_rebuild,
        "materialization": materialization,
        "baseline_partition_export_guard": baseline,
        "S5-F12": f12,
        "S5-F13": f13,
        "S5-F14": f14,
        "S5-F15": f15,
        "ordinary_source_allowlist_control": ordinary_control,
        "decision_contract_alignment": decision_alignment,
        "model_prompt_gold_leakage": prompt_leakage,
        "gold_release_containment": gold_containment,
    }
    failed = [name for name, gate in gates.items() if not gate.get("pass")]
    passed = not failed
    result = {
        "stage": "S5",
        "version": "v0.4.1",
        "eval_name": "policy-root-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "source_fresh_suite": "S5 v0.4 first observation; now exposed",
        **gates,
        "historical_failure_disposition": {
            "S5-F12": "REPAIRED_EXPOSED_REGRESSION" if f12["pass"] else "OPEN",
            "S5-F13": "REPAIRED_EXPOSED_REGRESSION" if f13["pass"] else "OPEN",
            "S5-F14": "REPAIRED_EXPOSED_REGRESSION" if f14["pass"] else "OPEN",
            "S5-F15": "REPAIRED_EXPOSED_REGRESSION" if f15["pass"] else "OPEN",
        },
        "failed_gates": failed,
        "regression_gate": "PASS" if passed else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_fresh_requirement": (
            "freeze v0.4.1 then author a new post-freeze policy-root suite; "
            "v0.4 is exposed forever"
        ),
        "notes": [
            "v0.4 is exposed regression evidence only; its fresh FAIL remains immutable.",
            "The registry authenticates policy path and Git-blob identity above caller-selected policy data.",
            "No clinical gold approval, real-patient validation, or model-training gain is inferred.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
