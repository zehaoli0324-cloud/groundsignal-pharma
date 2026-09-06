#!/usr/bin/env python3
"""Explainable S5 benchmark-lineage detector for exposed v0.7 repair.

This module is deliberately dependency-light and deterministic. It does not
claim semantic generalization: v0.7.2 is calibrated only on already-exposed and
development transformations. A new post-freeze suite is still required.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable

METHOD_VERSION = "s5-lineage-hybrid-v0.7.2"
PROTECTED_SPLITS = {"heldout", "regression"}
SEMANTIC_CORE_FIELDS = (
    "task_type",
    "data_origin",
    "patient_context",
    "evidence_snapshot",
    "interaction",
    "expected_behavior",
    "graph_eval",
    "safety",
    "scoring",
)
MATCH_FIELDS = (
    "patient_context",
    "evidence_snapshot",
    "interaction",
    "expected_behavior",
    "graph_eval",
    "safety",
    "scoring",
)
HIGH_SIGNAL_FIELDS = (
    "evidence_snapshot",
    "expected_behavior",
    "graph_eval",
    "safety",
    "scoring",
)
RECORD_BLOCK_THRESHOLD = 0.86
RECORD_REVIEW_THRESHOLD = 0.70
FIELD_NEAR_THRESHOLD = 0.90
MIN_EXACT_HIGH_SIGNAL_FIELDS = 2
MIN_NEAR_HIGH_SIGNAL_FIELDS = 2
SPAN_SIMILARITY_THRESHOLD = 0.94
MIN_SPAN_CHARS = 24
MIN_SPAN_TOKENS = 4


def canonical_case_id(value: Any) -> str:
    """Compatibility-safe system-key normalization."""
    return unicodedata.normalize("NFKC", str(value or ""))


def require_compatibility_safe_case_id(value: Any, label: str = "case") -> str:
    raw = str(value or "")
    if not raw:
        raise ValueError(f"{label}: case_id is required")
    normalized = canonical_case_id(raw)
    if raw != normalized:
        raise ValueError(f"{label}: case_id must already be Unicode NFKC canonical")
    return normalized


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def semantic_core_sha256(case: dict[str, Any]) -> str:
    core = {key: case.get(key) for key in SEMANTIC_CORE_FIELDS}
    return hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()


def _normalized_text(value: Any) -> str:
    raw = _canonical_json(value) if not isinstance(value, str) else value
    text = unicodedata.normalize("NFKC", raw).casefold()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    return {t for t in _normalized_text(value).split() if t}


def lexical_similarity(a: Any, b: Any) -> float:
    if _canonical_json(a) == _canonical_json(b):
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        jaccard = 1.0
    elif not ta or not tb:
        jaccard = 0.0
    else:
        jaccard = len(ta & tb) / len(ta | tb)
    seq = SequenceMatcher(None, _normalized_text(a), _normalized_text(b), autojunk=False).ratio()
    return round(0.55 * jaccard + 0.45 * seq, 6)


def record_similarity(candidate: dict[str, Any], reference: dict[str, Any]) -> float:
    a = {field: candidate.get(field) for field in MATCH_FIELDS}
    b = {field: reference.get(field) for field in MATCH_FIELDS}
    return lexical_similarity(a, b)


def field_similarities(candidate: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in MATCH_FIELDS:
        score = lexical_similarity(candidate.get(field), reference.get(field))
        rows.append(
            {
                "field": field,
                "similarity": score,
                "exact": _canonical_json(candidate.get(field)) == _canonical_json(reference.get(field)),
            }
        )
    return rows


def _leaf_strings(value: Any, path: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, str):
        normalized = _normalized_text(value)
        if len(normalized) >= MIN_SPAN_CHARS and len(normalized.split()) >= MIN_SPAN_TOKENS:
            out.append((path, value))
    elif isinstance(value, dict):
        for key, item in value.items():
            out.extend(_leaf_strings(item, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            out.extend(_leaf_strings(item, f"{path}[{idx}]"))
    return out


def span_matches(candidate: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    cand = []
    ref = []
    for field in MATCH_FIELDS:
        cand.extend(_leaf_strings(candidate.get(field), field))
        ref.extend(_leaf_strings(reference.get(field), field))
    matches: list[dict[str, Any]] = []
    for c_path, c_text in cand:
        c_norm = _normalized_text(c_text)
        for r_path, r_text in ref:
            r_norm = _normalized_text(r_text)
            if c_norm == r_norm:
                score = 1.0
            else:
                score = SequenceMatcher(None, c_norm, r_norm, autojunk=False).ratio()
            if score >= SPAN_SIMILARITY_THRESHOLD:
                matches.append(
                    {
                        "candidate_path": c_path,
                        "reference_path": r_path,
                        "similarity": round(score, 6),
                    }
                )
    matches.sort(key=lambda row: (-float(row["similarity"]), row["candidate_path"], row["reference_path"]))
    return matches


def _decision_for_pair(candidate: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    rec = record_similarity(candidate, reference)
    fields = field_similarities(candidate, reference)
    spans = span_matches(candidate, reference)
    exact_high = [row["field"] for row in fields if row["field"] in HIGH_SIGNAL_FIELDS and row["exact"]]
    near_high = [
        row["field"]
        for row in fields
        if row["field"] in HIGH_SIGNAL_FIELDS and float(row["similarity"]) >= FIELD_NEAR_THRESHOLD
    ]
    reasons: list[str] = []
    if semantic_core_sha256(candidate) == semantic_core_sha256(reference):
        reasons.append("EXACT_SEMANTIC_CORE")
    if len(exact_high) >= MIN_EXACT_HIGH_SIGNAL_FIELDS:
        reasons.append("MULTI_FIELD_EXACT_REUSE")
    if rec >= RECORD_BLOCK_THRESHOLD:
        reasons.append("HIGH_RECORD_NEAR_DUPLICATE")
    if len(near_high) >= MIN_NEAR_HIGH_SIGNAL_FIELDS and rec >= 0.60:
        reasons.append("MULTI_FIELD_NEAR_REUSE")
    span_fields = {str(row["candidate_path"]).split(".", 1)[0] for row in spans}
    if len(spans) >= 3 and len(span_fields) >= 2:
        reasons.append("MULTI_SPAN_REUSE")

    if reasons:
        decision = "BLOCK"
    elif rec >= RECORD_REVIEW_THRESHOLD or len(near_high) >= 1 or len(spans) >= 2:
        decision = "REVIEW"
    else:
        decision = "ALLOW"
    return {
        "record_similarity": rec,
        "field_matches": [row for row in fields if float(row["similarity"]) >= 0.50 or bool(row["exact"])],
        "span_matches": spans,
        "exact_high_signal_fields": exact_high,
        "near_high_signal_fields": near_high,
        "reasons": reasons,
        "decision": decision,
    }


def detect_lineage(
    candidate: dict[str, Any],
    references: Iterable[dict[str, Any]],
    *,
    candidate_id: str | None = None,
    reference_snapshot: str = "authenticated-policy",
) -> dict[str, Any]:
    """Return explainable nearest-reference contamination evidence."""
    candidate_id = candidate_id or canonical_case_id(candidate.get("case_id"))
    best: dict[str, Any] | None = None
    for ref in references:
        case = ref.get("case")
        if not isinstance(case, dict):
            continue
        pair = _decision_for_pair(candidate, case)
        rank = (
            {"ALLOW": 0, "REVIEW": 1, "BLOCK": 2}[str(pair["decision"])],
            float(pair["record_similarity"]),
            len(pair["exact_high_signal_fields"]),
            len(pair["span_matches"]),
        )
        row = {
            "reference_id": str(ref.get("case_id") or case.get("case_id") or ""),
            "reference_split": str(ref.get("split") or ""),
            "rank": rank,
            **pair,
        }
        if best is None or row["rank"] > best["rank"]:
            best = row
    if best is None:
        return {
            "candidate_id": candidate_id,
            "reference_snapshot": reference_snapshot,
            "nearest_reference_id": None,
            "record_similarity": 0.0,
            "field_matches": [],
            "span_matches": [],
            "decision": "ALLOW",
            "reasons": ["NO_PROTECTED_REFERENCE"],
            "method_version": METHOD_VERSION,
        }
    return {
        "candidate_id": candidate_id,
        "reference_snapshot": reference_snapshot,
        "nearest_reference_id": best["reference_id"],
        "nearest_reference_split": best["reference_split"],
        "record_similarity": best["record_similarity"],
        "field_matches": best["field_matches"],
        "span_matches": best["span_matches"],
        "decision": best["decision"],
        "reasons": best["reasons"],
        "method_version": METHOD_VERSION,
    }


def validate_policy_records(
    benchmark_records: Iterable[dict[str, Any]],
    ordinary_records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Validate split isolation and ordinary-source lineage.

    Raises ValueError on a hard-gate violation and returns traces otherwise.
    """
    benchmarks = list(benchmark_records)
    ordinary = list(ordinary_records)

    seen_core: dict[str, dict[str, Any]] = {}
    for row in benchmarks:
        case = row["case"]
        case_id = require_compatibility_safe_case_id(case.get("case_id"), f"benchmark {row.get('source')}")
        split = str(row.get("split") or "")
        core = semantic_core_sha256(case)
        prior = seen_core.get(core)
        if prior is not None:
            prior_split = str(prior["split"])
            if prior_split != split:
                raise ValueError(
                    "cross-split semantic duplicate: "
                    f"{prior['case_id']!r}({prior_split}) vs {case_id!r}({split})"
                )
        else:
            seen_core[core] = {"case_id": case_id, "split": split}

    protected = [
        {
            "case_id": canonical_case_id(row["case"].get("case_id")),
            "split": str(row.get("split") or ""),
            "case": row["case"],
        }
        for row in benchmarks
        if str(row.get("split") or "") in PROTECTED_SPLITS
    ]
    traces: list[dict[str, Any]] = []
    for row in ordinary:
        case = row["case"]
        case_id = require_compatibility_safe_case_id(case.get("case_id"), f"ordinary {row.get('source')}")
        trace = detect_lineage(case, protected, candidate_id=case_id)
        trace["source"] = row.get("source")
        traces.append(trace)
        if trace["decision"] == "BLOCK":
            raise ValueError(
                f"ordinary source {row.get('source')!r} is protected-benchmark derived; "
                f"nearest={trace['nearest_reference_id']!r}, reasons={','.join(trace['reasons'])}"
            )
    return {"method_version": METHOD_VERSION, "traces": traces}
