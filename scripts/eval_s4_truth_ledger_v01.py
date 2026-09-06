#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from s4_truth_ledger_v01 import TruthLedger


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def drop_path(doc, dotted):
    parts = dotted.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur.get(part, {})
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def materialize_event(base_event, step):
    event = deep_merge(base_event, step.get("event", {}))
    for dotted in step.get("drop", []):
        drop_path(event, dotted)
    return event


def _counts(ledger: TruthLedger):
    vals = list(ledger.edges.values())
    return {
        "edge_count": len(vals),
        "active_count": sum(e["lifecycle_status"] == "ACTIVE" for e in vals),
        "contested_count": sum(e["lifecycle_status"] == "CONTESTED" for e in vals),
        "superseded_count": sum(e["lifecycle_status"] == "SUPERSEDED" for e in vals),
        "stale_active": ledger.summary()["stale_active_edge_count"],
        "unresolved_contradiction_slots": len(ledger.summary()["unresolved_contradiction_slots"]),
        "active_objects": sorted(e["object_id"] for e in vals if e["lifecycle_status"] == "ACTIVE"),
        "max_provenance_on_any_edge": max((len(e.get("provenance", [])) for e in vals), default=0),
    }


def run_case(case, base_event):
    ledger = TruthLedger(graph_partition=case.get("graph_partition", "clinical_external"))
    actions = []
    rejection_reasons = []
    checkpoints = {}
    rollback_exact = None

    for step in case["steps"]:
        op = step["op"]
        if op == "ingest":
            result = ledger.ingest(materialize_event(base_event, step))
            actions.append(result["action"])
            if result["action"] == "REJECTED":
                rejection_reasons.append(result["reason"])
        elif op == "checkpoint":
            checkpoints[step["name"]] = ledger.state_hash()
            actions.append("CHECKPOINT")
        elif op == "rollback_last":
            result = ledger.rollback_last()
            actions.append(result["action"])
        elif op == "assert_checkpoint":
            expected = checkpoints[step["name"]]
            rollback_exact = ledger.state_hash() == expected
            actions.append("CHECKPOINT_MATCH" if rollback_exact else "CHECKPOINT_MISMATCH")
        else:
            raise ValueError(f"unknown op: {op}")

    got = _counts(ledger)
    got.update({
        "actions": actions,
        "rejections": len(rejection_reasons),
        "rejection_reasons": rejection_reasons,
        "rollback_exact": rollback_exact,
    })

    failures = []
    for key, expected in case["expect"].items():
        if key == "min_provenance_on_any_edge":
            if got["max_provenance_on_any_edge"] < expected:
                failures.append({"field": key, "expected": f">={expected}", "got": got["max_provenance_on_any_edge"]})
            continue
        actual = got.get(key)
        if actual != expected:
            failures.append({"field": key, "expected": expected, "got": actual})

    return {
        "case_id": case["case_id"],
        "name": case["name"],
        "passed": not failures,
        "observed": got,
        "failures": failures,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    suite = load(args.suite)
    base_event = suite["base_event"]
    results = [run_case(case, base_event) for case in suite["cases"]]
    n = len(results)
    passed = sum(r["passed"] for r in results)
    failed = n - passed

    safety_cases = {"S4D-006", "S4D-007", "S4D-008", "S4D-012"}
    safety_rows = [r for r in results if r["case_id"] in safety_cases]
    safety_passed = sum(r["passed"] for r in safety_rows)
    rollback_rows = [r for r in results if r["case_id"] == "S4D-009"]
    contradiction_rows = [r for r in results if r["case_id"] == "S4D-005"]
    stale_total = sum(r["observed"]["stale_active"] for r in results)

    metrics = {
        "benchmark_id": suite["benchmark_id"],
        "split": suite["split"],
        "fresh_heldout": bool(suite.get("fresh_heldout", False)),
        "implementation_version": "S4-truth-ledger-v0.1",
        "n_cases": n,
        "case_accuracy": passed / n if n else 0.0,
        "passed_cases": passed,
        "failed_cases": failed,
        "safety_gate_accuracy": safety_passed / len(safety_rows) if safety_rows else 0.0,
        "high_risk_false_accept_count": sum(
            1 for r in safety_rows if r["observed"]["rejections"] == 0
        ),
        "rollback_exactness": sum(
            r["observed"]["rollback_exact"] is True for r in rollback_rows
        ) / len(rollback_rows) if rollback_rows else 0.0,
        "contradiction_preservation_accuracy": sum(r["passed"] for r in contradiction_rows) / len(contradiction_rows) if contradiction_rows else 0.0,
        "stale_active_edge_count": stale_total,
    }
    gate_checks = {
        "case_accuracy": metrics["case_accuracy"] == 1.0,
        "safety_gate_accuracy": metrics["safety_gate_accuracy"] == 1.0,
        "high_risk_false_accept_count": metrics["high_risk_false_accept_count"] == 0,
        "rollback_exactness": metrics["rollback_exactness"] == 1.0,
        "contradiction_preservation_accuracy": metrics["contradiction_preservation_accuracy"] == 1.0,
        "stale_active_edge_count": metrics["stale_active_edge_count"] == 0,
        "development_only_not_fresh": metrics["fresh_heldout"] is False and metrics["split"] == "development",
    }
    development_gate = "PASS" if all(gate_checks.values()) else "FAIL"
    failures = [r for r in results if not r["passed"]]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({
        "metrics": metrics,
        "gate_checks": gate_checks,
        "development_gate": development_gate,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "case-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"metrics": metrics, "gate_checks": gate_checks, "development_gate": development_gate}, ensure_ascii=False, indent=2))
    return 0 if development_gate == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
