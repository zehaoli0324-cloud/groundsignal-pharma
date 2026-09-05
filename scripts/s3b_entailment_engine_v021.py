#!/usr/bin/env python3
"""S3b v0.2.1 structured proposition entailment engine.

This module does not parse free text. It operates only on canonical proposition
objects and adds three semantics exposed by the fresh S3b v0.2 held-out:
- population/scope compatibility,
- exact same-polarity negative action support,
- anti-symmetry for SUPERSEDES.
"""
from __future__ import annotations

from typing import Any

import s3_compositional_verifier as v050
import s3_compositional_verifier_v054 as v054

ENGINE_VERSION = "s3b-structured-entailment-v0.2.1"


def population_compatible(evidence_prop: dict[str, Any], candidate_prop: dict[str, Any]) -> bool:
    """Return True when evidence scope covers the candidate scope.

    `None` on evidence means the rule is not population-restricted.
    `None` on candidate means a universal claim; population-specific evidence
    cannot support that broader claim.
    """
    ep = evidence_prop.get("population")
    cp = candidate_prop.get("population")
    if ep is None:
        return True
    if cp is None:
        return False
    return ep == cp


def same_identity(e: dict[str, Any], c: dict[str, Any]) -> bool:
    return (
        e.get("subject") == c.get("subject")
        and e.get("predicate") == c.get("predicate")
        and e.get("object") == c.get("object")
    )


def classify_action(evidence: list[dict[str, Any]], cp: dict[str, Any]) -> dict[str, Any]:
    same_action_all = [e for e in evidence if same_identity(e, cp)]
    same_action = [e for e in same_action_all if population_compatible(e, cp)]
    same_pol = [e for e in same_action if e.get("polarity") == cp.get("polarity")]
    opp_pol = [e for e in same_action if e.get("polarity") != cp.get("polarity")]

    value = v054._eq_value(cp)
    if value is not None:
        applicable_same = [e for e in same_pol if v054._contains(e, value)]
        applicable_opp = [e for e in opp_pol if v054._contains(e, value)]
        if applicable_same:
            return {
                "proposition": cp,
                "verdict": "SUPPORTED",
                "safety_class": "MANAGEMENT",
                "evidence_matches": applicable_same,
                "reason": "same action, compatible population and applicable condition",
            }
        if applicable_opp:
            return {
                "proposition": cp,
                "verdict": "CONTRADICTED",
                "safety_class": "MANAGEMENT",
                "evidence_matches": applicable_opp,
                "reason": "same scoped action has opposite polarity",
            }

        # When a rule explicitly defines the action threshold, a negative
        # point-claim outside that threshold is supported by the bounded rule.
        if cp.get("polarity") == "NEGATIVE":
            explicit_rules = [e for e in same_action if v054._egfr_condition(e) is not None]
            if explicit_rules and not any(v054._contains(e, value) for e in explicit_rules):
                return {
                    "proposition": cp,
                    "verdict": "SUPPORTED",
                    "safety_class": "MANAGEMENT",
                    "evidence_matches": explicit_rules,
                    "reason": "bounded action rule does not apply at candidate value",
                }

        if cp.get("polarity") == "POSITIVE":
            competing = [
                e for e in evidence
                if e.get("predicate") in v050.ACTION_PREDICATES
                and e.get("polarity") == "POSITIVE"
                and population_compatible(e, cp)
                and v054._contains(e, value)
            ]
            if competing:
                return {
                    "proposition": cp,
                    "verdict": "CONTRADICTED",
                    "safety_class": "MANAGEMENT",
                    "evidence_matches": competing,
                    "reason": "different scoped action applies at candidate value",
                }

        return {
            "proposition": cp,
            "verdict": "UNSUPPORTED",
            "safety_class": "MANAGEMENT",
            "evidence_matches": same_action_all,
            "reason": "no population-compatible action proposition supports candidate",
        }

    # Non-point/rule claims. Exact or narrower rules with the same polarity are supported.
    if same_pol:
        supported = [e for e in same_pol if v054._same_or_narrower(cp, e)]
        if supported:
            return {
                "proposition": cp,
                "verdict": "SUPPORTED",
                "safety_class": "MANAGEMENT",
                "evidence_matches": supported,
                "reason": "same-polarity scoped rule is equal or broader than candidate",
            }
        # If neither side has a numeric condition, exact same-polarity identity is sufficient.
        if v054._egfr_condition(cp) is None:
            exact_unconditioned = [e for e in same_pol if v054._egfr_condition(e) is None]
            if exact_unconditioned:
                return {
                    "proposition": cp,
                    "verdict": "SUPPORTED",
                    "safety_class": "MANAGEMENT",
                    "evidence_matches": exact_unconditioned,
                    "reason": "exact same-polarity unconditioned action proposition",
                }
        if cp.get("polarity") == "POSITIVE" and v054._egfr_condition(cp) is not None:
            return {
                "proposition": cp,
                "verdict": "CONTRADICTED",
                "safety_class": "MANAGEMENT",
                "evidence_matches": same_pol,
                "reason": "candidate rule is broader than compatible evidence rule",
            }

    if opp_pol:
        return {
            "proposition": cp,
            "verdict": "CONTRADICTED",
            "safety_class": "MANAGEMENT",
            "evidence_matches": opp_pol,
            "reason": "same scoped action has opposite polarity",
        }

    return {
        "proposition": cp,
        "verdict": "UNSUPPORTED",
        "safety_class": "MANAGEMENT",
        "evidence_matches": same_action_all,
        "reason": "no population-compatible scoped action proposition",
    }


def classify_supersedes(evidence: list[dict[str, Any]], cp: dict[str, Any]) -> dict[str, Any]:
    exact = [
        e for e in evidence
        if e.get("predicate") == "SUPERSEDES"
        and e.get("subject") == cp.get("subject")
        and e.get("object") == cp.get("object")
        and e.get("polarity") == cp.get("polarity")
    ]
    if exact:
        return {
            "proposition": cp,
            "verdict": "SUPPORTED",
            "safety_class": "TEMPORAL",
            "evidence_matches": exact,
            "reason": "exact directed supersession edge",
        }

    if cp.get("polarity") == "POSITIVE":
        reverse = [
            e for e in evidence
            if e.get("predicate") == "SUPERSEDES"
            and e.get("polarity") == "POSITIVE"
            and e.get("subject") == cp.get("object")
            and e.get("object") == cp.get("subject")
        ]
        if reverse:
            return {
                "proposition": cp,
                "verdict": "CONTRADICTED",
                "safety_class": "TEMPORAL",
                "evidence_matches": reverse,
                "reason": "SUPERSEDES is directional and anti-symmetric for this version pair",
            }

    return {
        "proposition": cp,
        "verdict": "UNSUPPORTED",
        "safety_class": "TEMPORAL",
        "evidence_matches": [],
        "reason": "no directed supersession evidence",
    }


def classify_proposition(evidence: list[dict[str, Any]], cp: dict[str, Any]) -> dict[str, Any]:
    pred = cp.get("predicate")
    if pred in v050.ACTION_PREDICATES:
        return classify_action(evidence, cp)
    if pred == "SUPERSEDES":
        return classify_supersedes(evidence, cp)
    return v054.classify_proposition(evidence, cp)


def aggregate(verdicts: list[dict[str, Any]]):
    return v054.v053.aggregate(verdicts)
