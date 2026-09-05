#!/usr/bin/env python3
"""Evaluate S2 live retrieval output.

External availability errors and semantic retrieval errors are reported as
separate metric families. A semantic release gate is evaluated only on tests
whose source call completed successfully.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_semantics(test, run):
    if run.get("execution_status") != "OK":
        return False, [run.get("execution_status", "UNKNOWN_INFRA_ERROR")]

    result = run.get("result", {})
    expect = test.get("expect", {})
    adapter = test["adapter"]
    failures = []

    if adapter == "dailymed_spls":
        rows = result.get("records", [])
        if result.get("result_count", 0) < expect.get("min_results", 1):
            failures.append("EMPTY_RESULT")
        terms = [x.upper() for x in expect.get("title_contains_any", [])]
        if terms and not any(any(t in (r.get("title") or "").upper() for t in terms) for r in rows):
            failures.append("EXPECTED_CONTENT_NOT_FOUND")
        if expect.get("require_setid") and rows and not any(r.get("setid") for r in rows):
            failures.append("MISSING_IDENTIFIER")
        if expect.get("require_published_date") and rows and not any(r.get("published_date") for r in rows):
            failures.append("MISSING_VERSION_DATE")

    elif adapter == "openfda_drugsfda":
        if result.get("result_count", 0) < expect.get("min_results", 1):
            failures.append("EMPTY_RESULT")
        app = expect.get("application_number")
        if app and app not in (result.get("application_numbers") or []):
            failures.append("EXPECTED_IDENTIFIER_NOT_FOUND")

    elif adapter == "clinicaltrials_study":
        if result.get("nct_id") != expect.get("nct_id"):
            failures.append("EXPECTED_IDENTIFIER_NOT_FOUND")
        if expect.get("overall_status") and result.get("overall_status") != expect.get("overall_status"):
            failures.append("WRONG_CURRENT_STATUS")

    elif adapter == "rxnorm_rxcui":
        if len(result.get("rxnorm_ids") or []) < expect.get("min_ids", 1):
            failures.append("EMPTY_RESULT")

    elif adapter == "pubmed_esearch":
        if expect.get("pmid") not in (result.get("pmids") or []):
            failures.append("EXPECTED_IDENTIFIER_NOT_FOUND")

    elif adapter == "openfda_faers":
        total = result.get("total")
        if total is None:
            failures.append("MISSING_TOTAL")
        elif total < expect.get("min_total", 1):
            failures.append("EMPTY_RESULT")

    return not failures, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="medical/stage-evals/S2/live-retrieval-v0.2.json")
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-source-availability", type=float, default=0.80)
    ap.add_argument("--min-semantic-success", type=float, default=0.90)
    ap.add_argument("--max-critical-live-miss", type=float, default=0.0)
    args = ap.parse_args()

    suite = load(args.suite)
    runs = {r["test_id"]: r for r in load(args.runs)["results"]}

    infra_counts = Counter()
    semantic_counts = Counter()
    details = []
    available = semantic_success = 0
    high_risk_available = high_risk_miss = 0

    for test in suite["tests"]:
        run = runs.get(test["test_id"], {"execution_status": "MISSING_RUN"})
        status = run.get("execution_status", "MISSING_RUN")
        if status == "OK":
            available += 1
            if test.get("high_risk"):
                high_risk_available += 1
            ok, labels = evaluate_semantics(test, run)
            semantic_success += int(ok)
            if test.get("high_risk") and not ok:
                high_risk_miss += 1
            for label in labels:
                semantic_counts[label] += 1
        else:
            ok, labels = False, [status]
            infra_counts[status] += 1

        details.append({
            "test_id": test["test_id"],
            "source_id": test["source_id"],
            "execution_status": status,
            "semantic_ok": ok if status == "OK" else None,
            "labels": labels,
            "latency_ms": run.get("latency_ms"),
            "result": run.get("result") if status == "OK" else None,
            "error": run.get("error") if status != "OK" else None,
        })

    n = len(suite["tests"])
    source_availability = available / n if n else 0
    semantic_rate = semantic_success / available if available else 0
    critical_rate = high_risk_miss / high_risk_available if high_risk_available else 0

    metrics = {
        "n_tests": n,
        "source_availability_rate": source_availability,
        "semantic_success_rate_given_available": semantic_rate,
        "critical_live_miss_rate_given_available": critical_rate,
        "available_tests": available,
        "high_risk_available_tests": high_risk_available,
        "infrastructure_failure_counts": dict(infra_counts),
        "semantic_failure_counts": dict(semantic_counts),
    }
    gate_checks = {
        "source_availability": source_availability >= args.min_source_availability,
        "semantic_success": semantic_rate >= args.min_semantic_success,
        "no_critical_live_miss": critical_rate <= args.max_critical_live_miss,
    }
    report = {
        "benchmark_id": suite["benchmark_id"],
        "metrics": metrics,
        "gate_checks": gate_checks,
        "release_gate": "PASS" if all(gate_checks.values()) else "FAIL",
        "details": details,
        "interpretation_rule": "NETWORK/HTTP/PARSE failures are infrastructure availability failures; EMPTY/IDENTIFIER/CONTENT/STATUS failures are semantic retrieval failures."
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "gate_checks": gate_checks, "release_gate": report["release_gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
