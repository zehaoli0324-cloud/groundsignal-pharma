#!/usr/bin/env python3
"""S3a v0.5.1 compositional-frame architectural repair.

Development-only repair over v0.5.0. This version addresses three previously
recorded exposed-regression failures without creating or inspecting a new fresh
held-out:

1. clause-local elided eGFR comparatives override sentence-level inheritance;
2. target-local copular/passive negation is recognized before proposition emission;
3. every v0.4 fallback frame is adapted into the v0.5 trace/provenance contract.

The semantic event inventory remains the v0.5 architecture. This file is not a
new synonym-patching route; it changes scope resolution and fallback provenance.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.1"

# Preserve v0.5.0 implementations before patching the module globals used by
# v05.detect().
_V05_CONDITIONS = v05.conditions
_V05_NEG_SCOPE = v05.neg_scope
_V05_POPS = v05.pops


def _num(raw: str):
    return float(raw) if "." in raw else int(raw)


def conditions(text: str, *, allow_elided_egfr: bool = False) -> list[list[dict[str, Any]]]:
    """Return condition candidates with explicit local comparatives taking priority.

    v0.5.0 correctly parses explicit ``eGFR < X`` forms but can miss a later
    clause such as ``discontinuation only under 30``. When the sentence has
    already established eGFR as the numeric variable, this function permits a
    *local* bare comparator to recover the elided variable. The local result is
    then preferred over sentence inheritance by ``nodes``.
    """
    explicit = _V05_CONDITIONS(text)
    if explicit:
        return explicit
    if not allow_elided_egfr:
        return []

    t = v05.n(text)
    hits: list[tuple[int, list[dict[str, Any]]]] = []
    # Bare comparatives are intentionally limited to unambiguous comparison
    # morphology; plain numbers never inherit an eGFR variable.
    for m in re.finditer(r"\b(?:below|under|less\s+than|lower\s+than)\s*(\d+(?:\.\d+)?)\b|<\s*(\d+(?:\.\d+)?)", t):
        raw = m.group(1) or m.group(2)
        hits.append((m.start(), [{"variable": "egfr", "operator": "LT", "value": _num(raw)}]))

    out: list[list[dict[str, Any]]] = []
    seen: set[str] = set()
    for _, cond in sorted(hits):
        key = json.dumps(cond, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(cond)
    return out


def nodes(text: str) -> list[dict[str, Any]]:
    """Build clause nodes with explicit local-vs-inherited condition provenance."""
    out: list[dict[str, Any]] = []
    nid = 0
    sentences = [x.strip(" ,") for x in re.split(r"(?<=[.!?])\s+", text) if x.strip(" ,")]
    for sid, sent in enumerate(sentences):
        sentence_conditions = _V05_CONDITIONS(sent)
        sentence_pops = _V05_POPS(sent)
        has_egfr_context = bool(re.search(r"\begfr\b", v05.n(sent)))
        clauses = [
            x.strip(" ,")
            for x in re.split(
                r"\s*;\s*|,?\s+\b(?:whereas|while|yet|but|nevertheless|however)\b\s+|,\s+although\s+",
                sent,
                flags=re.I,
            )
            if x.strip(" ,")
        ]
        for cid, clause in enumerate(clauses):
            local_conditions = conditions(clause, allow_elided_egfr=has_egfr_context)
            local_pops = _V05_POPS(clause)
            if len(local_conditions) == 1:
                bound_condition = local_conditions[0]
                condition_source = "clause_local"
            elif not local_conditions and len(sentence_conditions) == 1:
                bound_condition = sentence_conditions[0]
                condition_source = "sentence_inherited_unique"
            else:
                bound_condition = []
                condition_source = "unresolved_or_ambiguous"

            out.append(
                {
                    "node_id": nid,
                    "sentence_id": sid,
                    "clause_id": cid,
                    "text": clause,
                    "sentence": sent,
                    "condition": bound_condition,
                    "condition_source": condition_source,
                    "local_condition_candidates": local_conditions,
                    "sentence_condition_candidates": sentence_conditions,
                    "local_populations": local_pops,
                    "sentence_populations": sentence_pops,
                    "inherited_population": sentence_pops[0] if not local_pops and len(sentence_pops) == 1 else None,
                }
            )
            nid += 1
    return out


def neg_scope(text: str, target: str | None = None) -> bool:
    """Target-local negation with explicit copular/passive handling."""
    t = v05.n(text)
    if target:
        match = re.search(target, t, re.I)
        if match:
            local = t[max(0, match.start() - 160) : match.end() + 100]
            # Examples covered structurally: "is not contraindicated" and
            # "is not a contraindication". The optional article is treated as
            # syntax, not as a lexical special case.
            if re.search(rf"\b(?:is|are|was|were|be|been|being)\s+not\s+(?:an?\s+)?{target}", local, re.I):
                return True
            if re.search(rf"\bnot\s+(?:an?\s+)?{target}", local, re.I):
                return True
    return _V05_NEG_SCOPE(t, target)


def _trace_for_legacy(frame: dict[str, Any], scope_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    span = v05.n(str(frame.get("source_span") or ""))
    node_id = None
    for node in scope_nodes:
        node_text = v05.n(node.get("text", ""))
        if span and (span in node_text or node_text in span):
            node_id = node.get("node_id")
            break
    return {
        "scope": "legacy_fallback_adapted",
        "adapter": VERSION,
        "source_extractor": "s3a-semantic-frame-v0.4",
        "node_id": node_id,
    }


def adapt_legacy_frame(frame: dict[str, Any], scope_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Make a v0.4 fallback auditable under the v0.5 trace contract."""
    out = dict(frame)
    out["trigger_family"] = out.get("trigger_family") or f"v0.4_fallback:{str(out.get('event_type', 'unknown')).lower()}"
    out["scope_trace"] = _trace_for_legacy(out, scope_nodes)
    return out


# v05.detect resolves these functions from its module globals at runtime.
v05.conditions = conditions
v05.nodes = nodes
v05.neg_scope = neg_scope


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    new_frames, scope_nodes = v05.detect(item)
    legacy_frames = v04.detect_frames(item, legacy_cfg)
    override_types = {f["event_type"] for f in new_frames}
    fallback = [adapt_legacy_frame(f, scope_nodes) for f in legacy_frames if f.get("event_type") not in override_types]
    frames = v05.dedupe(new_frames + fallback)
    propositions = v04.dedupe_props([v04.compile_frame(f) for f in frames])

    unresolved = []
    text_norm = v05.n(item["text"])
    if v05.hit(text_norm, v05.CRITICAL) and not any(f.get("event_type") in v05.CRITICAL_TYPES for f in frames):
        unresolved = [
            {
                "text": item["text"],
                "reason": "critical semantic content detected but no v0.5.1/v0.5/v0.4 frame emitted",
                "potentially_critical": True,
            }
        ]

    return {
        "item_id": item["item_id"],
        "role": item.get("role", "evidence"),
        "scope_nodes": scope_nodes,
        "semantic_frames": frames,
        "predicted_propositions": propositions,
        "abstain": bool(unresolved),
        "unresolved_spans": unresolved,
        "extractor_version": VERSION,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--legacy-config", default="medical/configs/s3a-semantic-frame-v0.4.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = v05.load(args.input)
    legacy_cfg = v05.load(args.legacy_config)
    rows = [extract(item, legacy_cfg) for item in doc["items"]]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.5.1 compositional-frame records to {out}")


if __name__ == "__main__":
    main()
