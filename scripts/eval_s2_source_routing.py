#!/usr/bin/env python3
import argparse, json, sys
from collections import Counter
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_types(registry_paths):
    out = {}
    for path in registry_paths:
        p = Path(path)
        if not p.exists():
            continue
        for src in load(p).get("sources", []):
            out[src["source_id"]] = src.get("source_type")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--registry", default="medical/knowledge-base/SOURCE_REGISTRY.json")
    ap.add_argument("--registry-supplement", default="medical/knowledge-base/SOURCE_REGISTRY_SUPPLEMENT.json")
    ap.add_argument("--min-primary-r1", type=float, default=0.80)
    ap.add_argument("--min-acceptable-r3", type=float, default=0.95)
    ap.add_argument("--max-wrong-authority", type=float, default=0.05)
    args = ap.parse_args()

    gold = load(args.gold)["queries"]
    pred_rows = load(args.pred)["predictions"]
    pred = {r["query_id"]: r for r in pred_rows}
    types = source_types([args.registry, args.registry_supplement])

    n = len(gold)
    primary1 = acceptable3 = source_type_ok = freshness_ok = 0
    wrong_authority = secondary_as_gold = critical_miss = 0
    freshness_n = high_risk_n = 0
    failures = []
    failure_counts = Counter()

    for row in gold:
        qid = row["query_id"]
        ranked = pred.get(qid, {}).get("ranked_source_ids", [])
        top1 = ranked[0] if ranked else None
        top3 = ranked[:3]
        acceptable = set(row["acceptable_source_ids"])
        primary = row["expected_primary_source_id"]

        p1 = top1 == primary
        a3 = any(x in acceptable for x in top3)
        t_ok = top1 is not None and types.get(top1) == row["expected_source_type"]
        w = top1 is None or top1 not in acceptable
        secondary = top1 in set(row.get("forbidden_as_gold", []))

        primary1 += int(p1)
        acceptable3 += int(a3)
        source_type_ok += int(t_ok)
        wrong_authority += int(w)
        secondary_as_gold += int(secondary)

        if row.get("freshness_sensitive"):
            freshness_n += 1
            freshness_ok += int(a3)
        if row.get("high_risk"):
            high_risk_n += 1
            if not a3:
                critical_miss += 1

        labels = []
        if not a3:
            labels.append("SOURCE_MISS")
        elif not p1:
            labels.append("PRIMARY_SOURCE_NOT_TOP1")
        if not t_ok:
            labels.append("WRONG_SOURCE_TYPE")
        if w:
            labels.append("WRONG_AUTHORITY")
        if secondary:
            labels.append("SECONDARY_AS_GOLD")
        if row.get("high_risk") and not a3:
            labels.append("CRITICAL_SOURCE_MISS")
        for lab in labels:
            failure_counts[lab] += 1
        if labels:
            failures.append({
                "query_id": qid,
                "query": row["query"],
                "predicted": ranked,
                "primary_gold": primary,
                "acceptable_gold": sorted(acceptable),
                "labels": labels
            })

    metrics = {
        "n_queries": n,
        "primary_source_recall_at_1": primary1 / n if n else 0,
        "acceptable_source_recall_at_3": acceptable3 / n if n else 0,
        "source_type_accuracy": source_type_ok / n if n else 0,
        "freshness_routing_accuracy": freshness_ok / freshness_n if freshness_n else None,
        "wrong_authority_rate": wrong_authority / n if n else 0,
        "secondary_as_gold_rate": secondary_as_gold / n if n else 0,
        "critical_source_miss_rate": critical_miss / high_risk_n if high_risk_n else 0,
        "high_risk_queries": high_risk_n,
        "freshness_sensitive_queries": freshness_n,
        "failure_counts": dict(failure_counts)
    }

    gate_checks = {
        "primary_r1": metrics["primary_source_recall_at_1"] >= args.min_primary_r1,
        "acceptable_r3": metrics["acceptable_source_recall_at_3"] >= args.min_acceptable_r3,
        "wrong_authority": metrics["wrong_authority_rate"] <= args.max_wrong_authority,
        "no_secondary_as_gold": metrics["secondary_as_gold_rate"] == 0,
        "no_critical_source_miss": metrics["critical_source_miss_rate"] == 0
    }
    report = {
        "benchmark_id": "S2-source-routing-v0.1",
        "router": pred_rows[0].get("router_version") if pred_rows else None,
        "metrics": metrics,
        "gate_checks": gate_checks,
        "release_gate": "PASS" if all(gate_checks.values()) else "FAIL",
        "failures": failures
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "gate_checks": gate_checks, "release_gate": report["release_gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
