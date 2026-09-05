#!/usr/bin/env python3
"""Validate GroundSignal medical case-family integrity.

This validator is intentionally dependency-free so it can run in GitHub Actions.
It checks referential integrity across family manifests, cases, evidence manifests,
and graph snapshots. It does not perform clinical validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def add_error(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path}: {message}")


def validate_family(family_dir: Path, rubric_version: str) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    manifest_path = family_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"{family_dir}: missing manifest.json"], {}

    manifest = load_json(manifest_path)
    family_id = manifest.get("family_id")
    if family_id != family_dir.name:
        add_error(errors, manifest_path, f"family_id={family_id!r} does not match directory {family_dir.name!r}")

    graph_path = family_dir / str(manifest.get("graph_snapshot", ""))
    evidence_path = family_dir / str(manifest.get("evidence_manifest", ""))
    if not graph_path.is_file():
        add_error(errors, manifest_path, f"graph_snapshot does not exist: {graph_path.name}")
        graph = {"nodes": [], "edges": []}
    else:
        graph = load_json(graph_path)
    if not evidence_path.is_file():
        add_error(errors, manifest_path, f"evidence_manifest does not exist: {evidence_path.name}")
        evidence = {"claims": []}
    else:
        evidence = load_json(evidence_path)

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = [n.get("node_id") for n in nodes if n.get("node_id")]
    edge_ids = [e.get("edge_id") for e in edges if e.get("edge_id")]
    node_set, edge_set = set(node_ids), set(edge_ids)

    for kind, ids, src in (("node_id", node_ids, graph_path), ("edge_id", edge_ids, graph_path)):
        dupes = [x for x, n in Counter(ids).items() if n > 1]
        if dupes:
            add_error(errors, src, f"duplicate {kind}(s): {dupes}")

    evidence_passages = {
        claim.get("passage_id")
        for claim in evidence.get("claims", [])
        if claim.get("passage_id")
    }
    graph_passages: set[str] = set()
    for item in [*nodes, *edges]:
        graph_passages.update(p for p in item.get("source_passage_ids", []) if p)
    missing_graph_passages = sorted(graph_passages - evidence_passages)
    if missing_graph_passages:
        add_error(errors, graph_path, f"graph references passage IDs absent from evidence manifest: {missing_graph_passages}")

    cases = manifest.get("cases", [])
    case_ids = [c.get("case_id") for c in cases if c.get("case_id")]
    dupes = [x for x, n in Counter(case_ids).items() if n > 1]
    if dupes:
        add_error(errors, manifest_path, f"duplicate case_id(s): {dupes}")

    variant_types = Counter(c.get("variant_type") for c in cases)
    splits = Counter(c.get("split") for c in cases)
    if variant_types.get("heldout", 0) < 1 and splits.get("heldout", 0) < 1:
        add_error(errors, manifest_path, "family has no held-out case")

    for case_ref in cases:
        rel = case_ref.get("path")
        if not rel:
            add_error(errors, manifest_path, f"case {case_ref.get('case_id')} has no path")
            continue
        case_path = family_dir / rel
        if not case_path.is_file():
            add_error(errors, manifest_path, f"referenced case file does not exist: {rel}")
            continue
        case = load_json(case_path)
        if case.get("case_id") != case_ref.get("case_id"):
            add_error(errors, case_path, f"case_id {case.get('case_id')!r} != manifest {case_ref.get('case_id')!r}")

        scoring = case.get("scoring", {})
        if scoring.get("rubric_version") != rubric_version:
            add_error(errors, case_path, f"rubric_version must be {rubric_version!r}, got {scoring.get('rubric_version')!r}")

        snapshot = case.get("evidence_snapshot", {})
        case_passages = set(snapshot.get("allowed_passage_ids", [])) | set(snapshot.get("withheld_passage_ids", []))
        missing_case_passages = sorted(case_passages - evidence_passages)
        if missing_case_passages:
            add_error(errors, case_path, f"case references passage IDs absent from evidence manifest: {missing_case_passages}")

        graph_eval = case.get("graph_eval", {})
        missing_nodes = sorted(set(graph_eval.get("required_node_ids", [])) - node_set)
        missing_edges = sorted(set(graph_eval.get("required_edge_ids", [])) - edge_set)
        if missing_nodes:
            add_error(errors, case_path, f"required graph nodes do not exist: {missing_nodes}")
        if missing_edges:
            add_error(errors, case_path, f"required graph edges do not exist: {missing_edges}")

        if case_ref.get("split") == "heldout" and case_ref.get("variant_type") != "heldout":
            add_error(errors, manifest_path, f"{case_ref.get('case_id')} is split=heldout but variant_type={case_ref.get('variant_type')!r}")
        if case_ref.get("variant_type") == "heldout" and case_ref.get("split") != "heldout":
            add_error(errors, manifest_path, f"{case_ref.get('case_id')} is variant_type=heldout but split={case_ref.get('split')!r}")

    summary = {
        "family_id": family_id,
        "cases": len(cases),
        "variants": dict(variant_types),
        "splits": dict(splits),
        "nodes": len(nodes),
        "edges": len(edges),
        "evidence_passages": len(evidence_passages),
        "status": manifest.get("status"),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="medical/case-families", help="case-family root")
    parser.add_argument("--rubric-version", default="medical-clinical-v0.2")
    parser.add_argument("--expect-families", type=int, default=None)
    parser.add_argument("--expect-cases", type=int, default=None)
    parser.add_argument("--expect-cases-per-family", type=int, default=None)
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: case-family root does not exist: {root}", file=sys.stderr)
        return 2

    family_dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").exists())
    all_errors: list[str] = []
    summaries: list[dict[str, Any]] = []

    for family_dir in family_dirs:
        try:
            errors, summary = validate_family(family_dir, args.rubric_version)
        except ValueError as exc:
            all_errors.append(str(exc))
            continue
        all_errors.extend(errors)
        summaries.append(summary)

    total_cases = sum(s.get("cases", 0) for s in summaries)
    if args.expect_families is not None and len(summaries) != args.expect_families:
        all_errors.append(f"expected {args.expect_families} families, found {len(summaries)}")
    if args.expect_cases is not None and total_cases != args.expect_cases:
        all_errors.append(f"expected {args.expect_cases} cases, found {total_cases}")
    if args.expect_cases_per_family is not None:
        for s in summaries:
            if s.get("cases") != args.expect_cases_per_family:
                all_errors.append(
                    f"{s.get('family_id')}: expected {args.expect_cases_per_family} cases, found {s.get('cases')}"
                )

    print("Medical case-family validation")
    print(f"families={len(summaries)} cases={total_cases}")
    for s in summaries:
        print(
            f"OK? {s['family_id']}: cases={s['cases']} nodes={s['nodes']} "
            f"edges={s['edges']} passages={s['evidence_passages']} status={s['status']}"
        )

    if all_errors:
        print("\nVALIDATION FAILED", file=sys.stderr)
        for err in all_errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
