#!/usr/bin/env python3
"""Explainable multilingual and multi-reference S5 lineage detector v0.8.1.

This exposed repair extends the frozen v0.7.3 detector. It adds two generic
signals: multilingual concept/identifier agreement for translated derivatives,
and aggregation across multiple protected references for mosaic contamination.
It also tightens low-evidence REVIEW assignment so ordinary same-domain records
are not escalated merely for sharing generic medical vocabulary.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any, Iterable

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_base = _load("s5_lineage_detector_v073_base", _HERE / "s5_lineage_detector_v073.py")
for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)

METHOD_VERSION = "s5-lineage-multilingual-mosaic-v0.8.1"
MOSAIC_MIN_REFERENCES = 2
MOSAIC_MIN_ANCHORS_PER_REFERENCE = 8
MOSAIC_MIN_TOTAL_ANCHORS = 16
MOSAIC_MIN_RECORD_SIMILARITY = 0.52
REVIEW_MIN_DENSE_ANCHORS = 8

# Hyphenated alphanumeric codes are treated as identifiers. Underscored rubric
# labels such as ``causal_boundary`` are deliberately excluded because they are
# shared schema vocabulary, not case identity.
_IDENTIFIER_RE = re.compile(r"\b[a-z][a-z0-9]{1,20}-[a-z0-9]{1,20}\b", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

# Small, inspectable bilingual ontology. Entries describe reasoning roles rather
# than v0.8 case IDs, drug names or benchmark-specific graph nodes.
_CONCEPT_PATTERNS: dict[str, tuple[str, ...]] = {
    "protocol_deviation": ("protocol deviation", "conduct departure", "departed from plan", "方案偏离", "偏离方案"),
    "investigational_intervention": ("investigational", "experimental", "研究性", "试验性"),
    "rescue_intervention": ("rescue dose", "rescue intervention", "补救用药", "补救措施"),
    "unverified_source": ("unverified", "not verified", "未经核实", "尚未核实"),
    "missing_evidence": ("missing", "absent", "unavailable", "cannot be inspected", "缺失", "不可用", "无法核查"),
    "audit_or_adjudication": ("audit", "adjudication", "审计", "裁定"),
    "hypothesis_only": ("hypothesis-level", "hypothesis generating", "supports a hypothesis", "只能形成假设", "假设层面"),
    "efficacy_claim": ("efficacy", "clinically effective", "patient benefit", "临床疗效", "治疗效果"),
    "causal_attribution": ("causal", "causally", "attribution", "因果", "归因"),
    "treatment_recommendation": ("treatment recommendation", "recommendation is requested", "治疗建议", "用药建议"),
    "biomarker_change": ("biomarker", "marker change", "phospho-marker", "标志物", "磷酸化"),
    "renal_clearance": ("renal clearance", "clearance estimate", "renal exposure", "肾清除", "清除率", "肾暴露"),
    "hydration_confounder": ("hydration", "fluid intervention", "补液", "水化"),
    "confounding": ("confounder", "confounding", "混杂"),
    "uncertainty": ("uncertain", "uncertainty", "provisional", "不确定", "暂缓"),
}


def _record_value(case: dict[str, Any]) -> dict[str, Any]:
    return {field: case.get(field) for field in MATCH_FIELDS}


def _identifiers(case: dict[str, Any]) -> set[str]:
    return {value.casefold() for value in _IDENTIFIER_RE.findall(_canonical_json(_record_value(case)))}


def _concepts(case: dict[str, Any]) -> set[str]:
    text = _normalized_text(_record_value(case))
    return {
        concept for concept, patterns in _CONCEPT_PATTERNS.items()
        if any(_normalized_text(pattern) in text for pattern in patterns)
    }


def _uses_cjk(case: dict[str, Any]) -> bool:
    return bool(_CJK_RE.search(_canonical_json(_record_value(case))))


class ReferenceIndex(_base.ReferenceIndex):
    """v0.7.3 index plus protected-exclusive identifiers and concepts."""

    def __init__(
        self,
        references: Iterable[dict[str, Any]],
        allowed_references: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        refs = list(references)
        allowed = list(allowed_references or [])
        super().__init__(refs, allowed)
        allowed_ids: set[str] = set()
        for row in allowed:
            allowed_ids.update(_identifiers(row.get("case") or {}))
        self.exclusive_identifiers = {
            str(row.get("case_id") or (row.get("case") or {}).get("case_id") or ""):
            frozenset(_identifiers(row.get("case") or {}) - allowed_ids)
            for row in refs
        }
        self.reference_concepts = {
            str(row.get("case_id") or (row.get("case") or {}).get("case_id") or ""):
            frozenset(_concepts(row.get("case") or {}))
            for row in refs
        }


def _decision_for_pair(
    candidate: dict[str, Any], reference: Any, index: ReferenceIndex | None = None,
) -> dict[str, Any]:
    pair = dict(_base._decision_for_pair(candidate, reference))
    candidate_ids = _identifiers(candidate)
    exclusive_ids = set(index.exclusive_identifiers.get(reference.case_id, ())) if index else _identifiers(reference.case)
    identifier_overlap = sorted(candidate_ids & exclusive_ids)
    candidate_concepts = _concepts(candidate)
    reference_concepts = set(index.reference_concepts.get(reference.case_id, ())) if index else _concepts(reference.case)
    concept_overlap = sorted(candidate_concepts & reference_concepts)
    cross_language = _uses_cjk(candidate) != _uses_cjk(reference.case)

    multilingual_match = bool(
        cross_language
        and (
            len(identifier_overlap) >= 2
            or (identifier_overlap and len(concept_overlap) >= 3)
            or len(concept_overlap) >= 7
        )
    )
    if multilingual_match:
        pair["decision"] = "BLOCK"
        pair["reasons"] = [*pair.get("reasons", []), "MULTILINGUAL_SEMANTIC_LINEAGE_REUSE"]
        pair["risk_score"] = max(float(pair.get("risk_score") or 0.0), 0.94)
    elif pair.get("decision") == "REVIEW":
        spans = pair.get("span_matches") or []
        strong_review = bool(
            (float(pair.get("record_similarity") or 0.0) >= RECORD_REVIEW_THRESHOLD and pair.get("exclusive_anchor_overlap"))
            or (
                len(pair.get("near_exclusive_fields") or []) >= 2
                and pair.get("exclusive_anchor_overlap")
            )
            or any(row.get("exclusive_anchor_overlap") for row in spans)
            or (
                len(pair.get("exclusive_anchor_overlap") or []) >= REVIEW_MIN_DENSE_ANCHORS
                and float(pair.get("record_similarity") or 0.0) >= 0.52
            )
        )
        if not strong_review:
            pair["decision"] = "ALLOW"

    pair["exclusive_identifier_overlap"] = identifier_overlap
    pair["semantic_concept_overlap"] = concept_overlap
    pair["cross_language_pair"] = cross_language
    return pair


def detect_lineage(
    candidate: dict[str, Any],
    references: Iterable[dict[str, Any]] | ReferenceIndex,
    *, allowed_references: Iterable[dict[str, Any]] | None = None,
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
            float(pair["risk_score"]), float(pair["record_similarity"]),
        )
        rows.append({"reference_id": ref.case_id, "reference_split": ref.split, "rank": rank, **pair})
    if not rows:
        return {
            "candidate_id": candidate_id, "reference_snapshot": reference_snapshot,
            "nearest_reference_id": None, "record_similarity": 0.0, "risk_score": 0.0,
            "field_matches": [], "span_matches": [], "decision": "ALLOW",
            "reasons": ["NO_PROTECTED_REFERENCE"], "method_version": METHOD_VERSION,
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
    reasons = list(best.get("reasons") or [])
    decision = str(best["decision"])
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
        "cross_language_pair": best.get("cross_language_pair", False),
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


def validate_policy_records(
    benchmark_records: Iterable[dict[str, Any]], ordinary_records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    benchmarks = list(benchmark_records)
    ordinary = list(ordinary_records)
    seen_core: dict[str, dict[str, Any]] = {}
    for row in benchmarks:
        case = row["case"]
        case_id = require_compatibility_safe_case_id(case.get("case_id"), f"benchmark {row.get('source')}")
        split = str(row.get("split") or "")
        core = semantic_core_sha256(case)
        prior = seen_core.get(core)
        if prior is not None and str(prior["split"]) != split:
            raise ValueError(
                "cross-split semantic duplicate: "
                f"{prior['case_id']!r}({prior['split']}) vs {case_id!r}({split})"
            )
        seen_core.setdefault(core, {"case_id": case_id, "split": split})

    protected = [
        {"case_id": canonical_case_id(row["case"].get("case_id")), "split": str(row.get("split") or ""), "case": row["case"]}
        for row in benchmarks if str(row.get("split") or "") in PROTECTED_SPLITS
    ]
    allowed = [
        {"case_id": canonical_case_id(row["case"].get("case_id")), "split": str(row.get("split") or ""), "case": row["case"]}
        for row in benchmarks if str(row.get("split") or "") not in PROTECTED_SPLITS
    ]
    index = ReferenceIndex(protected, allowed)
    traces: list[dict[str, Any]] = []
    for row in ordinary:
        case = row["case"]
        case_id = require_compatibility_safe_case_id(case.get("case_id"), f"ordinary {row.get('source')}")
        trace = detect_lineage(case, index, candidate_id=case_id)
        trace["source"] = row.get("source")
        traces.append(trace)
        if trace["decision"] == "BLOCK":
            raise ValueError(
                f"ordinary source {row.get('source')!r} is protected-benchmark derived; "
                f"nearest={trace['nearest_reference_id']!r}, reasons={','.join(trace['reasons'])}"
            )
    return {
        "method_version": METHOD_VERSION,
        "reference_count": index.reference_count,
        "allowed_reference_count": index.allowed_count,
        "index_size_bytes": index.serialized_size_bytes(),
        "traces": traces,
    }
