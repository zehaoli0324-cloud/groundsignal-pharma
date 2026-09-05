#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base
import s3_compositional_verifier as v050
import s3_compositional_verifier_v052 as v052

VERIFIER_VERSION = "s3-compositional-proposition-v0.5.3"


def norm(text: str) -> str:
    return base.norm(text)


def p(subject: str, predicate: str, object_: str, polarity: str, clause: str, *, conditions=None, population=None, confidence=1.0):
    return base.proposition(subject, predicate, object_, polarity, clause, conditions=conditions, population=population, confidence=confidence)


def _lt_condition(value: int) -> list[dict]:
    return [{"variable": "egfr", "operator": "LT", "value": value, "low": None, "high": None, "unit": None}]


def _repair_action_scope(text: str, props: list[dict]) -> list[dict]:
    """Preserve action polarity and bind threshold-only wording to its action."""
    out: list[dict] = []
    for prop in props:
        q = dict(prop)
        src = norm(q.get("source_clause", ""))
        pred = q.get("predicate")

        if pred == "CONTRAINDICATED" and re.search(r"\b(?:is|are|be)?\s*not\s+contraindicated\b|\bnot\s+an?\s+contraindication\b", src):
            q["polarity"] = "NEGATIVE"

        if pred == "DISCONTINUE" and re.search(r"\bnot\s+(?:automatic(?:ally)?\s+)?(?:discontinu|stop)|\bwithout\s+automatic\s+discontinu", src):
            q["polarity"] = "NEGATIVE"

        # The v0.5 set intentionally uses threshold-noun wording without repeating eGFR.
        if pred == "DISCONTINUE" and not q.get("conditions"):
            m = re.search(r"(?:discontinuation|stopping|stop)\s+threshold\s+(?:is\s+)?(?:below|under|<)\s*(\d+)", src)
            if m:
                q["conditions"] = _lt_condition(int(m.group(1)))

        out.append(q)
    return out


def _remove_spurious_props(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out: list[dict] = []
    for prop in props:
        pred = prop.get("predicate")
        src = norm(prop.get("source_clause", ""))

        # "no comparison showing which subgroup..." is not a diagnosis statement.
        if pred == "CONFIRMS_DIAGNOSIS" and not any(x in t for x in ["diagnos", "syndrome", "lesion", "malignan", "benign", "patient has"]):
            continue

        # "no evidence that the endpoint was met" must never create a positive endpoint-achievement fact.
        if pred == "ACHIEVES_ENDPOINT" and any(x in src for x in ["no evidence", "does not show", "does not establish", "not establish", "whether that endpoint was achieved"]):
            continue

        # Endpoint-evidence limitations are not generic causal propositions.
        if pred == "ESTABLISHES_CAUSALITY" and "endpoint" in src:
            continue

        out.append(prop)
    return out


def _add_signal_and_causality(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out = list(props)

    if any(x in t for x in [
        "contribute to detecting a possible safety signal",
        "contribute to safety-signal detection",
        "contribute to detecting a safety signal",
        "identify a safety signal",
        "detecting a possible safety signal",
    ]):
        out.append(p("spontaneous_report_system", "SUPPORTS_SIGNAL_DETECTION", "safety_signal", "POSITIVE", text))

    if any(x in t for x in [
        "causal attribution cannot be established",
        "causal attribution remains unestablished",
        "causal attribution remains unproven",
        "cannot establish that the product caused",
        "cannot establish causality",
    ]):
        out.append(p("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "NEGATIVE", text))

    return out


def _add_incidence_props(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out = list(props)
    if re.search(r"(?:observed\s+)?(?:spontaneous-?report|report)\s+count[^.;]*\b(?:is not|does not)\b[^.;]*(?:measure|determine|estimate)[^.;]*(?:true\s+)?(?:event\s+)?incidence", t):
        out.append(p("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "NEGATIVE", text))
    if re.search(r"(?:observed\s+)?(?:spontaneous-?report|report)\s+count[^.;]*(?:measure|determine|estimate)s?[^.;]*(?:true\s+)?(?:event\s+)?incidence", t) and not re.search(r"\b(?:is not|does not|cannot)\b", t):
        out.append(p("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "POSITIVE", text))
    return out


def _add_endpoint_props(text: str, props: list[dict], *, candidate: bool) -> list[dict]:
    t = norm(text)
    out = list(props)

    limitation = any(x in t for x in [
        "does not show whether that endpoint was achieved",
        "does not establish that the endpoint was achieved",
        "does not establish that the endpoint was met",
        "no evidence here that the endpoint was met",
        "no evidence that the endpoint was met",
        "no evidence here that the endpoint was achieved",
    ])
    if limitation:
        out.append(p("evidence", "ESTABLISHES_ENDPOINT_ACHIEVEMENT", "primary_endpoint", "NEGATIVE", text))

    # Positive endpoint success is an independent proposition and must not disappear behind completion status.
    if re.search(r"(?:primary\s+)?endpoint\s+(?:was|is|has been)\s+(?:successfully\s+)?(?:achieved|met)", t):
        if not limitation:
            out.append(p("study", "ACHIEVES_ENDPOINT", "primary_endpoint", "POSITIVE", text))

    return out


def _add_ranking_props(text: str, props: list[dict], *, candidate: bool) -> list[dict]:
    t = norm(text)
    out = list(props)

    # Risk subgroup ranking.
    if re.search(r"(?:patients|people)\s+(?:over|older than|aged over)\s*75[^.;]*(?:greatest|highest)\s+risk", t):
        out.append(p("age_group", "RISK_RANKING", "over_75_highest", "POSITIVE", text))
    if any(x in t for x in ["no comparison showing which age group has the greatest risk", "no comparison showing which age group has the highest risk"]):
        out.append(p("evidence", "PROVIDES_RISK_RANKING", "age_groups", "NEGATIVE", text))

    # Generic subgroup association-strength ranking used in v0.5.
    m = re.search(r"subgroup\s+([a-z0-9._-]+)\s+has\s+(?:a\s+)?stronger\s+association\s+than\s+subgroup\s+([a-z0-9._-]+)", t)
    if m:
        out.append(p("subgroup_comparison", "ASSOCIATION_RANKING", f"{m.group(1)}>{m.group(2)}", "POSITIVE", text))
    if re.search(r"no information about whether subgroup\s+[a-z0-9._-]+\s+has\s+stronger\s+association\s+than\s+subgroup\s+[a-z0-9._-]+", t):
        out.append(p("evidence", "PROVIDES_ASSOCIATION_RANKING", "subgroups", "NEGATIVE", text))

    return out


def _add_association_props(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out = list(props)
    for pat in [
        r"supports\s+(?:an\s+)?association\s+([a-z0-9._-]+)\s+with\s+(?:outcome\s+)?([a-z0-9._-]+)",
        r"association\s+([a-z0-9._-]+)\s+with\s+(?:outcome\s+)?([a-z0-9._-]+)",
    ]:
        m = re.search(pat, t)
        if m:
            out.append(p(m.group(1), "ASSOCIATED_WITH", m.group(2), "POSITIVE", text))
            break
    return out


def _add_category_props(text: str, props: list[dict]) -> list[dict]:
    t = norm(text)
    out = list(props)
    if re.search(r"lesion\s+(?:is\s+)?(?:explicitly\s+)?classified\s+as\s+benign", t):
        out.append(p("lesion", "CLASSIFIED_AS", "benign", "POSITIVE", text))
    if re.search(r"lesion\s+(?:is\s+)?(?:explicitly\s+)?classified\s+as\s+malignant", t):
        out.append(p("lesion", "CLASSIFIED_AS", "malignant", "POSITIVE", text))
    return out


def parse_atomic(text: str, *, candidate: bool = False) -> list[dict]:
    props = v052.parse_atomic(text, candidate=candidate)
    props = _repair_action_scope(text, props)
    props = _remove_spurious_props(text, props)
    props = _add_signal_and_causality(text, props)
    props = _add_incidence_props(text, props)
    props = _add_endpoint_props(text, props, candidate=candidate)
    props = _add_ranking_props(text, props, candidate=candidate)
    props = _add_association_props(text, props)
    props = _add_category_props(text, props)
    return base.dedupe_props(props)


def _point_value(prop: dict) -> float | None:
    for c in prop.get("conditions", []):
        if c.get("variable") == "egfr" and c.get("operator") == "EQ" and c.get("value") is not None:
            return float(c["value"])
    return None


def _condition_covers(prop: dict, value: float) -> bool:
    conds = [c for c in prop.get("conditions", []) if c.get("variable") == "egfr"]
    if not conds:
        return True
    for c in conds:
        op = c.get("operator")
        if op == "LT" and value < float(c["value"]):
            return True
        if op == "EQ" and value == float(c["value"]):
            return True
        if op == "RANGE" and float(c["low"]) <= value <= float(c["high"]):
            return True
    return False


def _action_identity(e: dict, c: dict) -> bool:
    return e.get("predicate") == c.get("predicate") and e.get("subject") == c.get("subject")


def _classify_action(evidence: list[dict], cp: dict) -> dict:
    value = _point_value(cp)
    same_action = [e for e in evidence if _action_identity(e, cp)]

    if value is not None:
        applicable = [e for e in same_action if _condition_covers(e, value)]
        nonapplicable_explicit = [e for e in same_action if e.get("conditions") and not _condition_covers(e, value)]
    else:
        applicable = same_action
        nonapplicable_explicit = []

    same_pol = [e for e in applicable if e.get("polarity") == cp.get("polarity")]
    opp_pol = [e for e in applicable if e.get("polarity") != cp.get("polarity")]

    if same_pol:
        return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_pol, "reason": "matching scoped action proposition"}
    if opp_pol:
        return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": opp_pol, "reason": "same scoped action has opposite polarity"}

    # A negative patient-level action can be supported by an explicit threshold rule that does not apply at this value.
    if cp.get("polarity") == "NEGATIVE" and value is not None and nonapplicable_explicit:
        return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": nonapplicable_explicit, "reason": "explicit action threshold does not apply at this value"}

    # Preserve v0.5.2's useful conflict logic for positive point claims.
    if cp.get("polarity") == "POSITIVE" and value is not None:
        competing = [
            e for e in evidence
            if e.get("predicate") in v050.ACTION_PREDICATES
            and e.get("polarity") == "POSITIVE"
            and _condition_covers(e, value)
        ]
        if competing:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": competing, "reason": "different evidence action applies at this value"}

    return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_action, "reason": "no supporting scoped action proposition"}


def classify_proposition(evidence: list[dict], cp: dict) -> dict:
    pred = cp.get("predicate")

    if pred in v050.ACTION_PREDICATES:
        return _classify_action(evidence, cp)

    # Explicitly mutually exclusive categorical report values.
    if pred == "CLASSIFIED_AS" and cp.get("polarity") == "POSITIVE":
        same_subject = [e for e in evidence if e.get("predicate") == "CLASSIFIED_AS" and e.get("subject") == cp.get("subject") and e.get("polarity") == "POSITIVE"]
        exact = [e for e in same_subject if str(e.get("object")) == str(cp.get("object"))]
        if exact:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "DIAGNOSTIC", "evidence_matches": exact, "reason": "same explicit report classification"}
        mutually_exclusive = {"benign", "malignant"}
        if str(cp.get("object")) in mutually_exclusive and any(str(e.get("object")) in mutually_exclusive for e in same_subject):
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "DIAGNOSTIC", "evidence_matches": same_subject, "reason": "mutually exclusive explicit report classification"}

    # Unsupported subgroup ranking stays unsupported when the source explicitly says it contains no comparison.
    if pred == "RISK_RANKING":
        exact = [e for e in evidence if e.get("predicate") == pred and e.get("subject") == cp.get("subject") and e.get("object") == cp.get("object") and e.get("polarity") == cp.get("polarity")]
        if exact:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "OTHER", "evidence_matches": exact, "reason": "same subgroup risk ranking"}
        limitations = [e for e in evidence if e.get("predicate") == "PROVIDES_RISK_RANKING" and e.get("polarity") == "NEGATIVE"]
        return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "OTHER", "evidence_matches": limitations, "reason": "source does not provide the claimed subgroup risk ranking"}

    if pred == "ASSOCIATION_RANKING":
        exact = [e for e in evidence if e.get("predicate") == pred and e.get("object") == cp.get("object") and e.get("polarity") == cp.get("polarity")]
        if exact:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "OTHER", "evidence_matches": exact, "reason": "same subgroup association ranking"}
        limitations = [e for e in evidence if e.get("predicate") == "PROVIDES_ASSOCIATION_RANKING" and e.get("polarity") == "NEGATIVE"]
        return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "OTHER", "evidence_matches": limitations, "reason": "source does not provide the claimed subgroup association ranking"}

    # Absence of endpoint-achievement evidence is not evidence the endpoint failed.
    if pred == "ACHIEVES_ENDPOINT" and cp.get("polarity") == "POSITIVE":
        positive = [e for e in evidence if e.get("predicate") == pred and e.get("object") == cp.get("object") and e.get("polarity") == "POSITIVE"]
        if positive:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "EFFICACY", "evidence_matches": positive, "reason": "endpoint achievement explicitly supported"}
        limitation = [e for e in evidence if e.get("predicate") == "ESTABLISHES_ENDPOINT_ACHIEVEMENT" and e.get("polarity") == "NEGATIVE"]
        if limitation:
            return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "EFFICACY", "evidence_matches": limitation, "reason": "source does not establish endpoint achievement"}

    return v052.classify_proposition(evidence, cp)


def aggregate(verdicts: list[dict]):
    return v052.aggregate(verdicts)


def verify(evidence_text: str, claim_text: str):
    evidence = parse_atomic(evidence_text, candidate=False)
    candidate = parse_atomic(claim_text, candidate=True)
    verdicts = [classify_proposition(evidence, cp) for cp in candidate]
    relation, cues = aggregate(verdicts)
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
        rows.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "evidence_propositions": evidence,
            "candidate_propositions": candidate,
            "proposition_verdicts": verdicts,
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3 v0.5.3 predictions to {out}")


if __name__ == "__main__":
    main()
