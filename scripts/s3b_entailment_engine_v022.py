#!/usr/bin/env python3
"""S3b v0.2.2 structured entailment engine.

Adds explicit condition-domain semantics:
- EXACT_DOMAIN: outside the stated domain the proposition is false.
- SUFFICIENT_ONLY: inside is supported; outside remains unknown.

Free-text parsing is intentionally out of scope.
"""
from __future__ import annotations

from typing import Any

import s3_compositional_verifier as v050
import s3_compositional_verifier_v054 as v054
import s3b_entailment_engine_v021 as v021

ENGINE_VERSION = "s3b-structured-entailment-v0.2.2"


def semantics(prop: dict[str, Any]) -> str:
    return str(prop.get("condition_semantics") or "SUFFICIENT_ONLY").upper()


def egfr_condition(prop: dict[str, Any]) -> dict[str, Any] | None:
    for c in prop.get("conditions", []) or []:
        if c.get("variable") == "egfr":
            return c
    return None


def contains(prop: dict[str, Any], value: float) -> bool:
    c = egfr_condition(prop)
    if c is None:
        return True
    op = str(c.get("operator", "")).upper()
    if op == "EQ":
        return value == float(c["value"])
    if op == "LT":
        return value < float(c["value"])
    if op == "LTE":
        return value <= float(c["value"])
    if op == "GT":
        return value > float(c["value"])
    if op == "GTE":
        return value >= float(c["value"])
    if op == "RANGE":
        return float(c["low"]) <= value <= float(c["high"])
    return False


def point_value(prop: dict[str, Any]) -> float | None:
    c = egfr_condition(prop)
    if c and str(c.get("operator", "")).upper() == "EQ":
        return float(c["value"])
    return None


def interval(prop: dict[str, Any]):
    """Return numeric interval tuple (low, low_closed, high, high_closed)."""
    c = egfr_condition(prop)
    if c is None:
        return (float("-inf"), False, float("inf"), False)
    op = str(c.get("operator", "")).upper()
    if op == "EQ":
        v = float(c["value"])
        return (v, True, v, True)
    if op == "LT":
        return (float("-inf"), False, float(c["value"]), False)
    if op == "LTE":
        return (float("-inf"), False, float(c["value"]), True)
    if op == "GT":
        return (float(c["value"]), False, float("inf"), False)
    if op == "GTE":
        return (float(c["value"]), True, float("inf"), False)
    if op == "RANGE":
        return (float(c["low"]), True, float(c["high"]), True)
    raise ValueError(f"Unsupported condition operator: {op}")


def interval_subset(candidate: dict[str, Any], evidence: dict[str, Any]) -> bool:
    cl, clc, ch, chc = interval(candidate)
    el, elc, eh, ehc = interval(evidence)

    if cl < el or ch > eh:
        return False
    if cl == el and clc and not elc:
        return False
    if ch == eh and chc and not ehc:
        return False
    return True


def same_identity(e: dict[str, Any], c: dict[str, Any]) -> bool:
    return v021.same_identity(e, c)


def classify_action(evidence: list[dict[str, Any]], cp: dict[str, Any]) -> dict[str, Any]:
    same_all = [e for e in evidence if same_identity(e, cp)]
    same_scope = [e for e in same_all if v021.population_compatible(e, cp)]
    same_pol = [e for e in same_scope if e.get("polarity") == cp.get("polarity")]
    opp_pol = [e for e in same_scope if e.get("polarity") != cp.get("polarity")]

    value = point_value(cp)
    if value is not None:
        applicable_same = [e for e in same_pol if contains(e, value)]
        applicable_opp = [e for e in opp_pol if contains(e, value)]
        if applicable_same:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": applicable_same, "reason": "same scoped action applies at candidate value"}
        if applicable_opp:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": applicable_opp, "reason": "opposite-polarity scoped action applies at candidate value"}

        exact_same = [e for e in same_pol if egfr_condition(e) is not None and semantics(e) == "EXACT_DOMAIN"]
        exact_opp = [e for e in opp_pol if egfr_condition(e) is not None and semantics(e) == "EXACT_DOMAIN"]

        # Candidate asserts the same polarity outside an exhaustively closed domain.
        if exact_same and not any(contains(e, value) for e in exact_same):
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": exact_same, "reason": "candidate value lies outside exact applicability domain"}

        # Candidate denies the proposition outside a positive exact domain.
        if cp.get("polarity") == "NEGATIVE":
            positive_exact = [e for e in same_scope if e.get("polarity") == "POSITIVE" and semantics(e) == "EXACT_DOMAIN" and egfr_condition(e) is not None]
            if positive_exact and not any(contains(e, value) for e in positive_exact):
                return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": positive_exact, "reason": "negative candidate is outside positive exact domain"}

        if exact_opp and not any(contains(e, value) for e in exact_opp):
            # Opposite exact domain being false outside does not automatically prove candidate unless logical complement is intended; stay conservative.
            pass

        if cp.get("polarity") == "POSITIVE":
            competing = [
                e for e in evidence
                if e.get("predicate") in v050.ACTION_PREDICATES
                and e.get("polarity") == "POSITIVE"
                and v021.population_compatible(e, cp)
                and contains(e, value)
            ]
            if competing:
                return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": competing, "reason": "different scoped action applies at candidate value"}

        return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_all, "reason": "value not supported; available domains are open or non-applicable"}

    # Rule-level candidate.
    if same_pol:
        subset_matches = [e for e in same_pol if interval_subset(cp, e)]
        if subset_matches:
            return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": subset_matches, "reason": "candidate rule domain is within same-polarity evidence domain"}

        exact_domains = [e for e in same_pol if semantics(e) == "EXACT_DOMAIN"]
        if exact_domains:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": exact_domains, "reason": "candidate rule exceeds exact same-polarity evidence domain"}

        # Exact unconditioned same-polarity proposition.
        if egfr_condition(cp) is None:
            unconditioned = [e for e in same_pol if egfr_condition(e) is None]
            if unconditioned:
                return {"proposition": cp, "verdict": "SUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": unconditioned, "reason": "same unconditioned proposition"}

    if opp_pol:
        overlapping_opp = [e for e in opp_pol if interval_subset(cp, e) or interval_subset(e, cp)]
        if overlapping_opp:
            return {"proposition": cp, "verdict": "CONTRADICTED", "safety_class": "MANAGEMENT", "evidence_matches": overlapping_opp, "reason": "opposite-polarity scoped proposition overlaps candidate domain"}

    return {"proposition": cp, "verdict": "UNSUPPORTED", "safety_class": "MANAGEMENT", "evidence_matches": same_all, "reason": "no compatible structured action rule"}


def classify_proposition(evidence: list[dict[str, Any]], cp: dict[str, Any]) -> dict[str, Any]:
    if cp.get("predicate") in v050.ACTION_PREDICATES:
        return classify_action(evidence, cp)
    return v021.classify_proposition(evidence, cp)


def aggregate(verdicts: list[dict[str, Any]]):
    return v021.aggregate(verdicts)
