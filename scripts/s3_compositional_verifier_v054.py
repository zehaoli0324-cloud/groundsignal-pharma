#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base
import s3_compositional_verifier as v050
import s3_compositional_verifier_v053 as v053

VERIFIER_VERSION = "s3-compositional-proposition-v0.5.4"


def norm(text: str) -> str:
    return base.norm(text)


def _lt(v: int) -> list[dict]:
    return [{"variable": "egfr", "operator": "LT", "value": v, "low": None, "high": None, "unit": None}]


def _repair_missing_action_thresholds(props: list[dict]) -> list[dict]:
    out = []
    for prop in props:
        q = dict(prop)
        if q.get("predicate") in v050.ACTION_PREDICATES and not q.get("conditions"):
            src = norm(q.get("source_clause", ""))
            m = re.search(r"(?:below|under|lower\s+than|less\s+than|<)\s*(\d+)", src)
            if m:
                q["conditions"] = _lt(int(m.group(1)))
        out.append(q)
    return out


def _repair_endpoint_limitations(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out = []
    endpoint_limitation = any(x in t for x in [
        "no result showing that the endpoint was met",
        "contains no result showing that the endpoint was met",
        "contains no result showing the endpoint was met",
        "does not contain peer-reviewed trial results",
        "not claiming that the endpoint was successfully met",
        "not claiming the endpoint was successfully met",
    ])
    for prop in props:
        if endpoint_limitation and prop.get("predicate") == "ACHIEVES_ENDPOINT" and prop.get("polarity") == "POSITIVE":
            continue
        out.append(prop)
    if endpoint_limitation and "endpoint" in t:
        out.append(base.proposition("evidence", "ESTABLISHES_ENDPOINT_ACHIEVEMENT", "primary_endpoint", "NEGATIVE", text))
    return out


def _repair_negated_rankings(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    ranking_limited = bool(re.search(r"(?:no information|no comparison|does not provide|provides no information)[^.;]{0,80}(?:subgroup|age group)[^.;]{0,80}(?:stronger association|greatest risk|highest risk)", t))
    out = []
    for prop in props:
        if ranking_limited and prop.get("predicate") in {"ASSOCIATION_RANKING", "RISK_RANKING"} and prop.get("polarity") == "POSITIVE":
            continue
        out.append(prop)
    return out


def parse_atomic(text: str, *, candidate: bool = False) -> list[dict]:
    props = v053.parse_atomic(text, candidate=candidate)
    props = _repair_missing_action_thresholds(props)
    props = _repair_endpoint_limitations(text, props)
    if not candidate:
        props = _repair_negated_rankings(text, props)
    return base.dedupe_props(props)


def _egfr_condition(prop: dict) -> dict | None:
    for c in prop.get("conditions", []):
        if c.get("variable") == "egfr":
            return c
    return None


def _eq_value(prop: dict) -> float | None:
    c = _egfr_condition(prop)
    if c and c.get("operator") == "EQ":
        return float(c["value"])
    return None


def _contains(rule: dict, value: float) -> bool:
    c = _egfr_condition(rule)
    if c is None:
        return True
    op = c.get("operator")
    if op == "LT":
        return value < float(c["value"])
    if op == "EQ":
        return value == float(c["value"])
    if op == "RANGE":
        return float(c["low"]) <= value <= float(c["high"])
    return False


def _same_or_narrower(candidate: dict, evidence: dict) -> bool:
    """Return True when every eGFR value asserted by candidate lies inside evidence rule."""
    cc = _egfr_condition(candidate)
    ec = _egfr_condition(evidence)
    if ec is None:
        return True
    if cc is None:
        return False
    cop, eop = cc.get("operator"), ec.get("operator")
    if cop == "EQ":
        return _contains(evidence, float(cc["value"]))
    if cop == "LT" and eop == "LT":
        return float(cc["value"]) <= float(ec["value"])
    if cop == "RANGE" and eop == "RANGE":
        return float(ec["low"]) <= float(cc["low"]) and float(cc["high"]) <= float(ec["high"])
    if cop == "RANGE" and eop == "LT":
        return float(cc["high"]) < float(ec["value"])
    return False


def _classify_action(evidence: list[dict], cp: dict) -> dict:
    same_action = [e for e in evidence if e.get("predicate") == cp.get("predicate") and e.get("subject") == cp.get("subject")]
    same_pol = [e for e in same_action if e.get("polarity") == cp.get("polarity")]
    opp_pol = [e for e in same_action if e.get("polarity") != cp.get("polarity")]

    # Patient-point claims.
    value = _eq_value(cp)
    if value is not None:
        applicable_same = [e for e in same_pol if _contains(e, value)]
        applicable_opp = [e for e in opp_pol if _contains(e, value)]
        if applicable_same:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": applicable_same, "reason": "same action applies at patient eGFR"}
        if applicable_opp:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": applicable_opp, "reason": "same action has opposite polarity at patient eGFR"}
        if cp.get("polarity") == "NEGATIVE" and any(_egfr_condition(e) is not None for e in same_pol + opp_pol):
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_pol + opp_pol, "reason": "explicit action threshold does not apply at patient eGFR"}
        competing = [e for e in evidence if e.get("predicate") in v050.ACTION_PREDICATES and e.get("polarity") == "POSITIVE" and _contains(e, value)]
        if cp.get("polarity") == "POSITIVE" and competing:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": competing, "reason": "different action applies at patient eGFR"}
        return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_action, "reason": "claimed action not supported at patient eGFR"}

    # Rule claims such as <45 versus an evidence rule of <30.
    if cp.get("polarity") == "POSITIVE":
        supported = [e for e in same_pol if _same_or_narrower(cp, e)]
        if supported:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": supported, "reason": "candidate action range is within evidence rule"}
        if same_pol and _egfr_condition(cp) is not None:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": same_pol, "reason": "candidate action range is broader than evidence rule"}
        if opp_pol:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": opp_pol, "reason": "same action has opposite polarity"}

    if cp.get("polarity") == "NEGATIVE" and opp_pol:
        return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": opp_pol, "reason": "evidence positively specifies the denied action"}

    return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_action, "reason": "no compatible scoped action proposition"}


def classify_proposition(evidence: list[dict], cp: dict) -> dict:
    if cp.get("predicate") in v050.ACTION_PREDICATES:
        return _classify_action(evidence, cp)
    return v053.classify_proposition(evidence, cp)


def verify(evidence_text: str, claim_text: str):
    evidence = parse_atomic(evidence_text, candidate=False)
    candidate = parse_atomic(claim_text, candidate=True)
    verdicts = [classify_proposition(evidence, cp) for cp in candidate]
    relation, cues = v053.aggregate(verdicts)
    return relation, evidence, candidate, verdicts, cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        relation, evidence, candidate, verdicts, cues = verify(item["evidence_text"], item["candidate_claim"])
        rows.append({"item_id": item["item_id"], "predicted_relation": relation, "evidence_propositions": evidence, "candidate_propositions": candidate, "proposition_verdicts": verdicts, "cues": cues, "verifier_version": VERIFIER_VERSION})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3 v0.5.4 predictions to {out}")


if __name__ == "__main__":
    main()
