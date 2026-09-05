#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROUTER_VERSION = "intent-first-s2-v0.3.0"


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def detect_features(query: str, feature_groups: dict[str, list[str]]):
    q = query.lower().strip()
    hits = {}
    for name, phrases in feature_groups.items():
        matched = [p for p in phrases if p.lower() in q]
        if matched:
            hits[name] = matched
    return hits


def rule_matches(rule: dict, feature_hits: dict[str, list[str]]):
    present = set(feature_hits)
    required_all = set(rule.get("all", []))
    required_any = set(rule.get("any", []))
    forbidden = set(rule.get("none", []))
    if not required_all.issubset(present):
        return False
    if required_any and not (required_any & present):
        return False
    if forbidden & present:
        return False
    return True


def classify_intent(query: str, feature_cfg: dict):
    hits = detect_features(query, feature_cfg["feature_groups"])
    candidates = []
    for index, rule in enumerate(feature_cfg["intent_rules"]):
        if rule_matches(rule, hits):
            matched_groups = set(rule.get("all", [])) | (set(rule.get("any", [])) & set(hits))
            score = float(rule.get("priority", 0)) + len(matched_groups) * 0.01
            candidates.append((score, -index, rule["intent"], sorted(matched_groups)))
    if not candidates:
        return feature_cfg["fallback_intent"], 0.0, hits, []
    candidates.sort(reverse=True)
    score, _, intent, matched_groups = candidates[0]
    return intent, score, hits, matched_groups


def route(query: str, feature_cfg: dict, source_policy: dict):
    intent, score, feature_hits, matched_groups = classify_intent(query, feature_cfg)
    policy = source_policy["intents"].get(intent)
    if policy is None:
        intent = feature_cfg["fallback_intent"]
        policy = source_policy["intents"][intent]
    return {
        "predicted_intent": intent,
        "ranked_source_ids": policy["ranked_source_ids"][:3],
        "intent_score": score,
        "feature_hits": feature_hits,
        "matched_groups": matched_groups,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--features", default="medical/stage-evals/S2/intent-features-v0.3.json")
    ap.add_argument("--policy", default="medical/stage-evals/S2/source-policy-v0.3.json")
    args = ap.parse_args()

    data = load(args.input)
    feature_cfg = load(args.features)
    source_policy = load(args.policy)
    preds = []
    for row in data["queries"]:
        routed = route(row["query"], feature_cfg, source_policy)
        preds.append({
            "query_id": row["query_id"],
            "router_version": ROUTER_VERSION,
            **routed,
        })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} predictions to {out}")


if __name__ == "__main__":
    main()
