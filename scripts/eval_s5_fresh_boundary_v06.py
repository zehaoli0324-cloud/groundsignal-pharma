#!/usr/bin/env python3
"""S5 v0.6 genuinely fresh identity/TOCTOU boundary first observation.

The target implementation is frozen at 60f74c7f30c007008ee73df3eed6eacf4a9bab0a
before this evaluator and every v0.6 attack fixture existed. This suite targets
identity canonicalization, transformed-source laundering, and check/read races.
No repair is applied before the first observation is recorded.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.6"
DEFAULT_PROTOCOL = EVAL_ROOT / "protocol-v0.6.json"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-boundary-v0.6.json"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"

CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"
CARRIER_FAMILY = "S5FRESH-BOUNDARY-003"
CARRIER_HELDOUT = CARRIER_ROOT / CARRIER_FAMILY / "cases/S5FRESH-BND4-HO-001.json"
ORDINARY_SOURCE = ROOT / "medical/examples/clinical-medication-safety-001.json"

DERIVED_SOURCE = EVAL_ROOT / "attack-sources/derived-heldout-ordinary.json"
TOCTOU_SOURCE = EVAL_ROOT / "attack-sources/toctou-ordinary.json"
UNICODE_ORDINARY = EVAL_ROOT / "attack-sources/unicode-collision-ordinary.json"
UNICODE_SUITE = EVAL_ROOT / "unicode-authority/suite-unicode-v0.6.json"
UNICODE_ROOT = EVAL_ROOT / "unicode-authority/families"

ORDINARY_CASE_ID = "clinical-medication-safety-001"
HELDOUT_CASE_ID = "S5FRESH-BND4-HO-001"
TOCTOU_CASE_ID = "S5FRESH-BND6-TOCTOU-ORD-001"
UNICODE_BENCHMARK_ID = "S5FRESH-BND6-ID-é"
UNICODE_ORDINARY_ID = "S5FRESH-BND6-ID-é"


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
            "ideal_response": "synthetic v0.6 identity/TOCTOU probe response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}
    except Exception as exc:
        return {
            "blocked": False,
            "exported": False,
            "error_type": type(exc).__name__,
            "unexpected_error": str(exc),
        }


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
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    protocol = load_json(args.protocol)
    eval_suite = load_json(args.suite)
    schema = load_json(args.schema)
    freeze = str(protocol["target_implementation_freeze_commit"])

    target_rows: dict[str, dict[str, Any]] = {}
    for rel, expected in protocol["target_blob_contract"].items():
        observed = git_blob_sha(ROOT / rel)
        target_rows[rel] = {
            "expected_blob": expected,
            "observed_blob": observed,
            "match": observed == expected,
        }
    frozen_identity = {
        "freeze_commit": freeze,
        "suite_declares_same_freeze": eval_suite.get("implementation_freeze_commit") == freeze,
        "target_blobs": target_rows,
    }
    frozen_identity["pass"] = bool(
        frozen_identity["suite_declares_same_freeze"]
        and all(x["match"] for x in target_rows.values())
    )

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v06_frozen")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v06_frozen")
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v06_frozen")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v06_frozen")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v06_frozen")

    trust_root = exporter.trust_root_status()
    trust_root["pass"] = bool(trust_root.get("pass"))

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v06-") as td:
        td_path = Path(td)
        carrier_out = td_path / "carrier"
        summary = materializer.materialize(CARRIER_SUITE, CARRIER_ROOT, carrier_out)
        paths = sorted(
            x for x in carrier_out.rglob("*.json")
            if x.name != "materialization-manifest.json"
        )
        cases = [load_json(x) for x in paths]
        by_split: dict[str, dict[str, Any]] = {}
        split_counts: dict[str, int] = {}
        for case in cases:
            split = str((case.get("benchmark_provenance") or {}).get("split") or "")
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

        bdev = export_probe(exporter, by_split["dev"])
        breg = export_probe(exporter, by_split["regression"])
        bho = export_probe(exporter, by_split["heldout"])
        baseline = {"dev": bdev, "regression": breg, "heldout": bho}
        baseline["pass"] = bool(bdev["exported"] and breg["blocked"] and bho["blocked"])

        ordinary_loaded = exporter.load_cases(ORDINARY_SOURCE)[ORDINARY_CASE_ID]
        ordinary_result = export_probe(exporter, ordinary_loaded)
        ordinary_baseline = {**ordinary_result, "pass": ordinary_result["exported"]}

        # F20: a transformed copy of an authenticated heldout case is given a new
        # case_id and submitted as an ordinary source. Exact blob/case_id guards
        # do not establish independence from benchmark-derived content.
        f20_builder_rejected = False
        f20_validator_rejected = False
        f20_policy = None
        try:
            f20_policy = trust.build_policy(
                [(CARRIER_SUITE, CARRIER_ROOT)],
                ordinary_sources=[DERIVED_SOURCE],
                policy_version="s5-trust-root-v0.6-derived-attack",
            )
        except ValueError:
            f20_builder_rejected = True
        if f20_policy is not None:
            try:
                exporter._validate_policy_content(
                    f20_policy, "s5-trust-root-v0.6-derived-attack"
                )
            except PermissionError:
                f20_validator_rejected = True
        derived_obj = load_json(DERIVED_SOURCE)
        f20 = {
            "probe": "transformed heldout benchmark copy is proposed as byte-distinct ordinary source",
            "derived_from_case_id": derived_obj.get("derived_from_case_id"),
            "policy_builder_rejected": f20_builder_rejected,
            "policy_content_validator_rejected": f20_validator_rejected,
            "pass": f20_builder_rejected or f20_validator_rejected,
        }

        # F21: Unicode canonically equivalent case identifiers must be treated as
        # the same namespace identity, not merely compared as raw code points.
        f21_builder_rejected = False
        f21_validator_rejected = False
        f21_policy = None
        try:
            f21_policy = trust.build_policy(
                [(UNICODE_SUITE, UNICODE_ROOT)],
                ordinary_sources=[UNICODE_ORDINARY],
                policy_version="s5-trust-root-v0.6-unicode-attack",
            )
        except ValueError:
            f21_builder_rejected = True
        if f21_policy is not None:
            try:
                exporter._validate_policy_content(
                    f21_policy, "s5-trust-root-v0.6-unicode-attack"
                )
            except PermissionError:
                f21_validator_rejected = True
        f21 = {
            "probe": "NFC benchmark case_id collides with canonically equivalent NFD ordinary case_id",
            "benchmark_case_id": UNICODE_BENCHMARK_ID,
            "ordinary_case_id": UNICODE_ORDINARY_ID,
            "nfc_equal": (
                unicodedata.normalize("NFC", UNICODE_BENCHMARK_ID)
                == unicodedata.normalize("NFC", UNICODE_ORDINARY_ID)
            ),
            "policy_builder_rejected": f21_builder_rejected,
            "policy_content_validator_rejected": f21_validator_rejected,
            "pass": f21_builder_rejected or f21_validator_rejected,
        }

        # F22: registry identity is hashed and then read in separate operations.
        # Simulate replacement exactly between those two operations. The hash is
        # still computed from the genuine trusted bytes.
        runtime_policy = EVAL_ROOT / "runtime-toctou-policy-v0.6.json"
        registry_path = exporter.TRUST_POLICY_REGISTRY_PATH
        registry_original = registry_path.read_text(encoding="utf-8")
        attack_policy_id = "s5-trust-root-v0.6-toctou-attack"
        attack_policy = trust.build_policy(
            ordinary_sources=[TOCTOU_SOURCE],
            policy_version=attack_policy_id,
        )
        runtime_policy.write_text(
            json.dumps(attack_policy, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        original_hash = exporter.git_blob_sha1
        attack_registry = {
            "registry_version": exporter.TRUST_POLICY_REGISTRY_VERSION,
            "default_policy_id": attack_policy_id,
            "policies": {
                attack_policy_id: {
                    "path": runtime_policy.relative_to(ROOT).as_posix(),
                    "git_blob_sha1": original_hash(runtime_policy),
                }
            },
        }
        attack_registry_text = (
            json.dumps(attack_registry, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        f22_state = {"triggered": False}

        def registry_race_hash(path: Path) -> str:
            target = Path(path).resolve()
            if target == registry_path.resolve():
                registry_path.write_text(registry_original, encoding="utf-8")
                digest = original_hash(registry_path)
                registry_path.write_text(attack_registry_text, encoding="utf-8")
                f22_state["triggered"] = True
                return digest
            return original_hash(Path(path))

        exporter.git_blob_sha1 = registry_race_hash
        try:
            f22_loaded = exporter.load_cases(TOCTOU_SOURCE)[TOCTOU_CASE_ID]
            f22_result = export_probe(exporter, f22_loaded)
        finally:
            exporter.git_blob_sha1 = original_hash
            registry_path.write_text(registry_original, encoding="utf-8")
            runtime_policy.unlink(missing_ok=True)
        f22 = {
            "probe": "replace authenticated registry after hash check but before JSON read",
            "race_triggered": f22_state["triggered"],
            **f22_result,
            "pass": f22_result["blocked"],
        }

        # F23: the canonical ordinary source is similarly hashed and then read.
        # The replacement preserves case_id but changes the payload.
        ordinary_original = ORDINARY_SOURCE.read_text(encoding="utf-8")
        malicious = json.loads(ordinary_original)
        marker = "S5_V06_POST_HASH_SOURCE_REPLACEMENT"
        malicious["interaction"]["prompt"] += f" [{marker}]"
        malicious_text = json.dumps(malicious, ensure_ascii=False, separators=(",", ":")) + "\n"
        original_hash = exporter.git_blob_sha1
        f23_state = {"triggered": False}

        def ordinary_race_hash(path: Path) -> str:
            target = Path(path).resolve()
            if target == ORDINARY_SOURCE.resolve():
                ORDINARY_SOURCE.write_text(ordinary_original, encoding="utf-8")
                digest = original_hash(ORDINARY_SOURCE)
                ORDINARY_SOURCE.write_text(malicious_text, encoding="utf-8")
                f23_state["triggered"] = True
                return digest
            return original_hash(Path(path))

        exporter.git_blob_sha1 = ordinary_race_hash
        try:
            f23_loaded = exporter.load_cases(ORDINARY_SOURCE)[ORDINARY_CASE_ID]
            marker_loaded = marker in str(f23_loaded.get("interaction", {}).get("prompt", ""))
            f23_result = export_probe(exporter, f23_loaded)
        finally:
            exporter.git_blob_sha1 = original_hash
            ORDINARY_SOURCE.write_text(ordinary_original, encoding="utf-8")
        f23 = {
            "probe": "replace authenticated ordinary source after hash check but before payload read",
            "race_triggered": f23_state["triggered"],
            "mutated_payload_loaded": marker_loaded,
            **f23_result,
            "pass": f23_result["blocked"],
        }

        exemption = copy.deepcopy(by_split["dev"])
        exemption.pop("benchmark_provenance", None)
        exemption.pop("graph_eval", None)
        exemption["decision_contract_exemption"] = {
            "type": "NON_REASONING_CONTROL",
            "rationale": "v0.6 alignment control",
        }
        materializer_accepts_exemption = True
        try:
            materializer.validate_decision_contract(exemption)
        except ValueError:
            materializer_accepts_exemption = False
        decision_alignment = {
            "materializer_accepts_exemption": materializer_accepts_exemption,
            "schema_accepts_exemption_shape": schema_exemption_aligned(schema),
        }
        decision_alignment["pass"] = bool(
            decision_alignment["materializer_accepts_exemption"]
            and decision_alignment["schema_accepts_exemption_shape"]
        )

        sentinel = "S5_FRESH_V06_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {
            "sentinel_leaked": sentinel in rendered,
            "pass": sentinel not in rendered,
        }

    gold = release_gate.evaluate(CARRIER_SUITE, CARRIER_ROOT)
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

    hard_gates = {
        "S5-F20": f20,
        "S5-F21": f21,
        "S5-F22": f22,
        "S5-F23": f23,
    }
    hard_failures = [name for name, gate in hard_gates.items() if not gate["pass"]]
    preconditions = {
        "FROZEN_TARGET_IDENTITY": frozen_identity,
        "AUTHENTICATED_TRUST_ROOT": trust_root,
        "CARRIER_MATERIALIZATION": materialization,
        "BASELINE_PARTITION_EXPORT_GUARD": baseline,
        "ORDINARY_SOURCE_BASELINE_EXPORT": ordinary_baseline,
        "DECISION_CONTRACT_ALIGNMENT": decision_alignment,
        "MODEL_PROMPT_GOLD_LEAKAGE": prompt_leakage,
        "GOLD_RELEASE_CONTAINMENT": gold_containment,
    }
    precondition_failures = [
        name for name, gate in preconditions.items() if not gate["pass"]
    ]
    fresh_pass = not hard_failures and not precondition_failures

    result = {
        "stage": "S5",
        "version": "v0.6",
        "eval_name": "fifth-fresh-identity-toctou-first-observation",
        "evidence_class": "independent_fresh_structural",
        "fresh_evidence": True,
        "first_observation": True,
        "target_implementation_freeze_commit": freeze,
        "eval_suite_id": eval_suite.get("suite_id"),
        "carrier_suite_id": eval_suite.get("carrier_suite_id"),
        **preconditions,
        **hard_gates,
        "hard_gate_failures": hard_failures,
        "precondition_failures": precondition_failures,
        "fresh_structural_gate": "PASS" if fresh_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "notes": [
            "All v0.6 evaluator logic and attack fixtures were authored after the v0.5.1 implementation freeze.",
            "Previously registered v0.4 cases are used only as authenticated carrier controls.",
            "No implementation repair is applied before this first observation is recorded.",
            "No expert approval, clinical validation, real-user evidence, or model-training gain is inferred.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
