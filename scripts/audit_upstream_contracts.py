#!/usr/bin/env python3
"""A1 offline counterexamples; exit 2 means a product invariant failed.

Only authored synthetic data and the public proposition registry are used.
This is an audit probe, not a new clinical benchmark or a release gate.
Run with a new --out directory; original reports are never overwritten.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_medical_knowledge_graph as graph
import eval_s2_live_retrieval as retrieval_eval
import s2_live_retrieval as retrieval
import s3_semantic_extractor as extraction
from s4_truth_ledger_v011 import TruthLedger
import validate_medical_knowledge_sources as sources


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def invoke_main(fn, args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.object(sys, "argv", [fn.__module__, *args]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = fn()
    return {"exit_code": code or 0, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


def event():
    return {"event_id": "audit-event", "proposition": {
        "subject_id": "synthetic:A", "predicate": "HAS_STATUS", "object_id": "synthetic:B",
        "effective_at": "2026-01-01", "polarity": "POSITIVE"},
        "provenance": {"source_id": "synthetic-source", "passage_id": "p1", "locator": "line 1", "source_version": "v1"},
        "s3_relation": "DIRECT_SUPPORT", "review_status": "SOURCE_VERIFIED", "source_scope": "synthetic_controlled"}


def probe():
    rows = []

    def record(pid, finding, expected, actual, passed):
        rows.append({"probe_id": pid, "finding_id": finding, "expected": expected,
                     "actual": actual, "invariant_pass": bool(passed)})

    ledger = TruthLedger(graph_partition="benchmark_synthetic")
    malformed = event(); del malformed["event_id"]
    before = ledger.state_hash()
    error = None
    try:
        ledger.ingest(malformed)
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
    after = ledger.state_hash()
    rollback = ledger.rollback_last()
    record("ledger_missing_event_id", "A1-001", "Invalid event leaves state unchanged",
           {"exception": error, "state_changed": before != after, "edge_count": len(ledger.edges), "rollback": rollback}, before == after)

    valid = TruthLedger(graph_partition="benchmark_synthetic")
    before = valid.state_hash(); valid.ingest(event()); valid.rollback_last()
    record("ledger_valid_rollback", None, "Valid event rollback restores prior state", {"state_restored": before == valid.state_hash()}, before == valid.state_hash())
    wrong = TruthLedger(graph_partition="clinical_external").ingest(event())
    record("ledger_explicit_synthetic_rejected", None, "Explicit synthetic event cannot enter external partition", wrong, wrong["action"] == "REJECTED")

    edge = {"edge_id": "e1", "subject_id": "n1", "predicate": "HAS_STATUS", "object_id": "n2",
            "status": "OBSERVED", "polarity": "POSITIVE", "source_passage_ids": ["p1"],
            "locator": "line 1", "review_status": "source_verified", "evidence_scope": "scope A"}
    second = {**edge, "polarity": "NEGATIVE", "source_passage_ids": ["p2"], "locator": "line 2",
              "review_status": "unreviewed", "evidence_scope": "scope B"}
    store = {}; error = None
    try:
        graph.merge_edge(store, copy.deepcopy(edge), "fixture:a")
        graph.merge_edge(store, copy.deepcopy(second), "fixture:b")
    except ValueError as exc:
        error = str(exc)
    record("graph_conflicting_evidence", "A1-002", "Reject incompatible semantic/evidence attributes, or retain both explicitly",
           {"error": error, "merged": store}, error is not None or len(store) == 2)
    store = {}; error = None
    try:
        graph.merge_edge(store, copy.deepcopy(edge), "a")
        graph.merge_edge(store, {**edge, "object_id": "other"}, "b")
    except ValueError as exc:
        error = str(exc)
    record("graph_endpoint_collision_rejected", None, "Existing triple collision check rejects different endpoints", {"error": error}, error is not None)

    registry = json.loads((ROOT / "medical/stage-evals/S3/proposition-registry-v0.1.json").read_text())
    proposition = {"subject": "synthetic item", "predicate": "HAS_STATUS", "object": "synthetic status", "polarity": "POSITIVE",
                   "conditions": [], "population": None, "confidence": 1.0, "source_span": "synthetic item has synthetic status"}
    for pid, change in [("semantic_null_subject", {"subject": None}),
                        ("semantic_string_threshold", {"conditions": [{"variable": "egfr", "operator": "LT", "value": "not-a-number"}]})]:
        checked = extraction.validate_semantic_output({"propositions": [{**proposition, **change}], "abstain": False, "unresolved_spans": []}, registry)
        record(pid, "A1-004", "Schema-invalid proposition cannot be accepted", checked, not checked["propositions"])
    checked = extraction.validate_semantic_output({"propositions": [{**proposition, "predicate": "UNREGISTERED"}], "abstain": False, "unresolved_spans": []}, registry)
    record("semantic_unknown_predicate_rejected", None, "Unregistered predicate triggers abstention", checked, checked["abstain"] and not checked["propositions"])

    with tempfile.TemporaryDirectory(prefix="groundsignal-a1-synthetic-") as temp:
        root = Path(temp)
        family = root / "medical/case-families/synthetic-audit"; family.mkdir(parents=True)
        dump(family / "graph.json", {"nodes": [{"node_id": "n1", "node_type": "SYNTHETIC", "label": "synthetic item"}], "edges": [edge]})
        run = invoke_main(graph.main, ["--root", str(root), "--out", "graph-result.json"])
        built = json.loads((root / "graph-result.json").read_text())
        node_ids = {n["node_id"] for n in built["nodes"]}
        dangling = [e["edge_id"] for e in built["edges"] if e["subject_id"] not in node_ids or e["object_id"] not in node_ids]
        record("graph_dangling_endpoint", "A1-003", "Graph build rejects dangling endpoints", {"exit_code": run["exit_code"], "dangling_edges": dangling}, run["exit_code"] != 0)

        dump(root / "registry.json", {"sources": []})
        run = invoke_main(sources.main, ["--registry", str(root / "registry.json"), "--registry-supplement", str(root / "absent-supplement"),
            "--case-root", str(root / "absent-cases"), "--backbone", str(root / "absent-backbone"), "--strict-hosts"])
        record("source_validation_empty_input", "A1-006", "Required missing inputs cannot yield successful validation", run, run["exit_code"] != 0)

        suite = {"benchmark_id": "synthetic-audit-current", "tests": [{"test_id": "test-1", "source_id": "RXNORM", "adapter": "rxnorm_rxcui", "expect": {"min_ids": 1}}]}
        wrong_runs = {"benchmark_id": "synthetic-audit-stale", "results": [
            {"test_id": "test-1", "source_id": "RXNORM", "adapter": "rxnorm_rxcui", "execution_status": "NETWORK_ERROR"},
            {"test_id": "test-1", "source_id": "WRONG_SOURCE", "adapter": "wrong-adapter", "execution_status": "OK", "result": {"rxnorm_ids": ["synthetic-id"]}}]}
        dump(root / "suite.json", suite); dump(root / "runs.json", wrong_runs)
        run = invoke_main(retrieval_eval.main, ["--suite", str(root / "suite.json"), "--runs", str(root / "runs.json"), "--out", str(root / "retrieval-report.json")])
        report = json.loads((root / "retrieval-report.json").read_text())
        record("retrieval_mismatched_duplicate_runs", "A1-005", "Reject duplicate test IDs and wrong suite/source/adapter binding", {"suite": suite, "runs": wrong_runs, "exit_code": run["exit_code"], "report": report}, run["exit_code"] != 0)

    error = None
    try:
        retrieval.run_one({"test_id": "invalid-config", "source_id": "synthetic", "adapter": "unknown-adapter"})
    except KeyError as exc:
        error = str(exc)
    record("retrieval_bad_adapter_isolated", "A1-007", "Malformed adapter gets a structured error without aborting the batch", {"uncaught_key_error": error}, error is None)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    argv = list(sys.argv)
    # Fail closed if a future imported path attempts networking during probes.
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("A1 probes prohibit network")), patch.object(socket, "create_connection", side_effect=RuntimeError("A1 probes prohibit network")):
        rows = probe()
    failed = sum(not row["invariant_pass"] for row in rows)
    result = {"scope": "A1 upstream authored synthetic counterexamples", "checks": len(rows), "invariants_passed": len(rows)-failed,
              "invariants_failed": failed, "project_audit_complete": False, "project_tests_complete": False,
              "external_model_calls": 0, "real_case_runs": 0, "rows": rows}
    dump(out / "observations.json", result)
    tracked = ["scripts/audit_upstream_contracts.py", "scripts/build_medical_knowledge_graph.py", "scripts/eval_s2_live_retrieval.py",
               "scripts/s2_live_retrieval.py", "scripts/s3_semantic_extractor.py", "scripts/s4_truth_ledger_v01.py",
               "scripts/s4_truth_ledger_v011.py", "scripts/validate_medical_knowledge_sources.py", "medical/stage-evals/S3/proposition-registry-v0.1.json"]
    dump(out / "run-manifest.json", {"argv": [sys.executable, *argv], "cwd": str(Path.cwd()), "python": platform.python_version(),
        "input_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_git_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "probe_script_uncommitted_at_first_execution": True,
        "file_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked},
        "input_scope": "new authored synthetic objects; public proposition registry only", "network": "blocked in process", "output": str(out),
        "expected_exit_code": 2, "actual_exit_code": 2 if failed else 0, "result": "FAIL" if failed else "PASS",
        "interpretation": "Exit 2 records observed engineering invariant failures, not a passing product test."})
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
