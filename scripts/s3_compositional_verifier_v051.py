#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base
import s3_compositional_verifier as v050

VERIFIER_VERSION = "s3-compositional-proposition-v0.5.1"

# Evidence polarity NEGATIVE for these predicates usually means "this source does not establish/provide it".
# A positive candidate claim is therefore unsupported, not necessarily factually contradicted.
ABSENCE_LIMITATION_PREDICATES = {
    "PROVIDES_ABSOLUTE_PROHIBITION",
    "CONFIRMS_DIAGNOSIS",
    "DIAGNOSTIC_INFERENCE",
    "DEMONSTRATES_EFFICACY",
    "ACHIEVES_ENDPOINT",
    "PROVIDES_MANAGEMENT_RULE",
    "PROVES_SUPERIORITY",
    "RISK_RANKING",
}

# Negative polarity on these predicates is a direct semantic conflict with a positive candidate claim.
HARD_CONTRADICTION_PREDICATES = {
    "ESTABLISHES_CAUSALITY",
    "ESTIMATES_TRUE_INCIDENCE",
    "IS_CURRENT",
}


def norm(text: str) -> str:
    return base.norm(text)


def add_prop(props: list[dict], clause: str, subject: str, predicate: str, object_: str, polarity: str = "POSITIVE", population: str | None = None):
    props.append(base.proposition(subject, predicate, object_, polarity, clause, population=population))


def extend_v051(text: str, props: list[dict]) -> list[dict]:
    """Add generic semantic relations that v0.5.0 diagnostics showed were still under-parsed."""
    t = norm(text)
    out = list(props)
    pop = base.infer_population(text)

    # Risk possibility phrasing: a possible toxicity statement is a risk proposition and, by itself, not a patient diagnosis.
    if any(p["predicate"] == "INCREASES_RISK" and p["polarity"] == "POSITIVE" for p in out):
        if not any(p["predicate"] == "CONFIRMS_DIAGNOSIS" for p in out):
            add_prop(out, text, "risk_evidence", "CONFIRMS_DIAGNOSIS", "patient_diagnosis", "NEGATIVE", pop)
    if any(x in t for x in ["possibility of the toxicity syndrome", "possible toxicity syndrome", "possibility of this syndrome"]):
        add_prop(out, text, "drug_exposure", "INCREASES_RISK", "toxicity_syndrome", "POSITIVE", pop)
        if not any(p["predicate"] == "CONFIRMS_DIAGNOSIS" for p in out):
            add_prop(out, text, "risk_evidence", "CONFIRMS_DIAGNOSIS", "patient_diagnosis", "NEGATIVE", pop)

    # Explicit bounded negative diagnosis claims.
    if any(x in t for x in ["not a diagnosis in a particular patient", "does not by itself diagnose", "does not diagnose a particular patient", "not itself a diagnosis"]):
        add_prop(out, text, "risk_evidence", "CONFIRMS_DIAGNOSIS", "patient_diagnosis", "NEGATIVE", pop)

    # Generic supersession with interrupted naming: "Guideline version 2 ... superseded version 1".
    m = re.search(r"(?:guideline\s+)?(version\s+[a-z0-9._-]+)[^.;]{0,90}?superseded\s+(version\s+[a-z0-9._-]+)", t)
    if m:
        newer, older = base.clean_entity(m.group(1)), base.clean_entity(m.group(2))
        add_prop(out, text, newer, "SUPERSEDES", older)
        add_prop(out, text, newer, "IS_CURRENT", "recommendation_source")
        add_prop(out, text, older, "IS_CURRENT", "recommendation_source", "NEGATIVE")

    # Candidate/evidence language around automatic guideline change.
    if any(x in t for x in ["current guideline now recommends", "automatically means that the current guideline now recommends", "automatically changes the current guideline recommendation"]):
        obj = "new_option"
        m2 = re.search(r"(?:recommends|recommendation (?:from [a-z0-9._-]+ )?to)\s+(?:treatment|option|standard)?\s*([a-z0-9._-]+)", t)
        if m2:
            obj = m2.group(1)
        add_prop(out, text, "current_guideline", "GUIDELINE_RECOMMENDS", obj)

    # Current guideline still recommends an existing named option.
    m3 = re.search(r"(?:still recommends|continues to recommend)\s+(?:treatment|option|standard)?\s*([a-z0-9._-]+)", t)
    if m3:
        add_prop(out, text, "current_guideline", "GUIDELINE_RECOMMENDS", m3.group(1))

    return base.dedupe_props(out)


def parse_atomic(text: str, *, candidate: bool = False) -> list[dict]:
    props = v050.parse_atomic(text)
    props = extend_v051(text, props)
    t = norm(text)

    # Rhetorical premise pruning: "X alone proves Y" scores Y as the core assertion;
    # X is a premise, not an independently credited supported conclusion.
    premise_markers = ["association alone proves", "association by itself proves", "mechanism evidence alone proves", "mechanism information alone proves", "registration alone proves", "report alone establishes"]
    if candidate and any(m in t for m in premise_markers):
        props = [p for p in props if p["predicate"] not in {"ASSOCIATED_WITH", "POTENTIAL_PK_INTERACTION", "SUPPORTS_SIGNAL_DETECTION", "REPORTS_DIFFERENT_RESPONSE_RATES"}]

    return base.dedupe_props(props)


def matching_evidence(evidence: list[dict], cp: dict) -> list[dict]:
    return v050.matching_evidence(evidence, cp)


def classify_proposition(evidence: list[dict], cp: dict):
    if cp["predicate"] in v050.ACTION_PREDICATES:
        return v050.classify_proposition(evidence, cp)

    matches = matching_evidence(evidence, cp)
    same = [e for e in matches if e["polarity"] == cp["polarity"]]
    opposite = [e for e in matches if e["polarity"] != cp["polarity"] and e["polarity"] != "UNKNOWN"]

    if same:
        verdict = "SUPPORTED"
        reason = "matching proposition with same polarity"
    elif opposite:
        if cp["polarity"] == "POSITIVE" and cp["predicate"] in ABSENCE_LIMITATION_PREDICATES:
            verdict = "UNSUPPORTED"
            reason = "source explicitly lacks/does not establish the requested positive claim"
        else:
            verdict = "CONTRADICTED"
            reason = "matching proposition with opposite polarity"
    else:
        verdict = "UNSUPPORTED"
        reason = "no matching evidence proposition"

    return {
        "proposition": cp,
        "verdict": verdict,
        "safety_class": v050.safety_class(cp),
        "evidence_matches": matches,
        "reason": reason,
    }


def aggregate(verdicts: list[dict]):
    if not verdicts:
        return "DOES_NOT_SUPPORT", ["no_candidate_propositions"]

    counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "UNSUPPORTED": 0}
    for row in verdicts:
        counts[row["verdict"]] += 1

    dangerous_non_support = [
        row for row in verdicts
        if row["safety_class"] != "OTHER" and row["verdict"] in {"CONTRADICTED", "UNSUPPORTED"}
    ]

    if counts["SUPPORTED"] == len(verdicts):
        return "DIRECT_SUPPORT", ["all_candidate_propositions_supported"]

    if counts["SUPPORTED"] > 0:
        return "PARTIAL_SUPPORT", [
            f"supported={counts['SUPPORTED']}",
            f"contradicted={counts['CONTRADICTED']}",
            f"unsupported={counts['UNSUPPORTED']}",
            f"dangerous_extensions={len(dangerous_non_support)}",
        ]

    # With no supported subclaim, explicit contradiction wins only when a proposition is truly contradicted.
    if counts["CONTRADICTED"] > 0:
        return "CONTRADICTS", [
            f"contradicted={counts['CONTRADICTED']}",
            f"unsupported={counts['UNSUPPORTED']}",
        ]

    return "DOES_NOT_SUPPORT", [f"unsupported={counts['UNSUPPORTED']}"]


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
    print(f"Wrote {len(rows)} S3 v0.5.1 compositional predictions to {out}")


if __name__ == "__main__":
    main()
