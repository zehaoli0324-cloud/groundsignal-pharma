#!/usr/bin/env python3
"""Joint S2 -> S3a -> S3b evaluation harness.

This is a stage-interface evaluator, not a new medical retriever. It exercises:
query -> S2 intent/source routing -> source-scoped controlled passage selection
-> S3a free-text proposition extraction -> S3b structured entailment.

The controlled passage bank isolates handoff semantics from live-network noise.
A separate workflow sidecar reruns the existing live DailyMed retrieval tests.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import s2_intent_router as s2
import s3a_compositional_frame_parser_v0561 as s3a
import s3b_entailment_engine_v022 as s3b
import s3a_compositional_frame_parser_v05 as v05

VERSION = "s2-s3-joint-pipeline-v0.1"


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_source_document(ranked_source_ids: list[str], documents: list[dict[str, Any]]):
    by_source: dict[str, list[dict[str, Any]]] = {}
    for d in documents:
        by_source.setdefault(d["source_id"], []).append(d)
    for rank, source_id in enumerate(ranked_source_ids, start=1):
        docs = by_source.get(source_id)
        if docs:
            return rank, copy.deepcopy(docs[0])
    return None, None


def add_condition_semantics(props: list[dict[str, Any]], mode: str | None):
    if not mode:
        return props
    out = copy.deepcopy(props)
    for p in out:
        if p.get("conditions"):
            p["condition_semantics"] = mode
    return out


def run_item(item: dict[str, Any], feature_cfg: dict, source_policy: dict, legacy_cfg: dict):
    routed = s2.route(item["query"], feature_cfg, source_policy)
    source_rank, selected = select_source_document(routed["ranked_source_ids"], item.get("source_documents", []))

    if selected is None:
        return {
            "item_id": item["item_id"],
            "s2": routed,
            "selected_source_id": None,
            "selected_source_rank": None,
            "s3a_abstain": None,
            "s3a_propositions": [],
            "s3b_relation": "NO_EVIDENCE",
            "error_stage": "S2_SOURCE_HANDOFF",
            "pipeline_version": VERSION,
        }

    extraction = s3a.extract({
        "item_id": item["item_id"],
        "role": "evidence",
        "text": selected["text"],
    }, legacy_cfg)
    evidence = add_condition_semantics(
        extraction.get("predicted_propositions", []),
        item.get("evidence_condition_semantics"),
    )

    if extraction.get("abstain"):
        relation = "ABSTAIN"
        verdicts = []
        cues = {"abstain": True}
        error_stage = "S3A_ABSTENTION"
    else:
        verdicts = [s3b.classify_proposition(evidence, cp) for cp in item.get("candidate_propositions", [])]
        relation, cues = s3b.aggregate(verdicts)
        error_stage = None

    return {
        "item_id": item["item_id"],
        "s2": routed,
        "selected_source_id": selected["source_id"],
        "selected_source_rank": source_rank,
        "selected_document_id": selected.get("document_id"),
        "selected_text": selected["text"],
        "s3a_abstain": extraction.get("abstain"),
        "s3a_unresolved_spans": extraction.get("unresolved_spans", []),
        "s3a_propositions": evidence,
        "s3b_relation": relation,
        "s3b_verdicts": verdicts,
        "s3b_cues": cues,
        "error_stage": error_stage,
        "pipeline_version": VERSION,
    }


def evaluate(doc: dict[str, Any], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    pm = {x["item_id"]: x for x in predictions}
    rows = []
    counts = {
        "n": len(doc["items"]),
        "intent_correct": 0,
        "primary_source_correct": 0,
        "source_handoff_correct": 0,
        "s3a_nonabstain": 0,
        "s3b_relation_correct": 0,
        "end_to_end_correct": 0,
        "high_risk_false_support": 0,
    }
    attribution = {"S2_INTENT": 0, "S2_SOURCE": 0, "S2_SOURCE_HANDOFF": 0, "S3A": 0, "S3B": 0}

    for item in doc["items"]:
        p = pm[item["item_id"]]
        intent_ok = p["s2"]["predicted_intent"] == item["expected_intent"]
        primary_ok = bool(p["s2"]["ranked_source_ids"]) and p["s2"]["ranked_source_ids"][0] == item["expected_primary_source"]
        handoff_ok = p.get("selected_source_id") == item["expected_primary_source"]
        s3a_ok = p.get("s3a_abstain") is False
        s3b_ok = p.get("s3b_relation") == item["gold_relation"]
        e2e = intent_ok and primary_ok and handoff_ok and s3a_ok and s3b_ok

        counts["intent_correct"] += int(intent_ok)
        counts["primary_source_correct"] += int(primary_ok)
        counts["source_handoff_correct"] += int(handoff_ok)
        counts["s3a_nonabstain"] += int(s3a_ok)
        counts["s3b_relation_correct"] += int(s3b_ok)
        counts["end_to_end_correct"] += int(e2e)

        false_support = bool(item.get("high_risk")) and item["gold_relation"] != "DIRECT_SUPPORT" and p.get("s3b_relation") == "DIRECT_SUPPORT"
        counts["high_risk_false_support"] += int(false_support)

        failure_stage = None
        if not intent_ok:
            failure_stage = "S2_INTENT"
        elif not primary_ok:
            failure_stage = "S2_SOURCE"
        elif not handoff_ok:
            failure_stage = "S2_SOURCE_HANDOFF"
        elif not s3a_ok:
            failure_stage = "S3A"
        elif not s3b_ok:
            failure_stage = "S3B"
        if failure_stage:
            attribution[failure_stage] += 1

        rows.append({
            "item_id": item["item_id"],
            "intent_ok": intent_ok,
            "primary_source_ok": primary_ok,
            "source_handoff_ok": handoff_ok,
            "s3a_nonabstain": s3a_ok,
            "s3b_relation_ok": s3b_ok,
            "gold_relation": item["gold_relation"],
            "predicted_relation": p.get("s3b_relation"),
            "high_risk": bool(item.get("high_risk")),
            "high_risk_false_support": false_support,
            "end_to_end_correct": e2e,
            "failure_stage": failure_stage,
        })

    n = counts["n"] or 1
    metrics = {
        "n_items": counts["n"],
        "intent_accuracy": counts["intent_correct"] / n,
        "primary_source_accuracy": counts["primary_source_correct"] / n,
        "source_handoff_accuracy": counts["source_handoff_correct"] / n,
        "s3a_nonabstention_rate": counts["s3a_nonabstain"] / n,
        "s3b_relation_accuracy": counts["s3b_relation_correct"] / n,
        "end_to_end_accuracy": counts["end_to_end_correct"] / n,
        "high_risk_false_support_count": counts["high_risk_false_support"],
    }
    crit = doc["release_criteria"]
    checks = {
        "intent_accuracy": metrics["intent_accuracy"] >= crit["min_intent_accuracy"],
        "primary_source_accuracy": metrics["primary_source_accuracy"] >= crit["min_primary_source_accuracy"],
        "source_handoff_accuracy": metrics["source_handoff_accuracy"] >= crit["min_source_handoff_accuracy"],
        "s3a_nonabstention_rate": metrics["s3a_nonabstention_rate"] >= crit["min_s3a_nonabstention_rate"],
        "s3b_relation_accuracy": metrics["s3b_relation_accuracy"] >= crit["min_s3b_relation_accuracy"],
        "end_to_end_accuracy": metrics["end_to_end_accuracy"] >= crit["min_end_to_end_accuracy"],
        "high_risk_false_support_count": metrics["high_risk_false_support_count"] <= crit["max_high_risk_false_support_count"],
    }
    return {
        "benchmark_id": doc["benchmark_id"],
        "metrics": metrics,
        "gate_checks": checks,
        "failure_attribution": attribution,
        "items": rows,
        "release_gate": "PASS" if all(checks.values()) else "FAIL",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--pred-out", required=True)
    ap.add_argument("--report-out", required=True)
    ap.add_argument("--features", default="medical/stage-evals/S2/intent-features-v0.3.json")
    ap.add_argument("--policy", default="medical/stage-evals/S2/source-policy-v0.3.json")
    ap.add_argument("--legacy-config", default="medical/configs/s3a-semantic-frame-v0.4.json")
    args = ap.parse_args()

    doc = load(args.suite)
    features = load(args.features)
    policy = load(args.policy)
    legacy = load(args.legacy_config)
    predictions = [run_item(item, features, policy, legacy) for item in doc["items"]]
    report = evaluate(doc, predictions)

    Path(args.pred_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.pred_out).write_text(json.dumps({"predictions": predictions}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print("release_gate", report["release_gate"])
    if report["release_gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
