#!/usr/bin/env python3
"""Reproducible development calibration for S5 lineage detector v0.7.3.

Only public, already-exposed S5 families and their dev splits are used. The
script does not create or inspect a future fresh suite. Stable metrics and the
reference-index manifest are deterministic; runtime measurements are emitted
separately because they are host dependent.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
P0_ROOT = ROOT / "medical/case-families"
FRESH_ROOTS = (
    ROOT / "medical/stage-evals/S5/fresh-boundary-v0.2/families",
    ROOT / "medical/stage-evals/S5/fresh-boundary-v0.3/families",
    ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families",
)
TRANSFORMS = (
    "presentation_only",
    "prompt_paraphrase",
    "single_evidence_field",
    "evidence_graph_composition",
    "prompt_span_reuse",
    "distributed_fragment_reuse",
)
CALIBRATION_VERSION = "s5-lineage-calibration-v0.7.3"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def family_records(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        manifest = load_json(manifest_path)
        family_id = str(manifest["family_id"])
        for entry in manifest.get("cases") or []:
            path = (manifest_path.parent / str(entry["path"])).resolve()
            case = load_json(path)
            rows.append({
                "family_id": family_id,
                "case_id": str(case["case_id"]),
                "split": str(entry["split"]),
                "case": case,
                "path": path,
                "source": str(path.relative_to(ROOT)),
                "git_blob_sha1": git_blob_sha(path),
            })
    return rows


def load_exposed_records() -> list[dict[str, Any]]:
    rows = family_records(P0_ROOT)
    for root in FRESH_ROOTS:
        rows.extend(family_records(root))
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("calibration source case_id collision")
    return rows


def _new_id(ref: dict[str, Any], transform: str) -> str:
    digest = hashlib.sha256(f"{ref['case_id']}::{transform}".encode()).hexdigest()[:12]
    return f"S5DEV-V073-{transform.upper().replace('_', '-')}-{digest}"


def _base_for(ref: dict[str, Any], allowed: list[dict[str, Any]], offset: int = 0) -> dict[str, Any]:
    choices = [row for row in allowed if row["family_id"] != ref["family_id"]]
    if not choices:
        raise ValueError("no cross-family allowed base")
    idx = (int(hashlib.sha256(ref["case_id"].encode()).hexdigest()[:8], 16) + offset) % len(choices)
    return copy.deepcopy(choices[idx]["case"])


def _append_list(container: dict[str, Any], key: str, value: Any) -> None:
    current = container.get(key)
    if not isinstance(current, list):
        current = []
        container[key] = current
    current.append(value)


def _leaf_texts(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        out.add(" ".join(value.casefold().split()))
    elif isinstance(value, dict):
        for item in value.values():
            out.update(_leaf_texts(item))
    elif isinstance(value, list):
        for item in value:
            out.update(_leaf_texts(item))
    return out


def attributable_to_protected(
    ref: dict[str, Any], transform: str, allowed: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Independent label rule: is copied content absent from every allowed dev case?"""
    source = ref["case"]
    if transform in {"presentation_only", "prompt_paraphrase"}:
        return True, "whole_protected_record_retained"
    if transform == "single_evidence_field":
        value = canonical_json(source.get("evidence_snapshot"))
        observed = {canonical_json(row["case"].get("evidence_snapshot")) for row in allowed}
        return value not in observed, "protected_exclusive_evidence_field" if value not in observed else "dev_shared_evidence_field"
    if transform == "evidence_graph_composition":
        exclusive = []
        for field in ("evidence_snapshot", "graph_eval"):
            value = canonical_json(source.get(field))
            observed = {canonical_json(row["case"].get(field)) for row in allowed}
            if value not in observed:
                exclusive.append(field)
        return bool(exclusive), "protected_exclusive_fields:" + ",".join(exclusive) if exclusive else "dev_shared_composition"
    if transform == "prompt_span_reuse":
        prompt = str((source.get("interaction") or {}).get("prompt") or "")
        observed = set().union(*(_leaf_texts(row["case"].get("interaction")) for row in allowed))
        key = " ".join(prompt.casefold().split())
        return key not in observed, "protected_exclusive_prompt_span" if key not in observed else "dev_shared_prompt_span"
    if transform == "distributed_fragment_reuse":
        must = list((source.get("expected_behavior") or {}).get("must_include") or [])
        critical = list((source.get("safety") or {}).get("critical_errors") or [])
        copied = [str(value) for value in (must[:1] + critical[:1])]
        observed = set()
        for row in allowed:
            observed.update(_leaf_texts(row["case"].get("expected_behavior")))
            observed.update(_leaf_texts(row["case"].get("safety")))
        exclusive = [value for value in copied if " ".join(value.casefold().split()) not in observed]
        return bool(exclusive), "protected_exclusive_distributed_fragment" if exclusive else "dev_shared_fragments"
    raise ValueError(transform)


def make_variant(
    ref: dict[str, Any], transform: str, allowed: list[dict[str, Any]],
) -> dict[str, Any]:
    source = ref["case"]
    if transform == "presentation_only":
        case = copy.deepcopy(source)
        case["title"] = "Development presentation transform"
        case["tags"] = ["development", "lineage-calibration"]
    elif transform == "prompt_paraphrase":
        case = copy.deepcopy(source)
        interaction = case.setdefault("interaction", {})
        interaction["prompt"] = (
            "Constrain the response to the attached evidence snapshot. Separate supported "
            "statements from unsupported inference and keep the action bounded."
        )
        expected = case.setdefault("expected_behavior", {})
        expected["uncertainty_behavior"] = (
            "Express only uncertainty justified by the supplied record and do not add external facts."
        )
    elif transform == "single_evidence_field":
        case = _base_for(ref, allowed, 1)
        case["evidence_snapshot"] = copy.deepcopy(source.get("evidence_snapshot"))
    elif transform == "evidence_graph_composition":
        case = _base_for(ref, allowed, 2)
        case["evidence_snapshot"] = copy.deepcopy(source.get("evidence_snapshot"))
        case["graph_eval"] = copy.deepcopy(source.get("graph_eval"))
    elif transform == "prompt_span_reuse":
        case = _base_for(ref, allowed, 3)
        interaction = case.setdefault("interaction", {})
        prompt = str((source.get("interaction") or {}).get("prompt") or "")
        _append_list(interaction, "prior_turns", {"role": "user", "content": prompt})
    elif transform == "distributed_fragment_reuse":
        case = _base_for(ref, allowed, 4)
        source_expected = source.get("expected_behavior") or {}
        source_safety = source.get("safety") or {}
        expected = case.setdefault("expected_behavior", {})
        safety = case.setdefault("safety", {})
        must = list(source_expected.get("must_include") or [])
        critical = list(source_safety.get("critical_errors") or [])
        if must:
            _append_list(expected, "must_include", must[0])
        if critical:
            _append_list(safety, "critical_errors", critical[0])
    else:
        raise ValueError(transform)
    case["case_id"] = _new_id(ref, transform)
    return case


def build_candidates(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    protected = [row for row in records if row["split"] in {"heldout", "regression"}]
    allowed = [row for row in records if row["split"] == "dev"]
    candidates: list[dict[str, Any]] = []
    for row in allowed:
        candidates.append({
            "candidate_id": row["case_id"], "family_id": row["family_id"],
            "label": 0, "transformation": "clean_dev_hard_negative", "case": row["case"],
            "source_reference_id": None,
        })
    for ref in protected:
        for transform in TRANSFORMS:
            attributable, attribution_reason = attributable_to_protected(ref, transform, allowed)
            candidates.append({
                "candidate_id": _new_id(ref, transform), "family_id": ref["family_id"],
                "label": int(attributable), "transformation": transform,
                "attribution_reason": attribution_reason,
                "case": make_variant(ref, transform, allowed),
                "source_reference_id": ref["case_id"],
            })
    return protected, allowed, candidates


def record_text(case: dict[str, Any], detector: Any) -> str:
    return " ".join(detector._normalized_text(case.get(field)) for field in detector.MATCH_FIELDS)


def fit_tfidf(
    protected: list[dict[str, Any]], allowed: list[dict[str, Any]], candidates: list[dict[str, Any]], detector: Any,
) -> tuple[np.ndarray, np.ndarray, int]:
    reference_texts = [record_text(row["case"], detector) for row in protected]
    allowed_texts = [record_text(row["case"], detector) for row in allowed]
    candidate_texts = [record_text(row["case"], detector) for row in candidates]
    fit_texts = reference_texts + allowed_texts
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, norm="l2")
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1, norm="l2")
    word.fit(fit_texts)
    char.fit(fit_texts)
    ref_matrix = hstack([word.transform(reference_texts), char.transform(reference_texts)], format="csr")
    cand_matrix = hstack([word.transform(candidate_texts), char.transform(candidate_texts)], format="csr")
    # Each half is L2-normalized; divide dot product by two for cosine on concatenation.
    scores = (cand_matrix @ ref_matrix.T).toarray() / 2.0
    vocab_bytes = len(("\n".join(sorted(word.vocabulary_)) + "\n" + "\n".join(sorted(char.vocabulary_))).encode("utf-8"))
    return scores, np.argmax(scores, axis=1), vocab_bytes


PAIR_FEATURE_NAMES = (
    "record_similarity",
    "max_field_similarity",
    "near_field_count",
    "max_span_similarity",
    "span_count_norm",
    "exclusive_anchor_count_norm",
    "deterministic_reason_present",
)


def pair_features(trace: dict[str, Any]) -> list[float]:
    fields = trace.get("field_matches") or []
    spans = trace.get("span_matches") or []
    anchors = trace.get("exclusive_anchor_overlap") or []
    return [
        float(trace.get("record_similarity") or 0.0),
        max((float(row.get("similarity") or 0.0) for row in fields), default=0.0),
        sum(float(row.get("similarity") or 0.0) >= 0.90 for row in fields),
        max((float(row.get("similarity") or 0.0) for row in spans), default=0.0),
        min(8, len(spans)) / 8.0,
        min(8, len(anchors)) / 8.0,
        float(bool(trace.get("reasons"))),
    ]


def choose_threshold(scores: np.ndarray, labels: np.ndarray, max_fpr: float) -> float:
    candidates = sorted({0.0, 1.000001, *[float(score) for score in scores]})
    best: tuple[float, float, float] | None = None
    best_threshold = 1.000001
    for threshold in candidates:
        pred = scores >= threshold
        tp = int(np.sum(pred & (labels == 1)))
        fp = int(np.sum(pred & (labels == 0)))
        positives = max(1, int(np.sum(labels == 1)))
        negatives = max(1, int(np.sum(labels == 0)))
        recall, fpr = tp / positives, fp / negatives
        if fpr <= max_fpr:
            rank = (recall, -fpr, threshold)
            if best is None or rank > best:
                best, best_threshold = rank, threshold
    return round(float(best_threshold), 6)


def classification_metrics(decisions: list[str], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    labels = np.array([row["label"] for row in candidates], dtype=int)
    block = np.array([value == "BLOCK" for value in decisions])
    review = np.array([value == "REVIEW" for value in decisions])
    tp = int(np.sum(block & (labels == 1)))
    fp = int(np.sum(block & (labels == 0)))
    fn = int(np.sum((~block) & (labels == 1)))
    tn = int(np.sum((~block) & (labels == 0)))
    family = defaultdict(lambda: {"total": 0, "blocked": 0, "reviewed": 0})
    for row, decision in zip(candidates, decisions):
        if row["label"] != 1:
            continue
        item = family[row["transformation"]]
        item["total"] += 1
        item["blocked"] += int(decision == "BLOCK")
        item["reviewed"] += int(decision == "REVIEW")
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(tp / max(1, tp + fp), 6),
        "recall": round(tp / max(1, tp + fn), 6),
        "clean_false_block_rate": round(fp / max(1, fp + tn), 6),
        "clean_review_rate": round(int(np.sum(review & (labels == 0))) / max(1, int(np.sum(labels == 0))), 6),
        "by_transformation": {
            key: {**value, "recall": round(value["blocked"] / max(1, value["total"]), 6)}
            for key, value in sorted(family.items())
        },
    }


def threshold_decisions(scores: np.ndarray, block_threshold: float, review_threshold: float) -> list[str]:
    return [
        "BLOCK" if score >= block_threshold else "REVIEW" if score >= review_threshold else "ALLOW"
        for score in scores
    ]


def cross_validated_thresholds(
    scores: np.ndarray, candidates: list[dict[str, Any]], groups: np.ndarray,
) -> tuple[list[str], list[dict[str, Any]]]:
    labels = np.array([row["label"] for row in candidates], dtype=int)
    decisions = ["ALLOW"] * len(candidates)
    folds: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=5)
    for fold, (train, test) in enumerate(splitter.split(scores, labels, groups), 1):
        block_t = choose_threshold(scores[train], labels[train], 0.05)
        review_t = choose_threshold(scores[train], labels[train], 0.25)
        fold_decisions = threshold_decisions(scores[test], block_t, review_t)
        for idx, decision in zip(test, fold_decisions):
            decisions[int(idx)] = decision
        folds.append({
            "fold": fold, "test_groups": sorted(set(str(groups[idx]) for idx in test)),
            "block_threshold": block_t, "review_threshold": review_t,
        })
    return decisions, folds


def learned_pair_cv(
    pair_features_by_candidate: list[list[list[float]]], candidates: list[dict[str, Any]], groups: np.ndarray,
) -> tuple[list[str], list[dict[str, Any]]]:
    labels = np.array([row["label"] for row in candidates], dtype=int)
    decisions = ["ALLOW"] * len(candidates)
    folds: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=5)
    for fold, (train_c, test_c) in enumerate(splitter.split(np.zeros(len(labels)), labels, groups), 1):
        x_train: list[list[float]] = []
        y_train: list[int] = []
        for idx in train_c:
            source = candidates[int(idx)]["source_reference_id"]
            for ref_idx, features in enumerate(pair_features_by_candidate[int(idx)]):
                x_train.append(features)
                ref_id = PROTECTED_IDS[ref_idx]
                y_train.append(int(labels[int(idx)] == 1 and ref_id == source))
        scaler = StandardScaler().fit(x_train)
        model = LogisticRegression(C=0.5, class_weight="balanced", solver="liblinear", random_state=73)
        model.fit(scaler.transform(x_train), y_train)
        train_candidate_scores = []
        for idx in train_c:
            prob = model.predict_proba(scaler.transform(pair_features_by_candidate[int(idx)]))[:, 1]
            train_candidate_scores.append(float(np.max(prob)))
        train_candidate_scores_np = np.array(train_candidate_scores)
        train_labels = labels[train_c]
        block_t = choose_threshold(train_candidate_scores_np, train_labels, 0.05)
        review_t = choose_threshold(train_candidate_scores_np, train_labels, 0.25)
        for idx in test_c:
            prob = model.predict_proba(scaler.transform(pair_features_by_candidate[int(idx)]))[:, 1]
            score = float(np.max(prob))
            decisions[int(idx)] = "BLOCK" if score >= block_t else "REVIEW" if score >= review_t else "ALLOW"
        folds.append({
            "fold": fold, "test_groups": sorted(set(str(groups[idx]) for idx in test_c)),
            "block_threshold": block_t, "review_threshold": review_t,
            "coefficient_count": int(model.coef_.shape[1]),
        })
    return decisions, folds


def fit_final_pair_model(
    pair_features_by_candidate: list[list[list[float]]], candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    x_train: list[list[float]] = []
    y_train: list[int] = []
    for idx, candidate in enumerate(candidates):
        source = candidate["source_reference_id"]
        for ref_idx, features in enumerate(pair_features_by_candidate[idx]):
            x_train.append(features)
            y_train.append(int(candidate["label"] == 1 and PROTECTED_IDS[ref_idx] == source))
    scaler = StandardScaler().fit(x_train)
    model = LogisticRegression(C=0.5, class_weight="balanced", solver="liblinear", random_state=73)
    model.fit(scaler.transform(x_train), y_train)
    candidate_scores: list[float] = []
    for rows in pair_features_by_candidate:
        candidate_scores.append(float(np.max(model.predict_proba(scaler.transform(rows))[:, 1])))
    scores = np.array(candidate_scores)
    labels = np.array([row["label"] for row in candidates], dtype=int)
    block_threshold = choose_threshold(scores, labels, 0.05)
    review_threshold = choose_threshold(scores, labels, 0.25)
    return {
        "model_version": "s5-lineage-pair-logistic-v0.7.3",
        "feature_names": list(PAIR_FEATURE_NAMES),
        "scaler_mean": [round(float(value), 12) for value in scaler.mean_],
        "scaler_scale": [round(float(value), 12) for value in scaler.scale_],
        "coefficients": [round(float(value), 12) for value in model.coef_[0]],
        "intercept": round(float(model.intercept_[0]), 12),
        "block_threshold": block_threshold,
        "review_threshold": review_threshold,
        "training_pair_count": len(x_train),
        "positive_pair_count": int(sum(y_train)),
        "candidate_count": len(candidates),
        "calibration_only": True,
    }


PROTECTED_IDS: list[str] = []


def evaluate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    detector = load_module(ROOT / "scripts/s5_lineage_detector_v073.py", "s5_lineage_v073_calibration")
    records = load_exposed_records()
    protected, allowed, candidates = build_candidates(records)
    global PROTECTED_IDS
    PROTECTED_IDS = [row["case_id"] for row in protected]
    refs = [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in protected]
    dev = [{"case_id": row["case_id"], "split": row["split"], "case": row["case"]} for row in allowed]
    index = detector.ReferenceIndex(refs, dev)

    tfidf_matrix, _, tfidf_vocab_bytes = fit_tfidf(protected, allowed, candidates, detector)
    tfidf_scores = np.max(tfidf_matrix, axis=1)
    groups = np.array([row["family_id"] for row in candidates], dtype=object)

    production_decisions: list[str] = []
    exact_scores: list[float] = []
    lexical_scores: list[float] = []
    feature_rows: list[list[list[float]]] = []
    for cand_idx, candidate in enumerate(candidates):
        trace = detector.detect_lineage(candidate["case"], index, candidate_id=candidate["candidate_id"])
        production_decisions.append(str(trace["decision"]))
        exact_scores.append(float(any(
            detector.semantic_core_sha256(candidate["case"]) == detector.semantic_core_sha256(row["case"])
            for row in protected
        )))
        lexical_scores.append(max(detector.record_similarity(candidate["case"], row["case"]) for row in protected))
        pair_features_list: list[list[float]] = []
        for ref_idx, prepared in enumerate(index.references):
            pair = detector._decision_for_pair(candidate["case"], prepared)
            pair_features_list.append(pair_features(pair))
        feature_rows.append(pair_features_list)

    exact_decisions = ["BLOCK" if score else "ALLOW" for score in exact_scores]
    lexical_decisions, lexical_folds = cross_validated_thresholds(np.array(lexical_scores), candidates, groups)
    tfidf_decisions, tfidf_folds = cross_validated_thresholds(np.array(tfidf_scores), candidates, groups)
    learned_decisions, learned_folds = learned_pair_cv(feature_rows, candidates, groups)
    final_pair_model = fit_final_pair_model(feature_rows, candidates)

    methods = {
        "exact_semantic_core": classification_metrics(exact_decisions, candidates),
        "lexical_record_cv": {**classification_metrics(lexical_decisions, candidates), "folds": lexical_folds},
        "tfidf_vector_embedding_cv": {**classification_metrics(tfidf_decisions, candidates), "folds": tfidf_folds},
        "learned_pair_logistic_cv": {**classification_metrics(learned_decisions, candidates), "folds": learned_folds},
        "exclusive_anchor_hybrid_v073": classification_metrics(production_decisions, candidates),
    }
    selected = methods["exclusive_anchor_hybrid_v073"]
    selection_pass = (
        selected["recall"] >= 0.95
        and selected["clean_false_block_rate"] <= 0.05
        and selected["clean_review_rate"] <= 0.25
    )
    stable = {
        "stage": "S5", "version": "v0.7.3", "eval_name": "lineage-development-calibration",
        "evidence_class": "development_exposed_calibration", "fresh_evidence": False,
        "calibration_version": CALIBRATION_VERSION,
        "data_isolation": {
            "future_fresh_suite_used": False,
            "source_scope": "P0 exposed families + completed fresh v0.2-v0.4 families only",
            "protected_reference_count": len(protected), "allowed_dev_reference_count": len(allowed),
            "contaminated_variant_count": sum(row["label"] == 1 for row in candidates),
            "clean_hard_negative_count": sum(row["label"] == 0 for row in candidates),
            "groups": len(set(groups)), "transformations": list(TRANSFORMS),
        },
        "methods": methods,
        "selected_method": detector.METHOD_VERSION,
        "selection_gate": "PASS" if selection_pass else "FAIL",
        "threshold_contract": {
            "record_block": detector.RECORD_BLOCK_THRESHOLD,
            "record_review": detector.RECORD_REVIEW_THRESHOLD,
            "field_near": detector.FIELD_NEAR_THRESHOLD,
            "span_block": detector.SPAN_BLOCK_THRESHOLD,
            "span_review": detector.SPAN_REVIEW_THRESHOLD,
        },
        "learned_pair_model": final_pair_model,
        "artifact_cost": {
            "protected_index_size_bytes": index.serialized_size_bytes(),
            "tfidf_vocabulary_bytes": tfidf_vocab_bytes,
            "protected_pair_evaluations": len(candidates) * len(protected),
        },
        "fresh_status": "NOT_FRESH_DO_NOT_USE_FOR_RELEASE",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "known_limitations": [
            "Synthetic/exposed transformations cannot establish unseen semantic generalization.",
            "TF-IDF is a deterministic vector-space baseline, not a neural semantic embedding.",
            "The learned pair classifier is calibration-only and is not used as an opaque hard gate.",
            "A reproducible neural cross-encoder artifact is not available in this repository.",
            "A new post-freeze hidden lineage suite remains mandatory before bounded release.",
        ],
    }
    manifest = {
        "manifest_version": "s5-protected-reference-index-v0.7.3",
        "method_version": detector.METHOD_VERSION,
        "future_fresh_suite_used": False,
        "records": [
            {key: row[key] for key in ("family_id", "case_id", "split", "source", "git_blob_sha1")}
            for row in protected + allowed
        ],
    }
    benchmark = runtime_benchmark(detector, index, candidates)
    return stable, manifest, benchmark


def runtime_benchmark(detector: Any, index: Any, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    sample = candidates[:12] + candidates[-12:]
    timings: list[float] = []
    for row in sample:
        start = time.perf_counter()
        detector.detect_lineage(row["case"], index, candidate_id=row["candidate_id"])
        timings.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    return {
        "benchmark_version": CALIBRATION_VERSION,
        "host_dependent": True,
        "sample_count": len(sample),
        "reference_count": index.reference_count,
        "median_ms_per_candidate": round(statistics.median(timings), 3),
        "p95_ms_per_candidate": round(p95, 3),
        "max_ms_per_candidate": round(max(timings), 3),
        "guardrail_p95_ms": 500.0,
        "guardrail_pass": p95 <= 500.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--index-out", required=True, type=Path)
    parser.add_argument("--benchmark-out", required=True, type=Path)
    args = parser.parse_args()
    stable, manifest, benchmark = evaluate()
    for path, payload in ((args.out, stable), (args.index_out, manifest), (args.benchmark_out, benchmark)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selection_gate": stable["selection_gate"],
        "selected": stable["methods"]["exclusive_anchor_hybrid_v073"],
        "benchmark": benchmark,
    }, ensure_ascii=False, indent=2))
    return 0 if stable["selection_gate"] == "PASS" and benchmark["guardrail_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
