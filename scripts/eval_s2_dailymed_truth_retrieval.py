#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def section_is_gold(section: dict, test: dict):
    hay = ((section.get("title") or "") + " " + (section.get("text_preview") or "")).lower()
    title = (section.get("title") or "").lower()
    title_ok = any(t.lower() in title for t in test.get("acceptable_section_title_contains", []))
    groups_ok = all(any(term.lower() in hay for term in group) for group in test.get("must_contain_groups", []))
    return title_ok and groups_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-version-consistency", type=float, default=1.0)
    ap.add_argument("--min-recall-at-3", type=float, default=1.0)
    ap.add_argument("--min-recall-at-1", type=float, default=0.66)
    args = ap.parse_args()

    suite = load(args.suite)
    tests = {t["test_id"]: t for t in suite["tests"]}
    rows = load(args.runs)["results"]
    available = [r for r in rows if r.get("execution_status") == "OK"]
    infra_counts = Counter(r.get("execution_status") for r in rows if r.get("execution_status") != "OK")

    version_ok = 0
    r1 = r3 = 0
    failures = []
    for row in available:
        test = tests[row["test_id"]]
        v_ok = bool(row.get("version_consistent"))
        version_ok += int(v_ok)
        top = row.get("top_sections", [])
        hit1 = bool(top) and section_is_gold(top[0], test)
        hit3 = any(section_is_gold(s, test) for s in top[:3])
        r1 += int(hit1)
        r3 += int(hit3)
        labels = []
        if not v_ok:
            labels.append("CURRENT_VERSION_MISMATCH")
        if not hit3:
            labels.append("CRITICAL_PASSAGE_MISS_AT_3")
        elif not hit1:
            labels.append("CRITICAL_PASSAGE_NOT_TOP1")
        if labels:
            failures.append({
                "test_id": row["test_id"],
                "drug": test["drug"],
                "latest_history_entry": row.get("latest_history_entry"),
                "xml_version": row.get("xml_version"),
                "top_sections": row.get("top_sections", [])[:3],
                "labels": labels,
            })

    n = len(rows)
    a = len(available)
    metrics = {
        "n_tests": n,
        "source_availability_rate": a / n if n else 0.0,
        "current_version_consistency_rate_given_available": version_ok / a if a else 0.0,
        "critical_passage_recall_at_1_given_available": r1 / a if a else 0.0,
        "critical_passage_recall_at_3_given_available": r3 / a if a else 0.0,
        "infrastructure_failure_counts": dict(infra_counts),
    }
    checks = {
        "version_consistency": metrics["current_version_consistency_rate_given_available"] >= args.min_version_consistency,
        "passage_r1": metrics["critical_passage_recall_at_1_given_available"] >= args.min_recall_at_1,
        "passage_r3": metrics["critical_passage_recall_at_3_given_available"] >= args.min_recall_at_3,
    }
    report = {
        "benchmark_id": suite["benchmark_id"],
        "metrics": metrics,
        "gate_checks": checks,
        "release_gate": "PASS" if a == n and all(checks.values()) else "FAIL",
        "failures": failures,
        "interpretation": "Version consistency compares DailyMed history with the current SPL XML version. Passage Recall@K asks whether a preregistered critical section appears within the top K ranked sections."
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["release_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
