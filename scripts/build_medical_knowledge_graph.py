#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a canonical GroundSignal medical knowledge graph snapshot.

Inputs:
- medical/case-families/*/graph.json
- medical/knowledge-base/PHARMACOLOGY_BACKBONE_V0.1.json
- medical/knowledge-base/ORGAN_SPECIAL_POP_SAFETY_BACKBONE_V0.1.json

Output is a JSON graph preserving provenance and case/module contexts. This is an
evaluation-oriented snapshot, not a complete medical ontology or prescribing engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slug(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def canonical_kb_node_id(label: str) -> str:
    return f"kb:{slug(label)}"


def stable_edge_id(subject: str, predicate: str, obj: str, namespace: str) -> str:
    raw = f"{namespace}|{subject}|{predicate}|{obj}".encode("utf-8")
    return "edge:" + hashlib.sha1(raw).hexdigest()[:16]


def merge_node(store, node, context):
    nid = node["node_id"]
    normalized = dict(node)
    normalized.setdefault("contexts", [])
    if context and context not in normalized["contexts"]:
        normalized["contexts"].append(context)
    if nid not in store:
        store[nid] = normalized
        return
    current = store[nid]
    for key in ("node_type", "label"):
        a, b = current.get(key), normalized.get(key)
        if a and b and a != b:
            raise ValueError(f"node collision for {nid}: {key}={a!r} vs {b!r}")
    current.setdefault("contexts", [])
    for c in normalized.get("contexts", []):
        if c not in current["contexts"]:
            current["contexts"].append(c)
    current.setdefault("source_passage_ids", [])
    for pid in normalized.get("source_passage_ids", []):
        if pid not in current["source_passage_ids"]:
            current["source_passage_ids"].append(pid)
    current.setdefault("source_ids", [])
    for sid in normalized.get("source_ids", []):
        if sid not in current["source_ids"]:
            current["source_ids"].append(sid)


def merge_edge(store, edge, context):
    eid = edge["edge_id"]
    normalized = dict(edge)
    normalized.setdefault("contexts", [])
    if context and context not in normalized["contexts"]:
        normalized["contexts"].append(context)
    if eid not in store:
        store[eid] = normalized
        return
    current = store[eid]
    for key in ("subject_id", "predicate", "object_id"):
        if current.get(key) != normalized.get(key):
            raise ValueError(f"edge collision for {eid}: incompatible {key}")
    current.setdefault("contexts", [])
    for c in normalized.get("contexts", []):
        if c not in current["contexts"]:
            current["contexts"].append(c)
    current.setdefault("source_passage_ids", [])
    for pid in normalized.get("source_passage_ids", []):
        if pid not in current["source_passage_ids"]:
            current["source_passage_ids"].append(pid)
    current.setdefault("source_ids", [])
    for sid in normalized.get("source_ids", []):
        if sid not in current["source_ids"]:
            current["source_ids"].append(sid)


def add_case_graphs(root: Path, nodes, edges, source_files):
    for graph_path in sorted((root / "medical" / "case-families").glob("*/graph.json")):
        family_id = graph_path.parent.name
        graph = read_json(graph_path)
        source_files.append(str(graph_path))
        for node in graph.get("nodes", []):
            merge_node(nodes, node, f"case_family:{family_id}")
        for edge in graph.get("edges", []):
            merge_edge(edges, edge, f"case_family:{family_id}")


def infer_backbone_node_type(label: str) -> str:
    x = label.upper()
    if x.startswith("CYP") or x.startswith("UGT"):
        return "ENZYME"
    if any(t in x for t in ("P-GP", "BCRP", "OATP", "OAT", "OCT", "MATE")):
        return "TRANSPORTER"
    if x.startswith("HLA-") or "METABOLIZER" in x or "GENOTYPE" in x:
        return "GENETIC_OR_PHENOTYPE_CONTEXT"
    if any(k in x for k in ("BLEED", "QT", "RESPIRATORY", "SEDATION", "COMA", "DEATH", "HYPERSENSITIVITY", "HYPOGLYC", "SEROTONIN", "LIVER DAMAGE")):
        return "SAFETY_OUTCOME_OR_CONTEXT"
    if any(k in x for k in ("PREGNANC", "LACTATION", "REPRODUCTIVE", "RENAL", "HEPATIC")):
        return "SPECIAL_POPULATION_OR_ORGAN_CONTEXT"
    return "DRUG_OR_CLINICAL_CONCEPT"


def add_backbone_file(path: Path, context_prefix: str, nodes, edges, source_files):
    if not path.exists():
        return
    data = read_json(path)
    source_files.append(str(path))
    for module in data.get("modules", []):
        module_id = module["module_id"]
        source_id = module.get("source_id")
        evidence_scope = module.get("evidence_scope")
        forbidden = module.get("forbidden_inference")
        for claim in module.get("claims", []):
            subject_label = claim["subject"]
            object_label = claim["object"]
            sid = canonical_kb_node_id(subject_label)
            oid = canonical_kb_node_id(object_label)
            context = f"{context_prefix}:{module_id}"
            merge_node(nodes, {
                "node_id": sid,
                "node_type": infer_backbone_node_type(subject_label),
                "label": subject_label,
                "status": "OBSERVED",
                "source_passage_ids": [],
                "source_ids": [source_id] if source_id else [],
                "review_status": claim.get("review_status", "unknown")
            }, context)
            merge_node(nodes, {
                "node_id": oid,
                "node_type": infer_backbone_node_type(object_label),
                "label": object_label,
                "status": "OBSERVED",
                "source_passage_ids": [],
                "source_ids": [source_id] if source_id else [],
                "review_status": claim.get("review_status", "unknown")
            }, context)
            eid = stable_edge_id(sid, claim["predicate"], oid, module_id)
            merge_edge(edges, {
                "edge_id": eid,
                "subject_id": sid,
                "predicate": claim["predicate"],
                "object_id": oid,
                "status": "OBSERVED",
                "source_passage_ids": [],
                "source_ids": [source_id] if source_id else [],
                "locator": claim.get("locator"),
                "review_status": claim.get("review_status", "unknown"),
                "evidence_scope": evidence_scope,
                "forbidden_inference": forbidden
            }, context)


def add_backbones(root: Path, nodes, edges, source_files):
    add_backbone_file(
        root / "medical" / "knowledge-base" / "PHARMACOLOGY_BACKBONE_V0.1.json",
        "pharmacology_module", nodes, edges, source_files
    )
    add_backbone_file(
        root / "medical" / "knowledge-base" / "ORGAN_SPECIAL_POP_SAFETY_BACKBONE_V0.1.json",
        "organ_safety_module", nodes, edges, source_files
    )


def summarize(nodes, edges):
    by_node_type = defaultdict(int)
    by_predicate = defaultdict(int)
    by_review = defaultdict(int)
    by_context_family = defaultdict(int)
    for n in nodes.values():
        by_node_type[n.get("node_type", "UNKNOWN")] += 1
    for e in edges.values():
        by_predicate[e.get("predicate", "UNKNOWN")] += 1
        by_review[e.get("review_status", "unknown")] += 1
        for context in e.get("contexts", []):
            by_context_family[context.split(':', 1)[0]] += 1
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(by_node_type.items())),
        "predicates": dict(sorted(by_predicate.items())),
        "edge_review_status": dict(sorted(by_review.items())),
        "edge_context_types": dict(sorted(by_context_family.items()))
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="medical/knowledge-graph/generated/medical-kg-v0.2.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    nodes, edges, source_files = {}, {}, []
    add_case_graphs(root, nodes, edges, source_files)
    add_backbones(root, nodes, edges, source_files)

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "graph_id": "GroundSignal-Medical-KG",
        "graph_version": "v0.2",
        "build_semantics": "evaluation-oriented canonical graph; not a complete medical ontology or prescribing engine",
        "source_files": [str(Path(p).relative_to(root)) for p in source_files],
        "summary": summarize(nodes, edges),
        "nodes": sorted(nodes.values(), key=lambda x: x["node_id"]),
        "edges": sorted(edges.values(), key=lambda x: x["edge_id"])
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()
