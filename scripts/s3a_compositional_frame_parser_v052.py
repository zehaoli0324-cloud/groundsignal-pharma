#!/usr/bin/env python3
"""S3a v0.5.2 scope-safety repair (development / exposed regression only).

Architectural changes over v0.5.1:
1. event-aware local rebinding of eGFR conditions inside coordinated clauses;
2. conservative condition/population inheritance across contrastive scopes;
3. relation-specific passive/inverse argument normalization;
4. ontology-coverage guard: non-representable critical rules must abstain and
   suppress partial propositions rather than silently simplify them.

No fresh held-out should be created until all exposed proposition, abstention and
trace gates pass for this implementation.
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

import s3a_compositional_frame_parser_v051 as v051
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.2"

MANAGEMENT_TYPES = {
    "INITIATION_RESTRICTION",
    "CONTRAINDICATION",
    "BENEFIT_RISK_REASSESSMENT",
    "DISCONTINUATION",
}

EVENT_TRIGGERS = {
    "INITIATION_RESTRICTION": r"(?:initiat\w*|start\w*|begin\w*|commenc\w*)[^.;]{0,60}(?:not recommended|advised against|discourag\w*|rule against)",
    "CONTRAINDICATION": r"contraindicat\w*",
    "BENEFIT_RISK_REASSESSMENT": r"(?:benefit[- ]?risk|benefit and risk)[^.;]{0,60}(?:reassess\w*|review\w*|reconsider\w*)|(?:reassess\w*|review\w*|reconsider\w*)[^.;]{0,60}(?:benefit|risk)",
    "DISCONTINUATION": r"(?:discontinu\w*|withdraw\w*|stop(?:ping|ped)?|stopped)",
}

EXISTING_POP = [
    r"\bexisting\s+(?:users?|patients?)\b",
    r"\balready\s+(?:taking|receiving|on)\b",
    r"\b(?:people|patients?|users?)\s+(?:continuing|maintained)\b",
    r"\bcontinu(?:e|ing|es)\s+(?:the\s+)?(?:medicine|drug|therapy|treatment)\b",
    r"\bestablished\s+(?:users?|patients?)\b",
    r"\bmaintained\s+on\b",
]
NEW_POP = [
    r"\bnew\s+(?:users?|patients?)\b",
    r"\babout\s+to\s+(?:start|begin|commence)\b",
    r"\b(?:beginning|commencing|starting)\s+(?:the\s+)?(?:medicine|drug|therapy|treatment)\b",
    r"\btherapy\s+commencement\b",
]


def n(text: str) -> str:
    return v05.n(text)


def _num(raw: str):
    return float(raw) if "." in raw else int(raw)


def _frame(event_type: str, subject: str, object_: str, *, polarity="POSITIVE", conditions=None,
           population=None, span=None, modality="ASSERTED", family="v0.5.2:repair", trace=None) -> dict[str, Any]:
    f = v04.frame(event_type, subject=subject, object_=object_, polarity=polarity,
                  conditions=conditions or [], population=population, source_span=span,
                  modality=modality)
    f["trigger_family"] = family
    f["scope_trace"] = trace or {"scope": "v0.5.2_structural_repair"}
    return f


def _dedupe_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]; seen=set()
    for f in frames:
        key=(f.get("event_type"),f.get("subject"),f.get("object"),f.get("polarity"),f.get("population"),
             tuple(sorted(tuple(sorted(c.items())) for c in f.get("conditions",[]))))
        if key not in seen:
            seen.add(key); out.append(f)
    return out


def population_labels(text: str) -> list[str]:
    t=n(text); out=[]
    if any(re.search(p,t,re.I) for p in NEW_POP): out.append("new_or_initiating_user")
    if any(re.search(p,t,re.I) for p in EXISTING_POP): out.append("existing_user")
    return out


def egfr_candidates(text: str, *, allow_elided: bool = False) -> list[dict[str, Any]]:
    t=n(text); hits=[]
    pats=[
        ("R",r"(?:egfr(?: values?)?\s*)?(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)"),
        ("R",r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)"),
        ("L",r"egfr(?:\s+(?:is|falls|drops|slips))?\s*(?:below|under|less\s+than|lower\s+than|<)\s*(\d+(?:\.\d+)?)"),
        ("L",r"(?:below|under|less\s+than|lower\s+than|<)\s*egfr\s*(\d+(?:\.\d+)?)"),
        ("E",r"(?:at|with)\s+(?:an?\s+)?egfr\s*(?:of\s*)?(\d+(?:\.\d+)?)"),
        ("E",r"egfr\s*(?:of|=|is|at)\s*(\d+(?:\.\d+)?)"),
    ]
    for kind,pat in pats:
        for m in re.finditer(pat,t,re.I):
            if kind=="R": cond=[{"variable":"egfr","operator":"RANGE","low":_num(m.group(1)),"high":_num(m.group(2))}]
            elif kind=="L": cond=[{"variable":"egfr","operator":"LT","value":_num(m.group(1))}]
            else: cond=[{"variable":"egfr","operator":"EQ","value":_num(m.group(1))}]
            hits.append({"start":m.start(),"end":m.end(),"condition":cond,"explicit":True})
    if allow_elided and "egfr" in t:
        for m in re.finditer(r"\b(?:below|under|less\s+than|lower\s+than)\s*(\d+(?:\.\d+)?)\b|<\s*(\d+(?:\.\d+)?)",t,re.I):
            raw=m.group(1) or m.group(2)
            if any(h["start"]<=m.start()<h["end"] for h in hits): continue
            hits.append({"start":m.start(),"end":m.end(),"condition":[{"variable":"egfr","operator":"LT","value":_num(raw)}],"explicit":False})
    hits.sort(key=lambda x:x["start"])
    return hits


def coordination_segments(text: str) -> list[dict[str, Any]]:
    """Split on semantic coordination boundaries while retaining character offsets."""
    t=n(text); cuts=[0]
    sep=re.compile(r"\s*;\s*|,\s*(?:and|but|whereas|while|yet)\s+|\s+(?:but|whereas|while|yet)\s+",re.I)
    for m in sep.finditer(t):
        cuts.extend([m.start(),m.end()])
    cuts.append(len(t)); cuts=sorted(set(cuts))
    out=[]
    for a,b in zip(cuts[::2],cuts[1::2]):
        if b<=a: continue
        s=t[a:b].strip(" ,;")
        if not s: continue
        real_start=t.find(s,a,b)
        out.append({"start":real_start,"end":real_start+len(s),"text":s})
    if not out: out=[{"start":0,"end":len(t),"text":t}]
    return out


def _event_positions(text: str, event_type: str) -> list[int]:
    pat=EVENT_TRIGGERS.get(event_type)
    return [m.start() for m in re.finditer(pat,n(text),re.I)] if pat else []


def _segment_for_pos(segments: list[dict[str, Any]], pos: int) -> dict[str, Any]:
    return next((s for s in segments if s["start"]<=pos<s["end"]), segments[0])


def repair_management_scope(text: str, frames: list[dict[str, Any]]) -> None:
    t=n(text); segments=coordination_segments(text); conds=egfr_candidates(t,allow_elided=True)
    global_pops=population_labels(t)
    grouped={et:[f for f in frames if f.get("event_type")==et] for et in MANAGEMENT_TYPES}

    for et, group in grouped.items():
        positions=_event_positions(t,et)
        for i,f in enumerate(group):
            pos=positions[min(i,len(positions)-1)] if positions else t.find(n(str(f.get("source_span") or "")))
            if pos<0: pos=0
            seg=_segment_for_pos(segments,pos)
            local=[c for c in conds if seg["start"]<=c["start"]<seg["end"]]
            if local:
                chosen=min(local,key=lambda c:abs(c["start"]-pos))
                f["conditions"]=chosen["condition"]
                f.setdefault("scope_trace",{})["condition_rebind"]="coordination_local_nearest"
            elif f.get("conditions") and seg["start"]>0:
                # Do not leak a renal condition across an independent/contrastive segment.
                f["conditions"]=[]
                f.setdefault("scope_trace",{})["condition_rebind"]="dropped_cross_segment_inheritance"

            if et in {"INITIATION_RESTRICTION","BENEFIT_RISK_REASSESSMENT","DISCONTINUATION"} and not f.get("population"):
                local_pops=population_labels(seg["text"])
                if len(local_pops)==1:
                    f["population"]=local_pops[0]
                    f.setdefault("scope_trace",{})["population_rebind"]="segment_local"
                elif len(global_pops)==1:
                    f["population"]=global_pops[0]
                    f.setdefault("scope_trace",{})["population_rebind"]="sentence_unique"


def repair_negation(frames: list[dict[str, Any]]) -> None:
    for f in frames:
        span=n(str(f.get("source_span") or ""))
        if f.get("event_type")=="CONTRAINDICATION":
            neg=bool(re.search(r"\b(?:is|are|was|were)\s+not(?:\s*,[^,]{0,60},\s*)?\s+(?:an?\s+)?contraindicat",span,re.I)
                     or re.search(r"\bdoes\s+not\s+(?:say|state|indicate|establish|mean)[^.;]{0,120}contraindicat",span,re.I)
                     or re.search(r"\b(?:insufficient|inadequate)[^.;]{0,100}contraindicat",span,re.I))
            if neg:
                f["polarity"]="NEGATIVE"; f["modality"]="LIMITED"
                f.setdefault("scope_trace",{})["negation_repair"]="target_local_interrupted"


def add_evidence_relations(text: str, frames: list[dict[str, Any]]) -> None:
    t=n(text); tr={"scope":"v0.5.2_relation_grammar"}
    # Pharmacovigilance signal + incidence.
    reportish=bool(re.search(r"\b(?:spontaneous|case reports?|reports?|report counts?|report totals?|those counts|number of spontaneous reports)\b",t))
    if reportish and "signal" in t and re.search(r"\b(?:alert|raise|flag|detect|surface|prompt|investigat|review|follow-up|useful)\w*\b",t):
        frames.append(_frame("SIGNAL_DETECTION","spontaneous_report_system","safety_signal",span=text,family="v0.5.2:pv_signal",trace=tr))
    if "incidence" in t and reportish:
        neg=bool(re.search(r"\b(?:do not|does not|cannot|can not)\b[^.;]{0,100}(?:estimate|represent|provide|give|yield|convert\w*\s+into)[^.;]{0,80}incidence",t)
                 or re.search(r"(?:denominator|exposed population)[^.;]{0,80}(?:incomplete|unknown|unavailable)",t)
                 or re.search(r"without[^.;]{0,80}denominator",t))
        pos=bool(re.search(r"\b(?:directly\s+)?(?:estimate|represent|provide|give|yield)\w*[^.;]{0,80}(?:true\s+)?(?:event\s+)?incidence",t))
        if neg or pos:
            frames.append(_frame("INCIDENCE_ESTIMATION","report_count","event_incidence",polarity="NEGATIVE" if neg else "POSITIVE",span=text,modality="LIMITED" if neg else "ASSERTED",family="v0.5.2:incidence_relation",trace=tr))

    # Endpoint declaration and absence-of-result evidence.
    endpoint=bool(re.search(r"primary(?: efficacy)?\s+(?:endpoint|outcome)",t))
    if endpoint and re.search(r"\b(?:define|defined|specif\w*|identif\w*|record\w*|list\w*)\b",t):
        frames.append(_frame("PRIMARY_ENDPOINT_DECLARATION","study","primary_endpoint",span=text,family="v0.5.2:endpoint_declaration",trace=tr))
    if endpoint and (re.search(r"\bno\s+(?:efficacy\s+)?result[^.;]{0,80}(?:available|posted|show\w*|demonstrat\w*|confirm\w*|establish\w*)",t)
                     or re.search(r"\bno\s+(?:posted\s+)?(?:result|finding|evidence)[^.;]{0,100}(?:achiev\w*|met|success|succeed\w*)",t)
                     or re.search(r"\bdoes\s+not\s+(?:show|establish|confirm)[^.;]{0,100}(?:endpoint|outcome|success)",t)):
        frames.append(_frame("ENDPOINT_ACHIEVEMENT_EVIDENCE","evidence","primary_endpoint",polarity="NEGATIVE",span=text,modality="LIMITED",family="v0.5.2:endpoint_absence",trace=tr))

    # Active and passive guideline supersession with direction normalization.
    passive=re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:is|was|has been)\s+(?:replaced|superseded|displaced)\s+by\s+(guideline\s+[a-z0-9._-]+)",t)
    active=re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:replaced|superseded|displaced)\s+(guideline\s+[a-z0-9._-]+)",t)
    newer=older=None
    if passive: older,newer=passive.group(1),passive.group(2)
    elif active: newer,older=active.group(1),active.group(2)
    if newer and older:
        frames.append(_frame("SUPERSESSION",newer,older,span=text,family="v0.5.2:supersession_direction",trace=tr))
        if re.search(r"\b(?:now|current|operative|has not changed|unchanged)\b",t):
            frames.append(_frame("CURRENTNESS",newer,"recommendation_source",span=text,family="v0.5.2:currentness",trace=tr))
            frames.append(_frame("CURRENTNESS",older,"recommendation_source",polarity="NEGATIVE",span=text,modality="LIMITED",family="v0.5.2:currentness",trace=tr))

    # Trial option support: normalize passive and active argument direction.
    m=re.search(r"(?:option|strategy|treatment)\s+([a-z0-9._-]+)\s+(?:is|was)\s+(?:supported|favored|favour(?:ed)?)\s+by\s+(?:the\s+)?(?:randomized\s+)?(?:trial|study|experiment)",t)
    if m:
        frames.append(_frame("TRIAL_OPTION_SUPPORT","trial",v04.token(m.group(1)),span=text,family="v0.5.2:passive_trial_support",trace=tr))
    m=re.search(r"(?:randomized\s+)?(?:trial|study|experiment)[^.;]{0,80}(?:supports?|favors?|favours?)\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)",t)
    if m:
        frames.append(_frame("TRIAL_OPTION_SUPPORT","trial",v04.token(m.group(1)),span=text,family="v0.5.2:active_trial_support",trace=tr))
    m=re.search(r"current\s+guideline[^.;]{0,100}(?:still\s+|continues?\s+to\s+)?recommends?\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)",t)
    if m:
        frames.append(_frame("CURRENTNESS","current_guideline",v04.token(m.group(1)),span=text,family="v0.5.2:guideline_recommendation",trace=tr))

    # PGx association vs absent management rule.
    if "genotype" in t and "exposure" in t and re.search(r"\b(?:association|relationship|correlat\w*|link\w*|increased|greater)\b",t):
        frames.append(_frame("ASSOCIATION","genotype","drug_exposure",span=text,family="v0.5.2:pgx_association",trace=tr))
    if "genotype" in t and re.search(r"\bno\b[^.;]{0,50}(?:dose|dosing|management|therapeutic)[^.;]{0,40}(?:rule|recommendation|instruction|advice)",t):
        frames.append(_frame("MANAGEMENT_RULE_AVAILABILITY","mechanism_or_pk_evidence","drug_pair_or_patient",polarity="NEGATIVE",span=text,modality="LIMITED",family="v0.5.2:management_absence",trace=tr))


def ontology_guard(text: str) -> list[dict[str, Any]]:
    """Return reasons when a critical rule cannot be losslessly represented."""
    t=n(text); reasons=[]
    critical_action=bool(re.search(r"\b(?:stop|discontinu\w*|withdraw\w*|suspend\w*|avoid\w*|dose\s+(?:should\s+be\s+)?(?:reduced|increased)|reduce\w*\s+(?:the\s+)?dose|coadministration)\b",t))
    unsupported_var=bool(re.search(r"\b(?:qtc|torsades|dialysis|cyp\d+[a-z0-9]*|poor[- ]metaboli\w*|therapeutic drug monitoring)\b",t))
    disjunctive=critical_action and bool(re.search(r"\b(?:either\b[^.;]{0,160}\bor\b|\bor\s+if\b|\bif\b[^.;]{0,160}\bor\b)",t))
    conditional_exception=critical_action and " unless " in f" {t} "
    unsupported_action=bool(re.search(r"\b(?:permanently\s+suspend\w*|suspend\w*|avoid\s+coadministration|dose\s+should\s+be\s+(?:reduced|increased)|reduce\w*\s+(?:the\s+)?dose)\b",t))
    if disjunctive and (unsupported_var or unsupported_action): reasons.append("nonrepresentable disjunctive critical condition")
    if conditional_exception: reasons.append("conditional exception is outside closed proposition schema")
    if unsupported_action: reasons.append("critical management action is outside closed action ontology")
    if critical_action and unsupported_var and not reasons: reasons.append("critical condition variable is outside closed condition ontology")
    return reasons


def unresolved_known_semantics(text: str, frames: list[dict[str, Any]]) -> list[str]:
    t=n(text); types={f.get("event_type") for f in frames}; missing=[]
    checks=[
        (r"contraindicat","CONTRAINDICATION"),
        (r"\b(?:discontinu\w*|withdraw\w*|stop(?:ping|ped)?)\b","DISCONTINUATION"),
        (r"benefit[- ]?risk|benefit and risk","BENEFIT_RISK_REASSESSMENT"),
        (r"\b(?:caus\w*|attribut\w*)\b","CAUSALITY_ESTABLISHMENT"),
        (r"incidence","INCIDENCE_ESTIMATION"),
    ]
    for pat,et in checks:
        if re.search(pat,t,re.I) and et not in types: missing.append(et)
    if re.search(r"primary(?: efficacy)?\s+(?:endpoint|outcome)",t) and re.search(r"\bno\b[^.;]{0,100}(?:result|finding|evidence)",t) and "ENDPOINT_ACHIEVEMENT_EVIDENCE" not in types:
        missing.append("ENDPOINT_ACHIEVEMENT_EVIDENCE")
    if re.search(r"guideline\s+[a-z0-9._-]+[^.;]{0,40}(?:replaced|superseded|displaced)|(?:replaced|superseded|displaced)\s+by\s+guideline",t) and "SUPERSESSION" not in types:
        missing.append("SUPERSESSION")
    return missing


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    row=v051.extract(item,legacy_cfg)
    frames=[dict(f) for f in row["semantic_frames"]]
    text=item["text"]

    repair_management_scope(text,frames)
    repair_negation(frames)
    add_evidence_relations(text,frames)
    frames=_dedupe_frames(frames)

    guard=ontology_guard(text)
    if guard:
        unresolved=[{"text":text,"reason":r,"potentially_critical":True,"guard":"ontology_coverage"} for r in guard]
        propositions=[]
        abstain=True
    else:
        missing=unresolved_known_semantics(text,frames)
        unresolved=[{"text":text,"reason":f"representable critical semantic family unresolved: {m}","potentially_critical":True,"guard":"semantic_coverage"} for m in missing]
        propositions=v04.dedupe_props([v04.compile_frame(f) for f in frames if f.get("event_type") in v04.FRAME_TO_PREDICATE])
        abstain=bool(unresolved)

    return {
        "item_id":item["item_id"],
        "role":item.get("role","evidence"),
        "scope_nodes":row["scope_nodes"],
        "semantic_frames":frames,
        "predicted_propositions":propositions,
        "abstain":abstain,
        "unresolved_spans":unresolved,
        "extractor_version":VERSION,
    }


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--legacy-config",default="medical/configs/s3a-semantic-frame-v0.4.json")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    doc=v05.load(args.input); cfg=v05.load(args.legacy_config)
    rows=[extract(item,cfg) for item in doc["items"]]
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"predictions":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.5.2 scope-safety records to {out}")

if __name__=="__main__":
    main()
