#!/usr/bin/env python3
"""Materialize GroundSignal S5 benchmark cases with immutable partition provenance.

Raw case JSON remains a design source. This boundary joins each case to its family
manifest and suite contract so downstream consumers cannot lose family/split
metadata by reading a case file in isolation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER_VERSION = "s5-materializer-v0.1.1"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_decision_contract(case: dict[str, Any]) -> None:
    graph_eval = case.get("graph_eval")
    exemption = case.get("decision_contract_exemption")
    required = ("required_node_ids", "required_edge_ids", "expected_reasoning_path")
    if isinstance(graph_eval, dict) and all(k in graph_eval for k in required):
        return
    if isinstance(exemption, dict) and exemption.get("type") and exemption.get("rationale"):
        return
    raise ValueError(
        f"{case.get('case_id')}: missing decision contract; require graph_eval fields "
        f"{required} or a typed decision_contract_exemption"
    )


def materialize(suite_path: Path, root: Path, out_dir: Path) -> dict[str, Any]:
    suite = load_json(suite_path)
    suite_id = str(suite.get("suite_id") or "")
    if not suite_id:
        raise ValueError("suite_id is required")
    family_ids = [str(x) for x in suite.get("family_ids") or []]
    if not family_ids:
        raise ValueError("family_ids must be non-empty")
    allowed_training = {str(x) for x in suite.get("allowed_training_splits") or []}
    prohibited = {str(x) for x in suite.get("prohibited_training_splits") or []}
    if allowed_training & prohibited:
        raise ValueError("training split sets overlap")

    out_dir.mkdir(parents=True, exist_ok=True)
    split_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for family_id in family_ids:
        family_dir = root / family_id
        manifest_path = family_dir / "manifest.json"
        manifest = load_json(manifest_path)
        if manifest.get("family_id") != family_id:
            raise ValueError(f"{manifest_path}: family_id mismatch")
        manifest_sha = sha256_file(manifest_path)

        for ref in manifest.get("cases") or []:
            case_id = str(ref.get("case_id") or "")
            split = str(ref.get("split") or "")
            variant_type = str(ref.get("variant_type") or "")
            rel = str(ref.get("path") or "")
            if not case_id or not split or not rel:
                raise ValueError(f"{manifest_path}: incomplete case reference {ref!r}")
            if case_id in seen:
                raise ValueError(f"duplicate case_id across suite: {case_id}")
            seen.add(case_id)
            case_path = family_dir / rel
            case = load_json(case_path)
            if case.get("case_id") != case_id:
                raise ValueError(f"{case_path}: case_id mismatch")
            validate_decision_contract(case)

            materialized = deepcopy(case)
            materialized["benchmark_provenance"] = {
                "stage": "S5",
                "suite_id": suite_id,
                "family_id": family_id,
                "split": split,
                "variant_type": variant_type,
                "evidence_class": suite.get("evidence_class"),
                "fresh_evidence": bool(suite.get("fresh_evidence", False)),
                "source_snapshot_commit": suite.get("source_snapshot_commit"),
                "source_manifest_path": manifest_path.relative_to(ROOT).as_posix(),
                "source_case_path": case_path.relative_to(ROOT).as_posix(),
                "source_manifest_sha256": manifest_sha,
                "source_case_sha256": sha256_file(case_path),
                "materializer_version": MATERIALIZER_VERSION,
                "training_eligible": split in allowed_training and split not in prohibited,
            }
            target = out_dir / family_id / f"{case_id}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(materialized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            split_counts[split] += 1
            rows.append({
                "case_id": case_id,
                "family_id": family_id,
                "split": split,
                "training_eligible": materialized["benchmark_provenance"]["training_eligible"],
                "path": target.relative_to(out_dir).as_posix(),
                "source_case_sha256": materialized["benchmark_provenance"]["source_case_sha256"],
            })

    summary = {
        "stage": "S5",
        "materializer_version": MATERIALIZER_VERSION,
        "suite_id": suite_id,
        "evidence_class": suite.get("evidence_class"),
        "fresh_evidence": bool(suite.get("fresh_evidence", False)),
        "source_snapshot_commit": suite.get("source_snapshot_commit"),
        "family_count": len(family_ids),
        "case_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "training_eligible_count": sum(1 for r in rows if r["training_eligible"]),
        "training_blocked_count": sum(1 for r in rows if not r["training_eligible"]),
        "cases": rows,
    }
    (out_dir / "materialization-manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", type=Path, required=True)
    p.add_argument("--root", type=Path, default=ROOT / "medical/case-families")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    summary = materialize(args.suite, args.root, args.out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
