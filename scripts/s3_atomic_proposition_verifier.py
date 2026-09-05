#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERIFIER_VERSION = "s3-atomic-proposition-v0.4.0"

ACTION_PREDICATES = {
    "INITIATION_NOT_RECOMMENDED",
    "CONTRAINDICATED",
    "REASSESS_BENEFIT_RISK",
    "DISCONTINUE",
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def has(text: str, *phrases: str) -> bool:
    return any(p in text for p in phrases)


def clean_entity(text: str) -> str:
    x = re.sub(r"\b(the|a|an|current|later|older|newer|old|new)\b", " ", text.lower())
    x = re.sub(r"[^a-z0-9_. -]+", " ", x)
    return re.sub(r"\s+", " ", x).strip(" .-")


def infer_population(text: str) -> str | None:
    t = norm(text)
    if has(t, "already receiving", "already taking", "already on therapy", "existing user", "existing therapy", "patients already on", "person is already"):
        return "existing_user"
    if has(t, "new patient", "new treatment", "initiation", "starting", "start the drug", "starting the drug"):
        return "new_or_initiating_user"
    return None


def split_clauses(text: str) -> list[str]:
    """Clause split without generic 'and' splitting, so phrases like 'benefit and risk' stay intact."""
    t = re.sub(r"\s+", " ", text.strip())
    # Strong discourse boundaries first.
    t = re.sub(r"\s*;\s*", " || ", t)
    t = re.sub(r"\.(?=\s|$)", " || ", t)
    t = re.sub(r",\s*(whereas|while|but)\s+", " || ", t, flags=re.I)
    t = re.sub(r"\s+(whereas|while|but)\s+", " || ", t, flags=re.I)
    # Split coordinated clauses when the second side clearly starts a new proposition.
    t = re.sub(
        r",?\s+and\s+(?=(?:the|this|that|no|causal|discontinuation|initiation|use|guideline|drug|a spontaneous|an observational|the authors|the passage|the source|the registry))",
        " || ",
        t,
        flags=re.I,
    )
    return [c.strip(" ,") for c in t.split("||") if c.strip(" ,")]


def conditions_from_clause(clause: str) -> list[dict]:
    t = norm(clause)
    out: list[dict] = []
    for m in re.finditer(r"egfr[^.;,]{0,22}?(\d+)\s*(?:to|through|[-–])\s*(\d+)", t):
        a, b = int(m.group(1)), int(m.group(2))
        out.append({"variable": "egfr", "operator": "RANGE", "value": None, "low": min(a, b), "high": max(a, b), "unit": None})
    for pat in [r"egfr[^.;,]{0,20}?(?:below|under|<)\s*(\d+)", r"(?:below|under|<)\s*egfr\s*(\d+)"]:
        for m in re.finditer(pat, t):
            val = int(m.group(1))
            if not any(x.get("value") == val and x["operator"] == "LT" for x in out):
                out.append({"variable": "egfr", "operator": "LT", "value": val, "low": None, "high": None, "unit": None})
    # Concrete patient value, e.g. eGFR 34 / eGFR of 34 / at eGFR 41.
    for m in re.finditer(r"egfr\s*(?:of|=|is|at)?\s*(\d+)", t):
        val = int(m.group(1))
        if any((x.get("low") == val or x.get("high") == val or x.get("value") == val) for x in out):
            continue
        out.append({"variable": "egfr", "operator": "EQ", "value": val, "low": None, "high": None, "unit": None})
    return out


def proposition(subject: str, predicate: str, object_: str | int | float | None, polarity: str, clause: str, conditions=None, population=None, confidence=1.0):
    return {
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "polarity": polarity,
        "conditions": conditions or [],
        "population": population,
        "confidence": confidence,
        "source_clause": clause,
    }


def parse_action_clause(clause: str, population: str | None) -> list[dict]:
    t = norm(clause)
    conds = conditions_from_clause(clause)
    out = []

    if has(t, "contraindicat", "contraindication criterion"):
        # Explicit negation means absence of a contraindication rule, not a positive contraindication.
        if has(t, "does not provide", "does not state", "no contraindication", "no clinical contraindication", "contains no", "not an absolute contraindication"):
            out.append(proposition("evidence", "PROVIDES_ABSOLUTE_PROHIBITION", "drug_or_combination", "NEGATIVE", clause, population=population))
        else:
            out.append(proposition("drug_use", "CONTRAINDICATED", "use", "POSITIVE", clause, conds, population))

    if has(t, "not recommended") and has(t, "initiat", "starting", "new treatment", "new patient", "start"):
        out.append(proposition("drug_initiation", "INITIATION_NOT_RECOMMENDED", "initiation", "POSITIVE", clause, conds, population or "new_or_initiating_user"))

    if has(t, "reassess", "reassessment", "benefit-risk reassessment", "benefit versus risk", "benefit and risk should be reassessed", "benefit/risk"):
        out.append(proposition("drug_use", "REASSESS_BENEFIT_RISK", "benefit_risk", "POSITIVE", clause, conds, population))

    if has(t, "discontinu", "must stop", "must discontinue", "stop the medicine", "stop the drug"):
        out.append(proposition("drug_use", "DISCONTINUE", "drug", "POSITIVE", clause, conds, population))

    return out


def parse_non_action_clause(clause: str, population: str | None) -> list[dict]:
    t = norm(clause)
    out: list[dict] = []

    # Risk / absolute-management boundary.
    if has(t, "increase bleeding risk", "increased bleeding risk", "raise bleeding risk", "higher bleeding risk", "increase that risk", "increases risk"):
        out.append(proposition("drug_exposure", "INCREASES_RISK", "adverse_event", "POSITIVE", clause, population=population))
    if has(t, "does not provide an absolute", "does not state an absolute", "no absolute prohibition", "not an absolute prohibition", "no absolute contraindication"):
        out.append(proposition("evidence", "PROVIDES_ABSOLUTE_PROHIBITION", "drug_or_combination", "NEGATIVE", clause, population=population))
    elif has(t, "absolutely forbidden", "absolute prohibition", "absolutely contraindicated", "forbidden in all", "in all circumstances"):
        out.append(proposition("evidence", "PROVIDES_ABSOLUTE_PROHIBITION", "drug_or_combination", "POSITIVE", clause, population=population))

    # Diagnosis boundary.
    if has(t, "does not confirm", "does not state that a single symptom confirms", "does not by itself diagnose", "no malignant diagnosis", "does not classify the lesion as malignant"):
        out.append(proposition("evidence", "CONFIRMS_DIAGNOSIS", "diagnosis", "NEGATIVE", clause, population=population))
    elif has(t, "confirms the diagnosis", "confirms that", "proves that the treated patient has", "proves that the patient has", "confirmed diagnosis", "proves that the lesion is malignant"):
        out.append(proposition("evidence", "CONFIRMS_DIAGNOSIS", "diagnosis", "POSITIVE", clause, population=population))

    # Causal polarity.
    if has(t, "does not establish that", "does not establish causality", "do not on their own demonstrate", "causal attribution is not established", "causality is not established", "does not prove that", "cannot establish", "not establish that"):
        out.append(proposition("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "NEGATIVE", clause, population=population))
    elif has(t, "proves that", "establishes that", "establishes a causal", "caused the event", "causal effect") and not has(t, "does not", "not established", "cannot"):
        out.append(proposition("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "POSITIVE", clause, population=population))

    if has(t, "association between", "associated with", "found an association", "reports an association"):
        out.append(proposition("factor_a", "ASSOCIATED_WITH", "outcome_b", "POSITIVE", clause, population=population, confidence=0.9))

    # Incidence polarity.
    if has(t, "not a valid estimate of", "cannot be used to estimate", "cannot establish the true incidence", "cannot estimate", "not a valid estimate", "report counts cannot"):
        out.append(proposition("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "NEGATIVE", clause, population=population))
    elif has(t, "true incidence", "calculate the true incidence", "obtain the true incidence"):
        out.append(proposition("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "POSITIVE", clause, population=population))

    # Registry facts / efficacy boundary.
    if has(t, "recruiting"):
        out.append(proposition("study", "HAS_STATUS", "recruiting", "POSITIVE", clause, population=population))
    if has(t, "completed", "status completed"):
        out.append(proposition("study", "HAS_STATUS", "completed", "POSITIVE", clause, population=population))
    if has(t, "primary endpoint", "planned primary endpoint"):
        out.append(proposition("study", "HAS_PRIMARY_ENDPOINT", "primary_endpoint", "POSITIVE", clause, population=population))
    if has(t, "no efficacy outcome", "no efficacy result", "no result demonstrating clinical benefit", "contains no result demonstrating clinical benefit", "no clinical benefit result"):
        out.append(proposition("registry_evidence", "DEMONSTRATES_EFFICACY", "clinical_benefit", "NEGATIVE", clause, population=population))
    elif has(t, "proves that the investigational treatment works", "proves that the treatment works", "achieved clinical efficacy", "proves efficacy", "demonstrates clinical benefit") and not has(t, "no result", "contains no"):
        out.append(proposition("registry_evidence", "DEMONSTRATES_EFFICACY", "clinical_benefit", "POSITIVE", clause, population=population))

    # Directional supersession / currentness.
    for pat in [
        r"(guideline\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?supersedes\s+(guideline\s+[a-z0-9._-]+)",
        r"(version\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?supersedes\s+(version\s+[a-z0-9._-]+)",
    ]:
        m = re.search(pat, t)
        if m:
            newer, older = clean_entity(m.group(1)), clean_entity(m.group(2))
            out.append(proposition(newer, "SUPERSEDES", older, "POSITIVE", clause, population=population))
            out.append(proposition(newer, "IS_CURRENT", "recommendation_source", "POSITIVE", clause, population=population))
            out.append(proposition(older, "IS_CURRENT", "recommendation_source", "NEGATIVE", clause, population=population))

    m = re.search(r"(guideline\s+[a-z0-9._-]+|version\s+[a-z0-9._-]+)[^.;]{0,45}?(?:remains|is|be treated as)\s+(?:the\s+)?current", t)
    if m:
        out.append(proposition(clean_entity(m.group(1)), "IS_CURRENT", "recommendation_source", "POSITIVE", clause, population=population))

    # Guideline pending update / current recommendation state.
    if has(t, "has not been updated", "has not yet been updated", "has not been revised", "has not yet been revised"):
        out.append(proposition("current_guideline", "IS_CURRENT", "existing_recommendation", "POSITIVE", clause, population=population))
    if has(t, "continues to recommend", "still recommends"):
        m = re.search(r"(?:continues to recommend|still recommends)\s+(?:option|treatment|standard)?\s*([a-z0-9._-]+)", t)
        obj = m.group(1) if m else "existing_option"
        out.append(proposition("current_guideline", "IS_CURRENT", obj, "POSITIVE", clause, population=population))
    if has(t, "automatically changes the current guideline", "automatically changes the guideline", "guideline recommendation to"):
        out.append(proposition("current_guideline", "IS_CURRENT", "new_option", "POSITIVE", clause, population=population))

    # Mechanism vs management.
    if has(t, "inhibits cyp3a", "cyp3a inhibitor"):
        out.append(proposition("drug_p", "POTENTIAL_PK_INTERACTION", "cyp3a_pathway", "POSITIVE", clause, population=population, confidence=0.8))
    if has(t, "cyp3a substrate"):
        out.append(proposition("drug_q", "POTENTIAL_PK_INTERACTION", "cyp3a_pathway", "POSITIVE", clause, population=population, confidence=0.8))
    if has(t, "pharmacokinetic interaction", "cyp3a-mediated pharmacokinetic interaction", "plausible pharmacokinetic interaction"):
        out.append(proposition("drug_pair", "POTENTIAL_PK_INTERACTION", "cyp3a_pathway", "POSITIVE", clause, population=population))
    if has(t, "no management instruction", "no dose adjustment", "no therapeutic dose recommendation", "no therapeutic-management recommendation", "contains no dose adjustment", "no product-specific management rule"):
        out.append(proposition("mechanism_or_pk_evidence", "PROVIDES_MANAGEMENT_RULE", "drug_pair_or_patient", "NEGATIVE", clause, population=population))
    elif has(t, "requires a dose reduction", "must receive a lower dose", "clinically contraindicated", "dose reduction is required", "requires dose adjustment"):
        out.append(proposition("mechanism_or_pk_evidence", "PROVIDES_MANAGEMENT_RULE", "drug_pair_or_patient", "POSITIVE", clause, population=population))

    # PGx association.
    if has(t, "genotype is associated with", "genotype changes", "greater drug exposure", "higher drug exposure", "pharmacokinetic association"):
        out.append(proposition("genotype", "ASSOCIATED_WITH", "drug_exposure", "POSITIVE", clause, population=population))

    # Imaging/report uncertainty.
    if has(t, "indeterminate"):
        out.append(proposition("lesion", "CLASSIFIED_AS", "indeterminate", "POSITIVE", clause, population=population))
    if has(t, "malignant") and not has(t, "no malignant", "does not classify"):
        out.append(proposition("lesion", "CLASSIFIED_AS", "malignant", "POSITIVE", clause, population=population))
    if has(t, "recommend", "recommends") and has(t, "mri"):
        out.append(proposition("report", "RECOMMENDS_FOLLOWUP", "mri_characterization", "POSITIVE", clause, population=population))

    # Cross-trial superiority boundary.
    if has(t, "not a randomized direct comparison", "non-head-to-head", "without a randomized head-to-head", "different populations"):
        out.append(proposition("cross_trial_percentages", "PROVES_SUPERIORITY", "treatment_a_over_b", "NEGATIVE", clause, population=population))
    elif has(t, "proves treatment a is superior", "proves that treatment a is superior", "proves superiority"):
        out.append(proposition("cross_trial_percentages", "PROVES_SUPERIORITY", "treatment_a_over_b", "POSITIVE", clause, population=population))

    return out


def parse_atomic(text: str) -> list[dict]:
    global_population = infer_population(text)
    props: list[dict] = []
    for clause in split_clauses(text):
        pop = infer_population(clause) or global_population
        props.extend(parse_action_clause(clause, pop))
        props.extend(parse_non_action_clause(clause, pop))
    return dedupe_props(props)


def dedupe_props(props: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for p in props:
        cond_key = tuple((c["variable"], c["operator"], c.get("value"), c.get("low"), c.get("high")) for c in p["conditions"])
        key = (p["subject"], p["predicate"], str(p["object"]), p["polarity"], cond_key, p.get("population"))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def condition_holds(condition: dict, value: float) -> bool:
    op = condition["operator"]
    if op == "LT":
        return value < float(condition["value"])
    if op == "LE":
        return value <= float(condition["value"])
    if op == "GT":
        return value > float(condition["value"])
    if op == "GE":
        return value >= float(condition["value"])
    if op == "EQ":
        return value == float(condition["value"])
    if op == "RANGE":
        return float(condition["low"]) <= value <= float(condition["high"])
    return False


def claim_concrete_egfr(props: list[dict]) -> float | None:
    for p in props:
        for c in p["conditions"]:
            if c["variable"] == "egfr" and c["operator"] == "EQ":
                return float(c["value"])
    return None


def action_at_value(props: list[dict], value: float, population: str | None = None) -> set[str]:
    out = set()
    for p in props:
        if p["predicate"] not in ACTION_PREDICATES or p["polarity"] != "POSITIVE":
            continue
        if population and p.get("population") and p["population"] != population:
            continue
        if any(c["variable"] == "egfr" and condition_holds(c, value) for c in p["conditions"]):
            out.add(p["predicate"])
    return out


def population_from_props(props: list[dict]) -> str | None:
    vals = {p.get("population") for p in props if p.get("population")}
    if len(vals) == 1:
        return next(iter(vals))
    if "existing_user" in vals:
        return "existing_user"
    if "new_or_initiating_user" in vals:
        return "new_or_initiating_user"
    return None


def exact_prop_match(evidence: list[dict], claim: dict) -> tuple[bool, bool]:
    """Returns (same_positive, explicit_negative)."""
    same_pos = False
    explicit_neg = False
    for e in evidence:
        if e["predicate"] != claim["predicate"]:
            continue
        # For directional relations/currentness require subject/object identity when available.
        if claim["predicate"] in {"SUPERSEDES", "IS_CURRENT", "CLASSIFIED_AS", "HAS_STATUS", "HAS_PRIMARY_ENDPOINT", "RECOMMENDS_FOLLOWUP", "PROVES_SUPERIORITY"}:
            if e["subject"] != claim["subject"] or str(e["object"]) != str(claim["object"]):
                continue
        if e["polarity"] == "POSITIVE" and claim["polarity"] == "POSITIVE":
            same_pos = True
        if e["polarity"] == "NEGATIVE" and claim["polarity"] == "POSITIVE":
            explicit_neg = True
    return same_pos, explicit_neg


def compare(evidence: list[dict], claim: list[dict]) -> tuple[str, list[str]]:
    cues: list[str] = []

    # 1. Numeric/action constraints dominate everything else.
    value = claim_concrete_egfr(claim)
    claim_actions = {p["predicate"] for p in claim if p["predicate"] in ACTION_PREDICATES and p["polarity"] == "POSITIVE"}
    if value is not None and claim_actions:
        pop = population_from_props(claim)
        ev_actions = action_at_value(evidence, value, pop)
        if claim_actions & ev_actions:
            return "DIRECT_SUPPORT", [f"atomic_numeric_support:{value}", f"evidence_actions={sorted(ev_actions)}"]
        if ev_actions:
            return "CONTRADICTS", [f"atomic_numeric_action_conflict:{value}", f"evidence_actions={sorted(ev_actions)}", f"claim_actions={sorted(claim_actions)}"]
        return "DOES_NOT_SUPPORT", [f"no_evidence_rule_for_claimed_action_at:{value}"]

    # Threshold/range claims: require the same predicate over the entire claimed region.
    for cp in [p for p in claim if p["predicate"] in ACTION_PREDICATES and p["polarity"] == "POSITIVE" and p["conditions"]]:
        for cc in cp["conditions"]:
            probes: list[float] = []
            if cc["operator"] == "LT":
                th = float(cc["value"])
                probes = [max(0, th - 1), max(0, th - 5), max(0, th - 14)]
            elif cc["operator"] == "RANGE":
                lo, hi = float(cc["low"]), float(cc["high"])
                probes = [lo, (lo + hi) / 2, hi]
            if probes:
                pop = cp.get("population")
                bad = []
                good = []
                for v in probes:
                    acts = action_at_value(evidence, v, pop)
                    if cp["predicate"] in acts:
                        good.append(v)
                    elif acts:
                        bad.append((v, sorted(acts)))
                if bad:
                    return "CONTRADICTS", [f"claimed_region_contains_action_conflict:{bad}"]
                if len(good) == len(probes):
                    return "DIRECT_SUPPORT", ["claimed_region_fully_supported"]
                if good:
                    return "PARTIAL_SUPPORT", ["claimed_region_partially_supported"]

    # 2. Explicit polarity conflicts. Some semantics map to CONTRADICTS, others to DOES_NOT_SUPPORT.
    contradiction_preds = {"ESTABLISHES_CAUSALITY", "ESTIMATES_TRUE_INCIDENCE", "IS_CURRENT"}
    unsupported_preds = {"PROVIDES_ABSOLUTE_PROHIBITION", "CONFIRMS_DIAGNOSIS", "DEMONSTRATES_EFFICACY", "PROVIDES_MANAGEMENT_RULE", "PROVES_SUPERIORITY"}
    for cp in claim:
        if cp["polarity"] != "POSITIVE":
            continue
        same_pos, explicit_neg = exact_prop_match(evidence, cp)
        if explicit_neg and cp["predicate"] in contradiction_preds:
            return "CONTRADICTS", [f"explicit_negative_polarity:{cp['predicate']}"]
        if explicit_neg and cp["predicate"] in unsupported_preds:
            return "DOES_NOT_SUPPORT", [f"explicit_absence_or_limitation:{cp['predicate']}"]

    # 3. Directional supersession implies currentness even when candidate omits the word supersedes.
    for cp in claim:
        if cp["predicate"] == "IS_CURRENT" and cp["polarity"] == "POSITIVE":
            same_pos, explicit_neg = exact_prop_match(evidence, cp)
            if explicit_neg:
                return "CONTRADICTS", [f"superseded_entity_asserted_current:{cp['subject']}"]
            if same_pos:
                return "DIRECT_SUPPORT", [f"current_entity_supported:{cp['subject']}"]

    # 4. Registry bounded facts.
    claim_registry = [p for p in claim if p["predicate"] in {"HAS_STATUS", "HAS_PRIMARY_ENDPOINT"} and p["polarity"] == "POSITIVE"]
    if claim_registry:
        if all(exact_prop_match(evidence, p)[0] for p in claim_registry):
            return "DIRECT_SUPPORT", ["registry_atomic_facts_supported"]

    # 5. Bounded PK mechanism: two mechanism propositions or explicit potential interaction support the bounded claim.
    if any(p["predicate"] == "POTENTIAL_PK_INTERACTION" and p["polarity"] == "POSITIVE" for p in claim):
        ev_pk = [p for p in evidence if p["predicate"] == "POTENTIAL_PK_INTERACTION" and p["polarity"] == "POSITIVE"]
        if ev_pk:
            return "DIRECT_SUPPORT", ["bounded_pk_mechanism_supported"]

    # 6. PGx association with unresolved management.
    if any(p["predicate"] == "ASSOCIATED_WITH" and p["subject"] == "genotype" and p["polarity"] == "POSITIVE" for p in claim):
        if any(p["predicate"] == "ASSOCIATED_WITH" and p["subject"] == "genotype" and p["polarity"] == "POSITIVE" for p in evidence):
            if any(p["predicate"] == "PROVIDES_MANAGEMENT_RULE" and p["polarity"] == "POSITIVE" for p in claim):
                if any(p["predicate"] == "PROVIDES_MANAGEMENT_RULE" and p["polarity"] == "NEGATIVE" for p in evidence):
                    return "DOES_NOT_SUPPORT", ["pgx_association_does_not_supply_management"]
            return "DIRECT_SUPPORT", ["pgx_association_preserved"]

    # 7. Risk preservation.
    if any(p["predicate"] == "INCREASES_RISK" and p["polarity"] == "POSITIVE" for p in claim):
        if any(p["predicate"] == "INCREASES_RISK" and p["polarity"] == "POSITIVE" for p in evidence):
            return "DIRECT_SUPPORT", ["risk_relation_preserved"]

    # 8. Imaging/report uncertainty.
    claim_class = [p for p in claim if p["predicate"] == "CLASSIFIED_AS" and p["polarity"] == "POSITIVE"]
    if claim_class:
        for cp in claim_class:
            if exact_prop_match(evidence, cp)[0]:
                # If claim also asks for a follow-up, require it too.
                follow = [p for p in claim if p["predicate"] == "RECOMMENDS_FOLLOWUP" and p["polarity"] == "POSITIVE"]
                if not follow or all(exact_prop_match(evidence, fp)[0] for fp in follow):
                    return "DIRECT_SUPPORT", ["report_classification_scope_preserved"]
            # malignant claim against indeterminate evidence is unsupported.
            if str(cp["object"]) == "malignant" and any(p["predicate"] == "CLASSIFIED_AS" and p["object"] == "indeterminate" and p["polarity"] == "POSITIVE" for p in evidence):
                return "DOES_NOT_SUPPORT", ["indeterminate_not_malignant"]

    # 9. Direct positive propositions, with no permissive lexical fallback.
    positive_claims = [p for p in claim if p["polarity"] == "POSITIVE"]
    if positive_claims:
        matched = sum(1 for p in positive_claims if exact_prop_match(evidence, p)[0])
        if matched == len(positive_claims):
            return "DIRECT_SUPPORT", ["all_atomic_claims_supported"]
        if matched > 0:
            return "PARTIAL_SUPPORT", [f"atomic_support_fraction:{matched}/{len(positive_claims)}"]

    # Medical safety default: uncertainty never becomes positive support.
    return "DOES_NOT_SUPPORT", ["conservative_atomic_default"]


def verify(evidence_text: str, claim_text: str):
    evidence = parse_atomic(evidence_text)
    claim = parse_atomic(claim_text)
    relation, cues = compare(evidence, claim)
    return relation, evidence, claim, cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        relation, evidence_props, claim_props, cues = verify(item["evidence_text"], item["candidate_claim"])
        rows.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "evidence_propositions": evidence_props,
            "claim_propositions": claim_props,
            "cues": cues,
            "verifier_version": VERIFIER_VERSION,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3 v0.4 atomic-proposition predictions to {out}")


if __name__ == "__main__":
    main()
