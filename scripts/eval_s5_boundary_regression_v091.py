#!/usr/bin/env python3
"""S5 v0.9.1 exposed repair calibration and historical regression."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V09_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.9"
V09_FAMILY = V09_ROOT / "families/S5FRESH-LINEAGE-009"
V08_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.8"
V09_FIRST = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.9.json"
V09_FIRST_BLOB = "522c8f4ed39293d2ea01c81f48ffacc1d1ef4340"
GOLD_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
GOLD_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"


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
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode())
    digest.update(data)
    return digest.hexdigest()


def family_index(detector: Any, family: Path):
    protected: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for entry in load_json(family / "manifest.json")["cases"]:
        case = load_json(family / entry["path"])
        row = {"case_id": entry["case_id"], "split": entry["split"], "case": case}
        (protected if entry["split"] in detector.PROTECTED_SPLITS else allowed).append(row)
    return detector.ReferenceIndex(protected, allowed)


def compact_trace(detector: Any, index: Any, path: Path) -> dict[str, Any]:
    case = load_json(path)
    trace = detector.detect_lineage(case, index, candidate_id=case["case_id"], reference_snapshot="v0.9-exposed")
    return {
        "source": path.relative_to(ROOT).as_posix(),
        "decision": trace["decision"],
        "nearest_reference_id": trace.get("nearest_reference_id"),
        "reasons": trace.get("reasons", []),
        "candidate_language": trace.get("candidate_language"),
        "semantic_concept_overlap": trace.get("semantic_concept_overlap", []),
        "candidate_measurement_roles": trace.get("candidate_measurement_roles", []),
        "reference_measurement_roles": trace.get("reference_measurement_roles", []),
        "typed_role_mismatch_references": trace.get("typed_role_mismatch_references", []),
        "script_semantic_match_references": trace.get("script_semantic_match_references", []),
        "record_similarity": trace.get("record_similarity"),
        "risk_score": trace.get("risk_score"),
    }


def boundary_probe(
    trust: Any, raw_builder: Any, exporter: Any, detector: Any, index: Any, path: Path, expected: str,
) -> dict[str, Any]:
    version = f"s5-trust-root-v0.9.1-{path.stem}"
    builder_rejected = False
    try:
        trust.build_policy(
            [(V09_ROOT / "suite-fresh-lineage-v0.9.json", V09_ROOT / "families")],
            [path],
            policy_version=version,
        )
    except ValueError:
        builder_rejected = True
    raw = raw_builder.build_policy(
        [(V09_ROOT / "suite-fresh-lineage-v0.9.json", V09_ROOT / "families")],
        [path],
        policy_version=version,
    )
    exporter_rejected = False
    try:
        exporter._validate_policy_content(raw, version)
    except PermissionError:
        exporter_rejected = True
    observed = "BLOCK" if builder_rejected and exporter_rejected else "ALLOW"
    return {
        "expected": expected,
        "observed": observed,
        "builder_rejected": builder_rejected,
        "exporter_rejected": exporter_rejected,
        "trace": compact_trace(detector, index, path),
        "pass": observed == expected,
    }


def historical_metrics(detector: Any) -> dict[str, Any]:
    legacy = load_module(ROOT / "scripts/calibrate_s5_lineage_v073.py", "s5_v091_legacy_matrix")
    records = legacy.load_exposed_records()
    protected, allowed, candidates = legacy.build_candidates(records)
    legacy_index = detector.ReferenceIndex(
        [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in protected],
        [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in allowed],
    )
    decisions = [
        detector.detect_lineage(row["case"], legacy_index, candidate_id=row["candidate_id"])["decision"]
        for row in candidates
    ]
    legacy_result = legacy.classification_metrics(decisions, candidates)

    v08_index = family_index(detector, V08_ROOT / "families/S5FRESH-LINEAGE-008")
    v08_attacks = [compact_trace(detector, v08_index, path) for path in sorted((V08_ROOT / "attack-sources").glob("*.json"))]
    v08_clean = [compact_trace(detector, v08_index, path) for path in sorted((V08_ROOT / "clean-sources").glob("*.json"))]

    matrix = load_module(ROOT / "scripts/calibrate_s5_lineage_v081_matrix.py", "s5_v091_matrix_source")
    matrix_rows = [*matrix.translation_rows(), *matrix.mosaic_rows(), *matrix.clean_rows()]
    matrix_traces: list[dict[str, Any]] = []
    for row in matrix_rows:
        trace = detector.detect_lineage(row["case"], v08_index, candidate_id=row["case_id"])
        matrix_traces.append({
            "family": row["family"],
            "expected": row["expected"],
            "decision": trace["decision"],
            "reasons": trace.get("reasons", []),
        })
    translated = [row for row in matrix_traces if row["family"] == "cross_language"]
    mosaics = [row for row in matrix_traces if row["family"] == "mosaic_noise"]
    clean = [row for row in matrix_traces if row["family"] == "clean_near_neighbour"]
    return {
        "legacy_v073": legacy_result,
        "v08": {
            "attack_decisions": dict(Counter(row["decision"] for row in v08_attacks)),
            "clean_decisions": dict(Counter(row["decision"] for row in v08_clean)),
            "attack_count": len(v08_attacks),
            "clean_count": len(v08_clean),
        },
        "v081_matrix": {
            "translation_block_rate": sum(row["decision"] == "BLOCK" for row in translated) / len(translated),
            "mosaic_reasoned_block_rate": sum(
                row["decision"] == "BLOCK" and "MULTI_PROTECTED_REFERENCE_MOSAIC" in row["reasons"]
                for row in mosaics
            ) / len(mosaics),
            "clean_false_block_rate": sum(row["decision"] == "BLOCK" for row in clean) / len(clean),
            "clean_review_rate": sum(row["decision"] == "REVIEW" for row in clean) / len(clean),
            "counts": {"translations": len(translated), "mosaics": len(mosaics), "clean": len(clean)},
        },
    }


def evaluate() -> dict[str, Any]:
    detector = load_module(ROOT / "scripts/s5_lineage_detector_v091.py", "s5_lineage_v091_eval")
    trust = load_module(ROOT / "scripts/s5_trust_policy_v091.py", "s5_trust_v091_eval")
    raw_builder = load_module(ROOT / "scripts/s5_trust_policy_v071.py", "s5_raw_v091_eval")
    exporter = load_module(ROOT / "scripts/export_training_data_v091.py", "s5_export_v091_eval")
    release = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v091_eval")
    index = family_index(detector, V09_FAMILY)

    attacks = {
        path.stem: boundary_probe(trust, raw_builder, exporter, detector, index, path, "BLOCK")
        for path in sorted((V09_ROOT / "attack-sources").glob("*.json"))
    }
    clean = {
        path.stem: boundary_probe(trust, raw_builder, exporter, detector, index, path, "ALLOW")
        for path in sorted((V09_ROOT / "clean-sources").glob("*.json"))
    }
    historical = historical_metrics(detector)
    gold = release.evaluate(GOLD_SUITE, GOLD_ROOT)
    first_blob = git_blob_sha(V09_FIRST)

    failed = [f"v09_attack:{name}" for name, row in attacks.items() if not row["pass"]]
    failed.extend(f"v09_clean:{name}" for name, row in clean.items() if not row["pass"])
    legacy = historical["legacy_v073"]
    if not (
        legacy["recall"] >= 0.95
        and legacy["clean_false_block_rate"] <= 0.05
        and legacy["clean_review_rate"] <= 0.25
    ):
        failed.append("legacy_v073_matrix")
    v08 = historical["v08"]
    if v08["attack_decisions"] != {"BLOCK": 4} or v08["clean_decisions"] != {"ALLOW": 2}:
        failed.append("v08_regression")
    matrix = historical["v081_matrix"]
    if not (
        matrix["translation_block_rate"] == 1.0
        and matrix["mosaic_reasoned_block_rate"] == 1.0
        and matrix["clean_false_block_rate"] == 0.0
        and matrix["clean_review_rate"] == 0.0
    ):
        failed.append("v081_matrix")
    if first_blob != V09_FIRST_BLOB:
        failed.append("immutable_v09_first_observation")
    if not (
        gold.get("gold_approved_count") == 0
        and gold.get("release_ready") is False
        and gold.get("decision") == "BLOCKED_GOLD_REVIEW"
    ):
        failed.append("gold_containment")

    return {
        "stage": "S5",
        "version": "v0.9.1",
        "eval_name": "script-role-exposed-repair-regression",
        "evidence_class": "repaired_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "method_version": detector.METHOD_VERSION,
        "immutable_v09_first_observation": {
            "expected_blob": V09_FIRST_BLOB,
            "observed_blob": first_blob,
            "pass": first_blob == V09_FIRST_BLOB,
            "preserved_result": "FAIL",
        },
        "v09_exposed_attacks": attacks,
        "v09_exposed_clean_controls": clean,
        "historical_regression": historical,
        "repair_gate": "PASS" if not failed else "FAIL",
        "failed_gates": failed,
        "gold_approved_count": gold.get("gold_approved_count"),
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "limitations": [
            "v0.9 cases are exposed after their immutable first observation and cannot establish fresh evidence.",
            "Hangul support is an inspectable deterministic lexicon, not general multilingual semantic understanding.",
            "Typed-role downgrading currently covers lab measurement identity and requires absence of stronger lineage evidence.",
            "A new suite may be authored only after this candidate is reviewed and explicitly frozen.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["repair_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

