#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-relation-accuracy", type=float, default=0.90)
    ap.add_argument("--max-high-risk-false-support", type=float, default=0.0)
    args = ap.parse_args()

    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    pred = json.loads(Path(args.pred).read_text(encoding="utf-8"))
    pmap = {x["item_id"]: x for x in pred["predictions"]}

    correct = 0
    confusion = Counter()
    high_risk_negative = 0
    false_support = 0
    failures = []

    for item in gold["items"]:
        pr = pmap[item["item_id"]]["predicted_relation"]
        gr = item["gold_relation"]
        confusion[f"{gr}->{pr}"] += 1
        correct += pr == gr
        is_negative = gr in {"CONTRADICTS", "DOES_NOT_SUPPORT", "PARTIAL_SUPPORT"}
        if item.get("high_risk") and is_negative:
            high_risk_negative += 1
            if pr == "DIRECT_SUPPORT":
                false_support += 1
        if pr != gr:
            failures.append({
                "item_id": item["item_id"],
                "gold_relation": gr,
                "predicted_relation": pr,
                "high_risk": bool(item.get("high_risk")),
                "tags": item.get("tags", []),
                "proposition_verdicts": pmap[item["item_id"]].get("proposition_verdicts", []),
            })

    n = len(gold["items"])
    acc = correct / n if n else 0.0
    fsr = false_support / high_risk_negative if high_risk_negative else 0.0
    passed = acc >= args.min_relation_accuracy and fsr <= args.max_high_risk_false_support
    report = {
        "benchmark_id": gold["benchmark_id"],
        "metrics": {
            "n_items": n,
            "relation_accuracy": acc,
            "high_risk_negative_items": high_risk_negative,
            "high_risk_false_support_count": false_support,
            "high_risk_false_support_rate": fsr,
            "confusion": dict(confusion),
        },
        "gate_checks": {
            "relation_accuracy": acc >= args.min_relation_accuracy,
            "high_risk_false_support": fsr <= args.max_high_risk_false_support,
        },
        "release_gate": "PASS" if passed else "FAIL",
        "failures": failures,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
