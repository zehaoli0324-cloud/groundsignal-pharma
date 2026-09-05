#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base
import s3_compositional_verifier as v050
import s3_compositional_verifier_v051 as v051

VERIFIER_VERSION = "s3-compositional-proposition-v0.5.2"


def norm(text: str) -> str:
    return base.norm(text)


def clean_version_entity(x: str) -> str:
    return base.clean_entity(x.replace("guideline version", "version"))


def normalize_diagnosis_props(props: list[dict]) -> list[dict]:
    out = []
    for p in props:
        q = dict(p)
        if q["predicate"] == "CONFIRMS_DIAGNOSIS":
            q["subject"] = "evidence"
            q["object"] = "patient_diagnosis"
        out.append(q)
    return base.dedupe_props(out)


def repair_temporal_props(text: str, props: list[dict]) -> list[dict]:
    """Rebuild IS_CURRENT from directional supersession and clause-local current assertions.

    This intentionally removes permissive regex-derived IS_CURRENT propositions that can bind
    the subject from an earlier clause (e.g. version 2 ... , version 1 remains current).
    """
    t = norm(text)
    out = [p for p in props if p["predicate"] != "IS_CURRENT"]

    # Derive current / not-current only from explicit directional SUPERSEDES propositions.
    for p in list(out):
        if p["predicate"] == "SUPERSEDES" and p["polarity"] == "POSITIVE":
            out.append(base.proposition(p["subject"], "IS_CURRENT", "recommendation_source", "POSITIVE", p["source_clause"], population=p.get("population")))
            out.append(base.proposition(str(p["object"]), "IS_CURRENT", "recommendation_source", "NEGATIVE", p["source_clause"], population=p.get("population")))

    # Precise clause-local named current assertions. The entity must be immediately attached to the current predicate.
    patterns = [
        r"((?:guideline\s+)?version\s+[a-z0-9._-]+)\s+(?:remains|is|should still be treated as|should be treated as|is still treated as)\s+(?:the\s+)?current",
        r"(guideline\s+[a-z0-9._-]+)\s+(?:remains|is|should still be treated as|should be treated as|is still treated as)\s+(?:the\s+)?current",
    ]
    for pat in patterns:
        for m in re.finditer(pat, t):
            subject = clean_version_entity(m.group(1)) if "version" in m.group(1) else base.clean_entity(m.group(1))
            out.append(base.proposition(subject, "IS_CURRENT", "recommendation_source", "POSITIVE", m.group(0)))

    # Generic relational wording.
    if any(x in t for x in ["later guideline version is the current", "later version is the current", "newer guideline version is the current"]):
        out.append(base.proposition("later_version", "IS_CURRENT", "recommendation_source", "POSITIVE", text))
    if any(x in t for x in ["older guideline version is the current", "older version remains current", "old version remains current", "older guideline remains current"]):
        out.append(base.proposition("older_version", "IS_CURRENT", "recommendation_source", "POSITIVE", text))
    if "superseded older version" in t:
        out.append(base.proposition("older_version", "IS_CURRENT", "recommendation_source", "NEGATIVE", text))

    # Current guideline state is a separate concept, not a named version coreference.
    if any(x in t for x in ["current guideline has not", "current guideline still", "current guideline recommendation has not", "guideline remains unrevised", "guideline has not yet been revised"]):
        out.append(base.proposition("current_guideline", "IS_CURRENT", "existing_recommendation", "POSITIVE", text))

    return base.dedupe_props(out)


def parse_atomic(text: str, *, candidate: bool = False) -> list[dict]:
    props = v051.parse_atomic(text, candidate=candidate)
    props = normalize_diagnosis_props(props)
    props = repair_temporal_props(text, props)
    return base.dedupe_props(props)


def semantic_match(e: dict, c: dict) -> bool:
    if e["predicate"] != c["predicate"]:
        return False

    pred = c["predicate"]
    if pred == "CONFIRMS_DIAGNOSIS":
        return True
    if pred in {"SUPERSEDES", "IS_CURRENT", "GUIDELINE_RECOMMENDS", "CLASSIFIED_AS", "RECOMMENDS_FOLLOWUP", "HAS_STATUS", "HAS_PRIMARY_ENDPOINT", "ACHIEVES_ENDPOINT", "RISK_RANKING", "DIAGNOSTIC_INFERENCE"}:
        return e["subject"] == c["subject"] and str(e["object"]) == str(c["object"])
    return v050.proposition_identity_match(e, c)


def matching_evidence(evidence: list[dict], cp: dict) -> list[dict]:
    return [e for e in evidence if semantic_match(e, cp)]


def classify_proposition(evidence: list[dict], cp: dict):
    if cp["predicate"] in v050.ACTION_PREDICATES:
        return v050.classify_proposition(evidence, cp)

    # Current guideline recommendation with the same subject but a different option is a direct temporal conflict.
    if cp["predicate"] == "GUIDELINE_RECOMMENDS" and cp["polarity"] == "POSITIVE":
        competing = [
            e for e in evidence
            if e["predicate"] == "GUIDELINE_RECOMMENDS"
            and e["subject"] == cp["subject"]
            and e["polarity"] == "POSITIVE"
        ]
        if any(str(e["object"]) == str(cp["object"]) for e in competing):
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "TEMPORAL", "evidence_matches": competing, "reason": "same current guideline recommendation"}
        if competing:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "TEMPORAL", "evidence_matches": competing, "reason": "current guideline recommends a different option"}

    matches = matching_evidence(evidence, cp)
    same = [e for e in matches if e["polarity"] == cp["polarity"]]
    opposite = [e for e in matches if e["polarity"] != cp["polarity"] and e["polarity"] != "UNKNOWN"]

    if same:
        verdict = "SUPPORTED"
        reason = "matching normalized proposition with same polarity"
    elif opposite:
        if cp["polarity"] == "POSITIVE" and cp["predicate"] in v051.ABSENCE_LIMITATION_PREDICATES:
            verdict = "UNSUPPORTED"
            reason = "source does not establish/provide this positive claim"
        else:
            verdict = "CONTRADICTED"
            reason = "matching normalized proposition with opposite polarity"
    else:
        verdict = "UNSUPPORTED"
        reason = "no matching normalized evidence proposition"

    return {
        "proposition": cp,
        "verdict": verdict,
        "safety_class": v050.safety_class(cp),
        "evidence_matches": matches,
        "reason": reason,
    }


def aggregate(verdicts: list[dict]):
    return v051.aggregate(verdicts)


def verify(evidence_text: str, claim_text: str):
    evidence = parse_atomic(evidence_text, candidate=False)
    candidate = parse_atomic(claim_text, candidate=True)
    verdicts = [classify_proposition(evidence, p) for p in candidate]
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
    print(f"Wrote {len(rows)} S3 v0.5.2 predictions to {out}")


if __name__ == "__main__":
    main()
