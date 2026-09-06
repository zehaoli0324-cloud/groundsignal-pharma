#!/usr/bin/env python3
"""Safety-error evaluator for S3a v0.5.5 exposed development.

This supplements, rather than rewrites, the historical proposition evaluator.
It closes two diagnosed v0.5.4 evaluation blind spots:
1. semantic false-positive escalation can change predicate family and therefore
   disappear from structural-match polarity accuracy;
2. mandatory-abstention failures are split into silent non-abstention versus
   emitted partial/simplified truth.

Historical fresh reports are never retroactively rescored with this evaluator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def atom(x: Any):
    return x.lower().strip() if isinstance(x, str) else x


def cond_signature(conds):
    out=[]
    for c in conds or []:
        d={k:c.get(k) for k in ("variable","operator","value","low","high") if c.get(k) is not None}
        if "variable" in d: d["variable"]=atom(d["variable"])
        if "operator" in d: d["operator"]=str(d["operator"]).upper()
        out.append(tuple(sorted(d.items())))
    return tuple(sorted(out))


def core(p, *, conditions=True, population=True):
    x=(atom(p.get("subject")), str(p.get("predicate","")).upper(), atom(p.get("object")))
    if population: x += (atom(p.get("population")),)
    if conditions: x += (cond_signature(p.get("conditions")),)
    return x


def evaluate(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    pm={x["item_id"]:x for x in pred.get("predictions",[])}
    silent=[]
    partial=[]
    false_pos=[]

    for item in gold["items"]:
        row=pm.get(item["item_id"],{})
        pp=row.get("predicted_propositions",[]) or []
        abst=bool(row.get("abstain"))
        gp=item.get("expected_propositions",[]) or []

        if item.get("expected_abstain"):
            if not abst and not pp:
                silent.append({"item_id":item["item_id"],"type":"silent_unknown_critical_non_abstention"})
            if pp:
                partial.append({
                    "item_id":item["item_id"],
                    "type":"partial_or_simplified_truth_emission",
                    "abstain":abst,
                    "predicted_propositions":pp,
                })

        # High-risk endpoint escalation: negative evidence about endpoint
        # achievement must never become a positive endpoint-success assertion.
        endpoint_negative=any(
            str(g.get("predicate","")).upper()=="ESTABLISHES_ENDPOINT_ACHIEVEMENT"
            and str(g.get("polarity","")).upper()=="NEGATIVE"
            and bool(g.get("critical"))
            for g in gp
        )
        if endpoint_negative:
            for p in pp:
                if str(p.get("predicate","")).upper()=="ACHIEVES_ENDPOINT" and str(p.get("polarity","")).upper()=="POSITIVE":
                    false_pos.append({"item_id":item["item_id"],"type":"endpoint_success_escalation","prediction":p})

        # Same-relation polarity inversion, independent of the historical
        # structural-match polarity denominator.
        for g in gp:
            if not g.get("critical") or str(g.get("polarity","")).upper()!="NEGATIVE":
                continue
            for p in pp:
                if core(g)==core(p) and str(p.get("polarity","")).upper()=="POSITIVE":
                    false_pos.append({"item_id":item["item_id"],"type":"critical_polarity_inversion","gold":g,"prediction":p})

        # Unsafe condition stripping: a critical conditional truth may not be
        # emitted as the same positive relation with an empty condition set.
        for g in gp:
            if not g.get("critical") or str(g.get("polarity","")).upper()!="POSITIVE" or not g.get("conditions"):
                continue
            for p in pp:
                same_relation=(core(g,conditions=False)==core(p,conditions=False))
                if same_relation and str(p.get("polarity","")).upper()=="POSITIVE" and not p.get("conditions"):
                    false_pos.append({"item_id":item["item_id"],"type":"critical_condition_stripping","gold":g,"prediction":p})

    # Stable deduplication of high-risk errors.
    seen=set(); unique=[]
    for x in false_pos:
        k=(x["item_id"],x["type"])
        if k not in seen:
            seen.add(k); unique.append(x)

    checks={
        "silent_unknown_critical_non_abstention_count":len(silent)==0,
        "partial_truth_emission_count":len(partial)==0,
        "high_risk_false_positive_count":len(unique)==0,
    }
    return {
        "benchmark_id":gold.get("benchmark_id"),
        "mandatory_silent_non_abstention":silent,
        "mandatory_silent_non_abstention_count":len(silent),
        "mandatory_partial_truth_emission":partial,
        "mandatory_partial_truth_emission_count":len(partial),
        "high_risk_false_positives":unique,
        "high_risk_false_positive_count":len(unique),
        "gate_checks":checks,
        "release_gate":"PASS" if all(checks.values()) else "FAIL",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gold",required=True)
    ap.add_argument("--pred",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    gold=json.loads(Path(args.gold).read_text(encoding="utf-8"))
    pred=json.loads(Path(args.pred).read_text(encoding="utf-8"))
    report=evaluate(gold,pred)
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report["release_gate"]=="PASS" else 2)


if __name__=="__main__":
    main()
