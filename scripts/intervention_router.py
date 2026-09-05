#!/usr/bin/env python3
"""Map evaluated model failures to intervention candidates.

The router is deliberately deterministic and auditable. It does not claim that
an intervention is the causal fix; it records a prioritized hypothesis that
must be validated by held-out regression.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


ALIASES = {
    "STALE": "STALE_KNOWLEDGE",
    "FRESHNESS": "STALE_KNOWLEDGE",
    "MISSING_KNOWLEDGE": "KNOWLEDGE_MISSING",
    "RETRIEVAL_FAILURE": "RETRIEVAL_MISS",
    "SOURCE_ROLE": "SOURCE_HIERARCHY",
    "EVIDENCE_HIERARCHY": "SOURCE_HIERARCHY",
    "RELATION_SHORTCUT": "REASONING_FAILURE",
    "RELATION_OVERSIMPLIFY": "REASONING_FAILURE",
    "METRIC_SALIENCE_BIAS": "REASONING_FAILURE",
    "FORECAST_OVERCONFIDENCE": "OVERCLAIM",
    "UNSAFE_DRUG": "UNSAFE_MEDICATION",
    "MEDICATION_SAFETY": "UNSAFE_MEDICATION",
    "TOOL_FAILURE": "BAD_TOOL_CALL",
    "JUDGE_DRIFT": "JUDGE_INCONSISTENCY",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc


def canonical_failure(value: str) -> str:
    token = value.strip().upper()
    for sep in ("(", ":", "["):
        token = token.split(sep, 1)[0]
    token = token.strip().replace(" ", "_").replace("-", "_")
    return ALIASES.get(token, token)


def get_failures(row: Dict[str, Any]) -> List[str]:
    raw = row.get("failure_types")
    if raw is None:
        raw = row.get("failures")
    if raw is None:
        raw = row.get("failure_clusters")
    if isinstance(raw, str):
        raw = [raw]
    return [canonical_failure(str(x)) for x in (raw or []) if str(x).strip()]


def get_critical_errors(row: Dict[str, Any]) -> List[str]:
    raw = row.get("critical_errors") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(x) for x in raw]


def route_row(row: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    rules = cfg.get("rules") or {}
    failures = get_failures(row)
    critical_errors = get_critical_errors(row)

    recommendations: List[Dict[str, Any]] = []
    unknown: List[str] = []
    for failure in failures:
        rule = rules.get(failure)
        if not rule:
            unknown.append(failure)
            continue
        recommendations.append(
            {
                "failure_cluster": failure,
                "status": "intervention_hypothesis",
                "primary": rule.get("primary", []),
                "secondary": rule.get("secondary", []),
                "regression_metrics": rule.get("metrics", []),
            }
        )

    priority = "NORMAL"
    if critical_errors or "UNSAFE_MEDICATION" in failures:
        priority = "BLOCKER"
    elif failures:
        priority = "HIGH"

    return {
        "case_id": row.get("case_id"),
        "run_id": row.get("run_id") or row.get("response_id"),
        "model_id": row.get("model_id"),
        "router_version": cfg.get("version", "unknown"),
        "observed_failures": failures,
        "critical_errors": critical_errors,
        "triage_priority": priority,
        "recommendations": recommendations,
        "unmapped_failures": unknown,
        "causal_status": "not_proven_until_regression",
    }


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    failure_counts: Counter[str] = Counter()
    intervention_counts: Counter[str] = Counter()
    metric_to_failures: Dict[str, set[str]] = defaultdict(set)
    blockers = 0

    for row in rows:
        if row["triage_priority"] == "BLOCKER":
            blockers += 1
        failure_counts.update(row["observed_failures"])
        for rec in row["recommendations"]:
            for intervention in rec.get("primary", []):
                intervention_counts[intervention] += 1
            for metric in rec.get("regression_metrics", []):
                metric_to_failures[metric].add(rec["failure_cluster"])

    return {
        "n_rows": len(rows),
        "blocker_rows": blockers,
        "failure_counts": dict(failure_counts.most_common()),
        "primary_intervention_counts": dict(intervention_counts.most_common()),
        "regression_metric_map": {k: sorted(v) for k, v in sorted(metric_to_failures.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Route model failures to intervention hypotheses")
    parser.add_argument("--eval", required=True, type=Path, help="Evaluation JSONL containing failure_types / critical_errors")
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("medical/configs/intervention-rules.json"),
        help="Routing-rule JSON",
    )
    parser.add_argument("--out", required=True, type=Path, help="Output routed JSONL")
    parser.add_argument("--summary", type=Path, default=None, help="Optional aggregate summary JSON")
    args = parser.parse_args()

    cfg = load_json(args.rules)
    routed = [route_row(row, cfg) for row in iter_jsonl(args.eval)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in routed:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = aggregate(routed)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
