#!/usr/bin/env python3
"""S3a v0.5.4 typed event graph + relation-family arbitration.

Development-only structural repair over v0.5.3.

Design principles:
1. Start from the mature v0.5.2 frame set instead of rebuilding whole families.
2. Attach typed condition/population/polarity mentions to event-local nodes.
3. Repair existing management frames in place; add a frame only when an event node
   has no matching base frame.
4. Generate canonical relation candidates, then arbitrate within each semantic
   family so repaired and contradictory legacy frames cannot coexist.
5. Run the ontology-coverage guard before proposition emission; unsupported
   high-risk rules must abstain and emit no simplified truth.

All v0.1-v0.5.2 suites are exposed development data for this version. No fresh
validation is created by this implementation.
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
import s3a_compositional_frame_parser_v053 as v053
import s3a_compositional_frame_parser_v05 as v05
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.4"
MANAGEMENT_TYPES = {
    "INITIATION_RESTRICTION",
    "CONTRAINDICATION",
    "BENEFIT_RISK_REASSESSMENT",
    "DISCONTINUATION",
}

NEW_POP_PATTERNS = [
    r"\btreatment[- ]naive\b",
    r"\bnew\s+starter\b",
    r"\bnew\s+(?:user|patient)\b",
    r"\bnewly\s+start(?:ed|ing)\b",
    r"\bbeing\s+newly\s+started\b",
    r"\b(?:patient|person)\s+(?:beginning|starting|commencing)\s+(?:therapy|treatment|the\s+medicine|the\s+drug)\b",
    r"\babout\s+to\s+(?:start|begin|commence)\b",
]
EXISTING_POP_PATTERNS = [
    r"\bexisting\s+(?:user|patient)s?\b",
    r"\bestablished\s+(?:user|patient)s?\b",
    r"\balready\s+(?:taking|receiving|on)\b",
    r"\b(?:patient|person|people|users?)\s+(?:already\s+)?(?:taking|continuing|maintained)\b",
    r"\b(?:someone|patient|person|persons|people)\s+continuing\s+(?:therapy|treatment|the\s+medicine|the\s+drug)\b",
    r"\bcontinuing\s+(?:patient|user)s?\b",
    r"\bcontinu(?:e|ing|es)\s+(?:the\s+)?(?:medicine|drug|therapy|treatment)\b",
]
NON_RENAL_LOCAL = re.compile(
    r"\b(?:age|platelets?(?:\s+count)?|ha?emoglobin|potassium|creatinine|"
    r"blood\s+pressure|oxygen\s+saturation|bilirubin|alanine\s+aminotransferase|alt|"
    r"qtc|torsades|dialysis|urine\s+output|fever|toxicity)\b",
    re.I,
)


def n(text: str) -> str:
    return v05.n(text)


def frame_key(f: dict[str, Any]):
    return (
        f.get("event_type"), f.get("subject"), f.get("object"), f.get("polarity"),
        f.get("population"),
        tuple(sorted(tuple(sorted(c.items())) for c in f.get("conditions", []))),
    )


def dedupe_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]; seen=set()
    for f in frames:
        k=frame_key(f)
        if k not in seen:
            seen.add(k); out.append(f)
    return out


def make_frame(event_type: str, subject: str, object_: str, *, polarity="POSITIVE",
               conditions=None, population=None, span=None, modality="ASSERTED",
               family="v0.5.4:typed_graph", trace=None) -> dict[str, Any]:
    f=v04.frame(event_type, subject=subject, object_=object_, polarity=polarity,
                conditions=conditions or [], population=population,
                source_span=span, modality=modality)
    f["trigger_family"]=family
    f["scope_trace"]=trace or {"scope":"v0.5.4_typed_event_graph"}
    return f


def population_labels_local(text: str) -> list[str]:
    t=n(text); out=[]
    if any(re.search(p,t,re.I) for p in NEW_POP_PATTERNS) or "newly started" in t:
        out.append("new_or_initiating_user")
    if any(re.search(p,t,re.I) for p in EXISTING_POP_PATTERNS):
        out.append("existing_user")
    # Reuse mature recognizer as an additive source, not a replacement.
    for lab in v052.population_labels(t):
        if lab not in out: out.append(lab)
    return out


def _sentence_events(text: str) -> list[dict[str, Any]]:
    t=n(text)
    sentences=v053.sentence_spans(t)
    events=v053._event_matches(t)
    out=[]
    for e in events:
        si=v053._sentence_index(sentences,e["start"])
        x=dict(e); x["sentence_id"]=si; x["sentence"]=sentences[si]
        out.append(x)
    return out


def _event_windows(text: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create non-overlapping event-local windows inside each sentence.

    Boundaries are placed midway between adjacent event mentions. This keeps a
    threshold adjacent to one action from being inherited by another action in
    compact coordinated clauses without requiring item-specific wording.
    """
    t=n(text); out=[]
    by_sentence: dict[int,list[dict[str,Any]]]={}
    for e in events: by_sentence.setdefault(e["sentence_id"],[]).append(e)
    for si, group in by_sentence.items():
        group=sorted(group,key=lambda x:x["start"])
        sent=group[0]["sentence"]
        for i,e in enumerate(group):
            left=sent["start"] if i==0 else (group[i-1]["start"]+e["start"])//2
            right=sent["end"] if i==len(group)-1 else (e["start"]+group[i+1]["start"])//2
            x=dict(e); x["window_start"]=left; x["window_end"]=right; x["window_text"]=t[left:right]
            out.append(x)
    return sorted(out,key=lambda x:x["start"])


def _event_polarity(event_type: str, local_text: str) -> str | None:
    s=n(local_text)
    if event_type=="CONTRAINDICATION":
        negative = bool(
            re.search(r"\b(?:not|no)\b[^.;]{0,80}(?:an?\s+)?contraindicat",s)
            or re.search(r"\b(?:inadequate|insufficient)\b[^.;]{0,120}(?:grounds|evidence|basis)?[^.;]{0,100}contraindicat",s)
            or re.search(r"\bneither\b[^.;]{0,140}\b(?:constitutes?|is)\b[^.;]{0,50}contraindicat",s)
            or re.search(r"\bdoes\s+not\b[^.;]{0,100}contraindicat",s)
        )
        return "NEGATIVE" if negative else "POSITIVE"
    if event_type=="DISCONTINUATION":
        negative = bool(
            re.search(r"\b(?:does|do|should|must|is|are)\s+not\b[^.;]{0,80}(?:trigger\s+)?(?:discontinu|stop|withdraw)",s)
            or re.search(r"\bnot\b[^.;]{0,45}(?:discontinu|stop|withdraw)",s)
            or re.search(r"rather\s+than[^.;]{0,55}(?:automatically\s+)?(?:discontinu|stop|withdraw)",s)
            or re.search(r"without[^.;]{0,45}(?:discontinu|stop|withdraw)",s)
        )
        return "NEGATIVE" if negative else "POSITIVE"
    return None


def _canonical_args(event_type: str):
    return {
        "INITIATION_RESTRICTION":("drug_initiation","initiation"),
        "CONTRAINDICATION":("drug_use","use"),
        "BENEFIT_RISK_REASSESSMENT":("drug_use","benefit_risk"),
        "DISCONTINUATION":("drug_use","drug"),
    }[event_type]


def repair_management_with_event_ownership(text: str, frames: list[dict[str, Any]]) -> None:
    t=n(text)
    events=_event_windows(t,_sentence_events(t))
    if not events: return
    conds=v053.typed_egfr_candidates(t)
    by_type: dict[str,list[dict[str,Any]]]={}
    for e in events:
        by_type.setdefault(e["event_type"],[]).append(e)
    frame_by_type={et:[f for f in frames if f.get("event_type")==et] for et in MANAGEMENT_TYPES}

    for et, nodes in by_type.items():
        existing=frame_by_type.get(et,[])
        for i,node in enumerate(nodes):
            local_conds=[c for c in conds if node["window_start"]<=c["start"]<node["window_end"]]
            chosen=min(local_conds,key=lambda c:abs(c["start"]-node["start"])) if local_conds else None
            local=node["window_text"]
            pops=population_labels_local(local)
            sentence_pops=population_labels_local(node["sentence"]["text"])
            pop=pops[0] if len(pops)==1 else (sentence_pops[0] if len(sentence_pops)==1 else None)
            if et=="INITIATION_RESTRICTION" and pop is None:
                # Initiation semantics intrinsically targets a new/initiating user.
                pop="new_or_initiating_user"
            pol=_event_polarity(et,local)

            if i < len(existing):
                f=existing[i]
                f.setdefault("scope_trace",{})["v054_event_owner"]={
                    "sentence_id":node["sentence_id"],
                    "window_start":node["window_start"],
                    "window_end":node["window_end"],
                }
                if chosen is not None:
                    f["conditions"]=chosen["condition"]
                    f["scope_trace"]["v054_condition"]="event_local_typed"
                else:
                    # In a multi-event sentence, an inherited renal condition is
                    # unsafe when the local event window is explicitly about a
                    # different variable or a negative/contrastive action.
                    multi=len([x for x in events if x["sentence_id"]==node["sentence_id"]])>1
                    local_nonrenal=bool(NON_RENAL_LOCAL.search(local))
                    negative_local=(pol=="NEGATIVE")
                    explicit_break=bool(re.search(r"\b(?:whereas|while|yet|but|rather\s+than|by\s+itself|merely|solely)\b",local))
                    if f.get("conditions") and (local_nonrenal or negative_local or (multi and explicit_break)) and not re.search(r"\bsame\s+egfr\b",local):
                        f["conditions"]=[]
                        f["scope_trace"]["v054_condition"]="dropped_unowned_cross_event_condition"
                if pop is not None:
                    f["population"]=pop
                    f["scope_trace"]["v054_population"]="event_or_sentence_typed"
                if pol is not None:
                    f["polarity"]=pol
                    f["modality"]="LIMITED" if pol=="NEGATIVE" else "ASSERTED"
                    f["scope_trace"]["v054_polarity"]="event_local"
            else:
                subject,obj=_canonical_args(et)
                conditions=chosen["condition"] if chosen else []
                polarity=pol or "POSITIVE"
                frames.append(make_frame(et,subject,obj,polarity=polarity,conditions=conditions,
                                         population=None if et=="CONTRAINDICATION" else pop,
                                         span=local,modality="LIMITED" if polarity=="NEGATIVE" else "ASSERTED",
                                         family="v0.5.4:event_owner_add",
                                         trace={"scope":"event_local","sentence_id":node["sentence_id"]}))


def _remove_family(frames: list[dict[str, Any]], event_type: str, predicate) -> None:
    frames[:]=[f for f in frames if not (f.get("event_type")==event_type and predicate(f))]


def relation_family_arbitration(text: str, frames: list[dict[str, Any]]) -> None:
    """Add canonical relation candidates and remove semantically conflicting legacy frames."""
    t=n(text)
    tr={"scope":"v0.5.4_relation_family_arbitration"}

    # Causality: relation-local negation, including modal proof wording.
    if re.search(r"\b(?:causation|causality|causal|caused|proof\s+of\s+causation)\b",t):
        neg=bool(
            re.search(r"\b(?:cannot|can\s+not|does\s+not|do\s+not|must\s+not|should\s+not)\b[^.;]{0,130}(?:caus|proof)",t)
            or re.search(r"\bnot\s+(?:be\s+)?treated\s+as\s+proof\b",t)
            or re.search(r"\bneither\b[^.;]{0,120}\bestablish(?:es)?\s+caus",t)
        )
        if neg:
            _remove_family(frames,"CAUSALITY_ESTABLISHMENT",lambda f:f.get("polarity")!="NEGATIVE")
            frames.append(make_frame("CAUSALITY_ESTABLISHMENT","evidence","causal_relation",polarity="NEGATIVE",
                                     span=text,modality="LIMITED",family="v0.5.4:causality",trace=tr))

    # Endpoint roles: declaration and achievement are different event families.
    endpoint=bool(re.search(r"primary(?:\s+efficacy)?\s+(?:endpoint|outcome)|endpoint\s+achievement",t))
    achieved=bool(endpoint and re.search(r"primary(?:\s+efficacy)?\s+(?:endpoint|outcome)[^.;]{0,45}\b(?:was|is|has\s+been)?\s*(?:achieved|attained|met)\b",t))
    neg_evidence=bool(endpoint and (
        re.search(r"\b(?:no|not)\b[^.;]{0,110}(?:result|evidence|finding)[^.;]{0,130}(?:achiev|attain|met|endpoint|efficacy)",t)
        or re.search(r"\b(?:does\s+not|cannot|is\s+not)\b[^.;]{0,110}(?:constitute|establish|show|demonstrate|confirm)[^.;]{0,100}(?:efficacy\s+result|endpoint|outcome|achiev)",t)
        or re.search(r"\b(?:suspension|termination|enrollment|recruitment)[^.;]{0,90}\bnot\s+(?:evidence|proof)\b[^.;]{0,90}\bendpoint\b",t)
    ))
    declaration_verb=bool(
        re.search(r"(?:registry|record|study|trial)[^.;]{0,80}\b(?:specifies|lists|identifies|defines|records)\b[^.;]{0,60}primary(?:\s+efficacy)?\s+(?:endpoint|outcome)",t)
        or re.search(r"primary(?:\s+efficacy)?\s+(?:endpoint|outcome)\s+(?:is|was|remains)\s+(?:defined|specified|listed|identified)",t)
    )
    if achieved:
        frames.append(make_frame("ENDPOINT_ACHIEVEMENT","study","primary_endpoint",span=text,family="v0.5.4:endpoint_achievement",trace=tr))
        if not declaration_verb:
            _remove_family(frames,"PRIMARY_ENDPOINT_DECLARATION",lambda f:True)
    if neg_evidence:
        _remove_family(frames,"ENDPOINT_ACHIEVEMENT",lambda f:True)
        frames.append(make_frame("ENDPOINT_ACHIEVEMENT_EVIDENCE","evidence","primary_endpoint",polarity="NEGATIVE",
                                 span=text,modality="LIMITED",family="v0.5.4:endpoint_negative_evidence",trace=tr))
    if endpoint and declaration_verb:
        frames.append(make_frame("PRIMARY_ENDPOINT_DECLARATION","study","primary_endpoint",span=text,family="v0.5.4:endpoint_declaration",trace=tr))

    # Preserve typed study status; medication guards must not reinterpret it.
    sm=re.search(r"\b(?:study|trial)\s+(?:is|remains|was)\s+(ACTIVE,?\s+NOT\s+RECRUITING|RECRUITING|COMPLETED|TERMINATED|SUSPENDED)\b",text,re.I)
    if sm:
        status=n(sm.group(1)).replace(",","").replace(" ","_")
        frames.append(make_frame("STUDY_STATUS","study",status,span=sm.group(0),family="v0.5.4:study_status",trace=tr))

    # Trial support: support/favor/lend-support, active or passive, with generic option nouns.
    concrete=[]
    pass_pat=r"(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)\s+(?:is|was)\s+(not\s+)?(?:supported|favored|favoured)\s+by\s+(?:(?:a|an|the)\s+)?(?:randomized\s+)?(?:trial|study|experiment)"
    act_pat=r"(?:randomized\s+)?(?:trial|study|experiment)[^.;]{0,90}(does\s+not\s+|did\s+not\s+|not\s+)?(?:supports?|favors?|favours?)\s+(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)"
    lend_pat=r"(?:randomized\s+)?(?:trial|study|experiment)[^.;]{0,70}lends?\s+support\s+to\s+(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)"
    for m in re.finditer(pass_pat,t): concrete.append((v04.token(m.group(1)),"NEGATIVE" if m.group(2) else "POSITIVE"))
    for m in re.finditer(act_pat,t): concrete.append((v04.token(m.group(2)),"NEGATIVE" if m.group(1) else "POSITIVE"))
    for m in re.finditer(lend_pat,t): concrete.append((v04.token(m.group(1)),"POSITIVE"))
    if concrete:
        allowed={obj for obj,_ in concrete}
        _remove_family(frames,"TRIAL_OPTION_SUPPORT",lambda f:v04.token(str(f.get("object"))) not in allowed)
        for obj,pol in concrete:
            frames.append(make_frame("TRIAL_OPTION_SUPPORT","trial",obj,polarity=pol,span=text,
                                     modality="LIMITED" if pol=="NEGATIVE" else "ASSERTED",
                                     family="v0.5.4:trial_support",trace=tr))

    # Current guideline recommendation, including still-current/currently-operative variants.
    current=[]
    for m in re.finditer(r"(?:still[- ]current|current(?:ly)?(?:\s+operative)?|operative)\s+guideline[^.;]{0,100}(?:still\s+|continues?\s+to\s+)?recommends?\s+(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)",t):
        current.append(v04.token(m.group(1)))
    for m in re.finditer(r"current\s+guideline[^.;]{0,120}which[^.;]{0,60}(?:still\s+)?recommends?\s+(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)",t):
        current.append(v04.token(m.group(1)))
    if current:
        allowed=set(current)
        _remove_family(frames,"CURRENTNESS",lambda f:f.get("subject")=="current_guideline" and v04.token(str(f.get("object"))) not in allowed)
        for obj in current:
            frames.append(make_frame("CURRENTNESS","current_guideline",obj,span=text,family="v0.5.4:guideline_recommendation",trace=tr))

    # Guideline supersession: clean arguments, separate direction and polarity,
    # and derive currentness only for positive replacement.
    passive=re.search(r"(guideline\s+[a-z0-9_-]+)\s+(?:is|was|has\s+been)\s+(not\s+)?(?:replaced|superseded|displaced)\s+by\s+(guideline\s+[a-z0-9_-]+)",t)
    active=re.search(r"(guideline\s+[a-z0-9_-]+)\s+(did\s+not\s+)?(?:replace|replaced|supersede|superseded|displace|displaced)\s+(guideline\s+[a-z0-9_-]+)",t)
    newer=older=None; neg=False
    if passive:
        older,newer=passive.group(1),passive.group(3); neg=bool(passive.group(2))
    elif active:
        newer,older=active.group(1),active.group(3); neg=bool(active.group(2))
    if newer and older:
        newer=n(newer).strip(" .,:;"); older=n(older).strip(" .,:;")
        _remove_family(frames,"SUPERSESSION",lambda f:True)
        frames.append(make_frame("SUPERSESSION",newer,older,polarity="NEGATIVE" if neg else "POSITIVE",span=text,
                                 modality="LIMITED" if neg else "ASSERTED",family="v0.5.4:supersession",trace=tr))
        if not neg:
            frames.append(make_frame("CURRENTNESS",newer,"recommendation_source",span=text,family="v0.5.4:supersession_current",trace=tr))
            frames.append(make_frame("CURRENTNESS",older,"recommendation_source",polarity="NEGATIVE",span=text,modality="LIMITED",family="v0.5.4:supersession_current",trace=tr))

    # Explicit currentness with short anaphoric guideline symbols ("W remains...").
    cm=re.search(r"\b([a-z0-9_-]+)\s+remains\s+(?:the\s+)?(?:current|operative)\s+(?:recommendation\s+)?source\b",t)
    if cm:
        short=cm.group(1)
        if re.search(rf"\bguideline\s+{re.escape(short)}\b",t):
            frames.append(make_frame("CURRENTNESS",f"guideline {short}","recommendation_source",span=text,
                                     family="v0.5.4:anaphoric_currentness",trace=tr))

    # Inverse/passive biomarker association: canonical direction + local polarity.
    inv=re.search(r"(outcome\s+[a-z0-9_-]+)\s+(?:was|is)\s+(not\s+)?(?:found\s+to\s+be\s+)?associated\s+with\s+(biomarker\s+[a-z0-9_-]+)",t)
    if inv:
        subj=v04.token(inv.group(3)); obj=v04.token(inv.group(1)); pol="NEGATIVE" if inv.group(2) else "POSITIVE"
        _remove_family(frames,"ASSOCIATION",lambda f:v04.token(str(f.get("subject")))==subj and v04.token(str(f.get("object")))==obj)
        frames.append(make_frame("ASSOCIATION",subj,obj,polarity=pol,span=text,
                                 modality="LIMITED" if pol=="NEGATIVE" else "ASSERTED",
                                 family="v0.5.4:inverse_association",trace=tr))


def ontology_guard(text: str, frames: list[dict[str, Any]]) -> list[str]:
    reasons=list(v053.type_aware_ontology_guard(text,frames))
    t=n(text)
    # Close the older QTc/torsades passive morphology gap without treating trial
    # status SUSPENDED as a medication action.
    passive_permanent=bool(re.search(
        r"\b(?:therapy|treatment|medicine|drug|dose)\b[^.;]{0,45}\b(?:must|should|is\s+to\s+be)?\s*(?:be\s+)?permanent(?:ly)?\s+(?:suspend(?:ed|ion)?|stop(?:ped)?|discontinu(?:ed|ation)|withheld)\b",t
    ))
    qtc_torsades=bool(re.search(r"\b(?:qtc|torsades)\b",t))
    if passive_permanent and qtc_torsades:
        reasons.append("unsupported high-risk cardiac condition/action morphology")
    return list(dict.fromkeys(reasons))


def coverage_guard(text: str, frames: list[dict[str, Any]]) -> list[str]:
    """Representable-family coverage check after arbitration."""
    return v053.unresolved_known_semantics(text,frames)


def extract(item: dict[str, Any], legacy_cfg: dict[str, Any]) -> dict[str, Any]:
    base=v052.extract(item,legacy_cfg)
    text=item["text"]
    frames=[dict(f) for f in base["semantic_frames"]]

    # Non-destructive repair: mutate only event-owned fields and arbitrate
    # relation conflicts. Mature unrelated v0.5.2 frames remain intact.
    repair_management_with_event_ownership(text,frames)
    relation_family_arbitration(text,frames)
    frames=dedupe_frames(frames)

    guard=ontology_guard(text,frames)
    if guard:
        propositions=[]
        unresolved=[{"text":text,"reason":r,"potentially_critical":True,"guard":"typed_ontology_coverage"} for r in guard]
        abstain=True
    else:
        missing=coverage_guard(text,frames)
        unresolved=[{"text":text,"reason":f"representable critical semantic family unresolved: {m}","potentially_critical":True,"guard":"semantic_coverage"} for m in missing]
        propositions=v04.dedupe_props([v04.compile_frame(f) for f in frames if f.get("event_type") in v04.FRAME_TO_PREDICATE])
        abstain=bool(unresolved)

    return {
        "item_id":item["item_id"],
        "role":item.get("role","evidence"),
        "scope_nodes":base["scope_nodes"],
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
    print(f"Wrote {len(rows)} S3a v0.5.4 typed-event/arbitrated records to {out}")


if __name__=="__main__":
    main()
