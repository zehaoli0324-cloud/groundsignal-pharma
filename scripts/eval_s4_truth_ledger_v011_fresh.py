#!/usr/bin/env python3
"""Independent fresh evaluator for S4 truth-ledger v0.1.1.

The suite is valid as fresh evidence only when the implementation and its v0.1
base blobs match the pre-declared frozen Git objects. The evaluator checks both
case expectations and generic state invariants after every state transition.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from s4_truth_ledger_v011 import TruthLedger, VERSION

FROZEN_IMPLEMENTATION_COMMIT = "8d0406df9bb91b16d3201e2b0cf97a0f084e1dad"
FROZEN_IMPLEMENTATION_BLOB = "3063927fb22c711ee35f6d629d61284455363cd5"
FROZEN_BASE_V01_BLOB = "860e8b38131e74d9dc06160bd95ade8bd04e77df"
REQUIRED_TAGS = (
    "temporal",
    "contradiction",
    "frontier_closure",
    "scope",
    "rollback",
    "safety",
    "partition",
    "provenance",
    "long_chain",
    "late_arrival",
)


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


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


def counts(ledger: TruthLedger):
    vals = list(ledger.edges.values())
    summary = ledger.summary()
    return {
        "edge_count": len(vals),
        "active_count": sum(e["lifecycle_status"] == "ACTIVE" for e in vals),
        "contested_count": sum(e["lifecycle_status"] == "CONTESTED" for e in vals),
        "superseded_count": sum(e["lifecycle_status"] == "SUPERSEDED" for e in vals),
        "stale_active": summary["stale_active_edge_count"],
        "unresolved_contradiction_slots": len(summary["unresolved_contradiction_slots"]),
        "active_objects": sorted(e["object_id"] for e in vals if e["lifecycle_status"] == "ACTIVE"),
        "max_provenance_on_any_edge": max((len(e.get("provenance", [])) for e in vals), default=0),
    }


def state_invariant_errors(ledger: TruthLedger):
    errors = []
    edges = ledger.edges
    by_slot = defaultdict(list)
    for edge in edges.values():
        by_slot[edge["slot_id"]].append(edge)

    seen = defaultdict(list)
    for edge in edges.values():
        seen[(edge["claim_id"], edge["effective_at"])].append(edge["edge_id"])
    for key, ids in seen.items():
        if len(ids) > 1:
            errors.append({"type": "DUPLICATE_CLAIM_DATE", "key": list(key), "edge_ids": sorted(ids)})

    for slot_id, slot_edges in by_slot.items():
        current = [e for e in slot_edges if e["lifecycle_status"] in {"ACTIVE", "CONTESTED"}]
        current_dates = sorted({e["effective_at"] for e in current})
        active = [e for e in current if e["lifecycle_status"] == "ACTIVE"]
        contested = [e for e in current if e["lifecycle_status"] == "CONTESTED"]

        if len(current_dates) > 1:
            errors.append({"type": "MULTI_DATE_CURRENT_FRONTIER", "slot_id": slot_id, "dates": current_dates})
        if len(active) > 1:
            errors.append({"type": "MULTI_ACTIVE_FRONTIER", "slot_id": slot_id, "edge_ids": sorted(e["edge_id"] for e in active)})
        if active and contested:
            errors.append({"type": "ACTIVE_CONTESTED_COEXIST", "slot_id": slot_id})
        if contested and len(contested) < 2:
            errors.append({"type": "SINGLETON_CONTESTED", "slot_id": slot_id})

        if contested:
            ids = {e["edge_id"] for e in contested}
            for edge in contested:
                expected = ids - {edge["edge_id"]}
                actual = set(edge.get("conflicts_with", [])) & ids
                if actual != expected:
                    errors.append({
                        "type": "INCOMPLETE_CONTESTED_CLIQUE",
                        "slot_id": slot_id,
                        "edge_id": edge["edge_id"],
                        "expected": sorted(expected),
                        "got": sorted(actual),
                    })

    for edge in edges.values():
        for other_id in edge.get("conflicts_with", []):
            other = edges.get(other_id)
            if other is None:
                errors.append({"type": "DANGLING_CONFLICT_REF", "edge_id": edge["edge_id"], "other_id": other_id})
                continue
            if edge["edge_id"] not in other.get("conflicts_with", []):
                errors.append({"type": "ASYMMETRIC_CONFLICT_REF", "edge_id": edge["edge_id"], "other_id": other_id})
            if edge["slot_id"] != other["slot_id"] or edge["effective_at"] != other["effective_at"]:
                errors.append({"type": "CROSS_SLOT_OR_DATE_CONFLICT", "edge_id": edge["edge_id"], "other_id": other_id})

    for edge in edges.values():
        if edge["lifecycle_status"] != "SUPERSEDED":
            continue
        target_id = edge.get("superseded_by")
        target = edges.get(target_id) if target_id else None
        if target is None:
            errors.append({"type": "MISSING_SUPERSEDED_BY", "edge_id": edge["edge_id"], "target_id": target_id})
            continue
        if target["slot_id"] != edge["slot_id"]:
            errors.append({"type": "CROSS_SLOT_SUPERSESSION", "edge_id": edge["edge_id"], "target_id": target_id})
        if target["effective_at"] < edge["effective_at"]:
            errors.append({"type": "BACKWARD_TIME_SUPERSESSION", "edge_id": edge["edge_id"], "target_id": target_id})

    if ledger.summary()["stale_active_edge_count"]:
        errors.append({"type": "STALE_ACTIVE_PRESENT", "count": ledger.summary()["stale_active_edge_count"]})
    return errors


def run_case(case, base_event):
    ledger = TruthLedger(graph_partition=case.get("graph_partition", "clinical_external"))
    actions = []
    rejection_reasons = []
    checkpoints = {}
    rollback_exact = None
    invariant_errors = []

    for index, step in enumerate(case["steps"]):
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
            rollback_exact = ledger.state_hash() == checkpoints[step["name"]]
            actions.append("CHECKPOINT_MATCH" if rollback_exact else "CHECKPOINT_MISMATCH")
        else:
            raise ValueError(f"unknown op: {op}")

        for err in state_invariant_errors(ledger):
            invariant_errors.append({"step_index": index, "op": op, **err})

    got = counts(ledger)
    got.update({
        "actions": actions,
        "rejections": len(rejection_reasons),
        "rejection_reasons": rejection_reasons,
        "rollback_exact": rollback_exact,
        "invariant_violation_count": len(invariant_errors),
    })

    failures = []
    for key, expected in case["expect"].items():
        if key == "min_provenance_on_any_edge":
            if got["max_provenance_on_any_edge"] < expected:
                failures.append({"field": key, "expected": f">={expected}", "got": got["max_provenance_on_any_edge"]})
            continue
        if got.get(key) != expected:
            failures.append({"field": key, "expected": expected, "got": got.get(key)})
    if invariant_errors:
        failures.append({"field": "state_invariants", "expected": "0 violations", "got": invariant_errors})

    return {
        "case_id": case["case_id"],
        "name": case["name"],
        "tags": case.get("tags", []),
        "must_reject": bool(case.get("must_reject", False)),
        "passed": not failures,
        "observed": got,
        "invariant_errors": invariant_errors,
        "failures": failures,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--implementation", default="scripts/s4_truth_ledger_v011.py")
    ap.add_argument("--base-v01", default="scripts/s4_truth_ledger_v01.py")
    args = ap.parse_args()

    suite = load(args.suite)
    integrity = {
        "fresh_flag": suite.get("fresh_heldout") is True and suite.get("split") == "fresh_heldout",
        "created_after_freeze": suite.get("created_after_implementation_freeze") is True,
        "implementation_commit_matches": suite.get("implementation_freeze_commit") == FROZEN_IMPLEMENTATION_COMMIT,
        "implementation_blob_declared": suite.get("implementation_blob_sha") == FROZEN_IMPLEMENTATION_BLOB,
        "base_blob_declared": suite.get("base_v01_blob_sha") == FROZEN_BASE_V01_BLOB,
        "implementation_blob_runtime": git_blob_sha(Path(args.implementation)) == FROZEN_IMPLEMENTATION_BLOB,
        "base_blob_runtime": git_blob_sha(Path(args.base_v01)) == FROZEN_BASE_V01_BLOB,
        "version_matches": VERSION == "S4-truth-ledger-v0.1.1",
    }

    rows = [run_case(case, suite["base_event"]) for case in suite["cases"]]
    tag_rows = defaultdict(list)
    for row in rows:
        for tag in row["tags"]:
            tag_rows[tag].append(row)
    tag_accuracy = {
        tag: sum(r["passed"] for r in tagged) / len(tagged)
        for tag, tagged in sorted(tag_rows.items())
    }
    must_reject = [r for r in rows if r["must_reject"]]
    passed = sum(r["passed"] for r in rows)
    invariant_total = sum(r["observed"]["invariant_violation_count"] for r in rows)
    stale_total = sum(r["observed"]["stale_active"] for r in rows)

    metrics = {
        "benchmark_id": suite["benchmark_id"],
        "split": suite["split"],
        "fresh_heldout": True,
        "fresh_evidence": True,
        "first_observation": True,
        "implementation_version": VERSION,
        "implementation_freeze_commit": FROZEN_IMPLEMENTATION_COMMIT,
        "implementation_blob_sha": FROZEN_IMPLEMENTATION_BLOB,
        "base_v01_blob_sha": FROZEN_BASE_V01_BLOB,
        "n_cases": len(rows),
        "passed_cases": passed,
        "failed_cases": len(rows) - passed,
        "case_accuracy": passed / len(rows) if rows else 0.0,
        "tag_accuracy": tag_accuracy,
        "must_reject_cases": len(must_reject),
        "high_risk_false_accept_count": sum(r["observed"]["rejections"] == 0 for r in must_reject),
        "stale_active_edge_count": stale_total,
        "invariant_violation_count": invariant_total,
    }
    criteria = suite["release_criteria"]
    gate_checks = {
        "fresh_integrity": all(integrity.values()),
        "case_accuracy": metrics["case_accuracy"] >= criteria["min_case_accuracy"],
        "required_tag_coverage": all(tag in tag_accuracy for tag in REQUIRED_TAGS),
        "required_tag_accuracy": all(tag_accuracy.get(tag, 0.0) >= criteria["required_tag_accuracy"] for tag in REQUIRED_TAGS),
        "high_risk_false_accept_count": metrics["high_risk_false_accept_count"] <= criteria["max_high_risk_false_accept_count"],
        "stale_active_edge_count": stale_total <= criteria["max_stale_active_edge_count"],
        "invariant_violation_count": invariant_total <= criteria["max_invariant_violation_count"],
    }
    release_gate = "PASS" if all(gate_checks.values()) else "FAIL"
    failures = [r for r in rows if not r["passed"]]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({
        "integrity": integrity,
        "metrics": metrics,
        "gate_checks": gate_checks,
        "release_gate": release_gate,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "case-results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "integrity": integrity,
        "metrics": metrics,
        "gate_checks": gate_checks,
        "release_gate": release_gate,
    }, ensure_ascii=False, indent=2))
    return 0 if release_gate == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
