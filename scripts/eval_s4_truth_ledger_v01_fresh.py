#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

from s4_truth_ledger_v01 import TruthLedger

FROZEN_IMPLEMENTATION_COMMIT = "36b9bcb63a690efe33d80c50e65dfe73bd105418"
FROZEN_IMPLEMENTATION_BLOB = "860e8b38131e74d9dc06160bd95ade8bd04e77df"

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

def run_case(case, base_event):
    ledger = TruthLedger(graph_partition=case.get("graph_partition", "clinical_external"))
    actions, rejection_reasons = [], []
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
            rollback_exact = ledger.state_hash() == checkpoints[step["name"]]
            actions.append("CHECKPOINT_MATCH" if rollback_exact else "CHECKPOINT_MISMATCH")
        else:
            raise ValueError(f"unknown op: {op}")
    got = _counts(ledger)
    got.update({"actions":actions,"rejections":len(rejection_reasons),"rejection_reasons":rejection_reasons,"rollback_exact":rollback_exact})
    failures=[]
    for key, expected in case["expect"].items():
        if key == "min_provenance_on_any_edge":
            if got["max_provenance_on_any_edge"] < expected:
                failures.append({"field":key,"expected":f">={expected}","got":got["max_provenance_on_any_edge"]})
            continue
        actual=got.get(key)
        if actual != expected:
            failures.append({"field":key,"expected":expected,"got":actual})
    return {"case_id":case["case_id"],"name":case["name"],"tags":case.get("tags",[]),"must_reject":bool(case.get("must_reject",False)),"passed":not failures,"observed":got,"failures":failures}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--suite',required=True)
    ap.add_argument('--out-dir',required=True)
    args=ap.parse_args()
    suite=load(args.suite)
    integrity={
      "fresh_flag": suite.get("fresh_heldout") is True and suite.get("split") == "fresh_heldout",
      "created_after_freeze": suite.get("created_after_implementation_freeze") is True,
      "implementation_commit_matches": suite.get("implementation_freeze_commit") == FROZEN_IMPLEMENTATION_COMMIT,
      "implementation_blob_matches": suite.get("implementation_blob_sha") == FROZEN_IMPLEMENTATION_BLOB,
    }
    results=[run_case(c,suite["base_event"]) for c in suite["cases"]]
    n=len(results); passed=sum(r["passed"] for r in results)
    tag_rows=defaultdict(list)
    for r in results:
        for tag in r["tags"]: tag_rows[tag].append(r)
    tag_accuracy={tag:sum(x["passed"] for x in rows)/len(rows) for tag,rows in sorted(tag_rows.items())}
    must_reject=[r for r in results if r["must_reject"]]
    high_risk_false_accept=sum(1 for r in must_reject if r["observed"]["rejections"] == 0)
    stale_total=sum(r["observed"]["stale_active"] for r in results)
    metrics={
      "benchmark_id":suite["benchmark_id"],"split":suite["split"],"fresh_heldout":True,
      "implementation_version":"S4-truth-ledger-v0.1","implementation_freeze_commit":FROZEN_IMPLEMENTATION_COMMIT,"implementation_blob_sha":FROZEN_IMPLEMENTATION_BLOB,
      "n_cases":n,"passed_cases":passed,"failed_cases":n-passed,"case_accuracy":passed/n if n else 0.0,
      "tag_accuracy":tag_accuracy,"must_reject_cases":len(must_reject),"high_risk_false_accept_count":high_risk_false_accept,
      "stale_active_edge_count":stale_total,
    }
    required_tags=("temporal","contradiction","scope","rollback","safety","partition","provenance")
    gate_checks={
      "fresh_integrity":all(integrity.values()),
      "case_accuracy":metrics["case_accuracy"] == 1.0,
      "required_tag_coverage":all(tag in tag_accuracy for tag in required_tags),
      "required_tag_accuracy":all(tag_accuracy.get(tag,0.0) == 1.0 for tag in required_tags),
      "high_risk_false_accept_count":high_risk_false_accept == 0,
      "stale_active_edge_count":stale_total == 0,
    }
    release_gate="PASS" if all(gate_checks.values()) else "FAIL"
    failures=[r for r in results if not r["passed"]]
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    (out/'metrics.json').write_text(json.dumps({"integrity":integrity,"metrics":metrics,"gate_checks":gate_checks,"release_gate":release_gate},ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    (out/'case-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    (out/'failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    print(json.dumps({"integrity":integrity,"metrics":metrics,"gate_checks":gate_checks,"release_gate":release_gate},ensure_ascii=False,indent=2))
    return 0 if release_gate == 'PASS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
