#!/usr/bin/env python3
"""S3a v0.5.6 typed reference graph + endpoint discourse state.

Development-only structural repair over v0.5.5. Historical fresh results and
historical gold remain immutable.

This version addresses only the frozen v0.5.5 development failures that are
architectural rather than benchmark-label ambiguities:
1. typed anaphoric reference compatibility (scalar/range/threshold);
2. event-local variable-conflict veto for inherited/shared renal conditions;
3. endpoint entity state across adjacent sentences before evidence/achievement
   arbitration.

The v0.5.5 semantic safety evaluator is intentionally retained unchanged.
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

import s3a_compositional_frame_parser_v055 as v055
import s3a_compositional_frame_parser_v054 as v054
import s3a_compositional_frame_parser_v053 as v053
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.6"
MANAGEMENT_TYPES = set(v054.MANAGEMENT_TYPES)


def n(text: str) -> str:
    return v054.n(text)


def _condition_shape(conditions: list[dict[str, Any]]) -> str:
    if len(conditions) != 1:
        return "compound"
    op = str(conditions[0].get("operator", "")).upper()
    if op == "RANGE":
        return "range"
    if op == "EQ":
        return "scalar"
    if op in {"LT", "LE", "GT", "GE"}:
        return "threshold"
    return "other"


def _event_trigger_position(event_type: str, text: str) -> int | None:
    patterns = {
        "INITIATION_RESTRICTION": r"\b(?:initiation|initiate|starting|beginning|commencing)\b",
        "BENEFIT_RISK_REASSESSMENT": r"\b(?:reassess\w*|reassessment|review\w*|reconsider\w*)\b",
        "DISCONTINUATION": r"\b(?:discontinu\w*|withdraw\w*|stop\w*)\b",
        "CONTRAINDICATION": r"\bcontraindicat\w*\b",
    }
    pat = patterns.get(event_type)
    if not pat:
        return None
    hits = list(re.finditer(pat, n(text), re.I))
    return hits[-1].start() if hits else None


def _nearest_named_variable_before_event(event_type: str, text: str) -> tuple[str | None, int | None]:
    """Return the nearest named variable before the event trigger.

    This is a target-compatibility check, not a numeric parser. It prevents a
    shared renal condition from being linked onto an event whose local clause is
    governed by a nearer non-renal variable.
    """
    s = n(text)
    event_pos = _event_trigger_position(event_type, s)
    if event_pos is None:
        return None, None
    candidates: list[tuple[int, str]] = []
    for m in re.finditer(r"\begfr\b|\bkidney\s+function\b|\brenal\s+(?:value|threshold|function)\b", s, re.I):
        if m.start() < event_pos:
            candidates.append((m.start(), "renal"))
    for m in v054.NON_RENAL_LOCAL.finditer(s):
        if m.start() < event_pos:
            candidates.append((m.start(), "nonrenal"))
    if not candidates:
        return None, None
    pos, kind = max(candidates, key=lambda x: x[0])
    return kind, event_pos - pos


def repair_typed_condition_references(text: str, frames: list[dict[str, Any]]) -> None:
    """Validate v0.5.5 inherited condition edges against typed references.

    Two invariants are enforced:
    - a singular ``same ... value`` reference cannot inherit a RANGE antecedent;
    - a shared renal condition cannot override a nearer named non-renal variable
      governing the target event.

    Existing local conditions that were not introduced by the v0.5.5 shared
    linker are left unchanged.
    """
    for f in frames:
        if f.get("event_type") not in MANAGEMENT_TYPES:
            continue
        trace = f.get("scope_trace") or {}
        link = trace.get("v055_condition_link")
        if not isinstance(link, dict) or not f.get("conditions"):
            continue

        span = str(f.get("source_span") or text)
        shape = _condition_shape(f.get("conditions") or [])
        singular_same_value = bool(re.search(r"\bsame\s+(?:renal\s+)?(?:value|measurement|reading)\b", n(span), re.I))
        if singular_same_value and shape == "range":
            f["conditions"] = []
            f.setdefault("scope_trace", {})["v056_reference_veto"] = {
                "type": "reference_shape_incompatible",
                "anaphor_shape": "scalar_value",
                "antecedent_shape": "range",
            }
            continue

        kind, distance = _nearest_named_variable_before_event(str(f.get("event_type")), span)
        if kind == "nonrenal" and distance is not None and distance <= 120:
            f["conditions"] = []
            f.setdefault("scope_trace", {})["v056_reference_veto"] = {
                "type": "local_variable_conflict",
                "nearest_variable_type": "nonrenal",
                "distance_to_event": distance,
            }


def _endpoint_reference_state(sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create sentence-level endpoint entity links.

    Endpoint state persists only to the immediately adjacent sentence and only
    when that sentence contains an explicit endpoint/outcome anaphor. This keeps
    discourse linking conservative and inspectable.
    """
    out: list[dict[str, Any]] = []
    last_explicit: int | None = None
    explicit_pat = re.compile(r"\bprimary(?:\s+efficacy)?\s+(?:endpoint|outcome)\b|\bendpoint\s+achievement\b", re.I)
    anaphor_pat = re.compile(r"\b(?:the|this|that|such)\s+(?:endpoint|outcome)\b", re.I)
    for i, sent in enumerate(sentences):
        s = n(sent["text"])
        explicit = bool(explicit_pat.search(s))
        linked_from = None
        if explicit:
            last_explicit = i
        elif last_explicit is not None and i - last_explicit == 1 and anaphor_pat.search(s):
            linked_from = last_explicit
        out.append({
            "sentence_id": i,
            "explicit_endpoint": explicit,
            "endpoint_linked": explicit or linked_from is not None,
            "linked_from_sentence": linked_from,
        })
    return out


def _endpoint_sentence_semantics(sentence: str, linked: bool) -> tuple[bool, bool]:
    """Return (negative_evidence, direct_positive_achievement)."""
    if not linked:
        return False, False
    s = n(sentence)
    success = bool(re.search(r"\b(?:achiev(?:ed|ement)|attain(?:ed|ment)|met|success)\b", s))
    if not success:
        return False, False

    evidence_verb = r"(?:establish(?:es|ed)?|demonstrat(?:e|es|ed)|show(?:s|ed)?|confirm(?:s|ed)?|prove(?:s|d)?|constitut(?:e|es|ed))"
    negative = bool(
        re.search(rf"\b(?:no|none|nothing)\b[^.;]{{0,190}}{evidence_verb}[^.;]{{0,140}}(?:endpoint|outcome|achiev|attain|met)", s)
        or re.search(rf"\b(?:does\s+not|do\s+not|cannot|can\s+not|fails?\s+to|is\s+not)\b[^.;]{{0,140}}{evidence_verb}[^.;]{{0,140}}(?:endpoint|outcome|achiev|attain|met)", s)
        or re.search(r"\b(?:suspension|termination|enrollment|recruitment|status)\b[^.;]{0,110}\bnot\s+(?:evidence|proof)\b[^.;]{0,110}(?:endpoint|outcome|achiev|met)", s)
        or re.search(r"\bno\s+posted\s+(?:outcome|result|evidence)\b[^.;]{0,160}(?:achiev|met)", s)
    )
    positive = bool(
        re.search(r"\b(?:the|this|that|such|registered|prespecified|primary(?:\s+efficacy)?)?\s*(?:endpoint|outcome)\s+(?:was|is|has\s+been)\s+(?:achieved|attained|met)\b", s)
        and not negative
    )
    return negative, positive


def repair_endpoint_discourse_state(text: str, frames: list[dict[str, Any]]) -> None:
    """Link endpoint entities before evidence/achievement arbitration."""
    t = n(text)
    sentences = v053.sentence_spans(t)
    states = _endpoint_reference_state(sentences)

    negative_sentences: list[tuple[dict[str, Any], dict[str, Any]]] = []
    positive_sentences: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for sent, state in zip(sentences, states):
        neg, pos = _endpoint_sentence_semantics(sent["text"], bool(state["endpoint_linked"]))
        if neg:
            negative_sentences.append((sent, state))
        if pos:
            positive_sentences.append((sent, state))

    if not negative_sentences:
        return

    # Rebuild the endpoint outcome relation family from sentence-level typed
    # discourse state. This removes lexical positive frames embedded inside a
    # negative evidence statement while preserving independent direct positives.
    frames[:] = [
        f for f in frames
        if f.get("event_type") not in {"ENDPOINT_ACHIEVEMENT", "ENDPOINT_ACHIEVEMENT_EVIDENCE"}
    ]

    for sent, state in negative_sentences:
        frames.append(v054.make_frame(
            "ENDPOINT_ACHIEVEMENT_EVIDENCE", "evidence", "primary_endpoint",
            polarity="NEGATIVE", span=sent["text"], modality="LIMITED",
            family="v0.5.6:endpoint_discourse",
            trace={
                "scope": "typed_endpoint_discourse_evidence",
                "sentence_id": state["sentence_id"],
                "linked_from_sentence": state["linked_from_sentence"],
                "negation_bound_before_achievement_arbitration": True,
            },
        ))

    for sent, state in positive_sentences:
        frames.append(v054.make_frame(
            "ENDPOINT_ACHIEVEMENT", "study", "primary_endpoint",
            span=sent["text"], family="v0.5.6:endpoint_discourse",
            trace={
                "scope": "typed_endpoint_discourse_achievement",
                "sentence_id": state["sentence_id"],
                "linked_from_sentence": state["linked_from_sentence"],
            },
        ))


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    base = v055.extract(item, legacy_cfg)
    text = item["text"]
    frames = copy.deepcopy(base["semantic_frames"])

    repair_typed_condition_references(text, frames)
    repair_endpoint_discourse_state(text, frames)
    frames = v054.dedupe_frames(frames)

    guard = list(v054.ontology_guard(text, frames))
    guard.extend(v055.high_risk_structure_guard(text))
    guard = list(dict.fromkeys(guard))

    if guard:
        propositions: list[dict[str, Any]] = []
        unresolved = [
            {"text": text, "reason": r, "potentially_critical": True, "guard": "v0.5.6_safety_gate"}
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
    print(f"Wrote {len(rows)} S3a v0.5.6 typed-reference/discourse records to {out}")


if __name__ == "__main__":
    main()
