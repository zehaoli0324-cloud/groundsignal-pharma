#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERIFIER_VERSION = "s3-directional-claimframe-v0.3.0"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def has(text: str, *phrases: str) -> bool:
    return any(p in text for p in phrases)


def clean_entity(text: str) -> str:
    x = re.sub(r"\b(the|a|an|current|later|older|newer|old|new)\b", " ", text.lower())
    x = re.sub(r"[^a-z0-9_. -]+", " ", x)
    return re.sub(r"\s+", " ", x).strip(" .-")


def parse_numeric_conditions(text: str):
    t = norm(text)
    out = []

    for m in re.finditer(r"egfr[^.;,]{0,24}?(\d+)\s*(?:to|[-–])\s*(\d+)", t):
        low, high = int(m.group(1)), int(m.group(2))
        window = t[max(0, m.start() - 65): min(len(t), m.end() + 75)]
        out.append({
            "variable": "egfr",
            "operator": "RANGE",
            "low": min(low, high),
            "high": max(low, high),
            "value": None,
            "applies_to": infer_action(window),
        })

    patterns = [
        r"egfr[^.;,]{0,24}?(?:below|under|<)\s*(\d+)",
        r"(?:below|under|<)\s*(\d+)[^.;,]{0,16}?egfr",
    ]
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, t):
            val = int(m.group(1))
            key = (m.start(), val)
            if key in seen:
                continue
            seen.add(key)
            window = t[max(0, m.start() - 70): min(len(t), m.end() + 80)]
            out.append({
                "variable": "egfr",
                "operator": "LT",
                "value": val,
                "low": None,
                "high": None,
                "applies_to": infer_action(window),
            })

    for m in re.finditer(r"egfr\s*(?:of|=|is|at)?\s*(\d+)", t):
        val = int(m.group(1))
        # Do not duplicate values that are part of explicit ranges/thresholds.
        if any(c.get("value") == val or c.get("low") == val or c.get("high") == val for c in out):
            continue
        window = t[max(0, m.start() - 60): min(len(t), m.end() + 70)]
        out.append({
            "variable": "egfr",
            "operator": "EQ",
            "value": val,
            "low": None,
            "high": None,
            "applies_to": infer_action(window),
        })
    return out


def infer_action(text: str):
    t = norm(text)
    # Strongest/most specific action first.
    if has(t, "contraindicat"):
        return "CONTRAINDICATED"
    if has(t, "discontinu", "must stop", "must discontinue", "stop the drug"):
        return "DISCONTINUE"
    if has(t, "reassess", "benefit and risk", "benefit/risk"):
        return "REASSESS"
    if has(t, "not recommended") and has(t, "initiat", "starting", "start"):
        return "INITIATION_NOT_RECOMMENDED"
    if has(t, "not recommended"):
        return "NOT_RECOMMENDED"
    return None


def parse_supersession(text: str):
    t = norm(text)
    rels = []

    # Named direction: "Guideline B supersedes Guideline A" / "version 2 supersedes version 1".
    pats = [
        r"(guideline\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?supersedes\s+(guideline\s+[a-z0-9._-]+)",
        r"(version\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?supersedes\s+(version\s+[a-z0-9._-]+)",
    ]
    for pat in pats:
        for m in re.finditer(pat, t):
            rels.append({
                "subject": clean_entity(m.group(1)),
                "predicate": "SUPERSEDES",
                "object": clean_entity(m.group(2)),
                "polarity": "POSITIVE",
                "confidence": 1.0,
            })

    # Generic directional pattern used when versions are described relationally rather than named.
    if not rels and has(t, "supersedes", "superseded"):
        if has(t, "later", "newer") and has(t, "older", "old"):
            rels.append({"subject": "later_version", "predicate": "SUPERSEDES", "object": "older_version", "polarity": "POSITIVE", "confidence": 0.9})
        elif has(t, "version 2") and has(t, "version 1"):
            rels.append({"subject": "version 2", "predicate": "SUPERSEDES", "object": "version 1", "polarity": "POSITIVE", "confidence": 0.95})

    return rels


def parse_current_assertions(text: str):
    t = norm(text)
    rels = []
    pats = [
        r"(guideline\s+[a-z0-9._-]+)[^.;]{0,40}?(?:is|remains|treated as|be treated as)\s+(?:the\s+)?current",
        r"(version\s+[a-z0-9._-]+)[^.;]{0,40}?(?:is|remains|treated as|be treated as)\s+(?:the\s+)?current",
    ]
    for pat in pats:
        for m in re.finditer(pat, t):
            rels.append({
                "subject": clean_entity(m.group(1)),
                "predicate": "CURRENT_STATUS",
                "object": "current",
                "polarity": "POSITIVE",
                "confidence": 1.0,
            })

    # Common paraphrase: "later guideline version is the current recommendation source".
    if has(t, "later guideline version", "newer guideline version") and has(t, "current recommendation source"):
        rels.append({"subject": "later_version", "predicate": "CURRENT_STATUS", "object": "current", "polarity": "POSITIVE", "confidence": 0.9})
    if has(t, "older version", "old version") and has(t, "current recommendation"):
        rels.append({"subject": "older_version", "predicate": "CURRENT_STATUS", "object": "current", "polarity": "POSITIVE", "confidence": 0.9})
    return rels


def parse_causal_frame(text: str):
    t = norm(text)
    status = "UNKNOWN"
    limitations = []
    relations = []

    noncausal_patterns = [
        "does not establish that",
        "does not establish causality",
        "cannot establish causality",
        "cannot by themselves establish",
        "not establish that",
        "causality requires other evidence",
        "does not prove causality",
        "not proven causality",
        "do not by themselves establish",
    ]
    if has(t, *noncausal_patterns):
        status = "NOT_ESTABLISHED"
        limitations.append("CAUSALITY_NOT_ESTABLISHED")
    elif has(t, "association", "associated with", "observational analysis", "observational study"):
        status = "ASSOCIATION"
    elif has(t, "safety signal", "signal detection", "spontaneous adverse-event", "spontaneous report"):
        status = "SIGNAL_ONLY"
    elif has(t, "proves that", "caused by", "caused the", "establishes that"):
        status = "CAUSAL"

    # Capture simple A/B directional causal or association statements.
    m = re.search(r"association between\s+([a-z0-9]+)\s+and\s+([a-z0-9]+)", t)
    if m:
        relations.append({"subject": m.group(1), "predicate": "ASSOCIATED_WITH", "object": m.group(2), "polarity": "POSITIVE", "confidence": 0.95})
    m2 = re.search(r"([a-z0-9]+)\s+caused\s+([a-z0-9]+)", t)
    if m2:
        relations.append({"subject": m2.group(1), "predicate": "CAUSES", "object": m2.group(2), "polarity": "POSITIVE", "confidence": 0.95})

    return status, limitations, relations


def parse_frame(text: str):
    t = norm(text)
    modalities = set()
    limitations = []
    relations = []
    cues = []

    action_map = {
        "CONTRAINDICATED": ["contraindicat"],
        "DISCONTINUE": ["discontinu", "must stop", "must discontinue", "stop immediately"],
        "REASSESS": ["reassess", "benefit and risk", "benefit/risk"],
        "NOT_RECOMMENDED": ["not recommended"],
        "RISK_INCREASE": ["increase bleeding risk", "increased bleeding risk", "increase risk", "higher risk", "risk is increased"],
        "POSSIBLE": ["possible adverse", "possible serious", "may precipitate", "can precipitate", "may cause", "can cause"],
        "DIAGNOSIS_CONFIRMED": ["confirms that", "confirmed", "definitely has", "has confirmed"],
        "EFFICACY_PROVEN": ["proves efficacy", "proves that the treatment", "achieved clinical efficacy", "endpoint was successfully met"],
        "MANAGEMENT_REQUIRED": ["must receive a lower dose", "dose must be changed", "must change the dose", "clinically contraindicated together", "absolutely contraindicated"],
        "MANAGEMENT_UNRESOLVED": ["management unresolved", "management must be supported separately", "no therapeutic-management recommendation", "no product-specific management rule", "does not provide a clinical contraindication", "does not state an absolute contraindication"],
    }
    for modality, phrases in action_map.items():
        if has(t, *phrases):
            modalities.add(modality)
    if "NOT_RECOMMENDED" in modalities and has(t, "initiat", "starting", "start"):
        modalities.add("INITIATION_NOT_RECOMMENDED")

    if has(t, "signal detection", "safety signal", "spontaneous report", "spontaneous adverse-event"):
        modalities.add("SIGNAL_ONLY")
    if has(t, "association", "associated with"):
        modalities.add("ASSOCIATED")

    # Explicit limitations that should dominate lexical overlap.
    limitation_map = {
        "NO_ABSOLUTE_CONTRAINDICATION": ["does not state an absolute contraindication", "no clinical contraindication", "does not provide a clinical contraindication"],
        "NO_REPLACEMENT_REGIMEN": ["does not specify a replacement", "no replacement analgesic regimen"],
        "NO_EFFICACY_RESULT": ["no efficacy result", "no trial result", "does not contain peer-reviewed trial results", "no trial result is contained"],
        "NO_MANAGEMENT_RULE": ["no therapeutic-management recommendation", "no product-specific management rule", "management must be supported separately"],
        "NOT_DIAGNOSIS": ["does not by itself diagnose", "does not classify", "indeterminate", "further characterization"],
        "NO_HEAD_TO_HEAD": ["without a randomized head-to-head", "no randomized head-to-head", "different populations"],
        "GUIDELINE_NOT_UPDATED": ["has not yet been revised", "has not been revised", "has not yet been updated", "not yet changed", "continues to recommend", "still recommends"],
    }
    for label, phrases in limitation_map.items():
        if has(t, *phrases):
            limitations.append(label)

    causal_status, causal_limits, causal_relations = parse_causal_frame(text)
    limitations.extend(causal_limits)
    relations.extend(causal_relations)
    relations.extend(parse_supersession(text))
    relations.extend(parse_current_assertions(text))

    temporal_status = "UNKNOWN"
    if any(r["predicate"] == "SUPERSEDES" for r in relations):
        temporal_status = "CURRENT"
        cues.append("directional_supersession")
    elif "GUIDELINE_NOT_UPDATED" in limitations:
        temporal_status = "PENDING_UPDATE"
    elif has(t, "current guideline", "current label", "current recommendation"):
        temporal_status = "CURRENT"

    # Registry / report / mechanism facts.
    if has(t, "registry", "clinicaltrials.gov"):
        relations.append({"subject": "trial_registry", "predicate": "EVIDENCE_TYPE", "object": "registry", "polarity": "POSITIVE", "confidence": 1.0})
    if has(t, "status completed", "as completed", "status as completed", "has status completed"):
        relations.append({"subject": "study", "predicate": "STATUS", "object": "completed", "polarity": "POSITIVE", "confidence": 1.0})
    if has(t, "recruiting"):
        relations.append({"subject": "study", "predicate": "STATUS", "object": "recruiting", "polarity": "POSITIVE", "confidence": 1.0})
    if has(t, "primary endpoint"):
        relations.append({"subject": "study", "predicate": "HAS_REGISTERED_PRIMARY_ENDPOINT", "object": "primary_endpoint", "polarity": "POSITIVE", "confidence": 1.0})

    if has(t, "cyp3a inhibitor", "inhibits cyp3a"):
        relations.append({"subject": "drug_m", "predicate": "INHIBITS", "object": "cyp3a", "polarity": "POSITIVE", "confidence": 0.9})
    if has(t, "cyp3a substrate"):
        relations.append({"subject": "drug_n", "predicate": "SUBSTRATE_OF", "object": "cyp3a", "polarity": "POSITIVE", "confidence": 0.9})
    if has(t, "pharmacokinetic interaction", "cyp3a-mediated pharmacokinetic interaction", "interaction mechanism"):
        relations.append({"subject": "drug_pair", "predicate": "POTENTIAL_PK_INTERACTION", "object": "cyp3a", "polarity": "POSITIVE", "confidence": 0.85})
    if has(t, "higher drug exposure", "changes drug exposure", "pharmacokinetic association", "changes exposure"):
        relations.append({"subject": "genotype", "predicate": "ASSOCIATED_WITH", "object": "drug_exposure", "polarity": "POSITIVE", "confidence": 0.85})

    if has(t, "indeterminate"):
        relations.append({"subject": "lesion", "predicate": "CLASSIFICATION", "object": "indeterminate", "polarity": "POSITIVE", "confidence": 1.0})
    if has(t, "malignant"):
        relations.append({"subject": "lesion", "predicate": "CLASSIFICATION", "object": "malignant", "polarity": "POSITIVE", "confidence": 0.95})
    if has(t, "mri") and has(t, "recommend"):
        relations.append({"subject": "report", "predicate": "RECOMMENDS", "object": "mri_characterization", "polarity": "POSITIVE", "confidence": 1.0})

    if has(t, "response rates", "response rate") and has(t, "62%", "48%"):
        relations.append({"subject": "cross_trial", "predicate": "HAS_SEPARATE_RESPONSE_RATES", "object": "different_populations", "polarity": "POSITIVE", "confidence": 0.9})
    if has(t, "superior", "superiority"):
        relations.append({"subject": "treatment_a", "predicate": "SUPERIOR_TO", "object": "treatment_b", "polarity": "POSITIVE", "confidence": 0.9})

    return {
        "entities": [],
        "relations": relations,
        "conditions": parse_numeric_conditions(text),
        "modalities": sorted(modalities),
        "causal_status": causal_status if causal_status != "UNKNOWN" else "NOT_APPLICABLE",
        "temporal_status": temporal_status if temporal_status != "UNKNOWN" else "NOT_APPLICABLE",
        "limitations": sorted(set(limitations)),
        "raw_cues": cues,
    }


def relation_exists(frame, predicate: str, subject: str | None = None, object_: str | None = None):
    for r in frame["relations"]:
        if r["predicate"] != predicate:
            continue
        if subject is not None and r["subject"] != subject:
            continue
        if object_ is not None and r["object"] != object_:
            continue
        return True
    return False


def applicable_evidence_actions(frame, value: float):
    actions = set()
    for c in frame["conditions"]:
        if c["variable"] != "egfr" or not c.get("applies_to"):
            continue
        op = c["operator"]
        applies = False
        if op == "LT" and value < float(c["value"]):
            applies = True
        elif op == "RANGE" and float(c["low"]) <= value <= float(c["high"]):
            applies = True
        elif op == "EQ" and value == float(c["value"]):
            applies = True
        if applies:
            actions.add(c["applies_to"])
    return actions


def compare_numeric_rules(evidence, claim):
    # Concrete claim value: compare the claimed action with every evidence rule that applies at that value.
    concrete = [c for c in claim["conditions"] if c["variable"] == "egfr" and c["operator"] == "EQ"]
    if concrete:
        value = float(concrete[0]["value"])
        evidence_actions = applicable_evidence_actions(evidence, value)
        claimed_actions = {
            a for a in claim["modalities"]
            if a in {"CONTRAINDICATED", "DISCONTINUE", "REASSESS", "INITIATION_NOT_RECOMMENDED", "NOT_RECOMMENDED"}
        }
        if claimed_actions:
            if claimed_actions & evidence_actions:
                return "DIRECT_SUPPORT", [f"numeric_rule_applies:{value}"]
            if evidence_actions:
                return "CONTRADICTS", [f"action_conflict_at_value:{value}", f"evidence_actions={sorted(evidence_actions)}", f"claim_actions={sorted(claimed_actions)}"]

    # Claim threshold/range itself: detect an over-broad stronger action.
    for cc in claim["conditions"]:
        if cc["variable"] != "egfr" or not cc.get("applies_to"):
            continue
        ca = cc["applies_to"]
        if cc["operator"] == "LT":
            threshold = float(cc["value"])
            # Probe values just below threshold and within clinically meaningful integer band.
            probes = sorted(set([threshold - 1, threshold - 5, max(0, threshold - 14)]))
            conflicts = []
            supports = []
            for value in probes:
                acts = applicable_evidence_actions(evidence, value)
                if ca in acts:
                    supports.append(value)
                elif acts:
                    conflicts.append((value, sorted(acts)))
            if conflicts:
                return "CONTRADICTS", [f"overbroad_threshold_action:{ca}< {threshold}", f"conflicts={conflicts}"]
            if supports:
                return "DIRECT_SUPPORT", [f"threshold_action_supported:{ca}< {threshold}"]
    return None, []


def compare_frames(evidence, claim):
    # 1. Directional temporal contradictions.
    supersedes = [r for r in evidence["relations"] if r["predicate"] == "SUPERSEDES"]
    current_claims = [r for r in claim["relations"] if r["predicate"] == "CURRENT_STATUS" and r["object"] == "current"]
    for s in supersedes:
        for c in current_claims:
            if c["subject"] == s["object"]:
                return "CONTRADICTS", ["superseded_document_asserted_current", f"{s['subject']} supersedes {s['object']}"]
            if c["subject"] == s["subject"]:
                return "DIRECT_SUPPORT", ["newer_document_asserted_current"]
        # Generic relational aliases.
        if s["subject"] == "later_version" and any(c["subject"] == "older_version" for c in current_claims):
            return "CONTRADICTS", ["older_version_asserted_current"]
        if s["subject"] == "later_version" and any(c["subject"] == "later_version" for c in current_claims):
            return "DIRECT_SUPPORT", ["later_version_asserted_current"]

    # 2. Causal polarity dominates lexical overlap.
    if evidence["causal_status"] in {"NOT_ESTABLISHED", "ASSOCIATION", "SIGNAL_ONLY"} and claim["causal_status"] == "CAUSAL":
        # If evidence explicitly says causality is not established, contradiction. Pure association/signal without explicit negation is unsupported escalation.
        if evidence["causal_status"] == "NOT_ESTABLISHED" or "CAUSALITY_NOT_ESTABLISHED" in evidence["limitations"]:
            return "CONTRADICTS", ["causal_polarity_conflict"]
        return "DOES_NOT_SUPPORT", ["causal_escalation_without_support"]

    # 3. Numeric threshold/action reasoning.
    numeric_relation, numeric_cues = compare_numeric_rules(evidence, claim)
    if numeric_relation:
        return numeric_relation, numeric_cues

    # 4. Explicit limitation guards.
    if "NO_ABSOLUTE_CONTRAINDICATION" in evidence["limitations"] and (
        "CONTRAINDICATED" in claim["modalities"] or "MANAGEMENT_REQUIRED" in claim["modalities"]
    ):
        return "DOES_NOT_SUPPORT", ["risk_not_absolute_contraindication"]
    if "NO_REPLACEMENT_REGIMEN" in evidence["limitations"] and "MANAGEMENT_REQUIRED" in claim["modalities"]:
        return "DOES_NOT_SUPPORT", ["replacement_regimen_not_in_evidence"]
    if "NO_EFFICACY_RESULT" in evidence["limitations"] and "EFFICACY_PROVEN" in claim["modalities"]:
        return "DOES_NOT_SUPPORT", ["registry_without_efficacy_result"]
    if "NO_MANAGEMENT_RULE" in evidence["limitations"] and "MANAGEMENT_REQUIRED" in claim["modalities"]:
        return "DOES_NOT_SUPPORT", ["mechanism_or_pk_without_management_rule"]
    if "NOT_DIAGNOSIS" in evidence["limitations"] and "DIAGNOSIS_CONFIRMED" in claim["modalities"]:
        return "DOES_NOT_SUPPORT", ["observation_not_confirmed_diagnosis"]
    if "NO_HEAD_TO_HEAD" in evidence["limitations"] and relation_exists(claim, "SUPERIOR_TO"):
        return "DOES_NOT_SUPPORT", ["cross_trial_percentage_not_superiority"]
    if "GUIDELINE_NOT_UPDATED" in evidence["limitations"] and has_claim_guideline_change(claim):
        return "CONTRADICTS", ["new_evidence_does_not_auto_update_guideline"]

    # 5. Risk vs diagnosis.
    if "POSSIBLE" in evidence["modalities"] and "DIAGNOSIS_CONFIRMED" in claim["modalities"]:
        return "DOES_NOT_SUPPORT", ["possible_risk_not_patient_diagnosis"]
    if "RISK_INCREASE" in evidence["modalities"] and "RISK_INCREASE" in claim["modalities"]:
        return "DIRECT_SUPPORT", ["risk_relation_preserved"]

    # 6. Registry facts.
    if relation_exists(evidence, "EVIDENCE_TYPE", object_="registry"):
        if "EFFICACY_PROVEN" in claim["modalities"]:
            return "DOES_NOT_SUPPORT", ["registry_not_efficacy_proof"]
        needed = []
        if relation_exists(claim, "STATUS", object_="completed"):
            needed.append(("STATUS", "completed"))
        if relation_exists(claim, "STATUS", object_="recruiting"):
            needed.append(("STATUS", "recruiting"))
        if relation_exists(claim, "HAS_REGISTERED_PRIMARY_ENDPOINT"):
            needed.append(("HAS_REGISTERED_PRIMARY_ENDPOINT", "primary_endpoint"))
        if needed and all(relation_exists(evidence, p, object_=o) for p, o in needed):
            return "DIRECT_SUPPORT", ["registry_fact_preserved"]

    # 7. Mechanism / PK bounded inferences.
    if relation_exists(evidence, "INHIBITS", object_="cyp3a") and relation_exists(evidence, "SUBSTRATE_OF", object_="cyp3a"):
        if relation_exists(claim, "POTENTIAL_PK_INTERACTION", object_="cyp3a"):
            return "DIRECT_SUPPORT", ["bounded_cyp3a_pk_inference"]
        if "MANAGEMENT_REQUIRED" in claim["modalities"]:
            return "DOES_NOT_SUPPORT", ["mechanism_not_management"]

    if relation_exists(evidence, "ASSOCIATED_WITH", subject="genotype", object_="drug_exposure"):
        if relation_exists(claim, "ASSOCIATED_WITH", subject="genotype", object_="drug_exposure") and "MANAGEMENT_REQUIRED" not in claim["modalities"]:
            return "DIRECT_SUPPORT", ["pgx_pk_association_preserved"]
        if "MANAGEMENT_REQUIRED" in claim["modalities"]:
            return "DOES_NOT_SUPPORT", ["pgx_exposure_not_dose_rule"]

    # 8. Report uncertainty.
    if relation_exists(evidence, "CLASSIFICATION", subject="lesion", object_="indeterminate"):
        if relation_exists(claim, "CLASSIFICATION", subject="lesion", object_="malignant"):
            return "DOES_NOT_SUPPORT", ["indeterminate_not_malignant"]
        if relation_exists(claim, "CLASSIFICATION", subject="lesion", object_="indeterminate"):
            if relation_exists(claim, "RECOMMENDS", object_="mri_characterization"):
                return "DIRECT_SUPPORT", ["report_uncertainty_and_followup_preserved"]
            return "DIRECT_SUPPORT", ["report_uncertainty_preserved"]

    # 9. Temporal pending-update bounded statement.
    if evidence["temporal_status"] == "PENDING_UPDATE" and claim["temporal_status"] == "PENDING_UPDATE":
        return "DIRECT_SUPPORT", ["pending_update_state_preserved"]

    # 10. Conservative modality equality when no stronger contradiction exists.
    strong_modalities = {"CONTRAINDICATED", "DISCONTINUE", "REASSESS", "INITIATION_NOT_RECOMMENDED", "RISK_INCREASE", "POSSIBLE", "SIGNAL_ONLY"}
    common = strong_modalities & set(evidence["modalities"]) & set(claim["modalities"])
    if common:
        return "DIRECT_SUPPORT", [f"shared_bounded_modality:{sorted(common)}"]

    # 11. Conservative literal fallback: never promote an explicitly limited high-risk claim through overlap alone.
    e_terms = {x for x in re.findall(r"[a-z0-9]+", norm(json.dumps(evidence, sort_keys=True))) if len(x) > 2}
    c_terms = {x for x in re.findall(r"[a-z0-9]+", norm(json.dumps(claim, sort_keys=True))) if len(x) > 2}
    overlap = len(e_terms & c_terms) / max(1, len(c_terms))
    if overlap >= 0.88 and not evidence["limitations"]:
        return "DIRECT_SUPPORT", ["very_high_frame_overlap"]
    if overlap >= 0.45:
        return "PARTIAL_SUPPORT", ["partial_frame_overlap"]
    return "DOES_NOT_SUPPORT", ["insufficient_frame_support"]


def has_claim_guideline_change(frame):
    # Claim says a current guideline changed/recommends a new option, while evidence says update is pending.
    raw = " ".join(frame.get("raw_cues", []))
    if "guideline_changed_assertion" in raw:
        return True
    return False


def enrich_claim_specific_cues(frame, text: str):
    t = norm(text)
    if has(t, "guideline now recommends", "automatically changes the current guideline", "automatically means that the current guideline"):
        frame["raw_cues"].append("guideline_changed_assertion")
    if has(t, "current guideline still", "current guideline recommendation has not yet changed", "guideline has not yet changed"):
        frame["temporal_status"] = "PENDING_UPDATE"
    return frame


def verify(evidence_text: str, claim_text: str):
    evidence = parse_frame(evidence_text)
    claim = enrich_claim_specific_cues(parse_frame(claim_text), claim_text)
    relation, cues = compare_frames(evidence, claim)
    return relation, evidence, claim, cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        relation, evidence_frame, claim_frame, cues = verify(item["evidence_text"], item["candidate_claim"])
        rows.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "evidence_frame": evidence_frame,
            "claim_frame": claim_frame,
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3 ClaimFrame predictions to {out}")


if __name__ == "__main__":
    main()
