#!/usr/bin/env python3
"""S5 v0.9 genuinely fresh post-v0.8.1-repair lineage evaluation.

The protocol, fixtures and expected outcomes were authored only after the
canonical v0.8.1 implementation freeze and its separate receipt commit. The
first observation is immutable whether it passes or fails. This evaluator does
not modify or calibrate the frozen detector.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.9"
DEFAULT_PROTOCOL = EVAL_ROOT / "protocol-v0.9.json"
DEFAULT_SUITE = EVAL_ROOT / "suite-fresh-lineage-v0.9.json"
FAMILY_ROOT = EVAL_ROOT / "families"
ATTACK_ROOT = EVAL_ROOT / "attack-sources"
CLEAN_ROOT = EVAL_ROOT / "clean-sources"
RECEIPT = ROOT / "medical/stage-evals/S5/freeze-receipt-v0.8.1.json"
GOLD_CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
GOLD_CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"

ATTACKS = {
    "S5-F32": ("UNSEEN_SCRIPT_TRANSLATION", ATTACK_ROOT / "f32-unseen-script-korean.json"),
    "S5-F33": ("UNIT_TIME_ALIAS_LAUNDERING", ATTACK_ROOT / "f33-unit-time-alias.json"),
    "S5-F34": ("GRAPH_ROLE_COMPRESSION", ATTACK_ROOT / "f34-graph-role-compression.json"),
    "S5-F35": ("SUBTHRESHOLD_THREE_SOURCE_MOSAIC", ATTACK_ROOT / "f35-subthreshold-three-source-mosaic.json"),
    "S5-F36": ("IDENTIFIER_WORDING_AND_CODE_SWITCHING", ATTACK_ROOT / "f36-code-switched-identifier-wording.json"),
}
CLEAN = {
    "CLEAN-KOREAN-SAME-DOMAIN": CLEAN_ROOT / "clean-korean-same-domain.json",
    "CLEAN-NUMERIC-NEAR-NEIGHBOUR": CLEAN_ROOT / "clean-numeric-near-neighbour.json",
    "CLEAN-MULTI-CASE-SUMMARY": CLEAN_ROOT / "clean-multi-case-summary.json",
    "CLEAN-JAPANESE-IMAGING": CLEAN_ROOT / "clean-japanese-imaging.json",
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


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy_probe(trust: Any, exporter: Any, source: Path, version: str) -> dict[str, Any]:
    builder_rejected = False
    exporter_rejected = False
    error = None
    policy = None
    try:
        policy = trust.build_policy(
            [(DEFAULT_SUITE, FAMILY_ROOT)], ordinary_sources=[source],
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
    family = FAMILY_ROOT / "S5FRESH-LINEAGE-009"
    manifest = load_json(family / "manifest.json")
    protected: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for ref in manifest["cases"]:
        case = load_json(family / ref["path"])
        row = {"case_id": ref["case_id"], "split": ref["split"], "case": case}
        (protected if ref["split"] in lineage.PROTECTED_SPLITS else allowed).append(row)
    index = lineage.ReferenceIndex(protected, allowed)
    case = load_json(source)
    trace = lineage.detect_lineage(
        case, index, candidate_id=case["case_id"], reference_snapshot="fresh-v0.9",
    )
    return {
        "decision": trace["decision"],
        "nearest_reference_id": trace.get("nearest_reference_id"),
        "record_similarity": trace.get("record_similarity"),
        "risk_score": trace.get("risk_score"),
        "exclusive_anchor_overlap": trace.get("exclusive_anchor_overlap", []),
        "exclusive_identifier_overlap": trace.get("exclusive_identifier_overlap", []),
        "semantic_concept_overlap": trace.get("semantic_concept_overlap", []),
        "semantic_numeric_overlap": trace.get("semantic_numeric_overlap", []),
        "mosaic_reference_matches": trace.get("mosaic_reference_matches", []),
        "candidate_language": trace.get("candidate_language"),
        "cross_language_pair": trace.get("cross_language_pair"),
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
    receipt_commit = str(protocol["freeze_receipt_materialization_commit"])

    target_blobs: dict[str, dict[str, Any]] = {}
    for rel, expected in protocol["target_blob_contract"].items():
        observed = git_blob_sha(ROOT / rel)
        at_freeze = git("rev-parse", f"{freeze}:{rel}")
        frozen_blob = at_freeze.stdout.strip() if at_freeze.returncode == 0 else None
        target_blobs[rel] = {
            "expected_blob": expected,
            "observed_blob": observed,
            "freeze_commit_blob": frozen_blob,
            "match": expected == observed == frozen_blob,
        }
    frozen_identity = {
        "freeze_commit": freeze,
        "suite_declares_same_freeze": suite.get("implementation_freeze_commit") == freeze,
        "freeze_on_origin_main": git("merge-base", "--is-ancestor", freeze, "origin/main").returncode == 0,
        "target_blobs": target_blobs,
    }
    frozen_identity["pass"] = bool(
        frozen_identity["suite_declares_same_freeze"]
        and frozen_identity["freeze_on_origin_main"]
        and all(row["match"] for row in target_blobs.values())
    )

    receipt_absent_at_freeze = git(
        "cat-file", "-e", f"{freeze}:medical/stage-evals/S5/freeze-receipt-v0.8.1.json"
    ).returncode != 0
    fresh_absent_at_receipt = git(
        "cat-file", "-e", f"{receipt_commit}:medical/stage-evals/S5/fresh-lineage-v0.9"
    ).returncode != 0
    chronology = {
        "receipt_materialization_commit": receipt_commit,
        "freeze_is_parent_of_receipt": git("merge-base", "--is-ancestor", freeze, receipt_commit).returncode == 0,
        "receipt_is_ancestor_of_observation_head": git("merge-base", "--is-ancestor", receipt_commit, "HEAD").returncode == 0,
        "receipt_absent_at_freeze": receipt_absent_at_freeze,
        "fresh_assets_absent_at_receipt_commit": fresh_absent_at_receipt,
    }
    chronology["pass"] = all(value for key, value in chronology.items() if key not in {"receipt_materialization_commit", "pass"})

    admission_module = load_module(
        ROOT / "scripts/check_s5_next_fresh_admission.py", "s5_v09_admission_first_observation",
    )
    admission_result = admission_module.evaluate(RECEIPT, EVAL_ROOT)
    admission = {
        "decision": admission_result.get("admission_decision"),
        "receipt_valid": admission_result.get("receipt_valid"),
        "fresh_assets_present": admission_result.get("fresh_assets_present"),
        "fresh_protocol_valid": admission_result.get("fresh_protocol_valid"),
        "fresh_authoring_allowed": admission_result.get("fresh_authoring_allowed"),
        "failures": admission_result.get("failures"),
        "pass": bool(
            admission_result.get("guard_gate") == "PASS"
            and admission_result.get("admission_decision") == "ALLOW_AFTER_VERIFIED_FREEZE"
            and admission_result.get("receipt_valid") is True
            and admission_result.get("fresh_assets_present") is True
            and admission_result.get("fresh_protocol_valid") is True
        ),
    }

    asset_hashes = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(EVAL_ROOT.rglob("*.json"))
    }

    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v09_frozen")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v09_frozen")
    lineage = load_module(ROOT / "scripts/s5_lineage_detector_v081.py", "s5_lineage_v09_frozen")
    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v09_frozen")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v09_frozen")

    trust_root = exporter.trust_root_status()
    trust_root["pass"] = bool(trust_root.get("pass"))

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v09-") as td:
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
            "case_count": 6,
            "split_counts": {"dev": 3, "heldout": 2, "regression": 1},
            "training_eligible_count": 3,
            "training_blocked_count": 3,
        }

    baseline_policy_ok = True
    baseline_exporter_ok = True
    baseline_error = None
    baseline_version = "s5-trust-root-v0.9-fresh-baseline"
    try:
        baseline_policy = trust.build_policy(
            [(args.suite, FAMILY_ROOT)], ordinary_sources=[], policy_version=baseline_version,
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
        probe = policy_probe(trust, exporter, path, f"s5-trust-root-v0.9-{gate_id.lower()}")
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
        probe = policy_probe(trust, exporter, path, f"s5-trust-root-v0.9-{control_id.lower()}")
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
        "FRESHNESS_CHRONOLOGY": chronology,
        "AUTHORING_ADMISSION": admission,
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
        "version": "v0.9",
        "eval_name": "eighth-fresh-post-repair-lineage-first-observation",
        "evidence_class": "independent_fresh_structural",
        "fresh_evidence": True,
        "first_observation": True,
        "target_implementation_freeze_commit": freeze,
        "freeze_receipt_materialization_commit": receipt_commit,
        "eval_suite_id": suite.get("suite_id"),
        "fresh_asset_sha256": asset_hashes,
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
            "All v0.9 evaluator logic, benchmark cases, attacks and clean controls were authored after the v0.8.1 canonical freeze and receipt commit.",
            "The five transformations are absent from v0.8 and the v0.8.1 exposed development matrix.",
            "The first observation is retained unchanged whether PASS or FAIL.",
            "No implementation repair, gold approval, clinical validation, real-user evidence or S6 release claim is made."
        ]
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if fresh_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
