#!/usr/bin/env python3
"""S5 v0.8 genuinely fresh post-calibration lineage evaluation.

The target implementation is commit 62b791c. Every protocol, fixture and
expected outcome in this evaluator was authored after that commit was merged
and CI-confirmed. The first observation must be retained whether it passes or
fails; this script never repairs the frozen detector.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.8"
DEFAULT_PROTOCOL = EVAL_ROOT / "protocol-v0.8.json"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-lineage-v0.8.json"
FAMILY_ROOT = EVAL_ROOT / "families"
ATTACK_ROOT = EVAL_ROOT / "attack-sources"
CLEAN_ROOT = EVAL_ROOT / "clean-sources"
GOLD_CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
GOLD_CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"

ATTACKS = {
    "S5-F28": ("CROSS_LANGUAGE_LINEAGE_LAUNDERING", ATTACK_ROOT / "f28-cross-language.json"),
    "S5-F29": ("SEMANTIC_ABSTRACTION_LINEAGE_LAUNDERING", ATTACK_ROOT / "f29-semantic-abstraction.json"),
    "S5-F30": ("CROSS_FIELD_FLATTENING_LINEAGE_LAUNDERING", ATTACK_ROOT / "f30-cross-field-flattening.json"),
    "S5-F31": ("MULTI_PROTECTED_MOSAIC_LINEAGE_LAUNDERING", ATTACK_ROOT / "f31-multi-protected-mosaic.json"),
}
CLEAN = {
    "CLEAN-ENGLISH-SAME-DOMAIN": CLEAN_ROOT / "clean-english-same-domain.json",
    "CLEAN-CHINESE-SAME-DOMAIN": CLEAN_ROOT / "clean-chinese-same-domain.json",
}


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


def policy_probe(trust: Any, exporter: Any, source: Path, version: str) -> dict[str, Any]:
    builder_rejected = False
    exporter_rejected = False
    error = None
    policy = None
    try:
        policy = trust.build_policy(
            [(DEFAULT_SUITE, FAMILY_ROOT)],
            ordinary_sources=[source],
            policy_version=version,
        )
    except ValueError as exc:
        builder_rejected = True
        error = str(exc)
    if policy is not None:
        try:
            exporter._validate_policy_content(policy, version)
        except PermissionError as exc:
            exporter_rejected = True
            error = str(exc)
    return {
        "source": source.relative_to(ROOT).as_posix(),
        "policy_builder_rejected": builder_rejected,
        "exporter_policy_validator_rejected": exporter_rejected,
        "boundary_blocked": builder_rejected or exporter_rejected,
        "error": error,
    }


def detector_trace(lineage: Any, source: Path) -> dict[str, Any]:
    manifest = load_json(FAMILY_ROOT / "S5FRESH-LINEAGE-008/manifest.json")
    protected: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for ref in manifest["cases"]:
        case = load_json(FAMILY_ROOT / "S5FRESH-LINEAGE-008" / ref["path"])
        row = {"case_id": ref["case_id"], "split": ref["split"], "case": case}
        (protected if ref["split"] in lineage.PROTECTED_SPLITS else allowed).append(row)
    index = lineage.ReferenceIndex(protected, allowed)
    case = load_json(source)
    trace = lineage.detect_lineage(case, index, candidate_id=case["case_id"], reference_snapshot="fresh-v0.8")
    return {
        "decision": trace["decision"],
        "nearest_reference_id": trace.get("nearest_reference_id"),
        "record_similarity": trace.get("record_similarity"),
        "risk_score": trace.get("risk_score"),
        "exclusive_anchor_overlap": trace.get("exclusive_anchor_overlap", []),
        "reasons": trace.get("reasons", []),
        "method_version": trace.get("method_version"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    protocol = load_json(args.protocol)
    suite = load_json(args.suite)
    freeze = str(protocol["target_implementation_freeze_commit"])
    target_blobs: dict[str, dict[str, Any]] = {}
    for rel, expected in protocol["target_blob_contract"].items():
        observed = git_blob_sha(ROOT / rel)
        target_blobs[rel] = {"expected_blob": expected, "observed_blob": observed, "match": expected == observed}
    frozen_identity = {
        "freeze_commit": freeze,
        "suite_declares_same_freeze": suite.get("implementation_freeze_commit") == freeze,
        "target_blobs": target_blobs,
    }
    frozen_identity["pass"] = bool(
        frozen_identity["suite_declares_same_freeze"]
        and all(row["match"] for row in target_blobs.values())
    )

    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v08_frozen")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v08_frozen")
    lineage = load_module(ROOT / "scripts/s5_lineage_detector_v073.py", "s5_lineage_v08_frozen")
    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v08_frozen")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v08_frozen")

    trust_root = exporter.trust_root_status()
    trust_root["pass"] = bool(trust_root.get("pass"))

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v08-") as td:
        materialized = Path(td) / "materialized"
        summary = materializer.materialize(args.suite, FAMILY_ROOT, materialized)
        cases = [
            load_json(path) for path in materialized.rglob("*.json")
            if path.name != "materialization-manifest.json"
        ]
        split_counts: dict[str, int] = {}
        for case in cases:
            split = str((case.get("benchmark_provenance") or {}).get("split") or "")
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

    baseline_policy_ok = True
    baseline_exporter_ok = True
    baseline_error = None
    baseline_version = "s5-trust-root-v0.8-fresh-baseline"
    try:
        baseline_policy = trust.build_policy(
            [(args.suite, FAMILY_ROOT)], ordinary_sources=[], policy_version=baseline_version
        )
    except ValueError as exc:
        baseline_policy_ok = False
        baseline_exporter_ok = False
        baseline_error = str(exc)
    else:
        try:
            exporter._validate_policy_content(baseline_policy, baseline_version)
        except PermissionError as exc:
            baseline_exporter_ok = False
            baseline_error = str(exc)
    baseline = {
        "policy_builder_accepted": baseline_policy_ok,
        "exporter_policy_validator_accepted": baseline_exporter_ok,
        "error": baseline_error,
        "pass": baseline_policy_ok and baseline_exporter_ok,
    }

    hard_gates: dict[str, dict[str, Any]] = {}
    for gate_id, (name, path) in ATTACKS.items():
        probe = policy_probe(trust, exporter, path, f"s5-trust-root-v0.8-{gate_id.lower()}")
        trace = detector_trace(lineage, path)
        hard_gates[gate_id] = {
            "failure_name": name,
            "ground_truth": load_json(path).get("lineage_ground_truth"),
            **probe,
            "detector_trace": trace,
            "pass": bool(probe["boundary_blocked"] and trace["decision"] == "BLOCK"),
        }

    clean_controls: dict[str, dict[str, Any]] = {}
    for control_id, path in CLEAN.items():
        probe = policy_probe(trust, exporter, path, f"s5-trust-root-v0.8-{control_id.lower()}")
        trace = detector_trace(lineage, path)
        clean_controls[control_id] = {
            **probe,
            "detector_trace": trace,
            "pass": bool(not probe["boundary_blocked"] and trace["decision"] == "ALLOW"),
        }

    gold = release_gate.evaluate(GOLD_CARRIER_SUITE, GOLD_CARRIER_ROOT)
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

    preconditions = {
        "FROZEN_TARGET_IDENTITY": frozen_identity,
        "AUTHENTICATED_TRUST_ROOT": trust_root,
        "FRESH_SUITE_MATERIALIZATION": materialization,
        "FRESH_SUITE_BASELINE": baseline,
        "GOLD_RELEASE_CONTAINMENT": gold_containment,
    }
    hard_failures = [gate_id for gate_id, row in hard_gates.items() if not row["pass"]]
    clean_failures = [control_id for control_id, row in clean_controls.items() if not row["pass"]]
    precondition_failures = [name for name, row in preconditions.items() if not row["pass"]]
    fresh_pass = not hard_failures and not clean_failures and not precondition_failures

    result = {
        "stage": "S5",
        "version": "v0.8",
        "eval_name": "seventh-fresh-post-calibration-lineage-first-observation",
        "evidence_class": "independent_fresh_structural",
        "fresh_evidence": True,
        "first_observation": True,
        "target_implementation_freeze_commit": freeze,
        "eval_suite_id": suite.get("suite_id"),
        **preconditions,
        "hard_gates": hard_gates,
        "clean_controls": clean_controls,
        "hard_gate_failures": hard_failures,
        "clean_control_failures": clean_failures,
        "precondition_failures": precondition_failures,
        "fresh_structural_gate": "PASS" if fresh_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "notes": [
            "All v0.8 evaluator logic, benchmark cases, attack sources and clean controls were authored after the v0.7.3 merge freeze.",
            "The four transformations are absent from the v0.7.3 development calibration set.",
            "The first observation is retained unchanged whether PASS or FAIL.",
            "No implementation repair, gold approval, clinical validation, real-user evidence or S6 release claim is made."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
