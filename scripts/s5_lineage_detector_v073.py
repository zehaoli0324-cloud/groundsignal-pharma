#!/usr/bin/env python3
"""Fast, explainable S5 lineage detector calibrated on exposed/development data.

v0.7.3 adds an explicit allowed-development corpus. Shared family templates are
therefore not treated as held-out-specific evidence. Blocking requires either an
exact protected semantic core or case-specific field/span/anchor evidence that
is absent from the allowed corpus. No future fresh-suite content is used here.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, NamedTuple

METHOD_VERSION = "s5-lineage-exclusive-anchor-v0.7.3"
PROTECTED_SPLITS = {"heldout", "regression"}
SEMANTIC_CORE_FIELDS = (
    "task_type", "data_origin", "patient_context", "evidence_snapshot",
    "interaction", "expected_behavior", "graph_eval", "safety", "scoring",
)
MATCH_FIELDS = (
    "patient_context", "evidence_snapshot", "interaction", "expected_behavior",
    "graph_eval", "safety", "scoring",
)
HIGH_SIGNAL_FIELDS = (
    "evidence_snapshot", "expected_behavior", "graph_eval", "safety", "scoring",
)

# Frozen development thresholds. They are calibrated by
# scripts/calibrate_s5_lineage_v073.py, never on a future fresh suite.
RECORD_BLOCK_THRESHOLD = 0.88
RECORD_REVIEW_THRESHOLD = 0.70
FIELD_NEAR_THRESHOLD = 0.90
SPAN_BLOCK_THRESHOLD = 0.95
SPAN_REVIEW_THRESHOLD = 0.82
MIN_SPAN_CHARS = 30
MIN_SPAN_TOKENS = 5

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "case", "do", "for",
    "from", "in", "is", "it", "no", "not", "of", "on", "or", "that", "the",
    "this", "to", "use", "with", "without", "only", "provided", "supplied",
}


def canonical_case_id(value: Any) -> str:
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


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _normalized_text(value: Any) -> str:
    raw = _canonical_json(value) if not isinstance(value, str) else value
    text = unicodedata.normalize("NFKC", raw).casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> tuple[str, ...]:
    return tuple(token for token in _normalized_text(value).split() if token)


def _content_tokens(value: Any) -> set[str]:
    return {
        token for token in _tokens(value)
        if token not in _STOPWORDS and (len(token) >= 4 or any(ch.isdigit() for ch in token))
    }


def _char_ngrams(value: Any, n: int = 4) -> set[str]:
    text = _normalized_text(value)
    if not text:
        return set()
    if len(text) <= n:
        return {text}
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _set_dice(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def lexical_similarity(a: Any, b: Any) -> float:
    if _canonical_json(a) == _canonical_json(b):
        return 1.0
    token_score = _set_dice(set(_tokens(a)), set(_tokens(b)))
    char_score = _set_dice(_char_ngrams(a), _char_ngrams(b))
    return round(0.58 * token_score + 0.42 * char_score, 6)


def record_similarity(candidate: dict[str, Any], reference: dict[str, Any]) -> float:
    a = {field: candidate.get(field) for field in MATCH_FIELDS}
    b = {field: reference.get(field) for field in MATCH_FIELDS}
    return lexical_similarity(a, b)


def field_similarities(candidate: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in MATCH_FIELDS:
        left, right = candidate.get(field), reference.get(field)
        exact = not _empty(left) and not _empty(right) and _canonical_json(left) == _canonical_json(right)
        similarity = 0.0 if _empty(left) or _empty(right) else lexical_similarity(left, right)
        rows.append({"field": field, "similarity": similarity, "exact": exact})
    return rows


def _leaf_strings(value: Any, path: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, str):
        normalized = _normalized_text(value)
        if len(normalized) >= MIN_SPAN_CHARS and len(normalized.split()) >= MIN_SPAN_TOKENS:
            out.append((path, normalized))
    elif isinstance(value, dict):
        for key, item in value.items():
            out.extend(_leaf_strings(item, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            out.extend(_leaf_strings(item, f"{path}[{idx}]"))
    return out


class _PreparedReference(NamedTuple):
    case_id: str
    split: str
    case: dict[str, Any]
    record_tokens: frozenset[str]
    exclusive_anchors: frozenset[str]
    exclusive_fields: frozenset[str]
    exclusive_spans: tuple[tuple[str, str, frozenset[str]], ...]


class ReferenceIndex:
    """Precomputed protected-vs-allowed identity evidence."""

    def __init__(
        self,
        references: Iterable[dict[str, Any]],
        allowed_references: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        refs = list(references)
        allowed = list(allowed_references or [])
        allowed_tokens: set[str] = set()
        allowed_fields: dict[str, set[str]] = {field: set() for field in MATCH_FIELDS}
        allowed_spans: dict[str, set[str]] = {field: set() for field in MATCH_FIELDS}
        for row in allowed:
            case = row.get("case") or {}
            allowed_tokens.update(_content_tokens({field: case.get(field) for field in MATCH_FIELDS}))
            for field in MATCH_FIELDS:
                value = case.get(field)
                if not _empty(value):
                    allowed_fields[field].add(_normalized_text(value))
                for path, text in _leaf_strings(value, field):
                    allowed_spans[field].add(text)

        prepared: list[_PreparedReference] = []
        for row in refs:
            case = row.get("case")
            if not isinstance(case, dict):
                continue
            record_value = {field: case.get(field) for field in MATCH_FIELDS}
            record_tokens = _content_tokens(record_value)
            exclusive_fields = {
                field for field in HIGH_SIGNAL_FIELDS
                if not _empty(case.get(field)) and _normalized_text(case.get(field)) not in allowed_fields[field]
            }
            exclusive_spans: list[tuple[str, str, frozenset[str]]] = []
            for field in MATCH_FIELDS:
                for path, text in _leaf_strings(case.get(field), field):
                    if text not in allowed_spans[field]:
                        anchors = frozenset(_content_tokens(text) - allowed_tokens)
                        exclusive_spans.append((path, text, anchors))
            prepared.append(
                _PreparedReference(
                    case_id=str(row.get("case_id") or case.get("case_id") or ""),
                    split=str(row.get("split") or ""),
                    case=case,
                    record_tokens=frozenset(record_tokens),
                    exclusive_anchors=frozenset(record_tokens - allowed_tokens),
                    exclusive_fields=frozenset(exclusive_fields),
                    exclusive_spans=tuple(exclusive_spans),
                )
            )
        self.references = tuple(prepared)
        self.allowed_count = len(allowed)
        self.reference_count = len(prepared)

    def serialized_size_bytes(self) -> int:
        payload = [
            {
                "case_id": ref.case_id,
                "split": ref.split,
                "exclusive_anchors": sorted(ref.exclusive_anchors),
                "exclusive_fields": sorted(ref.exclusive_fields),
                "exclusive_spans": [(p, t, sorted(a)) for p, t, a in ref.exclusive_spans],
            }
            for ref in self.references
        ]
        return len(_canonical_json(payload).encode("utf-8"))


def _span_matches(
    candidate: dict[str, Any], reference: _PreparedReference,
) -> list[dict[str, Any]]:
    candidate_spans: list[tuple[str, str, set[str]]] = []
    for field in MATCH_FIELDS:
        for path, text in _leaf_strings(candidate.get(field), field):
            candidate_spans.append((path, text, _content_tokens(text)))
    matches: list[dict[str, Any]] = []
    for r_path, r_text, r_anchors in reference.exclusive_spans:
        r_field = r_path.split(".", 1)[0].split("[", 1)[0]
        for c_path, c_text, c_tokens in candidate_spans:
            c_field = c_path.split(".", 1)[0].split("[", 1)[0]
            if c_field != r_field:
                continue
            shared_anchors = sorted(set(r_anchors) & c_tokens)
            if c_text == r_text:
                score = 1.0
            elif not shared_anchors:
                continue
            else:
                score = lexical_similarity(c_text, r_text)
            if score >= SPAN_REVIEW_THRESHOLD:
                matches.append({
                    "candidate_path": c_path,
                    "reference_path": r_path,
                    "similarity": round(score, 6),
                    "exclusive_anchor_overlap": shared_anchors,
                })
    matches.sort(key=lambda row: (-float(row["similarity"]), row["candidate_path"], row["reference_path"]))
    return matches[:24]


def _decision_for_pair(candidate: dict[str, Any], reference: _PreparedReference) -> dict[str, Any]:
    rec = record_similarity(candidate, reference.case)
    fields = field_similarities(candidate, reference.case)
    candidate_tokens = _content_tokens({field: candidate.get(field) for field in MATCH_FIELDS})
    anchor_overlap = sorted(set(reference.exclusive_anchors) & candidate_tokens)
    exact_exclusive = [
        row["field"] for row in fields
        if row["exact"] and row["field"] in reference.exclusive_fields
    ]
    near_exclusive = [
        row["field"] for row in fields
        if row["field"] in reference.exclusive_fields and float(row["similarity"]) >= FIELD_NEAR_THRESHOLD
    ]
    spans = _span_matches(candidate, reference)
    blocking_spans = [
        row for row in spans
        if float(row["similarity"]) >= SPAN_BLOCK_THRESHOLD
        and (float(row["similarity"]) == 1.0 or row["exclusive_anchor_overlap"])
    ]
    reasons: list[str] = []
    if semantic_core_sha256(candidate) == semantic_core_sha256(reference.case):
        reasons.append("EXACT_SEMANTIC_CORE")
    if exact_exclusive:
        reasons.append("PROTECTED_EXCLUSIVE_FIELD_REUSE")
    if blocking_spans:
        reasons.append("PROTECTED_EXCLUSIVE_SPAN_REUSE")
    if rec >= RECORD_BLOCK_THRESHOLD and anchor_overlap:
        reasons.append("ANCHORED_HIGH_RECORD_NEAR_DUPLICATE")
    if len(near_exclusive) >= 2 and rec >= 0.62 and anchor_overlap:
        reasons.append("ANCHORED_MULTI_FIELD_NEAR_REUSE")
    if len(anchor_overlap) >= 3 and rec >= 0.62:
        reasons.append("DENSE_PROTECTED_ANCHOR_REUSE")

    max_field = max((float(row["similarity"]) for row in fields if row["field"] in reference.exclusive_fields), default=0.0)
    max_span = max((float(row["similarity"]) for row in spans), default=0.0)
    anchor_density = len(anchor_overlap) / max(1, len(reference.exclusive_anchors))
    risk = min(1.0, max(rec, 0.92 * max_field, 0.96 * max_span, 0.62 + 0.25 * anchor_density if anchor_overlap else 0.0))
    if reasons:
        decision = "BLOCK"
    elif (
        (rec >= RECORD_REVIEW_THRESHOLD and anchor_overlap)
        or (near_exclusive and anchor_overlap)
        or any(row["exclusive_anchor_overlap"] for row in spans)
        or (len(anchor_overlap) >= 2 and rec >= 0.52)
    ):
        decision = "REVIEW"
    else:
        decision = "ALLOW"
    return {
        "record_similarity": rec,
        "risk_score": round(risk, 6),
        "field_matches": [row for row in fields if float(row["similarity"]) >= 0.50 or row["exact"]],
        "span_matches": spans,
        "protected_exclusive_fields": sorted(reference.exclusive_fields),
        "exact_exclusive_fields": exact_exclusive,
        "near_exclusive_fields": near_exclusive,
        "exclusive_anchor_overlap": anchor_overlap,
        "reasons": reasons,
        "decision": decision,
    }


def detect_lineage(
    candidate: dict[str, Any],
    references: Iterable[dict[str, Any]] | ReferenceIndex,
    *,
    allowed_references: Iterable[dict[str, Any]] | None = None,
    candidate_id: str | None = None,
    reference_snapshot: str = "authenticated-policy",
) -> dict[str, Any]:
    candidate_id = candidate_id or canonical_case_id(candidate.get("case_id"))
    index = references if isinstance(references, ReferenceIndex) else ReferenceIndex(references, allowed_references)
    best: dict[str, Any] | None = None
    for ref in index.references:
        pair = _decision_for_pair(candidate, ref)
        rank = (
            {"ALLOW": 0, "REVIEW": 1, "BLOCK": 2}[str(pair["decision"])],
            float(pair["risk_score"]), float(pair["record_similarity"]),
        )
        row = {"reference_id": ref.case_id, "reference_split": ref.split, "rank": rank, **pair}
        if best is None or row["rank"] > best["rank"]:
            best = row
    if best is None:
        return {
            "candidate_id": candidate_id, "reference_snapshot": reference_snapshot,
            "nearest_reference_id": None, "record_similarity": 0.0, "risk_score": 0.0,
            "field_matches": [], "span_matches": [], "decision": "ALLOW",
            "reasons": ["NO_PROTECTED_REFERENCE"], "method_version": METHOD_VERSION,
        }
    return {
        "candidate_id": candidate_id,
        "reference_snapshot": reference_snapshot,
        "nearest_reference_id": best["reference_id"],
        "nearest_reference_split": best["reference_split"],
        "record_similarity": best["record_similarity"],
        "risk_score": best["risk_score"],
        "field_matches": best["field_matches"],
        "span_matches": best["span_matches"],
        "exclusive_anchor_overlap": best["exclusive_anchor_overlap"],
        "decision": best["decision"],
        "reasons": best["reasons"],
        "method_version": METHOD_VERSION,
    }


def validate_policy_records(
    benchmark_records: Iterable[dict[str, Any]],
    ordinary_records: Iterable[dict[str, Any]],
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
