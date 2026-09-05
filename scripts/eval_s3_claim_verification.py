#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-relation-accuracy", type=float, default=0.80)
    ap.add_argument("--max-high-risk-false-support", type=float, default=0.0)
    args = ap.parse_args()

    gold_doc = load(args.gold)
    gold = {r["item_id"]: r for r in gold_doc["items"]}
    pred_rows = load(args.pred)["predictions"]
    pred = {r["item_id"]: r for r in pred_rows}

    n = len(gold)
    correct = 0
    high_risk_negative_n = 0
    high_risk_false_support = 0
    failures = []
    confusion = Counter()
    tag_errors = Counter()

    for item_id, row in gold.items():
        got = pred.get(item_id, {})
        expected = row["gold_relation"]
        predicted = got.get("predicted_relation")
        confusion[f"{expected}->{predicted}"] += 1
        ok = predicted == expected
        correct += int(ok)

        is_negative = expected != "DIRECT_SUPPORT"
        if row.get("high_risk") and is_negative:
            high_risk_negative_n += 1
            if predicted == "DIRECT_SUPPORT":
                high_risk_false_support += 1

        if not ok:
            for tag in row.get("tags", []):
                tag_errors[tag] += 1
            failures.append({
                "item_id": item_id,
                "evidence_text": row["evidence_text"],
                "candidate_claim": row["candidate_claim"],
                "gold_relation": expected,
                "predicted_relation": predicted,
                "high_risk": bool(row.get("high_risk")),
                "false_support_failure": row.get("false_support_failure"),
                "lexical_overlap": got.get("lexical_overlap"),
                "cues": got.get("cues", []),
            })

    metrics = {
        "n_items": n,
        "relation_accuracy": correct / n if n else 0.0,
        "high_risk_negative_items": high_risk_negative_n,
        "high_risk_false_support_rate": high_risk_false_support / high_risk_negative_n if high_risk_negative_n else 0.0,
        "high_risk_false_support_count": high_risk_false_support,
        "confusion": dict(confusion),
        "error_tags": dict(tag_errors),
    }
    checks = {
        "relation_accuracy": metrics["relation_accuracy"] >= args.min_relation_accuracy,
        "high_risk_false_support": metrics["high_risk_false_support_rate"] <= args.max_high_risk_false_support,
    }
    report = {
        "benchmark_id": gold_doc["benchmark_id"],
        "verifier": pred_rows[0].get("verifier_version") if pred_rows else None,
        "metrics": metrics,
        "gate_checks": checks,
        "release_gate": "PASS" if all(checks.values()) else "FAIL",
        "failures": failures,
        "principle": "A high-risk unsupported/contradicted claim must never be promoted to DIRECT_SUPPORT merely because it shares words with the evidence."
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
