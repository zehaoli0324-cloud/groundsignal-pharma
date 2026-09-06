#!/usr/bin/env python3
"""S3a v0.5.6.1 frame/event registry reconciliation.

Development-only repair after the preserved v0.5.6 development FAIL.

The v0.5.6 semantic frame recognizer and the older event-node registry can
recognize slightly different verb morphology. This version derives shared-scope
targets from actual management frames, maps those frames back to sentence spans,
and applies preposed typed conditions only after target-compatibility checks.

Historical gold and fresh results remain immutable. The v0.5.5 semantic safety
evaluator remains unchanged.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import s3a_compositional_frame_parser_v056 as v056
import s3a_compositional_frame_parser_v055 as v055
import s3a_compositional_frame_parser_v054 as v054
import s3a_compositional_frame_parser_v053 as v053
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.6.1"
MANAGEMENT_TYPES = set(v054.MANAGEMENT_TYPES)


def n(text: str) -> str:
    return v054.n(text)


def _frame_sentence(frame: dict[str, Any], text: str, sentences: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    """Return (sentence_id, source_start) from trace or source-span matching."""
    trace = frame.get("scope_trace") or {}
    owner = trace.get("v054_event_owner") or {}
    si = owner.get("sentence_id") if isinstance(owner, dict) else None
    if not isinstance(si, int):
        raw_si = trace.get("sentence_id")
        if isinstance(raw_si, int):
            si = raw_si

    t = n(text)
    span = n(str(frame.get("source_span") or ""))
    if isinstance(si, int) and 0 <= si < len(sentences):
        s = sentences[si]
        pos = t.find(span, s["start"], s["end"]) if span else -1
        return si, (pos if pos >= 0 else None)

    if span:
        for i, s in enumerate(sentences):
            pos = t.find(span, s["start"], s["end"])
            if pos >= 0:
                return i, pos
    return None, None


def reconcile_shared_preposed_conditions(text: str, frames: list[dict[str, Any]]) -> None:
    """Use realized frames as shared-condition targets when event nodes miss them."""
    t = n(text)
    sentences = v053.sentence_spans(t)
    conds = v053.typed_egfr_candidates(t)

    frame_meta: list[tuple[dict[str, Any], int, int | None]] = []
    for f in frames:
        if f.get("event_type") not in MANAGEMENT_TYPES:
            continue
        si, start = _frame_sentence(f, t, sentences)
        if si is not None:
            frame_meta.append((f, si, start))

    for si, sent in enumerate(sentences):
        targets = [(f, start) for f, fsi, start in frame_meta if fsi == si]
        if len(targets) < 2:
            continue
        sc = [c for c in conds if sent["start"] <= c["start"] < sent["end"]]
        if len(sc) != 1:
            continue
        cond = sc[0]

        for f, source_start in targets:
            if f.get("conditions"):
                continue
            if source_start is not None and cond["start"] >= source_start:
                continue

            local = n(str(f.get("source_span") or sent["text"]))

            # Type/cardinality compatibility: singular "same value" cannot
            # resolve to a range antecedent.
            shape = v056._condition_shape(cond["condition"])
            if re.search(r"\bsame\s+(?:renal\s+)?(?:value|measurement|reading)\b", local, re.I) and shape == "range":
                f.setdefault("scope_trace", {})["v0561_reference_veto"] = {
                    "type": "reference_shape_incompatible",
                    "anaphor_shape": "scalar_value",
                    "antecedent_shape": "range",
                }
                continue

            # Event-local target compatibility: a nearer non-renal variable
            # prevents a renal condition from being propagated onto the event.
            kind, distance = v056._nearest_named_variable_before_event(str(f.get("event_type")), local)
            if kind == "nonrenal" and distance is not None and distance <= 120:
                f.setdefault("scope_trace", {})["v0561_reference_veto"] = {
                    "type": "local_variable_conflict",
                    "nearest_variable_type": "nonrenal",
                    "distance_to_event": distance,
                }
                continue

            if v054.NON_RENAL_LOCAL.search(local) and kind != "renal":
                continue

            f["conditions"] = copy.deepcopy(cond["condition"])
            f.setdefault("scope_trace", {})["v0561_condition_link"] = {
                "type": "frame_registry_shared_preposed_condition",
                "sentence_id": si,
                "condition_start": cond["start"],
                "target_source_start": source_start,
            }


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    base = v056.extract(item, legacy_cfg)
    text = item["text"]
    frames = copy.deepcopy(base["semantic_frames"])

    reconcile_shared_preposed_conditions(text, frames)
    # Re-run v0.5.6 reference vetoes after reconciliation so a newly attached
    # shared edge cannot bypass the established type/variable constraints.
    v056.repair_typed_condition_references(text, frames)
    v056.repair_endpoint_discourse_state(text, frames)
    frames = v054.dedupe_frames(frames)

    guard = list(v054.ontology_guard(text, frames))
    guard.extend(v055.high_risk_structure_guard(text))
    guard = list(dict.fromkeys(guard))

    if guard:
        propositions: list[dict[str, Any]] = []
        unresolved = [
            {"text": text, "reason": r, "potentially_critical": True, "guard": "v0.5.6.1_safety_gate"}
            for r in guard
        ]
        abstain = True
    else:
        missing = v054.coverage_guard(text, frames)
        unresolved = [
            {
                "text": text,
                "reason": f"representable critical semantic family unresolved: {m}",
                "potentially_critical": True,
                "guard": "semantic_coverage",
            }
            for m in missing
        ]
        propositions = v04.dedupe_props([
            v04.compile_frame(f) for f in frames if f.get("event_type") in v04.FRAME_TO_PREDICATE
        ])
        abstain = bool(unresolved)

    return {
        "item_id": item["item_id"],
        "role": item.get("role", "evidence"),
        "scope_nodes": base["scope_nodes"],
        "semantic_frames": frames,
        "predicted_propositions": propositions,
        "abstain": abstain,
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
    cfg = v05.load(args.legacy_config)
    rows = [extract(item, cfg) for item in doc["items"]]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.5.6.1 registry-reconciled records to {out}")


if __name__ == "__main__":
    main()
