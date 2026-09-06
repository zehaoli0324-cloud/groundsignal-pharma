#!/usr/bin/env python3
"""Stable exposed/development calibration for S5 lineage detector v0.8.1."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V08_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.8"
FAMILY_ROOT = V08_ROOT / "families/S5FRESH-LINEAGE-008"
ATTACK_ROOT = V08_ROOT / "attack-sources"
CLEAN_ROOT = V08_ROOT / "clean-sources"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def v08_index(detector: Any):
    manifest = load_json(FAMILY_ROOT / "manifest.json")
    protected: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for entry in manifest["cases"]:
        case = load_json(FAMILY_ROOT / entry["path"])
        row = {"case_id": entry["case_id"], "split": entry["split"], "case": case}
        (protected if entry["split"] in detector.PROTECTED_SPLITS else allowed).append(row)
    return detector.ReferenceIndex(protected, allowed), len(protected), len(allowed)


def compact_trace(detector: Any, index: Any, path: Path) -> dict[str, Any]:
    case = load_json(path)
    trace = detector.detect_lineage(case, index, candidate_id=case["case_id"], reference_snapshot="v0.8-exposed")
    return {
        "source": path.relative_to(ROOT).as_posix(),
        "decision": trace["decision"],
        "nearest_reference_id": trace.get("nearest_reference_id"),
        "reasons": trace.get("reasons", []),
        "record_similarity": trace.get("record_similarity"),
        "risk_score": trace.get("risk_score"),
        "exclusive_identifier_overlap": trace.get("exclusive_identifier_overlap", []),
        "semantic_concept_overlap": trace.get("semantic_concept_overlap", []),
        "mosaic_reference_matches": trace.get("mosaic_reference_matches", []),
    }


def evaluate() -> dict[str, Any]:
    legacy = load_module(ROOT / "scripts/calibrate_s5_lineage_v073.py", "s5_calibration_v073_source")
    detector = load_module(ROOT / "scripts/s5_lineage_detector_v081.py", "s5_lineage_v081_calibration")

    records = legacy.load_exposed_records()
    protected, allowed, candidates = legacy.build_candidates(records)
    index = detector.ReferenceIndex(
        [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in protected],
        [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in allowed],
    )
    decisions = [
        detector.detect_lineage(row["case"], index, candidate_id=row["candidate_id"])["decision"]
        for row in candidates
    ]
    legacy_metrics = legacy.classification_metrics(decisions, candidates)

    exposed_index, v08_protected, v08_allowed = v08_index(detector)
    attack_paths = sorted(ATTACK_ROOT.glob("*.json"))
    clean_paths = sorted(CLEAN_ROOT.glob("*.json"))
    attacks = [compact_trace(detector, exposed_index, path) for path in attack_paths]
    clean = [compact_trace(detector, exposed_index, path) for path in clean_paths]
    attack_block_rate = sum(row["decision"] == "BLOCK" for row in attacks) / max(1, len(attacks))
    clean_block_rate = sum(row["decision"] == "BLOCK" for row in clean) / max(1, len(clean))
    clean_review_rate = sum(row["decision"] == "REVIEW" for row in clean) / max(1, len(clean))

    gate_pass = bool(
        legacy_metrics["recall"] >= 0.95
        and legacy_metrics["clean_false_block_rate"] <= 0.05
        and legacy_metrics["clean_review_rate"] <= 0.25
        and attack_block_rate == 1.0
        and clean_block_rate == 0.0
        and clean_review_rate == 0.0
    )
    return {
        "stage": "S5",
        "version": "v0.8.1",
        "eval_name": "multilingual-mosaic-exposed-repair-calibration",
        "evidence_class": "development_exposed_calibration",
        "fresh_evidence": False,
        "method_version": detector.METHOD_VERSION,
        "data_isolation": {
            "future_fresh_suite_used": False,
            "legacy_development_candidate_count": len(candidates),
            "legacy_protected_reference_count": len(protected),
            "legacy_allowed_reference_count": len(allowed),
            "v0.8_exposed_protected_reference_count": v08_protected,
            "v0.8_exposed_allowed_reference_count": v08_allowed,
            "v0.8_exposed_attack_count": len(attacks),
            "v0.8_exposed_clean_count": len(clean),
        },
        "legacy_v073_matrix": legacy_metrics,
        "v08_exposed_matrix": {
            "attack_block_rate": round(attack_block_rate, 6),
            "clean_false_block_rate": round(clean_block_rate, 6),
            "clean_review_rate": round(clean_review_rate, 6),
            "attacks": attacks,
            "clean_controls": clean,
        },
        "rule_contract": {
            "cross_language": "block on cross-script protected identifier/concept agreement",
            "mosaic": {
                "minimum_references": detector.MOSAIC_MIN_REFERENCES,
                "minimum_anchors_per_reference": detector.MOSAIC_MIN_ANCHORS_PER_REFERENCE,
                "minimum_total_anchors": detector.MOSAIC_MIN_TOTAL_ANCHORS,
                "minimum_record_similarity": detector.MOSAIC_MIN_RECORD_SIMILARITY,
            },
            "review_minimum_dense_anchors": detector.REVIEW_MIN_DENSE_ANCHORS,
        },
        "selection_gate": "PASS" if gate_pass else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "limitations": [
            "v0.8 is exposed after its immutable first observation and therefore is regression evidence only.",
            "The multilingual ontology is deterministic and bilingual; it is not a general neural semantic model.",
            "Only two v0.8 clean controls exist, so another broader development calibration is required before the next fresh freeze.",
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
    return 0 if result["selection_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
