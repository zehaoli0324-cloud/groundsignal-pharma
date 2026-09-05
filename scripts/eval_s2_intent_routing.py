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
    ap.add_argument("--min-intent-accuracy", type=float, default=0.85)
    ap.add_argument("--min-primary-r1", type=float, default=0.80)
    ap.add_argument("--min-acceptable-r3", type=float, default=0.90)
    ap.add_argument("--max-critical-miss", type=float, default=0.0)
    args = ap.parse_args()

    gold_doc = load(args.gold)
    gold = gold_doc["queries"]
    pred_rows = load(args.pred)["predictions"]
    pred = {r["query_id"]: r for r in pred_rows}

    n = len(gold)
    intent_ok = primary_ok = acceptable_ok = 0
    high_risk_n = critical_miss = 0
    counts = Counter()
    failures = []

    for row in gold:
        got = pred.get(row["query_id"], {})
        intent = got.get("predicted_intent")
        ranked = got.get("ranked_source_ids", [])
        expected_intents = set(row.get("acceptable_intents") or [row["expected_intent"]])
        acceptable_sources = set(row["acceptable_source_ids"])
        p1 = bool(ranked) and ranked[0] == row["expected_primary_source_id"]
        a3 = any(s in acceptable_sources for s in ranked[:3])
        iok = intent in expected_intents

        intent_ok += int(iok)
        primary_ok += int(p1)
        acceptable_ok += int(a3)
        labels = []
        if not iok:
            labels.append("INTENT_MISCLASSIFIED")
        if not a3:
            labels.append("SOURCE_MISS")
        elif not p1:
            labels.append("PRIMARY_SOURCE_NOT_TOP1")
        if row.get("high_risk"):
            high_risk_n += 1
            if not a3:
                critical_miss += 1
                labels.append("CRITICAL_SOURCE_MISS")
        for lab in labels:
            counts[lab] += 1
        if labels:
            failures.append({
                "query_id": row["query_id"],
                "query": row["query"],
                "expected_intent": row["expected_intent"],
                "predicted_intent": intent,
                "primary_gold": row["expected_primary_source_id"],
                "predicted_sources": ranked,
                "feature_hits": got.get("feature_hits", {}),
                "labels": labels,
            })

    metrics = {
        "n_queries": n,
        "intent_accuracy": intent_ok / n if n else 0.0,
        "primary_source_recall_at_1": primary_ok / n if n else 0.0,
        "acceptable_source_recall_at_3": acceptable_ok / n if n else 0.0,
        "critical_source_miss_rate": critical_miss / high_risk_n if high_risk_n else 0.0,
        "high_risk_queries": high_risk_n,
        "failure_counts": dict(counts),
    }
    checks = {
        "intent_accuracy": metrics["intent_accuracy"] >= args.min_intent_accuracy,
        "primary_r1": metrics["primary_source_recall_at_1"] >= args.min_primary_r1,
        "acceptable_r3": metrics["acceptable_source_recall_at_3"] >= args.min_acceptable_r3,
        "critical_miss": metrics["critical_source_miss_rate"] <= args.max_critical_miss,
    }
    report = {
        "benchmark_id": gold_doc.get("benchmark_id"),
        "split": gold_doc.get("split"),
        "router": pred_rows[0].get("router_version") if pred_rows else None,
        "metrics": metrics,
        "gate_checks": checks,
        "release_gate": "PASS" if all(checks.values()) else "FAIL",
        "failures": failures,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "gate_checks": checks, "release_gate": report["release_gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
