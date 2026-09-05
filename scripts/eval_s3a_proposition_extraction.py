#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def norm_atom(x):
    if isinstance(x, str):
        return x.lower().strip()
    return x


def norm_conditions(conds):
    out = []
    for c in conds or []:
        d = {k: c.get(k) for k in ["variable", "operator", "value", "low", "high"] if c.get(k) is not None}
        if "variable" in d:
            d["variable"] = norm_atom(d["variable"])
        if "operator" in d:
            d["operator"] = str(d["operator"]).upper()
        out.append(tuple(sorted(d.items())))
    return tuple(sorted(out))


def signature(p, include_polarity=True):
    core = (
        norm_atom(p.get("subject")),
        str(p.get("predicate", "")).upper(),
        norm_atom(str(p.get("object"))) if p.get("object") is not None else None,
        norm_conditions(p.get("conditions")),
    )
    if include_polarity:
        return core + (str(p.get("polarity", "")).upper(),)
    return core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-critical-recall", type=float, default=0.95)
    args = ap.parse_args()

    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    pred = json.loads(Path(args.pred).read_text(encoding="utf-8"))
    pred_map = {x["item_id"]: x for x in pred["predictions"]}

    tp = fp = fn = 0
    critical_total = critical_hit = 0
    polarity_total = polarity_correct = 0
    failures = []

    for item in gold["items"]:
        gprops = item["expected_propositions"]
        pprops = pred_map.get(item["item_id"], {}).get("predicted_propositions", [])
        gs = [signature(x) for x in gprops]
        ps = [signature(x) for x in pprops]
        remaining = list(ps)
        hits = []
        misses = []
        for gp, sig in zip(gprops, gs):
            if sig in remaining:
                remaining.remove(sig)
                hits.append(gp)
            else:
                misses.append(gp)
        tp += len(hits)
        fn += len(misses)
        fp += len(remaining)

        for gp in gprops:
            if gp.get("critical"):
                critical_total += 1
                if signature(gp) in ps:
                    critical_hit += 1

        # Polarity accuracy only where structural identity (without polarity) was found.
        for gp in gprops:
            gid = signature(gp, include_polarity=False)
            matches = [pp for pp in pprops if signature(pp, include_polarity=False) == gid]
            if matches:
                polarity_total += 1
                if any(str(pp.get("polarity", "")).upper() == str(gp.get("polarity", "")).upper() for pp in matches):
                    polarity_correct += 1

        if misses or remaining:
            failures.append({
                "item_id": item["item_id"],
                "text": item["text"],
                "missing_gold": misses,
                "extra_predicted_signatures": [list(x) for x in remaining],
            })

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    critical_recall = critical_hit / critical_total if critical_total else 0.0
    polarity_accuracy = polarity_correct / polarity_total if polarity_total else 0.0

    report = {
        "benchmark_id": gold["benchmark_id"],
        "metrics": {
            "gold_propositions": tp + fn,
            "predicted_propositions": tp + fp,
            "true_positive": tp,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "critical_proposition_recall": critical_recall,
            "polarity_accuracy_on_structural_matches": polarity_accuracy,
            "polarity_structural_matches": polarity_total,
        },
        "gate_checks": {
            "critical_recall": critical_recall >= args.min_critical_recall
        },
        "release_gate": "PASS" if critical_recall >= args.min_critical_recall else "FAIL",
        "failures": failures,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["release_gate"] == "PASS" else 2)


if __name__ == "__main__":
    main()
