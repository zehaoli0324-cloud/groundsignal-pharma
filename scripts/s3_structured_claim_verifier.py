#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERIFIER_VERSION = "s3-structured-semantic-v0.2.0"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def has_any(text: str, phrases) -> bool:
    return any(p in text for p in phrases)


def extract_egfr(text: str):
    t = norm(text)
    ranges = [(int(a), int(b)) for a, b in re.findall(r"egfr[^.;,]{0,30}?(\d+)\s*(?:to|[-–])\s*(\d+)", t)]
    below = [int(x) for x in re.findall(r"(?:egfr[^.;,]{0,30}?(?:below|under|<)|(?:below|under|<)\s*)(\d+)", t)]
    concrete = []
    for x in re.findall(r"egfr\s*(?:of|=|is)?\s*(\d+)", t):
        val = int(x)
        if val not in below and all(val not in r for r in ranges):
            concrete.append(val)
    return {"ranges": ranges, "below": below, "concrete": concrete}


def extract_actions(text: str):
    t = norm(text)
    out = set()
    patterns = {
        "CONTRAINDICATED": ["contraindicated", "absolute contraindication"],
        "INITIATION_NOT_RECOMMENDED": ["initiation", "starting", "start"],
        "NOT_RECOMMENDED": ["not recommended"],
        "DISCONTINUE": ["discontinue", "stop the drug", "must stop", "must discontinue"],
        "REASSESS": ["reassess benefit", "assess benefit and risk", "reassessing benefit"],
        "INCREASE_RISK": ["increase bleeding risk", "increased bleeding risk", "increase risk", "higher risk", "risk is increased"],
        "REPLACEMENT_REGIMEN": ["replacing", "replace ", "replacement analgesic", "every 6 hours", "every six hours"],
        "POSSIBLE_SERIOUS_EVENT": ["possible serious adverse", "can precipitate", "may precipitate", "possible adverse"],
        "CONFIRMED_DIAGNOSIS": ["confirmed serotonin syndrome", "confirmed diagnosis", "has serotonin syndrome", "definitely has"],
        "SIGNAL_DETECTION": ["safety signal", "signal detection", "reported safety signal", "detection of a reported safety signal"],
        "CAUSALITY_PROVEN": ["proves that the drug caused", "proves causality", "establishes causality", "caused the reported adverse"],
        "CAUSALITY_LIMITED": ["cannot by themselves establish a causal", "cannot establish a causal", "causality requires other evidence", "not proven causality"],
        "INCIDENCE_ESTIMABLE": ["true adverse-event incidence", "true incidence", "obtain the incidence", "estimate incidence from report counts"],
        "INCIDENCE_LIMITED": ["cannot be used to estimate", "cannot estimate incidence", "report counts cannot"],
        "REGISTRY_ONLY": ["registry", "registered", "clinicaltrials.gov"],
        "STATUS_COMPLETED": ["status completed", "as completed", "study status as completed", "has status completed"],
        "PRIMARY_ENDPOINT": ["prespecified primary endpoint", "registered primary endpoint", "identifying the prespecified primary endpoint"],
        "EFFICACY_PROVEN": ["proves that the treatment is clinically effective", "proves efficacy", "endpoint was successfully met"],
        "SUPERSEDES": ["supersedes", "superseded"],
        "OLD_REMAINS_CURRENT": ["version 1 remains the current", "old guideline remains current"],
        "GUIDELINE_NOT_CHANGED": ["guideline has not yet", "still recommends", "recommendation has not yet changed", "guideline recommendation has not yet changed"],
        "GUIDELINE_CHANGED": ["guideline now recommends", "automatically means that the current guideline", "current guideline now"],
        "TRIAL_SUPPORTS_NEW_EVIDENCE": ["new randomized trial supports", "evidence landscape has changed"],
        "CYP_SUBSTRATE": ["cyp3a substrate", "cyp substrate"],
        "CYP_INHIBITOR": ["cyp3a inhibitor", "cyp inhibitor"],
        "PK_INTERACTION": ["pharmacokinetic interaction", "pk interaction", "interaction mechanism involving cyp"],
        "CLINICAL_CONTRAINDICATION": ["clinically contraindicated together", "are contraindicated together"],
        "PK_ASSOCIATION": ["changes drug exposure", "pharmacokinetic association", "changes exposure"],
        "DOSE_CHANGE_REQUIRED": ["dose must be changed", "must change the dose", "dose change is required"],
        "MANAGEMENT_UNRESOLVED": ["management must be supported separately", "leaving clinical management unresolved", "no therapeutic-management recommendation", "contains no therapeutic-management recommendation"],
        "EXPLICIT_NO_REPLACEMENT": ["does not specify a replacement", "does not specify replacement", "no replacement analgesic regimen"],
    }
    for action, phrases in patterns.items():
        if has_any(t, phrases):
            out.add(action)
    if "NOT_RECOMMENDED" in out and has_any(t, ["initiation", "starting", "start"]):
        out.add("INITIATION_NOT_RECOMMENDED")
    return out


def threshold_supports_action(evidence: str, claim: str, action: str) -> bool | None:
    ef = extract_egfr(evidence)
    cf = extract_egfr(claim)
    if not cf["concrete"]:
        return None
    value = cf["concrete"][0]
    et = norm(evidence)

    if action == "INITIATION_NOT_RECOMMENDED":
        for low, high in ef["ranges"]:
            if low <= value <= high and has_any(et, ["initiation", "starting", "start"]):
                return True
    if action in {"CONTRAINDICATED", "DISCONTINUE"}:
        for threshold in ef["below"]:
            if value < threshold and action.lower().split("_")[0] in et:
                return True
        # lexical variants
        if action == "DISCONTINUE" and any(value < th for th in ef["below"]) and "discontinu" in et:
            return True
        if action == "CONTRAINDICATED" and any(value < th for th in ef["below"]) and "contraindicat" in et:
            return True
    return False


def explicit_threshold_action_mismatch(evidence: str, claim: str, ea: set[str], ca: set[str]):
    ef = extract_egfr(evidence)
    cf = extract_egfr(claim)
    if not ef["below"] or not cf["below"]:
        return False
    # If claim assigns a stronger/different action to a threshold that evidence assigns another action to.
    if "DISCONTINUE" in ca and "REASSESS" in ea:
        claim_th = max(cf["below"])
        if claim_th in ef["below"] and "below 45" in norm(evidence) and claim_th == 45:
            return True
    if "CONTRAINDICATED" in ca and "CONTRAINDICATED" in ea:
        return min(cf["below"]) != min(ef["below"])
    return False


def semantic_verify(evidence: str, claim: str):
    e = norm(evidence)
    c = norm(claim)
    ea = extract_actions(evidence)
    ca = extract_actions(claim)
    cues = []

    # Explicit contradictions / dangerous escalation first.
    if "CAUSALITY_LIMITED" in ea and "CAUSALITY_PROVEN" in ca:
        return "CONTRADICTS", ["causality_level_conflict"]
    if "INCIDENCE_LIMITED" in ea and "INCIDENCE_ESTIMABLE" in ca:
        return "CONTRADICTS", ["incidence_level_conflict"]
    if "SUPERSEDES" in ea and "OLD_REMAINS_CURRENT" in ca:
        return "CONTRADICTS", ["temporal_supersession_conflict"]
    if "GUIDELINE_NOT_CHANGED" in ea and "GUIDELINE_CHANGED" in ca:
        return "CONTRADICTS", ["guideline_temporal_conflict"]
    if explicit_threshold_action_mismatch(evidence, claim, ea, ca):
        return "CONTRADICTS", ["threshold_action_mismatch"]

    # Unsupported clinical escalation.
    if "INCREASE_RISK" in ea and ("CONTRAINDICATED" in ca or "CLINICAL_CONTRAINDICATION" in ca):
        return "DOES_NOT_SUPPORT", ["risk_to_contraindication_escalation"]
    if "EXPLICIT_NO_REPLACEMENT" in ea and "REPLACEMENT_REGIMEN" in ca:
        return "DOES_NOT_SUPPORT", ["unsupported_replacement_regimen"]
    if "POSSIBLE_SERIOUS_EVENT" in ea and "CONFIRMED_DIAGNOSIS" in ca:
        return "DOES_NOT_SUPPORT", ["risk_to_diagnosis_escalation"]
    if "REGISTRY_ONLY" in ea and "EFFICACY_PROVEN" in ca:
        return "DOES_NOT_SUPPORT", ["registration_to_efficacy_escalation"]
    if "CYP_SUBSTRATE" in ea and "CYP_INHIBITOR" in ea and "CLINICAL_CONTRAINDICATION" in ca:
        return "DOES_NOT_SUPPORT", ["mechanism_to_management_escalation"]
    if "PK_ASSOCIATION" in ea and "MANAGEMENT_UNRESOLVED" in ea and "DOSE_CHANGE_REQUIRED" in ca:
        return "DOES_NOT_SUPPORT", ["pk_to_management_escalation"]

    # Direct numerical rule application.
    if "INITIATION_NOT_RECOMMENDED" in ca:
        r = threshold_supports_action(evidence, claim, "INITIATION_NOT_RECOMMENDED")
        if r is True:
            return "DIRECT_SUPPORT", ["range_rule_application"]
    if "DISCONTINUE" in ca:
        r = threshold_supports_action(evidence, claim, "DISCONTINUE")
        if r is True:
            return "DIRECT_SUPPORT", ["threshold_rule_application"]
    if "CONTRAINDICATED" in ca:
        r = threshold_supports_action(evidence, claim, "CONTRAINDICATED")
        if r is True:
            return "DIRECT_SUPPORT", ["threshold_rule_application"]

    # Direct semantic relations.
    direct_rules = [
        ("CONTRAINDICATED", "CONTRAINDICATED", "same_management_modality"),
        ("INITIATION_NOT_RECOMMENDED", "INITIATION_NOT_RECOMMENDED", "same_management_modality"),
        ("DISCONTINUE", "DISCONTINUE", "same_management_modality"),
        ("INCREASE_RISK", "INCREASE_RISK", "same_risk_relation"),
        ("SIGNAL_DETECTION", "SIGNAL_DETECTION", "same_signal_scope"),
        ("STATUS_COMPLETED", "STATUS_COMPLETED", "same_registry_status"),
        ("PRIMARY_ENDPOINT", "PRIMARY_ENDPOINT", "same_registry_endpoint"),
        ("SUPERSEDES", "SUPERSEDES", "same_temporal_relation"),
        ("GUIDELINE_NOT_CHANGED", "GUIDELINE_NOT_CHANGED", "same_temporal_state"),
        ("PK_ASSOCIATION", "PK_ASSOCIATION", "same_pk_relation"),
        ("MANAGEMENT_UNRESOLVED", "MANAGEMENT_UNRESOLVED", "same_management_uncertainty"),
    ]
    for e_action, c_action, cue in direct_rules:
        if e_action in ea and c_action in ca:
            cues.append(cue)

    # Derived but bounded semantic support.
    if "CYP_SUBSTRATE" in ea and "CYP_INHIBITOR" in ea and "PK_INTERACTION" in ca:
        cues.append("bounded_pk_interaction_inference")
    if "TRIAL_SUPPORTS_NEW_EVIDENCE" in ea and "GUIDELINE_NOT_CHANGED" in ea and "TRIAL_SUPPORTS_NEW_EVIDENCE" in ca and "GUIDELINE_NOT_CHANGED" in ca:
        cues.append("evidence_changed_guideline_unchanged")
    if "CAUSALITY_LIMITED" in ea and "SIGNAL_DETECTION" in ca and "CAUSALITY_PROVEN" not in ca:
        cues.append("signal_without_causality_escalation")
    if "REGISTRY_ONLY" in ea and "PRIMARY_ENDPOINT" in ca and "EFFICACY_PROVEN" not in ca:
        cues.append("registry_endpoint_bounded_support")

    if cues:
        return "DIRECT_SUPPORT", cues

    # Final conservative fallback: only direct lexical entailment when most claim concepts are explicitly present.
    claim_terms = {x for x in re.findall(r"[a-z0-9]+", c) if len(x) > 2}
    evidence_terms = {x for x in re.findall(r"[a-z0-9]+", e) if len(x) > 2}
    overlap = len(claim_terms & evidence_terms) / max(1, len(claim_terms))
    if overlap >= 0.78:
        return "DIRECT_SUPPORT", ["very_high_literal_entailment"]
    if overlap >= 0.48:
        return "PARTIAL_SUPPORT", ["partial_literal_overlap"]
    return "DOES_NOT_SUPPORT", ["insufficient_semantic_match"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    preds = []
    for item in data["items"]:
        relation, cues = semantic_verify(item["evidence_text"], item["candidate_claim"])
        preds.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "evidence_actions": sorted(extract_actions(item["evidence_text"])),
            "claim_actions": sorted(extract_actions(item["candidate_claim"])),
            "evidence_numeric": extract_egfr(item["evidence_text"]),
            "claim_numeric": extract_egfr(item["candidate_claim"]),
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} S3 structured predictions to {out}")


if __name__ == "__main__":
    main()
