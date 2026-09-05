#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base

VERIFIER_VERSION = "s3-atomic-proposition-v0.4.1"


def conditions_from_clause(clause: str) -> list[dict]:
    t = base.norm(clause)
    out: list[dict] = []
    range_patterns = [
        r"egfr[^.;,]{0,22}?(\d+)\s*(?:to|through|[-–])\s*(\d+)",
        r"egfr[^.;,]{0,22}?between\s*(\d+)\s*and\s*(\d+)",
        r"between\s+egfr\s*(\d+)\s*and\s*(\d+)",
    ]
    for pat in range_patterns:
        for m in re.finditer(pat, t):
            a, b = int(m.group(1)), int(m.group(2))
            row = {"variable": "egfr", "operator": "RANGE", "value": None, "low": min(a, b), "high": max(a, b), "unit": None}
            if row not in out:
                out.append(row)
    for pat in [r"egfr[^.;,]{0,20}?(?:below|under|<)\s*(\d+)", r"(?:below|under|<)\s*egfr\s*(\d+)"]:
        for m in re.finditer(pat, t):
            row = {"variable": "egfr", "operator": "LT", "value": int(m.group(1)), "low": None, "high": None, "unit": None}
            if row not in out:
                out.append(row)
    for m in re.finditer(r"egfr\s*(?:of|=|is|at)?\s*(\d+)", t):
        val = int(m.group(1))
        if any(x.get("value") == val or x.get("low") == val or x.get("high") == val for x in out):
            continue
        out.append({"variable": "egfr", "operator": "EQ", "value": val, "low": None, "high": None, "unit": None})
    return out


def parse_action_clause(clause: str, population: str | None) -> list[dict]:
    t = base.norm(clause)
    conds = conditions_from_clause(clause)
    out: list[dict] = []
    if base.has(t, "contraindicat", "contraindication criterion"):
        if base.has(t, "does not provide", "does not state", "no contraindication", "no clinical contraindication", "contains no", "not an absolute contraindication"):
            out.append(base.proposition("evidence", "PROVIDES_ABSOLUTE_PROHIBITION", "drug_or_combination", "NEGATIVE", clause, population=population))
        else:
            out.append(base.proposition("drug_use", "CONTRAINDICATED", "use", "POSITIVE", clause, conds, population))
    if base.has(t, "not recommended") and base.has(t, "initiat", "starting", "new treatment", "new patient", "start"):
        out.append(base.proposition("drug_initiation", "INITIATION_NOT_RECOMMENDED", "initiation", "POSITIVE", clause, conds, population or "new_or_initiating_user"))
    if base.has(t, "reassess", "reassessment", "benefit-risk reassessment", "benefit versus risk", "benefit and risk should be reassessed", "benefit/risk"):
        out.append(base.proposition("drug_use", "REASSESS_BENEFIT_RISK", "benefit_risk", "POSITIVE", clause, conds, population))
    if base.has(t, "discontinu", "must stop", "must discontinue", "stop the medicine", "stop the drug"):
        out.append(base.proposition("drug_use", "DISCONTINUE", "drug", "POSITIVE", clause, conds, population))
    return out


def parse_non_action_clause(clause: str, population: str | None) -> list[dict]:
    t = base.norm(clause)
    out = base.parse_non_action_clause(clause, population)

    def drop(predicate: str, polarity: str | None = None):
        nonlocal out
        out = [p for p in out if not (p["predicate"] == predicate and (polarity is None or p["polarity"] == polarity))]

    def add(subject, predicate, object_, polarity="POSITIVE", confidence=1.0):
        out.append(base.proposition(subject, predicate, object_, polarity, clause, population=population, confidence=confidence))

    # Risk/toxicity paraphrases.
    if base.has(t, "can precipitate", "may precipitate") and base.has(t, "syndrome", "toxicity"):
        add("drug_exposure", "INCREASES_RISK", "toxicity_syndrome")
    if base.has(t, "possible toxicity risk", "risk of the toxicity syndrome", "possible serious adverse"):
        add("drug_exposure", "INCREASES_RISK", "toxicity_syndrome")
    if base.has(t, "not a diagnosis", "does not by itself diagnose", "does not confirm", "no malignant diagnosis"):
        drop("CONFIRMS_DIAGNOSIS", "POSITIVE")
        add("evidence", "CONFIRMS_DIAGNOSIS", "diagnosis", "NEGATIVE")

    # Signal detection as an explicit bounded capability.
    if base.has(t, "signal detection", "detecting possible safety signals", "detection of a reported safety signal", "contribute to signal detection", "safety-signal detection"):
        add("spontaneous_report_system", "SUPPORTS_SIGNAL_DETECTION", "safety_signal")

    # Preserve causal negation across more paraphrases; negation always removes accidental positive causal propositions.
    causal_negative = (
        "does not establish that", "does not establish causality", "do not on their own demonstrate",
        "do not by themselves establish", "cannot by themselves establish", "cannot on their own establish",
        "causal attribution is not established", "causality is not established", "does not prove that",
        "cannot establish", "not establish that", "causality requires other evidence",
        "causal attribution remains unproven", "does not establish a causal relationship",
    )
    if base.has(t, *causal_negative):
        drop("ESTABLISHES_CAUSALITY", "POSITIVE")
        add("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "NEGATIVE")

    # Incidence polarity.
    incidence_negative = (
        "not a valid estimate of", "cannot be used to estimate", "cannot establish the true incidence",
        "cannot estimate", "report counts cannot", "not sufficient to calculate the true incidence",
        "cannot establish true incidence",
    )
    if base.has(t, *incidence_negative):
        drop("ESTIMATES_TRUE_INCIDENCE", "POSITIVE")
        add("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "NEGATIVE")
    elif base.has(t, "obtain the true adverse-event incidence", "provides the true adverse-event incidence", "provides the true incidence", "calculate the true incidence", "true adverse-event incidence"):
        drop("ESTIMATES_TRUE_INCIDENCE", "NEGATIVE")
        add("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "POSITIVE")

    # Generic and interrupted supersession wording.
    supersession_patterns = [
        r"(guideline\s+[a-z0-9._-]+)[^.;]{0,65}?supersedes\s+(guideline\s+[a-z0-9._-]+)",
        r"(version\s+[a-z0-9._-]+)[^.;]{0,65}?supersedes\s+(version\s+[a-z0-9._-]+)",
    ]
    found = False
    for pat in supersession_patterns:
        m = re.search(pat, t)
        if m:
            newer, older = base.clean_entity(m.group(1)), base.clean_entity(m.group(2))
            add(newer, "SUPERSEDES", older)
            add(newer, "IS_CURRENT", "recommendation_source")
            add(older, "IS_CURRENT", "recommendation_source", "NEGATIVE")
            found = True
    if not found and base.has(t, "supersedes", "superseded") and base.has(t, "later", "newer") and base.has(t, "older", "old"):
        add("later_version", "SUPERSEDES", "older_version")
        add("later_version", "IS_CURRENT", "recommendation_source")
        add("older_version", "IS_CURRENT", "recommendation_source", "NEGATIVE")
    if base.has(t, "later guideline version is the current", "later version is the current", "newer guideline version is the current"):
        add("later_version", "IS_CURRENT", "recommendation_source")
    if base.has(t, "older version remains current", "old version remains current", "older guideline remains current"):
        add("older_version", "IS_CURRENT", "recommendation_source")

    # New evidence and current guideline state are represented separately.
    if base.has(t, "new randomized trial supports", "new randomized study favors", "newly published randomized trial favors", "evidence landscape has changed", "new trial evidence"):
        add("new_evidence", "NEW_EVIDENCE_SUPPORTS", "new_option")
    if base.has(t, "continues to recommend", "still recommends"):
        m = re.search(r"(?:continues to recommend|still recommends)\s+(?:option|treatment|standard)?\s*([a-z0-9._-]+)", t)
        add("current_guideline", "GUIDELINE_RECOMMENDS", m.group(1) if m else "existing_option")
    if base.has(t, "automatically changes the current guideline", "automatically changes the guideline", "automatically means that the current guideline", "guideline now recommends"):
        add("current_guideline", "GUIDELINE_RECOMMENDS", "new_option")
    if base.has(t, "current guideline recommendation has not yet changed", "current guideline still recommends"):
        add("current_guideline", "IS_CURRENT", "existing_recommendation")

    # Management language must override a benign association.
    if base.has(t, "dose must be changed", "must change the dose", "requires a lower dose", "must receive a lower dose", "clinically contraindicated", "requires dose adjustment"):
        drop("PROVIDES_MANAGEMENT_RULE", "NEGATIVE")
        add("mechanism_or_pk_evidence", "PROVIDES_MANAGEMENT_RULE", "drug_pair_or_patient")
    if base.has(t, "no therapeutic-management recommendation", "no therapeutic dose recommendation", "no management instruction", "no dose adjustment", "no product-specific management rule"):
        drop("PROVIDES_MANAGEMENT_RULE", "POSITIVE")
        add("mechanism_or_pk_evidence", "PROVIDES_MANAGEMENT_RULE", "drug_pair_or_patient", "NEGATIVE")

    # Registry no-result wording.
    if base.has(t, "no trial result", "contains no trial result", "no result demonstrating clinical benefit", "no efficacy outcome"):
        drop("DEMONSTRATES_EFFICACY", "POSITIVE")
        add("registry_evidence", "DEMONSTRATES_EFFICACY", "clinical_benefit", "NEGATIVE")

    return base.dedupe_props(out)


def parse_atomic(text: str) -> list[dict]:
    global_population = base.infer_population(text)
    props: list[dict] = []
    for clause in base.split_clauses(text):
        pop = base.infer_population(clause) or global_population
        props.extend(parse_action_clause(clause, pop))
        props.extend(parse_non_action_clause(clause, pop))
    return base.dedupe_props(props)


def compare(evidence: list[dict], claim: list[dict]) -> tuple[str, list[str]]:
    # Current guideline recommendation with different objects is an explicit temporal contradiction.
    ev_rec = [p for p in evidence if p["predicate"] == "GUIDELINE_RECOMMENDS" and p["polarity"] == "POSITIVE"]
    cl_rec = [p for p in claim if p["predicate"] == "GUIDELINE_RECOMMENDS" and p["polarity"] == "POSITIVE"]
    if ev_rec and cl_rec:
        ev_obj = {str(p["object"]) for p in ev_rec}
        cl_obj = {str(p["object"]) for p in cl_rec}
        if ev_obj & cl_obj:
            return "DIRECT_SUPPORT", ["current_guideline_recommendation_preserved"]
        return "CONTRADICTS", [f"guideline_recommendation_conflict:{sorted(ev_obj)}->{sorted(cl_obj)}"]

    # Explicit management absence dominates PGx/mechanistic association.
    claim_management = any(p["predicate"] == "PROVIDES_MANAGEMENT_RULE" and p["polarity"] == "POSITIVE" for p in claim)
    evidence_no_management = any(p["predicate"] == "PROVIDES_MANAGEMENT_RULE" and p["polarity"] == "NEGATIVE" for p in evidence)
    if claim_management and evidence_no_management:
        return "DOES_NOT_SUPPORT", ["explicit_no_management_rule"]

    return base.compare(evidence, claim)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        evidence = parse_atomic(item["evidence_text"])
        claim = parse_atomic(item["candidate_claim"])
        relation, cues = compare(evidence, claim)
        rows.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "evidence_propositions": evidence,
            "claim_propositions": claim,
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3 v0.4.1 predictions to {out}")


if __name__ == "__main__":
    main()
