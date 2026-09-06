#!/usr/bin/env python3
"""S3a v0.5.5 typed scope linker + safety error gate.

Development-only structural repair over v0.5.4. The v0.5.4 fresh suite is now
exposed regression data and is never relabelled as fresh.

Architecture additions:
1. independent discourse links for population continuity vs condition continuity;
2. explicit shared-condition edges from a preposed typed condition to compatible events;
3. typed endpoint scope arbitration: declaration != achievement != evidence-for-achievement;
4. negation/evidence scope resolved before endpoint success emission;
5. semantic high-risk guard for unsupported conditional action structures.

The implementation intentionally wraps the mature v0.5.4 extractor instead of
rebuilding semantic families. Repairs are applied only to typed scope links or
relation families with an explicit conflict.
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

import s3a_compositional_frame_parser_v054 as v054
import s3a_compositional_frame_parser_v053 as v053
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.5"
MANAGEMENT_TYPES = set(v054.MANAGEMENT_TYPES)


def n(text: str) -> str:
    return v054.n(text)


def _frame_sentence_id(frame: dict[str, Any]) -> int | None:
    trace = frame.get("scope_trace") or {}
    owner = trace.get("v054_event_owner") or {}
    if isinstance(owner, dict) and isinstance(owner.get("sentence_id"), int):
        return owner["sentence_id"]
    if isinstance(trace.get("sentence_id"), int):
        return trace["sentence_id"]
    return None


def _frames_by_type(frames: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for f in frames:
        out.setdefault(str(f.get("event_type")), []).append(f)
    return out


def link_population_continuity(text: str, frames: list[dict[str, Any]]) -> None:
    """Carry population discourse state without carrying condition state.

    Population continuity is allowed only across adjacent sentences when the
    current sentence has no competing population label and refers anaphorically
    to the prior treatment/user context. Condition inheritance is deliberately
    independent and is never performed here.
    """
    t = n(text)
    sentences = v053.sentence_spans(t)
    if len(sentences) < 2:
        return
    sentence_pops = [v054.population_labels_local(s["text"]) for s in sentences]
    anaphora = re.compile(
        r"\b(?:it|they|them|the\s+(?:medicine|drug|therapy|treatment)|"
        r"that\s+(?:patient|user|person)|those\s+(?:patients|users|people))\b",
        re.I,
    )
    for f in frames:
        if f.get("event_type") not in MANAGEMENT_TYPES or f.get("population") is not None:
            continue
        si = _frame_sentence_id(f)
        if si is None or si <= 0 or si >= len(sentences):
            continue
        if sentence_pops[si]:
            continue
        prev = sentence_pops[si - 1]
        if len(prev) != 1 or not anaphora.search(sentences[si]["text"]):
            continue
        f["population"] = prev[0]
        f.setdefault("scope_trace", {})["v055_population_link"] = {
            "type": "adjacent_sentence_anaphoric_population",
            "from_sentence": si - 1,
            "to_sentence": si,
            "population": prev[0],
            "condition_inherited": False,
        }


def link_shared_preposed_conditions(text: str, frames: list[dict[str, Any]]) -> None:
    """Attach one typed preposed eGFR condition to multiple compatible events.

    This applies only when one eGFR mention precedes every management event in a
    sentence and the target event does not locally introduce a non-renal variable.
    It therefore differs from generic sentence-wide condition inheritance.
    """
    t = n(text)
    sentences = v053.sentence_spans(t)
    events = v054._event_windows(t, v054._sentence_events(t))
    conds = v053.typed_egfr_candidates(t)
    by_sentence: dict[int, list[dict[str, Any]]] = {}
    for e in events:
        if e.get("event_type") in MANAGEMENT_TYPES:
            by_sentence.setdefault(e["sentence_id"], []).append(e)
    for si, evs in by_sentence.items():
        if len(evs) < 2:
            continue
        sent = sentences[si]
        sc = [c for c in conds if sent["start"] <= c["start"] < sent["end"]]
        if len(sc) != 1:
            continue
        cond = sc[0]
        if cond["start"] >= min(e["start"] for e in evs):
            continue
        typed_frames = [f for f in frames if f.get("event_type") in MANAGEMENT_TYPES and _frame_sentence_id(f) == si]
        if not typed_frames:
            continue
        for f in typed_frames:
            if f.get("conditions"):
                continue
            owner = (f.get("scope_trace") or {}).get("v054_event_owner") or {}
            ws = owner.get("window_start", sent["start"])
            we = owner.get("window_end", sent["end"])
            local = t[ws:we] if isinstance(ws, int) and isinstance(we, int) else sent["text"]
            if v054.NON_RENAL_LOCAL.search(local):
                continue
            f["conditions"] = copy.deepcopy(cond["condition"])
            f.setdefault("scope_trace", {})["v055_condition_link"] = {
                "type": "shared_preposed_typed_condition",
                "sentence_id": si,
                "condition_start": cond["start"],
            }


def _endpoint_sentence_flags(sentence: str) -> dict[str, bool]:
    s = n(sentence)
    endpoint = bool(re.search(r"\b(?:primary(?:\s+efficacy)?\s+(?:endpoint|outcome)|endpoint\s+achievement)\b", s))
    if not endpoint:
        return {"endpoint": False, "negative_evidence": False, "positive_achievement": False, "declaration": False}

    success = bool(re.search(r"\b(?:achiev(?:ed|ement)|attain(?:ed|ment)|met|success)\b", s))
    evidence_verb = r"(?:establish(?:es|ed)?|demonstrat(?:e|es|ed)|show(?:s|ed)?|confirm(?:s|ed)?|prove(?:s|d)?|constitut(?:e|es|ed))"
    negative_evidence = bool(success and (
        re.search(rf"\b(?:no|none|nothing)\b[^.;]{{0,140}}(?:result|outcome|evidence|finding|record)[^.;]{{0,140}}{evidence_verb}", s)
        or re.search(rf"\b(?:no|none|nothing)\b[^.;]{{0,180}}{evidence_verb}[^.;]{{0,120}}(?:endpoint|outcome|achiev|met)", s)
        or re.search(rf"\b(?:does\s+not|do\s+not|cannot|can\s+not|fails?\s+to|is\s+not)\b[^.;]{{0,120}}{evidence_verb}[^.;]{{0,120}}(?:endpoint|outcome|achiev|met)", s)
        or re.search(r"\b(?:suspension|termination|enrollment|recruitment|status)\b[^.;]{0,100}\bnot\s+(?:evidence|proof)\b[^.;]{0,100}(?:endpoint|outcome|achiev|met)", s)
        or re.search(r"\bno\s+posted\s+(?:outcome|result|evidence)\b[^.;]{0,140}(?:achiev|met)", s)
    ))
    direct_positive = bool(
        re.search(r"\b(?:registered|prespecified|primary(?:\s+efficacy)?)?\s*(?:endpoint|outcome)\s+(?:was|is|has\s+been)\s+(?:achieved|attained|met)\b", s)
        and not negative_evidence
    )
    declaration = bool(
        re.search(r"\b(?:registry|record|study|trial)\b[^.;]{0,100}\b(?:specifies|lists|identifies|defines|records|marks)\b[^.;]{0,80}\bprimary(?:\s+efficacy)?\s+(?:endpoint|outcome)\b", s)
        or re.search(r"\bprimary(?:\s+efficacy)?\s+(?:endpoint|outcome)\s+(?:is|was|remains)\s+(?:defined|specified|listed|identified)\b", s)
    )
    return {"endpoint": True, "negative_evidence": negative_evidence, "positive_achievement": direct_positive, "declaration": declaration}


def repair_endpoint_scope(text: str, frames: list[dict[str, Any]]) -> None:
    """Resolve endpoint negation/evidence scope before success arbitration."""
    t = n(text)
    sentences = v053.sentence_spans(t)
    flags = [(_endpoint_sentence_flags(s["text"]), s) for s in sentences]
    negative = [s for fl, s in flags if fl["negative_evidence"]]
    direct_positive = [s for fl, s in flags if fl["positive_achievement"]]
    declaration = [s for fl, s in flags if fl["declaration"]]

    if negative:
        # An embedded lexical phrase such as "endpoint was achieved" inside a
        # negated evidence statement is not a positive achievement assertion.
        if not direct_positive:
            frames[:] = [f for f in frames if f.get("event_type") != "ENDPOINT_ACHIEVEMENT"]
        frames[:] = [f for f in frames if f.get("event_type") != "ENDPOINT_ACHIEVEMENT_EVIDENCE"]
        for s in negative:
            frames.append(v054.make_frame(
                "ENDPOINT_ACHIEVEMENT_EVIDENCE", "evidence", "primary_endpoint",
                polarity="NEGATIVE", span=s["text"], modality="LIMITED",
                family="v0.5.5:endpoint_scope",
                trace={"scope": "typed_endpoint_evidence", "sentence_start": s["start"], "negation_bound_before_arbitration": True},
            ))

    if direct_positive:
        # Keep one canonical positive event for each independent direct assertion.
        frames[:] = [f for f in frames if f.get("event_type") != "ENDPOINT_ACHIEVEMENT"]
        for s in direct_positive:
            frames.append(v054.make_frame(
                "ENDPOINT_ACHIEVEMENT", "study", "primary_endpoint", span=s["text"],
                family="v0.5.5:endpoint_scope",
                trace={"scope": "typed_endpoint_achievement", "sentence_start": s["start"]},
            ))

    if declaration and not any(f.get("event_type") == "PRIMARY_ENDPOINT_DECLARATION" for f in frames):
        s = declaration[0]
        frames.append(v054.make_frame(
            "PRIMARY_ENDPOINT_DECLARATION", "study", "primary_endpoint", span=s["text"],
            family="v0.5.5:endpoint_scope",
            trace={"scope": "typed_endpoint_declaration", "sentence_start": s["start"]},
        ))


def high_risk_structure_guard(text: str) -> list[str]:
    """Detect unsupported conditional management structures semantically.

    The guard is intentionally family-level: it does not key on benchmark item
    identifiers or exact sentences. It blocks unsupported physiologic/PGx/drug-
    interaction condition/action compositions before proposition emission.
    """
    t = n(text)
    reasons: list[str] = []
    unsupported_var = bool(v053.UNSUPPORTED_CONDITION_MARKER.search(t) or v054.NON_RENAL_LOCAL.search(t))
    conditional = bool(re.search(r"\b(?:only\s+if|only\s+when|unless|otherwise|if|when|whenever|except\s+when|in\s+which\s+case)\b", t))
    branch = bool(re.search(r"\b(?:both|either)\b[^.;]{0,220}\b(?:and|or)\b|\botherwise\b|\bunless\b|\bexcept\b", t))
    unsupported_action = bool(re.search(
        r"\b(?:hold|withhold|skip|defer)\b[^.;]{0,40}\b(?:dose|treatment|therapy|medicine|drug)\b|"
        r"\b(?:reduce|increase)\b[^.;]{0,35}\bdose\b|\bavoid\w*\b[^.;]{0,50}\b(?:coadministration|drug)\b",
        t,
    ))
    continuation_rule = bool(re.search(r"\b(?:continue|administer|give|maintain)\b[^.;]{0,80}\bonly\s+(?:if|when)\b", t))
    negative_description = bool(re.search(r"\b(?:not|never)\b[^.;]{0,45}(?:a\s+reason\s+to|trigger|require)[^.;]{0,45}(?:stop|discontinu|hold|withhold)", t))

    if negative_description:
        return reasons
    if conditional and unsupported_var and (unsupported_action or continuation_rule):
        reasons.append("unsupported typed condition/action composition in critical management rule")
    if branch and unsupported_var and (unsupported_action or continuation_rule):
        reasons.append("nonrepresentable logical branch in critical management rule")
    return list(dict.fromkeys(reasons))


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    base = v054.extract(item, legacy_cfg)
    text = item["text"]
    frames = copy.deepcopy(base["semantic_frames"])

    link_population_continuity(text, frames)
    link_shared_preposed_conditions(text, frames)
    repair_endpoint_scope(text, frames)
    frames = v054.dedupe_frames(frames)

    guard = list(v054.ontology_guard(text, frames))
    guard.extend(high_risk_structure_guard(text))
    guard = list(dict.fromkeys(guard))
    if guard:
        propositions: list[dict[str, Any]] = []
        unresolved = [
            {"text": text, "reason": r, "potentially_critical": True, "guard": "v0.5.5_safety_gate"}
            for r in guard
        ]
        abstain = True
    else:
        missing = v054.coverage_guard(text, frames)
        unresolved = [
            {"text": text, "reason": f"representable critical semantic family unresolved: {m}", "potentially_critical": True, "guard": "semantic_coverage"}
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
    print(f"Wrote {len(rows)} S3a v0.5.5 typed-scope/safety-gated records to {out}")


if __name__ == "__main__":
    main()
