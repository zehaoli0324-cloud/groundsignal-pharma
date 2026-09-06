#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROUTER_VERSION = "intent-first-negation-aware-s2-v0.4.0"

# Explicit exclusion cues. They are intentionally generic and operate on local
# mention scope rather than on benchmark item IDs or exact full sentences.
CN_PRE_NEG = re.compile(r"(?:不涉及|不包括|不查|不看|不要|不用|无需|不需要|不是查|不是看|不是问|不是要|排除|避免|而非|不走|不参考|不依赖|不采用|不搜|不检索)\s*$", re.I)
EN_PRE_NEG = re.compile(r"(?:\bnot\b|\bno\b|\bwithout\b|\bexclude(?:d|s|ing)?\b|\bexcluding\b|\bdo\s+not\s+(?:want|need|use|check|search|look\s+for)\b|\bdon't\s+(?:want|need|use|check|search)\b|\bnot\s+looking\s+for\b|\brather\s+than\b|\binstead\s+of\b)\s*$", re.I)
POST_NEG = re.compile(r"^\s*(?:不需要|不用|不要|除外|排除|is\s+not\s+needed|not\s+needed|is\s+excluded)", re.I)

# Direct source-name exclusions are applied after intent policy selection.
SOURCE_ALIASES = {
    "PUBMED": ["pubmed", "医学文献", "同行评议文献", "文献"],
    "CLINICALTRIALS_GOV": ["clinicaltrials.gov", "trial registry", "试验注册", "临床试验注册"],
    "DAILYMED_SPL": ["dailymed", "产品标签", "美国说明书", "当前说明书", "最新说明书", "处方信息"],
    "DRUGS_AT_FDA": ["drugs@fda", "drugs at fda"],
    "OPENFDA_FAERS": ["faers", "自发不良事件", "自发报告", "不良事件系统"],
    "RXNORM": ["rxnorm"],
    "LOINC": ["loinc"],
}


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iter_occurrences(text: str, phrase: str):
    start = 0
    while True:
        i = text.find(phrase, start)
        if i < 0:
            break
        yield i, i + len(phrase)
        start = i + max(1, len(phrase))


def _is_negated(q: str, start: int, end: int) -> bool:
    # Keep scope local: punctuation and contrast boundaries truncate the window.
    prefix = q[max(0, start - 48):start]
    prefix = re.split(r"[。！？!?;；\n]", prefix)[-1]
    # For comma-delimited Chinese/English exclusions, a short prefix is enough.
    short_prefix = prefix[-24:]
    suffix = q[end:min(len(q), end + 18)]
    return bool(CN_PRE_NEG.search(short_prefix) or EN_PRE_NEG.search(prefix) or POST_NEG.search(suffix))


def detect_features(query: str, feature_groups: dict[str, list[str]]):
    q = query.lower().strip()
    positive: dict[str, list[str]] = {}
    negative: dict[str, list[str]] = {}
    occurrences: dict[str, list[dict]] = {}
    for name, phrases in feature_groups.items():
        pos_hits, neg_hits, rows = [], [], []
        for phrase in phrases:
            p = phrase.lower()
            for start, end in _iter_occurrences(q, p):
                neg = _is_negated(q, start, end)
                rows.append({"phrase": phrase, "start": start, "end": end, "polarity": "NEGATIVE" if neg else "POSITIVE"})
                (neg_hits if neg else pos_hits).append(phrase)
        # Explicit exclusion wins for the feature group. This prevents an ID
        # mention such as NCT from defeating "not trial registry status".
        if neg_hits:
            negative[name] = sorted(set(neg_hits))
        elif pos_hits:
            positive[name] = sorted(set(pos_hits))
        if rows:
            occurrences[name] = rows
    return positive, negative, occurrences


def rule_matches(rule: dict, positive_hits: dict[str, list[str]]):
    present = set(positive_hits)
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
    positive, negative, occurrences = detect_features(query, feature_cfg["feature_groups"])
    candidates = []
    for index, rule in enumerate(feature_cfg["intent_rules"]):
        if rule_matches(rule, positive):
            matched_groups = set(rule.get("all", [])) | (set(rule.get("any", [])) & set(positive))
            score = float(rule.get("priority", 0)) + len(matched_groups) * 0.01
            candidates.append((score, -index, rule["intent"], sorted(matched_groups)))
    if not candidates:
        return feature_cfg["fallback_intent"], 0.0, positive, negative, occurrences, []
    candidates.sort(reverse=True)
    score, _, intent, matched_groups = candidates[0]
    return intent, score, positive, negative, occurrences, matched_groups


def detect_source_exclusions(query: str) -> list[str]:
    q = query.lower().strip()
    excluded = []
    for source_id, aliases in SOURCE_ALIASES.items():
        for alias in aliases:
            for start, end in _iter_occurrences(q, alias.lower()):
                if _is_negated(q, start, end):
                    excluded.append(source_id)
                    break
            if source_id in excluded:
                break
    return sorted(set(excluded))


def route(query: str, feature_cfg: dict, source_policy: dict):
    intent, score, positive, negative, occurrences, matched_groups = classify_intent(query, feature_cfg)
    policy = source_policy["intents"].get(intent)
    if policy is None:
        intent = feature_cfg["fallback_intent"]
        policy = source_policy["intents"][intent]
    excluded_sources = detect_source_exclusions(query)
    ranked = [s for s in policy["ranked_source_ids"] if s not in excluded_sources]
    return {
        "predicted_intent": intent,
        "ranked_source_ids": ranked[:3],
        "intent_score": score,
        "feature_hits": positive,
        "negated_feature_hits": negative,
        "feature_occurrences": occurrences,
        "matched_groups": matched_groups,
        "excluded_source_ids": excluded_sources,
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
        preds.append({"query_id": row["query_id"], "router_version": ROUTER_VERSION, **route(row["query"], feature_cfg, source_policy)})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} S2 v0.4 predictions to {out}")


if __name__ == "__main__":
    main()
