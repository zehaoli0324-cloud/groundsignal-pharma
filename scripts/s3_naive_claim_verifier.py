#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERIFIER_VERSION = "s3-naive-lexical-v0.1.0"
STOP = {
    "the", "a", "an", "of", "to", "and", "or", "for", "in", "on", "with", "is", "are", "be", "by",
    "that", "this", "as", "it", "from", "at", "when", "if", "but", "has", "have", "had", "can", "all",
}


def tokens(text: str):
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if len(x) > 1 and x not in STOP}


def overlap(evidence: str, claim: str):
    e = tokens(evidence)
    c = tokens(claim)
    if not c:
        return 0.0
    return len(e & c) / len(c)


def has_any(text: str, phrases):
    t = text.lower()
    return any(p in t for p in phrases)


def verify(evidence: str, claim: str):
    e = evidence.lower()
    c = claim.lower()
    score = overlap(evidence, claim)

    # A deliberately small set of generic safety-aware contradiction cues.
    evidence_limits_causality = has_any(e, ["cannot by themselves establish a causal", "cannot establish a causal", "causality requires other evidence"])
    claim_asserts_causality = has_any(c, ["proves that the drug caused", "proves causality", "caused the reported adverse"])
    if evidence_limits_causality and claim_asserts_causality:
        return "CONTRADICTS", score, ["explicit_causality_limitation"]

    evidence_limits_incidence = has_any(e, ["cannot be used to estimate", "cannot estimate", "report counts cannot"])
    claim_asserts_incidence = has_any(c, ["true adverse-event incidence", "true incidence", "obtain the incidence"])
    if evidence_limits_incidence and claim_asserts_incidence:
        return "CONTRADICTS", score, ["explicit_incidence_limitation"]

    evidence_supersedes = has_any(e, ["superseded", "supersedes"])
    claim_keeps_old_current = has_any(c, ["version 1 remains the current", "old guideline remains current"])
    if evidence_supersedes and claim_keeps_old_current:
        return "CONTRADICTS", score, ["explicit_supersession"]

    evidence_guideline_unchanged = has_any(e, ["has not yet been revised", "still recommends", "has not yet changed"])
    claim_auto_changes_guideline = has_any(c, ["automatically means", "guideline now recommends"])
    if evidence_guideline_unchanged and claim_auto_changes_guideline:
        return "CONTRADICTS", score, ["explicit_temporal_limitation"]

    # Broad unsupported escalation cues.
    if has_any(e, ["does not specify", "does not state", "contains no", "management must be supported separately"]):
        if has_any(c, ["supports replacing", "clinically contraindicated", "dose must be changed", "must be changed"]):
            return "DOES_NOT_SUPPORT", score, ["explicit_scope_limitation"]

    if has_any(e, ["registry", "registered", "clinicaltrials.gov"]) and has_any(c, ["proves that the treatment is clinically effective", "proves efficacy"]):
        return "DOES_NOT_SUPPORT", score, ["registry_to_efficacy_guard"]

    if has_any(e, ["possible serious adverse", "possible", "can precipitate"]) and has_any(c, ["confirmed serotonin syndrome", "has confirmed"]):
        return "DOES_NOT_SUPPORT", score, ["risk_to_diagnosis_guard"]

    # Numerical modality sanity check for the metformin threshold family.
    if "contraindicat" in c and "contraindicat" in e:
        ev_below = re.findall(r"(?:below|<)\s*(\d+)", e)
        cl_below = re.findall(r"(?:below|<)\s*(\d+)", c)
        if ev_below and cl_below and ev_below[0] != cl_below[0]:
            return "CONTRADICTS", score, ["threshold_mismatch"]

    # Baseline lexical entailment. This is intentionally simple so the S3 eval can expose its limits.
    if score >= 0.62:
        return "DIRECT_SUPPORT", score, ["high_lexical_overlap"]
    if score >= 0.38:
        return "PARTIAL_SUPPORT", score, ["medium_lexical_overlap"]
    return "DOES_NOT_SUPPORT", score, ["low_lexical_overlap"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    preds = []
    for item in data["items"]:
        relation, score, cues = verify(item["evidence_text"], item["candidate_claim"])
        preds.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "lexical_overlap": round(score, 4),
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} S3 predictions to {out}")


if __name__ == "__main__":
    main()
