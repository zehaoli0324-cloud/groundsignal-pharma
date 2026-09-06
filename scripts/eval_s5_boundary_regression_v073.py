#!/usr/bin/env python3
"""S5 v0.7.3 exposed regression for lineage-generalization failures F24-F27.

This evaluator is not fresh. It deliberately reuses the already-exposed v0.7
attacks to verify the repair while preserving the v0.7 first observation
immutably. A later post-freeze suite is required for independent evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIRST_OBS = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.7.json"
EXPECTED_FIRST_OBS_BLOB = "b14f9e8f348976ee4823e26a5d3923b7417efa0b"

CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"
HELDOUT = CARRIER_ROOT / "S5FRESH-BOUNDARY-003/cases/S5FRESH-BND4-HO-001.json"
ORDINARY = ROOT / "medical/examples/clinical-medication-safety-001.json"

EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.7"
CROSS_SUITE = EVAL_ROOT / "cross-split-authority/suite-cross-split-v0.7.json"
CROSS_ROOT = EVAL_ROOT / "cross-split-authority/families"
PARAPHRASED = EVAL_ROOT / "attack-sources/paraphrased-heldout-ordinary.json"
PARTIAL = EVAL_ROOT / "attack-sources/partial-heldout-ordinary.json"
NFKC_SUITE = EVAL_ROOT / "nfkc-authority/suite-nfkc-v0.7.json"
NFKC_ROOT = EVAL_ROOT / "nfkc-authority/families"
NFKC_ORDINARY = EVAL_ROOT / "attack-sources/nfkc-collision-ordinary.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def policy_probe(
    trust: Any,
    legacy_builder: Any,
    exporter: Any,
    suite: Path,
    family_root: Path,
    ordinary_sources: list[Path],
    version: str,
) -> dict[str, Any]:
    builder_rejected = False
    try:
        trust.build_policy(
            [(suite, family_root)],
            ordinary_sources=ordinary_sources,
            policy_version=version,
        )
    except ValueError:
        builder_rejected = True

    legacy_policy = legacy_builder.build_policy(
        [(suite, family_root)],
        ordinary_sources=ordinary_sources,
        policy_version=version,
    )
    validator_rejected = False
    try:
        exporter._validate_policy_content(legacy_policy, version)
    except PermissionError:
        validator_rejected = True

    return {
        "policy_builder_rejected": builder_rejected,
        "policy_content_validator_rejected": validator_rejected,
        "pass": builder_rejected and validator_rejected,
    }


def development_probe(detector: Any) -> dict[str, Any]:
    reference = load_json(HELDOUT)
    paraphrased = load_json(PARAPHRASED)
    partial = load_json(PARTIAL)
    ordinary = load_json(ORDINARY)
    refs = [{"case_id": reference["case_id"], "split": "heldout", "case": reference}]

    presentation = copy.deepcopy(reference)
    presentation["case_id"] = "S5DEV-LINEAGE-PRESENTATION-001"
    presentation["title"] = "Development-only presentation transform"
    presentation["tags"] = ["development", "presentation-transform"]

    prompt_paraphrase = copy.deepcopy(reference)
    prompt_paraphrase["case_id"] = "S5DEV-LINEAGE-PARAPHRASE-002"
    prompt_paraphrase["interaction"]["prompt"] = (
        "Answer only from the attached synthetic evidence and keep every conclusion bounded "
        "to this infrastructure test."
    )
    prompt_paraphrase["expected_behavior"]["uncertainty_behavior"] = (
        "Keep all claims inside the synthetic fixture and avoid treating it as clinical evidence."
    )

    field_wrapper = copy.deepcopy(reference)
    field_wrapper["case_id"] = "S5DEV-LINEAGE-PARTIAL-003"
    field_wrapper["patient_context"] = {
        "chief_complaint": "Unrelated synthetic wrapper",
        "history": "Development-only wrapper",
        "medications": [],
        "allergies": [],
        "labs": [{"name": "synthetic_marker", "value": 1}],
        "imaging_reports": [],
        "other_reports": [],
        "longitudinal_events": [],
    }
    field_wrapper["interaction"]["prompt"] = (
        "New wrapper prompt for an already-exposed lineage-development probe."
    )

    ordinary_wrapper = copy.deepcopy(ordinary)
    ordinary_wrapper["case_id"] = "clinical-medication-safety-001-wrapper"
    ordinary_wrapper["title"] = "Development clean ordinary wrapper negative"
    ordinary_wrapper["tags"] = ["development-clean-negative"]

    positives = [
        ("exposed_paraphrase", paraphrased),
        ("exposed_partial", partial),
        ("presentation_only", presentation),
        ("development_paraphrase", prompt_paraphrase),
        ("development_partial_wrapper", field_wrapper),
    ]
    negatives = [
        ("ordinary_baseline", ordinary),
        ("ordinary_wrapper", ordinary_wrapper),
    ]

    exact_hits = 0
    lexical_hits = 0
    hybrid_hits = 0
    family_totals = {"paraphrase": 2, "partial_reuse": 2, "presentation": 1}
    family_hits = {"paraphrase": 0, "partial_reuse": 0, "presentation": 0}
    positive_rows: list[dict[str, Any]] = []

    for name, case in positives:
        exact = detector.semantic_core_sha256(case) == detector.semantic_core_sha256(reference)
        lexical = detector.record_similarity(case, reference) >= detector.RECORD_BLOCK_THRESHOLD
        trace = detector.detect_lineage(case, refs)
        blocked = trace["decision"] == "BLOCK"
        exact_hits += int(exact)
        lexical_hits += int(lexical)
        hybrid_hits += int(blocked)
        family = (
            "presentation"
            if name == "presentation_only"
            else "partial_reuse"
            if "partial" in name
            else "paraphrase"
        )
        family_hits[family] += int(blocked)
        positive_rows.append(
            {
                "name": name,
                "exact_core": exact,
                "lexical_record_block": lexical,
                "hybrid_decision": trace["decision"],
                "nearest_reference_id": trace["nearest_reference_id"],
            }
        )

    false_blocks = 0
    review_count = 0
    negative_rows: list[dict[str, Any]] = []
    for name, case in negatives:
        trace = detector.detect_lineage(case, refs)
        false_blocks += int(trace["decision"] == "BLOCK")
        review_count += int(trace["decision"] == "REVIEW")
        negative_rows.append({"name": name, "decision": trace["decision"]})

    total_pos = len(positives)
    total_neg = len(negatives)
    return {
        "method_version": detector.METHOD_VERSION,
        "development_scope": "already-exposed synthetic transformations + existing ordinary-source negatives",
        "positive_count": total_pos,
        "clean_negative_count": total_neg,
        "contamination_recall": hybrid_hits / total_pos,
        "clean_false_block_rate": false_blocks / total_neg,
        "clean_review_rate": review_count / total_neg,
        "transformation_recall": {
            family: family_hits[family] / family_totals[family] for family in family_totals
        },
        "ablation_recall": {
            "exact_semantic_core_only": exact_hits / total_pos,
            "lexical_record_only": lexical_hits / total_pos,
            "hybrid_record_field_span": hybrid_hits / total_pos,
        },
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
        "embedding_or_cross_encoder": "SEE_V0.7.3_BROADER_CALIBRATION",
        "latency_benchmark": "SEE_V0.7.3_BROADER_CALIBRATION",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v073")
    legacy_v071 = load_module(ROOT / "scripts/s5_trust_policy_v071.py", "s5_trust_v071_exposed")
    legacy_v061 = load_module(ROOT / "scripts/s5_trust_policy_v061.py", "s5_trust_v061_exposed")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_export_v073")
    detector = load_module(ROOT / "scripts/s5_lineage_detector_v073.py", "s5_lineage_detector_v073_eval")

    observed_blob = git_blob_sha(FIRST_OBS)
    preservation = {
        "expected_blob": EXPECTED_FIRST_OBS_BLOB,
        "observed_blob": observed_blob,
        "pass": observed_blob == EXPECTED_FIRST_OBS_BLOB,
    }

    baseline_version = "s5-trust-root-v0.7.3-baseline"
    baseline_builder_pass = True
    baseline_validator_pass = True
    try:
        baseline_policy = trust.build_policy(
            [(CARRIER_SUITE, CARRIER_ROOT)],
            ordinary_sources=[ORDINARY],
            policy_version=baseline_version,
        )
    except ValueError:
        baseline_builder_pass = False
        baseline_policy = None
    if baseline_policy is not None:
        try:
            exporter._validate_policy_content(baseline_policy, baseline_version)
        except PermissionError:
            baseline_validator_pass = False
    else:
        baseline_validator_pass = False

    trust_root = exporter.trust_root_status()
    baseline = {
        "policy_builder_pass": baseline_builder_pass,
        "policy_content_validator_pass": baseline_validator_pass,
        "registered_trust_root_pass": bool(trust_root.get("pass")),
    }
    baseline["pass"] = all(baseline.values())

    gates = {
        "S5-F24": policy_probe(
            trust,
            legacy_v061,
            exporter,
            CROSS_SUITE,
            CROSS_ROOT,
            [],
            "s5-trust-root-v0.7.3-f24-regression",
        ),
        "S5-F25": policy_probe(
            trust,
            legacy_v071,
            exporter,
            CARRIER_SUITE,
            CARRIER_ROOT,
            [PARAPHRASED],
            "s5-trust-root-v0.7.3-f25-regression",
        ),
        "S5-F26": policy_probe(
            trust,
            legacy_v071,
            exporter,
            CARRIER_SUITE,
            CARRIER_ROOT,
            [PARTIAL],
            "s5-trust-root-v0.7.3-f26-regression",
        ),
        "S5-F27": policy_probe(
            trust,
            legacy_v061,
            exporter,
            NFKC_SUITE,
            NFKC_ROOT,
            [NFKC_ORDINARY],
            "s5-trust-root-v0.7.3-f27-regression",
        ),
    }
    development = development_probe(detector)

    failed = [name for name, gate in gates.items() if not gate["pass"]]
    dev_pass = (
        development["contamination_recall"] == 1.0
        and development["clean_false_block_rate"] == 0.0
    )
    regression_pass = preservation["pass"] and baseline["pass"] and not failed and dev_pass

    result = {
        "stage": "S5",
        "version": "v0.7.3",
        "eval_name": "lineage-calibrated-exposed-regression",
        "evidence_class": "exposed_regression",
        "fresh_evidence": False,
        "source_fresh_observation": "medical/stage-evals/S5/fresh-first-observation-v0.7.json",
        "preserved_v0.7_first_observation": preservation,
        "baseline": baseline,
        **gates,
        "development_detector_metrics": development,
        "failed_gates": failed,
        "regression_gate": "PASS" if regression_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "notes": [
            "v0.7 remains the immutable independent FAIL; v0.7.3 is exposed repair evidence only.",
            "F24/F27 retain the deterministic v0.7.1 split/identifier repair.",
            "F25/F26 are addressed by an explainable protected-exclusive lineage detector using allowed-dev subtraction plus record, field, span, and anchor evidence.",
            "Both policy construction and authenticated export validation are required to reject all four exposed attacks.",
            "The legacy development probe remains exposed-only; the broader v0.7.3 calibration is reported separately and is not release evidence.",
            "Broader calibration, threshold comparison, and latency are recorded by calibrate_s5_lineage_v073.py; a new post-freeze fresh suite remains outstanding.",
            "No expert approval, real-user evidence, model-training gain, or clinical validation is inferred.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if regression_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
