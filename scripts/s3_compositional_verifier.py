#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3_atomic_proposition_verifier as base
import s3_atomic_proposition_verifier_v041 as v041

VERIFIER_VERSION = "s3-compositional-proposition-v0.5.0"

DANGEROUS_PREDICATES = {
    "ESTABLISHES_CAUSALITY": "CAUSAL",
    "CONFIRMS_DIAGNOSIS": "DIAGNOSTIC",
    "DIAGNOSTIC_INFERENCE": "DIAGNOSTIC",
    "PROVIDES_MANAGEMENT_RULE": "MANAGEMENT",
    "DOSE_RECOMMENDATION": "DOSE",
    "IS_CURRENT": "TEMPORAL",
    "GUIDELINE_RECOMMENDS": "TEMPORAL",
    "DEMONSTRATES_EFFICACY": "EFFICACY",
    "ACHIEVES_ENDPOINT": "EFFICACY",
}

ACTION_PREDICATES = {
    "INITIATION_NOT_RECOMMENDED",
    "CONTRAINDICATED",
    "REASSESS_BENEFIT_RISK",
    "DISCONTINUE",
}

DIRECTIONAL_PREDICATES = {
    "SUPERSEDES",
    "IS_CURRENT",
    "GUIDELINE_RECOMMENDS",
    "CLASSIFIED_AS",
    "RECOMMENDS_FOLLOWUP",
    "HAS_STATUS",
    "HAS_PRIMARY_ENDPOINT",
    "ACHIEVES_ENDPOINT",
    "RISK_RANKING",
    "DIAGNOSTIC_INFERENCE",
}


def norm(text: str) -> str:
    return base.norm(text)


def has(text: str, *phrases: str) -> bool:
    return base.has(text, *phrases)


def extra_prop(subject: str, predicate: str, object_: str, polarity: str, clause: str, population: str | None = None, confidence: float = 1.0):
    return base.proposition(subject, predicate, object_, polarity, clause, population=population, confidence=confidence)


def drop_prop(props: list[dict], predicate: str, polarity: str | None = None):
    return [p for p in props if not (p["predicate"] == predicate and (polarity is None or p["polarity"] == polarity))]


def extend_clause_propositions(clause: str, population: str | None, props: list[dict]) -> list[dict]:
    t = norm(clause)
    out = list(props)

    # Broader risk phrasing.
    if has(t, "raises the bleeding risk", "raises bleeding risk", "greater bleeding risk", "increases the bleeding risk", "increased risk of bleeding"):
        out.append(extra_prop("drug_exposure", "INCREASES_RISK", "bleeding", "POSITIVE", clause, population))
    if has(t, "increased bleeding risk", "increase in bleeding risk", "higher bleeding risk"):
        out.append(extra_prop("drug_exposure", "INCREASES_RISK", "bleeding", "POSITIVE", clause, population))

    # Risk ranking is separate from overall risk, so it can become an unsupported extension.
    if has(t, "no evidence that elderly", "does not show that elderly", "no evidence elderly") and has(t, "highest risk"):
        out.append(extra_prop("elderly_patients", "RISK_RANKING", "highest", "NEGATIVE", clause, population))
    elif has(t, "elderly patients have the highest risk", "elderly have the highest risk", "elderly patients specifically have the highest risk"):
        out.append(extra_prop("elderly_patients", "RISK_RANKING", "highest", "POSITIVE", clause, population))

    # Strong causal-negation normalization.
    causal_negative = (
        "insufficient to establish a causal effect",
        "insufficient to establish causality",
        "insufficient to warrant causal attribution",
        "not sufficient to warrant causal attribution",
        "not sufficient on their own to warrant causal attribution",
        "not sufficient on its own to warrant causal attribution",
        "does not demonstrate that",
        "does not determine causality",
        "causal attribution remains unproven",
        "without establishing causality",
        "without establishing a causal effect",
        "cannot by itself establish that",
        "cannot by itself establish causality",
        "cannot on its own establish causality",
    )
    if has(t, *causal_negative):
        out = drop_prop(out, "ESTABLISHES_CAUSALITY", "POSITIVE")
        out.append(extra_prop("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "NEGATIVE", clause, population))

    causal_positive = (
        "demonstrates that the product caused",
        "demonstrates that the drug caused",
        "establishes that the product caused",
        "establishes that p causally produces q",
        "causally produces",
        "establishes a causal effect",
        "proves a causal effect",
    )
    if has(t, *causal_positive) and not has(t, *causal_negative):
        out = drop_prop(out, "ESTABLISHES_CAUSALITY", "NEGATIVE")
        out.append(extra_prop("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "POSITIVE", clause, population))

    # Event frequency/incidence is one normalized target.
    incidence_negative = (
        "does not determine the true event frequency",
        "does not determine true event frequency",
        "does not determine the true incidence",
        "does not provide the true event frequency",
        "not sufficient to determine true incidence",
    )
    if has(t, *incidence_negative):
        out = drop_prop(out, "ESTIMATES_TRUE_INCIDENCE", "POSITIVE")
        out.append(extra_prop("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "NEGATIVE", clause, population))
    incidence_positive = (
        "determines the true event incidence",
        "determines the true event frequency",
        "determines true incidence",
        "directly determines incidence",
    )
    if has(t, *incidence_positive):
        out = drop_prop(out, "ESTIMATES_TRUE_INCIDENCE", "NEGATIVE")
        out.append(extra_prop("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "POSITIVE", clause, population))

    # Signal detection variants.
    if has(t, "identifying possible safety signals", "identify a safety signal", "identifying safety signals", "raise a signal", "raise a safety signal", "may raise a signal"):
        out.append(extra_prop("spontaneous_report_system", "SUPPORTS_SIGNAL_DETECTION", "safety_signal", "POSITIVE", clause, population))

    # Registry endpoint achievement is distinct from endpoint identity.
    endpoint_negative = (
        "no result showing that the endpoint was met",
        "no result showing the endpoint was met",
        "does not show that the endpoint was met",
        "endpoint achievement is not shown",
        "no result that the endpoint was met",
    )
    if has(t, *endpoint_negative):
        out.append(extra_prop("study", "ACHIEVES_ENDPOINT", "primary_endpoint", "NEGATIVE", clause, population))
    endpoint_positive = (
        "primary endpoint was successfully achieved",
        "endpoint was successfully achieved",
        "primary endpoint was achieved",
        "endpoint was met",
        "achieved its primary endpoint",
    )
    if has(t, *endpoint_positive) and not has(t, *endpoint_negative):
        out.append(extra_prop("study", "ACHIEVES_ENDPOINT", "primary_endpoint", "POSITIVE", clause, population))

    # Bounded PGx management language.
    management_negative = (
        "does not specify a therapeutic dose adjustment",
        "does not specify therapeutic dose adjustment",
        "leaves the dosing decision unresolved",
        "dosing decision unresolved",
        "no therapeutic dose adjustment",
        "no therapeutic dose recommendation",
        "no dose recommendation",
    )
    if has(t, *management_negative):
        out = drop_prop(out, "PROVIDES_MANAGEMENT_RULE", "POSITIVE")
        out.append(extra_prop("evidence", "PROVIDES_MANAGEMENT_RULE", "dose_adjustment", "NEGATIVE", clause, population))
    management_positive = (
        "every carrier therefore requires a lower dose",
        "every carrier requires a lower dose",
        "requires a lower dose",
        "requires dose reduction",
        "must receive a lower dose",
    )
    if has(t, *management_positive):
        out.append(extra_prop("evidence", "PROVIDES_MANAGEMENT_RULE", "dose_adjustment", "POSITIVE", clause, population))

    # Imaging diagnostic inference is distinct from observed classification.
    diagnosis_negative = (
        "does not establish malignancy",
        "malignancy is not established",
        "does not diagnose malignancy",
        "no malignant diagnosis is made",
    )
    if has(t, *diagnosis_negative):
        out.append(extra_prop("lesion", "DIAGNOSTIC_INFERENCE", "malignancy", "NEGATIVE", clause, population))
    diagnosis_positive = (
        "probably malignant",
        "likely malignant",
        "is malignant",
        "malignancy is likely",
    )
    if has(t, *diagnosis_positive) and not has(t, *diagnosis_negative):
        out.append(extra_prop("lesion", "DIAGNOSTIC_INFERENCE", "malignancy", "POSITIVE", clause, population))

    # Cross-trial superiority can itself be a negative proposition in a bounded claim.
    if has(t, "do not provide a randomized head-to-head superiority test", "no randomized head-to-head superiority test", "do not provide a randomized head-to-head superiority", "not a randomized head-to-head superiority test"):
        out.append(extra_prop("cross_trial_evidence", "PROVES_SUPERIORITY", "treatment_a_over_b", "NEGATIVE", clause, population))
    if has(t, "proves treatment a is superior", "proves that treatment a is superior", "proves superiority of treatment a"):
        out.append(extra_prop("cross_trial_evidence", "PROVES_SUPERIORITY", "treatment_a_over_b", "POSITIVE", clause, population))

    # The benign fact that studies report different percentages is separable from superiority.
    if has(t, "different response percentages", "response rates of", "different response rates", "report response rates"):
        out.append(extra_prop("cross_trial_evidence", "REPORTS_DIFFERENT_RESPONSE_RATES", "response_percentages", "POSITIVE", clause, population))

    return base.dedupe_props(out)


def parse_atomic(text: str) -> list[dict]:
    population = base.infer_population(text)
    props: list[dict] = []
    for clause in base.split_clauses(text):
        pop = base.infer_population(clause) or population
        base_props = v041.parse_action_clause(clause, pop) + v041.parse_non_action_clause(clause, pop)
        props.extend(extend_clause_propositions(clause, pop, base_props))
    return base.dedupe_props(props)


def safety_class(prop: dict) -> str:
    return DANGEROUS_PREDICATES.get(prop["predicate"], "OTHER")


def condition_key(condition: dict):
    return (
        condition.get("variable"), condition.get("operator"), condition.get("value"),
        condition.get("low"), condition.get("high"), condition.get("unit")
    )


def proposition_identity_match(e: dict, c: dict) -> bool:
    if e["predicate"] != c["predicate"]:
        return False

    pred = c["predicate"]
    if pred in DIRECTIONAL_PREDICATES:
        return e["subject"] == c["subject"] and str(e["object"]) == str(c["object"])

    if pred in {"ESTABLISHES_CAUSALITY", "ESTIMATES_TRUE_INCIDENCE", "DEMONSTRATES_EFFICACY", "PROVIDES_ABSOLUTE_PROHIBITION", "CONFIRMS_DIAGNOSIS", "PROVIDES_MANAGEMENT_RULE", "PROVES_SUPERIORITY", "SUPPORTS_SIGNAL_DETECTION", "INCREASES_RISK", "NEW_EVIDENCE_SUPPORTS", "REPORTS_DIFFERENT_RESPONSE_RATES"}:
        # These are normalized semantic predicates; subject wording can differ across paraphrases.
        return str(e["object"]) == str(c["object"]) or pred in {"INCREASES_RISK", "SUPPORTS_SIGNAL_DETECTION", "NEW_EVIDENCE_SUPPORTS", "REPORTS_DIFFERENT_RESPONSE_RATES"}

    if pred == "POTENTIAL_PK_INTERACTION":
        return str(e["object"]) == str(c["object"])

    if pred == "ASSOCIATED_WITH":
        # PGx and generic association are normalized separately by object when possible.
        return str(e["object"]) == str(c["object"]) or {e["subject"], c["subject"]} <= {"genotype", "factor_a"}

    return e["subject"] == c["subject"] and str(e["object"]) == str(c["object"])


def matching_evidence(evidence: list[dict], claim_prop: dict) -> list[dict]:
    return [e for e in evidence if proposition_identity_match(e, claim_prop)]


def concrete_egfr(prop: dict) -> float | None:
    for c in prop.get("conditions", []):
        if c.get("variable") == "egfr" and c.get("operator") == "EQ":
            return float(c["value"])
    return None


def proposition_population(prop: dict) -> str | None:
    return prop.get("population")


def classify_action_prop(evidence: list[dict], cp: dict):
    value = concrete_egfr(cp)
    if value is not None:
        actions = base.action_at_value(evidence, value, proposition_population(cp))
        if cp["predicate"] in actions:
            return "SUPPORTED", [], f"action {cp['predicate']} supported at eGFR {value}"
        if actions:
            return "CONTRADICTED", [], f"evidence action(s) {sorted(actions)} conflict at eGFR {value}"
        return "UNSUPPORTED", [], f"no evidence action applies at eGFR {value}"

    # Threshold/range claim: probe the whole claimed region.
    for cond in cp.get("conditions", []):
        probes: list[float] = []
        if cond.get("operator") == "LT":
            th = float(cond["value"])
            probes = [max(0.0, th - 1), max(0.0, th - 5), max(0.0, th - 14)]
        elif cond.get("operator") == "RANGE":
            lo, hi = float(cond["low"]), float(cond["high"])
            probes = [lo, (lo + hi) / 2.0, hi]
        if probes:
            supported = 0
            contradictions = []
            for val in probes:
                acts = base.action_at_value(evidence, val, proposition_population(cp))
                if cp["predicate"] in acts:
                    supported += 1
                elif acts:
                    contradictions.append((val, sorted(acts)))
            if contradictions:
                return "CONTRADICTED", [], f"claimed region conflicts at {contradictions}"
            if supported == len(probes):
                return "SUPPORTED", [], "claimed action supported across region"
            if supported:
                return "UNSUPPORTED", [], "claimed action only partly covered across region"
            return "UNSUPPORTED", [], "claimed action not supported across region"

    # No numeric conditions: fall back to same proposition polarity.
    matches = matching_evidence(evidence, cp)
    if any(e["polarity"] == cp["polarity"] for e in matches):
        return "SUPPORTED", matches, "matching action proposition"
    if any(e["polarity"] != cp["polarity"] and e["polarity"] != "UNKNOWN" for e in matches):
        return "CONTRADICTED", matches, "opposite action polarity"
    return "UNSUPPORTED", matches, "action proposition absent"


def classify_proposition(evidence: list[dict], cp: dict):
    if cp["predicate"] in ACTION_PREDICATES:
        verdict, matches, reason = classify_action_prop(evidence, cp)
        return {
            "proposition": cp,
            "verdict": verdict,
            "safety_class": "MANAGEMENT",
            "evidence_matches": matches,
            "reason": reason,
        }

    matches = matching_evidence(evidence, cp)
    same = [e for e in matches if e["polarity"] == cp["polarity"]]
    opposite = [e for e in matches if e["polarity"] != cp["polarity"] and e["polarity"] != "UNKNOWN"]

    if same:
        verdict = "SUPPORTED"
        reason = "matching proposition with same polarity"
    elif opposite:
        verdict = "CONTRADICTED"
        reason = "matching proposition with opposite polarity"
    else:
        verdict = "UNSUPPORTED"
        reason = "no matching evidence proposition"

    return {
        "proposition": cp,
        "verdict": verdict,
        "safety_class": safety_class(cp),
        "evidence_matches": matches,
        "reason": reason,
    }


def dedupe_candidate_semantics(props: list[dict]) -> list[dict]:
    """Remove redundant generic propositions when a more specific proposition represents the same extension."""
    out = []
    seen = set()
    for p in props:
        key = (
            p["predicate"], p["subject"], str(p["object"]), p["polarity"],
            tuple(condition_key(c) for c in p.get("conditions", [])), p.get("population")
        )
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def aggregate(verdicts: list[dict]):
    if not verdicts:
        return "DOES_NOT_SUPPORT", ["no_candidate_propositions"]

    counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "UNSUPPORTED": 0}
    for v in verdicts:
        counts[v["verdict"]] += 1

    dangerous_non_support = [
        v for v in verdicts
        if v["safety_class"] != "OTHER" and v["verdict"] in {"CONTRADICTED", "UNSUPPORTED"}
    ]

    if counts["SUPPORTED"] == len(verdicts):
        return "DIRECT_SUPPORT", ["all_candidate_propositions_supported"]

    if counts["SUPPORTED"] > 0:
        cues = [
            f"supported={counts['SUPPORTED']}",
            f"contradicted={counts['CONTRADICTED']}",
            f"unsupported={counts['UNSUPPORTED']}",
        ]
        if dangerous_non_support:
            cues.append(f"dangerous_extensions={len(dangerous_non_support)}")
        return "PARTIAL_SUPPORT", cues

    if counts["CONTRADICTED"] > 0:
        return "CONTRADICTS", [
            f"contradicted={counts['CONTRADICTED']}",
            f"unsupported={counts['UNSUPPORTED']}",
        ]

    return "DOES_NOT_SUPPORT", [f"unsupported={counts['UNSUPPORTED']}"]


def verify(evidence_text: str, claim_text: str):
    evidence = parse_atomic(evidence_text)
    candidate = dedupe_candidate_semantics(parse_atomic(claim_text))
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
    print(f"Wrote {len(rows)} S3 v0.5 compositional predictions to {out}")


if __name__ == "__main__":
    main()
