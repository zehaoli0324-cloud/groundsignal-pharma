#!/usr/bin/env python3
"""S3a v0.5.3 semantic-typing + guard-composition repair.

This version is a structural repair over v0.5.2.  It intentionally treats the
v0.5.2 fresh held-out as exposed regression data and does not create new fresh
validation evidence.

Architecture additions:
1. typed numeric-condition mentions, so non-renal numeric variables are not
   silently coerced into eGFR;
2. sentence-bounded management scope with explicit anaphora handling;
3. relation direction and polarity normalization as separate operations;
4. type-aware ontology coverage guard executed before proposition emission;
5. guard completeness invariant: a clinically consequential rule with an
   unrepresentable condition/action/branch may not emit a simplified truth.
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

import s3a_compositional_frame_parser_v052 as v052
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.3"

MANAGEMENT_TYPES = {
    "INITIATION_RESTRICTION",
    "CONTRAINDICATION",
    "BENEFIT_RISK_REASSESSMENT",
    "DISCONTINUATION",
}

NON_RENAL_VARIABLE = re.compile(
    r"\b(?:age|platelets?(?:\s+count)?|ha?emoglobin|potassium|creatinine|"
    r"systolic\s+blood\s+pressure|blood\s+pressure|oxygen\s+saturation|"
    r"bilirubin|alanine\s+aminotransferase|\balt\b|qtc|urine\s+output|"
    r"fever|toxicity)\b",
    re.I,
)

UNSUPPORTED_CONDITION_MARKER = re.compile(
    r"\b(?:platelets?(?:\s+count)?|ha?emoglobin|potassium|bilirubin|"
    r"alanine\s+aminotransferase|\balt\b|qtc|torsades|dialysis|"
    r"oxygen\s+saturation|systolic\s+blood\s+pressure|blood\s+pressure|"
    r"urine\s+output|fever|toxicity|cyp\d+[a-z0-9]*|poor[- ]metaboli\w*|"
    r"therapeutic\s+drug\s+monitoring)\b",
    re.I,
)


def n(text: str) -> str:
    return v05.n(text)


def _num(raw: str):
    return float(raw) if "." in raw else int(raw)


def _frame(
    event_type: str,
    subject: str,
    object_: str,
    *,
    polarity: str = "POSITIVE",
    conditions=None,
    population=None,
    span=None,
    modality: str = "ASSERTED",
    family: str = "v0.5.3:structural_repair",
    trace=None,
) -> dict[str, Any]:
    f = v04.frame(
        event_type,
        subject=subject,
        object_=object_,
        polarity=polarity,
        conditions=conditions or [],
        population=population,
        source_span=span,
        modality=modality,
    )
    f["trigger_family"] = family
    f["scope_trace"] = trace or {"scope": "v0.5.3_structural_repair"}
    return f


def _dedupe_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for f in frames:
        key = (
            f.get("event_type"),
            f.get("subject"),
            f.get("object"),
            f.get("polarity"),
            f.get("population"),
            tuple(sorted(tuple(sorted(c.items())) for c in f.get("conditions", []))),
        )
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def sentence_spans(text: str) -> list[dict[str, Any]]:
    """Return sentence-like spans while preserving offsets."""
    t = n(text)
    out = []
    start = 0
    for m in re.finditer(r"[.!?]+(?:\s+|$)", t):
        end = m.end()
        s = t[start:end].strip()
        if s:
            real = t.find(s, start, end)
            out.append({"start": real, "end": real + len(s), "text": s})
        start = end
    if start < len(t):
        s = t[start:].strip()
        if s:
            real = t.find(s, start)
            out.append({"start": real, "end": real + len(s), "text": s})
    return out or [{"start": 0, "end": len(t), "text": t}]


def _sentence_index(spans: list[dict[str, Any]], pos: int) -> int:
    for i, s in enumerate(spans):
        if s["start"] <= pos < s["end"]:
            return i
    return max(0, len(spans) - 1)


def _population(text: str) -> str | None:
    labels = v052.population_labels(text)
    return labels[0] if len(labels) == 1 else None


def typed_egfr_candidates(text: str) -> list[dict[str, Any]]:
    """Extract only eGFR-typed thresholds; reject nearby non-renal variables."""
    t = n(text)
    hits: list[dict[str, Any]] = []
    explicit_patterns = [
        ("R", r"(?:egfr(?: values?)?\s*)?(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)"),
        ("R", r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)"),
        ("L", r"egfr(?:\s+(?:is|falls|drops|slips))?\s*(?:below|under|less\s+than|lower\s+than|<)\s*(\d+(?:\.\d+)?)"),
        ("L", r"(?:below|under|less\s+than|lower\s+than|<)\s*egfr\s*(\d+(?:\.\d+)?)"),
        ("L", r"kidney\s+function[^.;]{0,20}(?:falls|drops|is)?\s*(?:below|under|<)\s*(\d+(?:\.\d+)?)"),
        ("E", r"(?:at|with)\s+(?:an?\s+)?egfr\s*(?:of\s*)?(\d+(?:\.\d+)?)"),
        ("E", r"egfr\s*(?:of|=|is|at)\s*(\d+(?:\.\d+)?)"),
    ]
    for kind, pat in explicit_patterns:
        for m in re.finditer(pat, t, re.I):
            if kind == "R":
                cond = [{"variable": "egfr", "operator": "RANGE", "low": _num(m.group(1)), "high": _num(m.group(2))}]
            elif kind == "L":
                cond = [{"variable": "egfr", "operator": "LT", "value": _num(m.group(1))}]
            else:
                cond = [{"variable": "egfr", "operator": "EQ", "value": _num(m.group(1))}]
            hits.append({"start": m.start(), "end": m.end(), "condition": cond, "explicit": True})

    spans = sentence_spans(t)
    for si, sent in enumerate(spans):
        st = sent["text"]
        renal_context = "egfr" in st or "kidney function" in st
        if not renal_context:
            continue
        for m in re.finditer(r"\b(?:below|under|less\s+than|lower\s+than)\s*(\d+(?:\.\d+)?)\b|<\s*(\d+(?:\.\d+)?)", st, re.I):
            raw = m.group(1) or m.group(2)
            abs_start = sent["start"] + m.start()
            abs_end = sent["start"] + m.end()
            if any(h["start"] <= abs_start < h["end"] for h in hits):
                continue
            local_left = st[max(0, m.start() - 48):m.start()]
            # A named non-renal analyte immediately governing the comparator
            # blocks eGFR inheritance even if eGFR occurs elsewhere in sentence.
            if NON_RENAL_VARIABLE.search(local_left):
                continue
            hits.append({
                "start": abs_start,
                "end": abs_end,
                "condition": [{"variable": "egfr", "operator": "LT", "value": _num(raw)}],
                "explicit": False,
                "sentence_id": si,
            })
    hits.sort(key=lambda x: x["start"])
    return hits


def _event_matches(text: str) -> list[dict[str, Any]]:
    t = n(text)
    patterns = [
        ("INITIATION_RESTRICTION", r"\b(?:initiation|starting|beginning|commencing)[^.;]{0,90}(?:not recommended|advised against|discourag\w*|rule against)|\bnot[- ]recommended\s+initiation\b"),
        ("BENEFIT_RISK_REASSESSMENT", r"\b(?:reassess\w*|reassessment|review\w*|reconsider\w*)\b[^.;]{0,70}(?:benefit|risk)|(?:benefit[- ]?risk|benefit and risk)[^.;]{0,70}\b(?:reassess\w*|review\w*|reconsider\w*)\b|\breassessment\b(?=[^.;]{0,80}(?:egfr|renal|below|under))"),
        ("DISCONTINUATION", r"\b(?:discontinu(?:e|ed|ation|ing)|withdraw(?:n|al)?|stop(?:ping|ped)?|stopping)\b"),
        ("CONTRAINDICATION", r"\bcontraindicat\w*\b"),
    ]
    out = []
    for et, pat in patterns:
        for m in re.finditer(pat, t, re.I):
            out.append({"event_type": et, "start": m.start(), "end": m.end(), "surface": m.group(0)})
    out.sort(key=lambda x: x["start"])
    return out


def _management_polarity(sentence: str, event_type: str, event_start_in_sentence: int) -> str:
    s = n(sentence)
    before = s[max(0, event_start_in_sentence - 80):event_start_in_sentence]
    around = s[max(0, event_start_in_sentence - 80):event_start_in_sentence + 90]
    if event_type == "CONTRAINDICATION":
        if re.search(r"\b(?:not|no)\b[^.;]{0,50}contraindicat|does\s+not[^.;]{0,80}contraindicat", around):
            return "NEGATIVE"
    if event_type == "DISCONTINUATION":
        if re.search(r"\b(?:not|never)\b[^.;]{0,35}(?:discontinu|stop|withdraw)", around):
            return "NEGATIVE"
        if re.search(r"rather\s+than[^.;]{0,35}(?:automatically\s+)?(?:discontinu|stop|withdraw)", around):
            return "NEGATIVE"
        if re.search(r"without[^.;]{0,35}(?:discontinu|stop|withdraw)", around):
            return "NEGATIVE"
    return "POSITIVE"


def rebuild_management_frames(text: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rebuild management frames from typed, sentence-bounded event mentions."""
    t = n(text)
    spans = sentence_spans(t)
    conds = typed_egfr_candidates(t)
    events = _event_matches(t)
    if not events:
        return existing

    non_mgmt = [f for f in existing if f.get("event_type") not in MANAGEMENT_TYPES]
    rebuilt: list[dict[str, Any]] = []
    prior_egfr_by_sentence: dict[int, list[dict[str, Any]]] = {}
    for c in conds:
        si = _sentence_index(spans, c["start"])
        prior_egfr_by_sentence.setdefault(si, []).append(c)

    for e in events:
        si = _sentence_index(spans, e["start"])
        sent = spans[si]
        local_event_pos = e["start"] - sent["start"]
        sent_conds = prior_egfr_by_sentence.get(si, [])
        chosen = None
        if sent_conds:
            # Prefer a condition closest to the event mention.  This separates
            # compact "reassessment <46 and discontinuation <29" constructions.
            chosen = min(sent_conds, key=lambda c: abs(c["start"] - e["start"]))

        # Cross-sentence inheritance is forbidden by default.  It is allowed
        # only for explicit anaphora, and preserves the antecedent operator.
        sent_text = sent["text"]
        if chosen is None and re.search(r"\b(?:same|that|this)\s+(?:egfr|renal\s+threshold)|\bat\s+the\s+same\s+egfr\b", sent_text, re.I):
            previous = [c for j in range(si - 1, -1, -1) for c in prior_egfr_by_sentence.get(j, [])]
            if previous:
                chosen = previous[-1]

        pop = _population(sent_text)
        if pop is None:
            # Population may carry only when explicitly referenced in the same
            # sentence or there is a unique unambiguous population globally.
            global_labels = v052.population_labels(t)
            if len(global_labels) == 1:
                pop = global_labels[0]

        pol = _management_polarity(sent_text, e["event_type"], local_event_pos)
        conditions = chosen["condition"] if chosen else []
        trace = {
            "scope": "v0.5.3_sentence_typed_binding",
            "sentence_id": si,
            "condition_source": "typed_local_or_anaphoric" if chosen else "none",
        }
        if e["event_type"] == "INITIATION_RESTRICTION":
            rebuilt.append(_frame(e["event_type"], "drug_initiation", "initiation", polarity=pol, conditions=conditions, population=pop, span=sent_text, family="v0.5.3:management_typed", trace=trace))
        elif e["event_type"] == "BENEFIT_RISK_REASSESSMENT":
            rebuilt.append(_frame(e["event_type"], "drug_use", "benefit_risk", polarity=pol, conditions=conditions, population=pop, span=sent_text, family="v0.5.3:management_typed", trace=trace))
        elif e["event_type"] == "DISCONTINUATION":
            rebuilt.append(_frame(e["event_type"], "drug_use", "drug", polarity=pol, conditions=conditions, population=pop, span=sent_text, modality="LIMITED" if pol == "NEGATIVE" else "ASSERTED", family="v0.5.3:management_typed", trace=trace))
        elif e["event_type"] == "CONTRAINDICATION":
            rebuilt.append(_frame(e["event_type"], "drug_use", "use", polarity=pol, conditions=conditions, population=None, span=sent_text, modality="LIMITED" if pol == "NEGATIVE" else "ASSERTED", family="v0.5.3:management_typed", trace=trace))
    return non_mgmt + rebuilt


def add_relation_repairs(text: str, frames: list[dict[str, Any]]) -> None:
    t = n(text)
    trace = {"scope": "v0.5.3_relation_direction_polarity"}

    # Causality: direction/semantic family is fixed; polarity is evaluated
    # independently from modal wording.
    if re.search(r"\b(?:causation|causality|causal|caused|proof of causation)\b", t):
        neg = bool(
            re.search(r"\b(?:cannot|can not|does not|do not|must not|should not|not sufficient|insufficient)\b[^.;]{0,110}(?:caus|proof)", t)
            or re.search(r"\bnot\s+(?:be\s+)?treated\s+as\s+proof\b", t)
            or re.search(r"\bneither\b[^.;]{0,100}\bestablish(?:es)?\s+caus", t)
        )
        pos = bool(re.search(r"\b(?:establishes?|proves?|confirms?)\b[^.;]{0,70}\bcaus", t))
        if neg or pos:
            frames.append(_frame("CAUSALITY_ESTABLISHMENT", "evidence", "causal_relation", polarity="NEGATIVE" if neg else "POSITIVE", span=text, modality="LIMITED" if neg else "ASSERTED", family="v0.5.3:causality", trace=trace))

    # Endpoint absence-of-result: several surface realizations map to the same
    # negative evidence proposition.
    endpoint_context = bool(re.search(r"primary(?: efficacy)?\s+(?:endpoint|outcome)|endpoint\s+achievement", t))
    endpoint_negative = bool(
        re.search(r"\bno\b[^.;]{0,80}(?:result|finding|evidence)[^.;]{0,100}(?:met|achiev\w*|success|establish\w*)", t)
        or re.search(r"\b(?:does not|cannot|is not)\b[^.;]{0,100}(?:constitute|establish|show|demonstrate|confirm)[^.;]{0,100}(?:efficacy\s+result|endpoint|outcome|achiev)", t)
        or re.search(r"\bsuspension\b[^.;]{0,70}\bnot\s+evidence\b[^.;]{0,60}\bendpoint\b", t)
    )
    if endpoint_context and endpoint_negative:
        frames.append(_frame("ENDPOINT_ACHIEVEMENT_EVIDENCE", "evidence", "primary_endpoint", polarity="NEGATIVE", span=text, modality="LIMITED", family="v0.5.3:endpoint_absence", trace=trace))

    # Preserve explicit study status including SUSPENDED; this is typed as a
    # trial-state relation and must never trigger a medication-action guard.
    sm = re.search(r"\b(?:study|trial)\s+(?:is|remains|was)\s+(ACTIVE,?\s+NOT\s+RECRUITING|RECRUITING|COMPLETED|TERMINATED|SUSPENDED)\b", text, re.I)
    if sm:
        status = n(sm.group(1)).replace(",", "").replace(" ", "_")
        frames.append(_frame("STUDY_STATUS", "study", status, span=sm.group(0), family="v0.5.3:typed_trial_status", trace=trace))
    if re.search(r"primary(?: efficacy)?\s+(?:endpoint|outcome)", t) and re.search(r"\b(?:defined|specified|listed|identif\w*|prespecified)\b", t):
        frames.append(_frame("PRIMARY_ENDPOINT_DECLARATION", "study", "primary_endpoint", span=text, family="v0.5.3:endpoint_declaration", trace=trace))

    # Guideline supersession: canonical direction and polarity are separate.
    passive = re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:is|was|has been)\s+(not\s+)?(?:replaced|superseded|displaced)\s+by\s+(guideline\s+[a-z0-9._-]+)", t)
    active = re.search(r"(guideline\s+[a-z0-9._-]+)\s+(did\s+not\s+)?(?:replace|replaced|supersede|superseded|displace|displaced)\s+(guideline\s+[a-z0-9._-]+)", t)
    newer = older = None
    neg = False
    if passive:
        older, newer = passive.group(1), passive.group(3)
        neg = bool(passive.group(2))
    elif active:
        newer, older = active.group(1), active.group(3)
        neg = bool(active.group(2))
    if newer and older:
        newer = n(newer).strip(" .,:;")
        older = n(older).strip(" .,:;")
        frames.append(_frame("SUPERSESSION", newer, older, polarity="NEGATIVE" if neg else "POSITIVE", span=text, modality="LIMITED" if neg else "ASSERTED", family="v0.5.3:supersession", trace=trace))
        if not neg:
            frames.append(_frame("CURRENTNESS", newer, "recommendation_source", span=text, family="v0.5.3:supersession_currentness", trace=trace))
            frames.append(_frame("CURRENTNESS", older, "recommendation_source", polarity="NEGATIVE", span=text, modality="LIMITED", family="v0.5.3:supersession_currentness", trace=trace))

    # Explicit currentness independent of supersession wording.
    cm = re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:remains|is)\s+(?:the\s+)?(?:current|operative)\s+(?:recommendation\s+)?source", t)
    if cm:
        frames.append(_frame("CURRENTNESS", n(cm.group(1)).strip(" .,:;"), "recommendation_source", span=text, family="v0.5.3:explicit_currentness", trace=trace))

    # Trial option support.  Canonical direction is always trial -> option;
    # polarity is derived independently, including negated passive forms.
    pm = re.search(r"(?:option|strategy|treatment)\s+([a-z0-9._-]+)\s+(?:is|was)\s+(not\s+)?(?:supported|favored|favoured)\s+by\s+(?:the\s+)?(?:randomized\s+)?(?:trial|study|experiment)", t)
    if pm:
        frames.append(_frame("TRIAL_OPTION_SUPPORT", "trial", v04.token(pm.group(1)), polarity="NEGATIVE" if pm.group(2) else "POSITIVE", span=text, modality="LIMITED" if pm.group(2) else "ASSERTED", family="v0.5.3:passive_trial_support", trace=trace))
    am = re.search(r"(?:randomized\s+)?(?:trial|study|experiment)[^.;]{0,80}(does\s+not\s+|did\s+not\s+|not\s+)?(?:supports?|favors?|favours?)\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)", t)
    if am:
        frames.append(_frame("TRIAL_OPTION_SUPPORT", "trial", v04.token(am.group(2)), polarity="NEGATIVE" if am.group(1) else "POSITIVE", span=text, modality="LIMITED" if am.group(1) else "ASSERTED", family="v0.5.3:active_trial_support", trace=trace))
    gm = re.search(r"(?:current(?:ly)?\s+|currently\s+operative\s+)?guideline[^.;]{0,110}(?:still\s+|continues?\s+to\s+)?recommends?\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)", t)
    if gm:
        frames.append(_frame("CURRENTNESS", "current_guideline", v04.token(gm.group(1)), span=text, family="v0.5.3:guideline_recommendation", trace=trace))

    # Passive/inverse association with polarity separated from argument order.
    inv = re.search(r"(outcome\s+[a-z0-9._-]+)\s+(?:was|is)\s+(not\s+)?(?:found\s+to\s+be\s+)?associated\s+with\s+(biomarker\s+[a-z0-9._-]+)", t)
    if inv:
        frames.append(_frame("ASSOCIATION", v04.token(inv.group(3)), v04.token(inv.group(1)), polarity="NEGATIVE" if inv.group(2) else "POSITIVE", span=text, modality="LIMITED" if inv.group(2) else "ASSERTED", family="v0.5.3:inverse_association", trace=trace))


def type_aware_ontology_guard(text: str, frames: list[dict[str, Any]]) -> list[str]:
    """Return blocking reasons before any proposition can be emitted.

    The invariant is conservative: unsupported clinically consequential rule
    structure suppresses all propositions rather than allowing a lossy subset.
    """
    t = n(text)
    reasons: list[str] = []

    # Distinguish medication actions from study status words such as SUSPENDED.
    medication_action = bool(re.search(
        r"\b(?:stop|discontinu\w*|withdraw\w*|withhold|withheld|hold\s+(?:the\s+)?(?:dose|treatment)|"
        r"avoid\w*|coadministration|reduce\w*\s+(?:the\s+)?dose|dose\s+(?:should\s+be\s+)?(?:reduced|increased)|"
        r"continue\s+treatment\s+only\s+when|permanently\s+(?:stop|suspend))\b", t
    ))
    if not medication_action:
        return reasons

    # Negative statements about an action ("should not stop because age...")
    # are representable assertions, not unsupported positive management rules.
    negative_action = bool(
        re.search(r"\b(?:not|never)\b[^.;]{0,35}(?:stop|discontinu|withdraw)", t)
        or re.search(r"rather\s+than[^.;]{0,40}(?:stop|discontinu|withdraw)", t)
    )

    conditional = bool(re.search(r"\b(?:if|when|whenever|unless|only\s+when|otherwise|in\s+which\s+case)\b", t))
    branch_logic = bool(re.search(r"\b(?:either|both)\b[^.;]{0,180}\b(?:or|and)\b|\bif\b[^.;]{0,180}\bor\b|\bunless\b|\botherwise\b|\bexcept\b", t))
    unsupported_condition = bool(UNSUPPORTED_CONDITION_MARKER.search(t))
    unsupported_action = bool(re.search(
        r"\b(?:withhold|withheld|hold\s+(?:the\s+)?(?:dose|treatment)|avoid\w*|coadministration|"
        r"reduce\w*\s+(?:the\s+)?dose|dose\s+(?:should\s+be\s+)?(?:reduced|increased)|permanently\s+suspend)\b", t
    ))

    # A positive high-risk action conditioned on an unsupported variable must
    # abstain even when the action itself (e.g. DISCONTINUE) is representable.
    if conditional and unsupported_condition and not negative_action:
        reasons.append("critical condition variable is outside closed typed condition ontology")
    if branch_logic and unsupported_condition and not negative_action:
        reasons.append("nonrepresentable logical composition in critical management rule")
    if unsupported_action and not negative_action:
        reasons.append("critical management action is outside closed action ontology")

    return list(dict.fromkeys(reasons))


def unresolved_known_semantics(text: str, frames: list[dict[str, Any]]) -> list[str]:
    """Coverage guard for semantic families that are representable today."""
    t = n(text)
    types = {f.get("event_type") for f in frames}
    missing: list[str] = []
    checks = [
        (r"contraindicat", "CONTRAINDICATION"),
        (r"\b(?:discontinu\w*|withdraw\w*|stop(?:ping|ped)?)\b", "DISCONTINUATION"),
        (r"benefit[- ]?risk|benefit and risk|\breassessment\b(?=[^.;]{0,80}(?:egfr|renal|below|under))", "BENEFIT_RISK_REASSESSMENT"),
        (r"\b(?:causation|causality|causal|caused|proof of causation)\b", "CAUSALITY_ESTABLISHMENT"),
        (r"incidence", "INCIDENCE_ESTIMATION"),
    ]
    for pat, et in checks:
        if re.search(pat, t, re.I) and et not in types:
            missing.append(et)
    if re.search(r"primary(?: efficacy)?\s+(?:endpoint|outcome)|endpoint\s+achievement", t) and re.search(r"\b(?:no|not|does not|cannot)\b[^.;]{0,120}(?:result|evidence|constitute|establish|achiev)", t) and "ENDPOINT_ACHIEVEMENT_EVIDENCE" not in types:
        missing.append("ENDPOINT_ACHIEVEMENT_EVIDENCE")
    if re.search(r"guideline\s+[a-z0-9._-]+[^.;]{0,50}(?:replaced|superseded|displaced)|(?:replaced|superseded|displaced)\s+by\s+guideline", t) and "SUPERSESSION" not in types:
        missing.append("SUPERSESSION")
    if re.search(r"(?:option|strategy|treatment)\s+[a-z0-9._-]+[^.;]{0,50}(?:supported|favored|favoured)\s+by\s+(?:the\s+)?(?:randomized\s+)?(?:trial|study)", t) and "TRIAL_OPTION_SUPPORT" not in types:
        missing.append("TRIAL_OPTION_SUPPORT")
    return list(dict.fromkeys(missing))


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    base = v052.extract(item, legacy_cfg)
    text = item["text"]
    frames = [dict(f) for f in base["semantic_frames"]]

    # Rebuild only the management family; keep all other v0.5.2 relations.
    frames = rebuild_management_frames(text, frames)
    add_relation_repairs(text, frames)
    frames = _dedupe_frames(frames)

    guard = type_aware_ontology_guard(text, frames)
    if guard:
        propositions: list[dict[str, Any]] = []
        unresolved = [
            {
                "text": text,
                "reason": reason,
                "potentially_critical": True,
                "guard": "typed_ontology_coverage",
            }
            for reason in guard
        ]
        abstain = True
    else:
        missing = unresolved_known_semantics(text, frames)
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
            v04.compile_frame(f)
            for f in frames
            if f.get("event_type") in v04.FRAME_TO_PREDICATE
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
    print(f"Wrote {len(rows)} S3a v0.5.3 semantic-typing records to {out}")


if __name__ == "__main__":
    main()
