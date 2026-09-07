#!/usr/bin/env python3
"""S5 v0.9.1 exposed repair for Hangul recall and typed-measurement precision.

The v0.8.1 detector remains unchanged. This candidate is calibrated only on
the already-observed v0.9 failures and prior exposed development matrices; it
does not create or inspect a later fresh suite.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_v081 = _load("s5_lineage_detector_v081_base", _HERE / "s5_lineage_detector_v081.py")
_v081_decision_for_pair = _v081._decision_for_pair
_v081_language = _v081._language
for _name in dir(_v081):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_v081, _name)

METHOD_VERSION = "s5-lineage-script-role-v0.9.1-exposed"
SCRIPT_MIN_SHARED_CONCEPTS = 5
SCRIPT_REQUIRED_BOUNDARY_CONCEPTS = frozenset(
    {"missing_evidence", "causal_attribution", "uncertainty"}
)
_HANGUL_RE = re.compile(r"[\uac00-\ud7af]")

_CONCEPT_PATTERNS = dict(_v081._CONCEPT_PATTERNS)
_KOREAN_PATTERNS: dict[str, tuple[str, ...]] = {
    "investigational_intervention": ("시험용", "연구용", "시험 약물", "시험용 시냅스 조절제"),
    "rescue_intervention": ("구조용", "구조 약물", "구조용 스테로이드", "구조 스테로이드"),
    "unverified_source": ("확인되지 않았", "확인되지 않", "미확인"),
    "missing_evidence": ("자료가 없", "기록이 없", "누락", "없음"),
    "audit_or_adjudication": ("안전 위원회", "위원회 검토", "판정"),
    "causal_attribution": ("인과", "인과성", "원인을 단정", "약물 탓"),
    "confounding": ("교란", "영향을 분리"),
    "uncertainty": ("확정되지 않", "불확실", "보류"),
    "treatment_recommendation": ("용량 권고", "치료 권고"),
}
for _concept, _patterns in _KOREAN_PATTERNS.items():
    _CONCEPT_PATTERNS[_concept] = (*_CONCEPT_PATTERNS.get(_concept, ()), *_patterns)

_MEASUREMENT_ROLE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "hepatic_enzyme": (
        re.compile(r"\balt\b", re.IGNORECASE),
        re.compile(r"\b(?:alanine\s+)?aminotransferase\b", re.IGNORECASE),
        re.compile(r"간\s*효소"),
    ),
    "glucose": (
        re.compile(r"\bglucose\b", re.IGNORECASE),
        re.compile(r"\bblood\s+sugar\b", re.IGNORECASE),
        re.compile(r"혈당"),
    ),
    "neurophysiology": (
        re.compile(r"\beeg\b", re.IGNORECASE),
        re.compile(r"electroencephal", re.IGNORECASE),
        re.compile(r"burst[- ]suppression", re.IGNORECASE),
        re.compile(r"뇌파|신경생리|버스트\s*억제"),
    ),
}


def _concepts(case: dict[str, Any]) -> set[str]:
    text = _v081._normalized_text(_v081._record_value(case))
    return {
        concept
        for concept, patterns in _CONCEPT_PATTERNS.items()
        if any(_v081._normalized_text(pattern) in text for pattern in patterns)
    }


def _language(case: dict[str, Any]) -> str:
    text = _v081._normalized_text(_v081._record_value(case))
    if _HANGUL_RE.search(text):
        return "ko"
    return _v081_language(case)


def _measurement_roles(case: dict[str, Any]) -> set[str]:
    """Return measurement types from observed lab values, not prompts or negations."""
    labs = ((case.get("patient_context") or {}).get("labs") or [])
    text = " ".join(str(value) for value in labs)
    return {
        role
        for role, patterns in _MEASUREMENT_ROLE_PATTERNS.items()
        if any(pattern.search(text) for pattern in patterns)
    }


# The preserved v0.8.1 class resolves these private helpers from its module at
# runtime. Patch only the isolated imported module used by this candidate.
_v081._CONCEPT_PATTERNS = _CONCEPT_PATTERNS
_v081._concepts = _concepts
_v081._language = _language
_v081.METHOD_VERSION = METHOD_VERSION


def _decision_for_pair(candidate: dict[str, Any], reference: Any, index: Any = None) -> dict[str, Any]:
    pair = dict(_v081_decision_for_pair(candidate, reference, index))
    shared = set(pair.get("semantic_concept_overlap") or [])
    boundary_shared = shared & SCRIPT_REQUIRED_BOUNDARY_CONCEPTS
    script_semantic_match = bool(
        pair.get("cross_language_pair")
        and pair.get("candidate_language") == "ko"
        and len(shared) >= SCRIPT_MIN_SHARED_CONCEPTS
        and len(boundary_shared) >= 2
    )
    if script_semantic_match:
        pair["decision"] = "BLOCK"
        pair["reasons"] = [*pair.get("reasons", []), "SCRIPT_SEMANTIC_LINEAGE_REUSE"]
        pair["risk_score"] = max(float(pair.get("risk_score") or 0.0), 0.94)

    candidate_roles = _measurement_roles(candidate)
    reference_roles = _measurement_roles(reference.case)
    role_conflict = bool(candidate_roles and reference_roles and candidate_roles.isdisjoint(reference_roles))
    blocking_reasons = set(pair.get("reasons") or [])
    typed_clean_downgrade = bool(
        role_conflict
        and pair.get("decision") == "BLOCK"
        and blocking_reasons == {"DENSE_PROTECTED_ANCHOR_REUSE"}
        and not pair.get("exclusive_identifier_overlap")
        and not pair.get("exact_exclusive_fields")
        and not pair.get("near_exclusive_fields")
    )
    if typed_clean_downgrade:
        pair["decision"] = "ALLOW"
        pair["reasons"] = ["TYPED_MEASUREMENT_ROLE_MISMATCH"]

    pair["candidate_measurement_roles"] = sorted(candidate_roles)
    pair["reference_measurement_roles"] = sorted(reference_roles)
    pair["measurement_role_conflict"] = role_conflict
    pair["script_semantic_match"] = script_semantic_match
    pair["typed_clean_downgrade"] = typed_clean_downgrade
    return pair


_v081._decision_for_pair = _decision_for_pair
ReferenceIndex = _v081.ReferenceIndex


def detect_lineage(
    candidate: dict[str, Any],
    references: Any,
    *,
    allowed_references: Any = None,
    candidate_id: str | None = None,
    reference_snapshot: str = "authenticated-policy",
) -> dict[str, Any]:
    candidate_id = candidate_id or canonical_case_id(candidate.get("case_id"))
    index = references if isinstance(references, ReferenceIndex) else ReferenceIndex(references, allowed_references)
    rows: list[dict[str, Any]] = []
    for ref in index.references:
        pair = _decision_for_pair(candidate, ref, index)
        rank = (
            {"ALLOW": 0, "REVIEW": 1, "BLOCK": 2}[str(pair["decision"])],
            float(pair["risk_score"]),
            float(pair["record_similarity"]),
        )
        rows.append({"reference_id": ref.case_id, "reference_split": ref.split, "rank": rank, **pair})
    if not rows:
        return {
            "candidate_id": candidate_id,
            "reference_snapshot": reference_snapshot,
            "nearest_reference_id": None,
            "record_similarity": 0.0,
            "risk_score": 0.0,
            "field_matches": [],
            "span_matches": [],
            "decision": "ALLOW",
            "reasons": ["NO_PROTECTED_REFERENCE"],
            "method_version": METHOD_VERSION,
        }

    best = max(rows, key=lambda row: row["rank"])
    mosaic_rows = [
        row for row in rows
        if float(row["record_similarity"]) >= MOSAIC_MIN_RECORD_SIMILARITY
        and len(row.get("exclusive_anchor_overlap") or []) >= MOSAIC_MIN_ANCHORS_PER_REFERENCE
    ]
    total_mosaic_anchors = sum(len(row.get("exclusive_anchor_overlap") or []) for row in mosaic_rows)
    mosaic_block = bool(
        len(mosaic_rows) >= MOSAIC_MIN_REFERENCES
        and total_mosaic_anchors >= MOSAIC_MIN_TOTAL_ANCHORS
    )
    decision = str(best["decision"])
    reasons = list(best.get("reasons") or [])
    risk = float(best["risk_score"])
    if mosaic_block:
        decision = "BLOCK"
        reasons.append("MULTI_PROTECTED_REFERENCE_MOSAIC")
        risk = max(risk, 0.96)

    return {
        "candidate_id": candidate_id,
        "reference_snapshot": reference_snapshot,
        "nearest_reference_id": best["reference_id"],
        "nearest_reference_split": best["reference_split"],
        "record_similarity": best["record_similarity"],
        "risk_score": round(risk, 6),
        "field_matches": best["field_matches"],
        "span_matches": best["span_matches"],
        "exclusive_anchor_overlap": best.get("exclusive_anchor_overlap", []),
        "exclusive_identifier_overlap": best.get("exclusive_identifier_overlap", []),
        "semantic_concept_overlap": best.get("semantic_concept_overlap", []),
        "semantic_numeric_overlap": best.get("semantic_numeric_overlap", []),
        "candidate_language": best.get("candidate_language", "unknown"),
        "reference_language": best.get("reference_language", "unknown"),
        "cross_language_pair": best.get("cross_language_pair", False),
        "candidate_measurement_roles": best.get("candidate_measurement_roles", []),
        "reference_measurement_roles": best.get("reference_measurement_roles", []),
        "measurement_role_conflict": best.get("measurement_role_conflict", False),
        "script_semantic_match": best.get("script_semantic_match", False),
        "typed_clean_downgrade": best.get("typed_clean_downgrade", False),
        "typed_role_mismatch_references": sorted(
            row["reference_id"] for row in rows if row.get("typed_clean_downgrade")
        ),
        "script_semantic_match_references": sorted(
            row["reference_id"] for row in rows if row.get("script_semantic_match")
        ),
        "mosaic_reference_matches": [
            {
                "reference_id": row["reference_id"],
                "record_similarity": row["record_similarity"],
                "exclusive_anchor_count": len(row.get("exclusive_anchor_overlap") or []),
            }
            for row in sorted(mosaic_rows, key=lambda row: row["reference_id"])
        ],
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "method_version": METHOD_VERSION,
    }


_v081.detect_lineage = detect_lineage
validate_policy_records = _v081.validate_policy_records
