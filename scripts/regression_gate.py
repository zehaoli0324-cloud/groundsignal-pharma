#!/usr/bin/env python3
"""Compare baseline vs candidate medical-model evaluations and emit a release gate.

Input evaluation JSONL rows should contain:
- case_id
- scores: numeric rubric dimensions
- critical_errors: []

The gate is policy-driven and intentionally fails on new critical safety errors
even when average capability improves.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def get_path(row: Dict[str, Any], dotted: str) -> Any:
    cur: Any = row
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def metric_average(rows: List[Dict[str, Any]], spec: Dict[str, Any]) -> Tuple[float | None, int]:
    values: List[float] = []
    scale_max = float(spec.get("scale_max", 1.0))
    if scale_max <= 0:
        raise ValueError(f"scale_max must be > 0 for metric {spec.get('name')}")

    for row in rows:
        raw = get_path(row, spec["path"])
        if raw is None:
            continue
        if not isinstance(raw, (int, float)):
            raise TypeError(f"Metric {spec['path']} must be numeric, got {type(raw).__name__}")
        values.append(float(raw) / scale_max)
    if not values:
        return None, 0
    return mean(values), len(values)


def case_ids(rows: List[Dict[str, Any]]) -> set[str]:
    return {str(row["case_id"]) for row in rows if row.get("case_id") is not None}


def count_critical_errors(rows: List[Dict[str, Any]]) -> int:
    total = 0
    for row in rows:
        errors = row.get("critical_errors") or []
        if isinstance(errors, str):
            errors = [errors]
        total += len(errors)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="GroundSignal medical-model regression gate")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("medical/configs/regression-policy.example.json"),
    )
    parser.add_argument("--out", required=True, type=Path, help="Regression report JSON")
    args = parser.parse_args()

    baseline = read_jsonl(args.baseline)
    candidate = read_jsonl(args.candidate)
    policy = read_json(args.policy)

    checks: List[Dict[str, Any]] = []
    release_pass = True

    baseline_cases = case_ids(baseline)
    candidate_cases = case_ids(candidate)
    if policy.get("require_same_case_ids", True):
        same = baseline_cases == candidate_cases
        checks.append(
            {
                "check": "same_case_ids",
                "status": "PASS" if same else "FAIL",
                "baseline_n": len(baseline_cases),
                "candidate_n": len(candidate_cases),
                "missing_in_candidate": sorted(baseline_cases - candidate_cases),
                "extra_in_candidate": sorted(candidate_cases - baseline_cases),
            }
        )
        release_pass = release_pass and same

    baseline_critical = count_critical_errors(baseline)
    candidate_critical = count_critical_errors(candidate)
    cpol = policy.get("critical_error_policy", {})
    max_candidate = int(cpol.get("max_candidate_errors", 0))
    allow_increase = bool(cpol.get("allow_increase", False))
    critical_ok = candidate_critical <= max_candidate and (allow_increase or candidate_critical <= baseline_critical)
    checks.append(
        {
            "check": "critical_errors",
            "status": "PASS" if critical_ok else "FAIL",
            "baseline": baseline_critical,
            "candidate": candidate_critical,
            "max_candidate_errors": max_candidate,
            "allow_increase": allow_increase,
        }
    )
    release_pass = release_pass and critical_ok

    metric_report: List[Dict[str, Any]] = []
    for spec in policy.get("metrics", []):
        base_avg, base_n = metric_average(baseline, spec)
        cand_avg, cand_n = metric_average(candidate, spec)
        required = bool(spec.get("required", True))
        min_delta = float(spec.get("min_delta", 0.0))

        if base_avg is None or cand_avg is None:
            status = "FAIL" if required else "SKIP"
            delta = None
        else:
            delta = cand_avg - base_avg
            status = "PASS" if delta >= min_delta else "FAIL"

        metric_report.append(
            {
                "name": spec.get("name"),
                "path": spec.get("path"),
                "baseline": base_avg,
                "candidate": cand_avg,
                "delta": delta,
                "min_delta": min_delta,
                "baseline_n": base_n,
                "candidate_n": cand_n,
                "required": required,
                "status": status,
            }
        )
        if status == "FAIL":
            release_pass = False

    report = {
        "policy_version": policy.get("version", "unknown"),
        "release_gate": "PASS" if release_pass else "FAIL",
        "baseline_rows": len(baseline),
        "candidate_rows": len(candidate),
        "hard_checks": checks,
        "metrics": metric_report,
        "principle": "average gains cannot override a new critical medical safety error",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not release_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
