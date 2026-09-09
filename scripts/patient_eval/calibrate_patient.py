"""Compare declared synthetic question labels with two versioned rule sets.

This is development calibration, not an independent estimate of patient-language
accuracy. A missing mapping is an error only when the declared label requires a
supported disclosure. No patient fact values or real model calls are involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .patient_intent import (
    DEFAULT_CLASSIFIER_VERSION, LEGACY_CLASSIFIER_VERSION, classify_requested_slots,
)

DEFAULT_SAMPLES = Path(__file__).resolve().parents[2] / "medical/patient-eval/calibration/v0.3/patient-questions.json"


def _summary(rows: list[dict]) -> dict:
    total = len(rows)
    false_count = sum(len(row["wrongly_disclosed_slots"]) for row in rows)
    missed_count = sum(len(row["missed_slots"]) for row in rows)
    expected_count = sum(len(row["expected_slots"]) for row in rows)
    predicted_count = sum(len(row["requested_slots"]) for row in rows)
    exact = sum(not row["wrongly_disclosed_slots"] and not row["missed_slots"] for row in rows)
    return {
        "case_count": total, "exact_match_count": exact,
        "exact_match_rate": exact / total if total else None,
        "false_disclosure_case_count": sum(bool(row["wrongly_disclosed_slots"]) for row in rows),
        "missed_disclosure_case_count": sum(bool(row["missed_slots"]) for row in rows),
        "wrongly_disclosed_slot_count": false_count, "missed_slot_count": missed_count,
        "expected_slot_count": expected_count, "predicted_slot_count": predicted_count,
        "wrong_disclosure_fraction_of_predictions": false_count / predicted_count if predicted_count else None,
        "miss_fraction_of_expected": missed_count / expected_count if expected_count else None,
        "unmapped_case_count": sum(not row["requested_slots"] for row in rows),
        "correctly_unmapped_case_count": sum(not row["requested_slots"] and not row["expected_slots"] for row in rows),
    }


def calibrate(samples_path: str | Path = DEFAULT_SAMPLES) -> dict:
    raw = Path(samples_path).read_bytes()
    samples = json.loads(raw)
    if samples.get("schema_version") != "patient-question-calibration.v0.3":
        raise ValueError("unsupported calibration schema")
    patterns = samples["fact_patterns"]
    if not patterns or any(not isinstance(v, list) or not v or any(not isinstance(p, str) or not p for p in v) for v in patterns.values()):
        raise ValueError("fact_patterns must contain nonempty literal patterns")
    facts = {slot: {"ask_patterns": values} for slot, values in patterns.items()}
    ids = set()
    for row in samples["cases"]:
        if row["case_id"] in ids or not isinstance(row["text"], str) or not row["text"].strip():
            raise ValueError("invalid or duplicate calibration case")
        ids.add(row["case_id"])
        for field in ("expected_slots", "legacy_observed_slots_before_change"):
            slots = row[field]
            if not isinstance(slots, list) or len(slots) != len(set(slots)) or not set(slots) <= set(facts):
                raise ValueError("invalid calibration slot labels")
        if row["declared_split"] not in ("development_design", "development_regression"):
            raise ValueError("this calibration runner accepts exposed development splits only")
    results = {}
    for version in (LEGACY_CLASSIFIER_VERSION, DEFAULT_CLASSIFIER_VERSION):
        rows = []
        for row in samples["cases"]:
            decision = classify_requested_slots(row["text"], facts, version)
            requested = decision["requested_slots"]
            if version == LEGACY_CLASSIFIER_VERSION and requested != row["legacy_observed_slots_before_change"]:
                raise ValueError("legacy implementation no longer reproduces the pre-change observation")
            expected = row["expected_slots"]
            rows.append({"case_id": row["case_id"], "text": row["text"], "category": row["category"],
                         "declared_split": row["declared_split"], "expected_slots": expected,
                         "requested_slots": requested,
                         "wrongly_disclosed_slots": sorted(set(requested) - set(expected)),
                         "missed_slots": sorted(set(expected) - set(requested)), "decision": decision})
        results[version] = {
            "overall": _summary(rows),
            "by_category": {key: _summary([r for r in rows if r["category"] == key]) for key in sorted({r["category"] for r in rows})},
            "by_declared_split": {key: _summary([r for r in rows if r["declared_split"] == key]) for key in sorted({r["declared_split"] for r in rows})},
            "cases": rows,
        }
    return {
        "schema_version": "patient-question-calibration-report.v0.3",
        "dataset_sha256": hashlib.sha256(raw).hexdigest(), "provenance": samples["provenance"],
        "limitations": ["Synthetic Agent-assisted labels; no independent human gold labels.",
                        "Both splits were exposed during development; results are not fresh held-out accuracy.",
                        "Exact success on these finite phrases is not general Chinese or clinical understanding.",
                        "Unmapped requests require operator review; unmapped is not automatically an error."],
        "metric_definitions": {"exact_match_rate": "cases with predicted slot set equal to expected / all cases",
                               "wrong_disclosure_fraction_of_predictions": "unexpected predicted slots / all predicted slots; null when zero",
                               "miss_fraction_of_expected": "missing expected slots / all expected slots; null when zero"},
        "legacy_prechange_observations_reproduced": True, "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--out", type=Path, required=True, help="New JSON path; existing files are never overwritten")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    report = calibrate(args.samples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({version: result["overall"] for version, result in report["results"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
