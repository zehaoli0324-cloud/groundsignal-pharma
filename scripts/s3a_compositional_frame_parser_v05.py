#!/usr/bin/env python3
"""S3a v0.5 compositional frame parser (development only).

text -> sentence/clause scope graph -> event-family recognition -> frame-local
argument/population/condition binding -> polarity/modality -> canonical proposition.

v0.4 remains an exposed-regression fallback only for event families that v0.5
fails to recognize. A v0.5 frame replaces same-type legacy frames rather than
unioning with them, preventing known legacy polarity/scope errors from surviving.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0, str(HERE))
import s3a_semantic_frame_extractor_v04 as v04

VERSION = "s3a-compositional-frame-v0.5.0"

NEW_POP = [r"\bnew(?:ly)?\s+(?:patient|user|start\w*)\b",r"\babout to begin\b",r"\bbeing newly started\b",r"\b(?:begin|commenc\w*|institut\w*)\s+(?:the )?(?:medicine|drug|therapy|treatment)\b",r"\btherapy (?:is )?first instituted\b",r"\binitiation\b"]
OLD_POP = [r"\bexisting (?:user|patient)\b",r"\balready (?:taking|receiving|on)\b",r"\bremain\w* on (?:therapy|treatment|the medicine|the drug)\b",r"\bcontinu\w* (?:the )?(?:medicine|drug|therapy|treatment)\b",r"\bcontinuing patient\b",r"\bestablished user\b",r"\bmaintained on\b",r"\bcurrently taking\b"]
NEG = [r"\bcannot\b",r"\bdoes not\b",r"\bdo not\b",r"\bnot sufficient\b",r"\binsufficient\b",r"\binadequate\b",r"\bno (?:evidence|result|finding|basis|grounds?|association|contraindication)\b",r"\bwithout (?:additional )?(?:evidence|findings?|basis|grounds?)\b",r"\bneither\b[^.;]{0,100}\bnor\b",r"\bno longer\b",r"\bnot automatic(?:ally)?\b"]
CRITICAL = [r"contraindicat",r"discontinu",r"withdraw",r"\bstop\b",r"benefit[- ]risk",r"reassess",r"reconsider",r"caus",r"attribut",r"incidence",r"primary .*?(?:endpoint|outcome)",r"guideline",r"dose",r"dosing",r"management",r"benign",r"malignant",r"indeterminate",r"biomarker",r"association",r"unrelated"]
CRITICAL_TYPES = {"INITIATION_RESTRICTION","CONTRAINDICATION","BENEFIT_RISK_REASSESSMENT","DISCONTINUATION","CAUSALITY_ESTABLISHMENT","INCIDENCE_ESTIMATION","ENDPOINT_ACHIEVEMENT_EVIDENCE","ENDPOINT_ACHIEVEMENT","SUPERSESSION","CURRENTNESS","MANAGEMENT_RULE_AVAILABILITY","DIAGNOSTIC_CLASSIFICATION","ASSOCIATION"}

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def n(s): return v04.norm(s)
def hit(s, pats): return any(re.search(p,s,re.I) for p in pats)
def tok(s): return v04.token(s)
def num(s): return float(s) if "." in s else int(s)

def F(t,sub,obj,pol="POSITIVE",cond=None,pop=None,span=None,mod="ASSERTED",family=None,trace=None):
    f=v04.frame(t,subject=sub,object_=obj,polarity=pol,conditions=cond or [],population=pop,source_span=span,modality=mod)
    f["trigger_family"]=family; f["scope_trace"]=trace or {}; return f

def conditions(text):
    t=n(text); hits=[]
    pats=[
      ("R",r"(?:egfr(?: values?)?\s*)?(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)"),
      ("R",r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)"),
      ("L",r"egfr(?:\s+(?:is|falls|drops|slips))?\s*(?:below|under|less than|lower than|<)\s*(\d+(?:\.\d+)?)"),
      ("L",r"(?:below|under|less than|lower than|<)\s*egfr\s*(\d+(?:\.\d+)?)"),
      ("L",r"(?:falls|drops|slips)\s+(?:below|under)\s+(?:egfr\s*)?(\d+(?:\.\d+)?)"),
      ("E",r"(?:at|with)\s+(?:an?\s+)?egfr\s*(?:of\s*)?(\d+(?:\.\d+)?)"),
      ("E",r"egfr\s*(?:of|=|is|at)\s*(\d+(?:\.\d+)?)")]
    for kind,p in pats:
      for m in re.finditer(p,t):
        if kind=="R" and "egfr" not in m.group(0) and "egfr" not in t[max(0,m.start()-30):m.end()+10]: continue
        if kind=="R": c=[{"variable":"egfr","operator":"RANGE","low":num(m.group(1)),"high":num(m.group(2))}]
        elif kind=="L": c=[{"variable":"egfr","operator":"LT","value":num(m.group(1))}]
        else: c=[{"variable":"egfr","operator":"EQ","value":num(m.group(1))}]
        hits.append((m.start(),c))
    hits.sort(); out=[]; seen=set()
    for _,c in hits:
      k=json.dumps(c,sort_keys=True)
      if k not in seen: seen.add(k); out.append(c)
    return out

def pops(text):
    t=n(text); out=[]
    if hit(t,NEW_POP): out.append("new_or_initiating_user")
    if hit(t,OLD_POP): out.append("existing_user")
    return out

def nodes(text):
    out=[]; nid=0
    for sid,sent in enumerate([x.strip(" ,") for x in re.split(r"(?<=[.!?])\s+",text) if x.strip(" ,")]):
      cs=conditions(sent); ps=pops(sent)
      clauses=[x.strip(" ,") for x in re.split(r"\s*;\s*|,?\s+\b(?:whereas|while|yet|but|nevertheless|however)\b\s+|,\s+although\s+",sent,flags=re.I) if x.strip(" ,")]
      for cid,c in enumerate(clauses):
        lc=conditions(c); lp=pops(c)
        out.append({"node_id":nid,"sentence_id":sid,"clause_id":cid,"text":c,"sentence":sent,
                    "condition":lc[0] if len(lc)==1 else (cs[0] if not lc and len(cs)==1 else []),
                    "local_populations":lp,"sentence_populations":ps,
                    "inherited_population":ps[0] if not lp and len(ps)==1 else None})
        nid+=1
    return out

def pop(node,init=False):
    lp=node["local_populations"]
    if len(lp)==1:return lp[0]
    if init and "existing_user" not in lp:return "new_or_initiating_user"
    return node["inherited_population"]

def neg_scope(t,target=None):
    t=n(t)
    if not hit(t,NEG): return False
    if not target:return True
    m=re.search(target,t,re.I)
    if not m:return False
    return hit(t[max(0,m.start()-140):m.end()+80],NEG)

def option(text,verbs):
    t=n(text)
    m=re.search(rf"(?:{verbs})[^.;,]{{0,45}}?(?:option|approach|strategy|treatment)\s+([a-z0-9._-]+)",t)
    if m:return tok(m.group(1))
    m=re.search(rf"(?:{verbs})\s+([a-z0-9._-]+)\b",t)
    if m and tok(m.group(1)) not in {"to","the","a","an","support","recommendation"}:return tok(m.group(1))
    return None

def detect(item):
    text=item["text"]; ns=nodes(text); fs=[]
    for x in ns:
      c=x["text"]; t=n(c); cond=x["condition"]; tr={"node_id":x["node_id"],"scope":"frame_local"}
      init=hit(t,[r"\binitiat\w*\b",r"\bstart\w*\b",r"\bbegin\w*\b",r"\bcommenc\w*\b",r"\binstitut\w*\b"]) and hit(t,[r"\bnot recommended\b",r"\badvised against\b",r"\bdiscourag\w*\b",r"\bshould not be initiated\b",r"\bshould not initiate\b",r"\brule against initiation\b"])
      if init: fs.append(F("INITIATION_RESTRICTION","drug_initiation","initiation",cond=cond,pop=pop(x,True),span=c,family="management:initiation",trace=tr))
      if re.search(r"\bcontraindicat\w*\b",t):
        q=neg_scope(t,r"contraindicat\w*") or hit(t,[r"\bdoes not treat\b[^.;]{0,100}contraindicat",r"\binadequate grounds\b[^.;]{0,100}contraindicat",r"\binsufficient\b[^.;]{0,100}contraindicat"])
        fs.append(F("CONTRAINDICATION","drug_use","use","NEGATIVE" if q else "POSITIVE",cond,None,c,"LIMITED" if q else "ASSERTED","management:contraindication",tr))
      if "benefit" in t and "risk" in t and hit(t,[r"reassess\w*",r"reconsider\w*",r"\breview\w*",r"\bassessment\b"]): fs.append(F("BENEFIT_RISK_REASSESSMENT","drug_use","benefit_risk",cond=cond,pop=pop(x),span=c,family="management:benefit_risk",trace=tr))
      if hit(t,[r"\bdiscontinu\w*\b",r"\bwithdraw\w*\b",r"\bstop(?:ping|ped)?\b"]):
        q=neg_scope(t,r"(?:discontinu\w*|withdraw\w*|stop\w*)")
        fs.append(F("DISCONTINUATION","drug_use","drug","NEGATIVE" if q else "POSITIVE",cond,pop(x),c,"LIMITED" if q else "ASSERTED","management:discontinuation",tr))
      report=hit(t,[r"\bspontaneous\b",r"\bcase reports?\b",r"\bpharmacovigilance\b",r"\bsurveillance\b"])
      if report and "signal" in t and hit(t,[r"signal",r"warning",r"flag\w*",r"detect\w*",r"surface\w*",r"investigat\w*",r"prompt\w*",r"trigger\w*"]): fs.append(F("SIGNAL_DETECTION","spontaneous_report_system","safety_signal",span=c,family="pv:signal",trace=tr))
      causal=hit(t,[r"\bcaus\w*\b",r"\battribut\w*\b"])
      if causal:
        q=neg_scope(t,r"(?:caus\w*|attribut\w*)"); posi=hit(t,[r"\b(?:establish|prove|demonstrate|confirm)\w*\b[^.;]{0,80}(?:caus|attribut)"])
        if q or posi: fs.append(F("CAUSALITY_ESTABLISHMENT","evidence","causal_relation","NEGATIVE" if q else "POSITIVE",span=c,mod="LIMITED" if q else "ASSERTED",family="evidence:causality",trace=tr))
      count=hit(t,[r"report counts?",r"report totals?",r"spontaneous[- ]case tally",r"tally of spontaneous cases",r"number of spontaneous reports",r"spontaneous cases"])
      if count and "incidence" in t:
        q=neg_scope(t,r"incidence") or hit(t,[r"unknown[^.;]{0,90}(?:population|denominator|size)",r"without[^.;]{0,90}denominator"]); posi=hit(t,[r"(?:represent|provide|give|yield|estimate)\w*[^.;]{0,90}(?:true )?(?:event'?s? )?incidence"])
        if q or posi: fs.append(F("INCIDENCE_ESTIMATION","report_count","event_incidence","NEGATIVE" if q else "POSITIVE",span=c,mod="LIMITED" if q else "ASSERTED",family="pv:incidence",trace=tr))
      if hit(t,[r"\bstudy\b",r"\btrial\b",r"\bregistry\b",r"\brecord\b"]):
        for st,p in [("active_not_recruiting",r"active,?\s*not recruiting"),("completed",r"\bcompleted\b"),("terminated",r"\bterminated\b"),("recruiting",r"\brecruiting\b")]:
          if re.search(p,t): fs.append(F("STUDY_STATUS","study",st,span=c,family="trial:status",trace=tr)); break
      ep=hit(t,[r"primary(?: efficacy)? endpoint",r"primary(?: efficacy)? outcome"]); sep=hit(n(x["sentence"]),[r"primary(?: efficacy)? endpoint",r"primary(?: efficacy)? outcome"])
      if ep and re.search(r"\b(?:specif\w*|identif\w*|defin\w*|list\w*|record\w*)\b",t): fs.append(F("PRIMARY_ENDPOINT_DECLARATION","study","primary_endpoint",span=c,family="trial:endpoint_declaration",trace=tr))
      if ep or sep:
        q=hit(t,[r"\bno\b[^.;]{0,80}(?:result|finding|evidence)[^.;]{0,120}(?:achiev\w*|attain\w*|met|succeed\w*|confirm\w*|demonstrat\w*)",r"\bdoes not\b[^.;]{0,100}(?:establish|show|confirm|demonstrate)[^.;]{0,80}(?:endpoint|outcome)"])
        posi=hit(t,[r"(?:endpoint|outcome)[^.;]{0,70}(?:was|is|has been)?\s*(?:successfully\s+)?(?:achiev\w*|attain\w*|met|succeed\w*)"])
        if q: fs.append(F("ENDPOINT_ACHIEVEMENT_EVIDENCE","evidence","primary_endpoint","NEGATIVE",span=c,mod="LIMITED",family="trial:endpoint_limit",trace=tr))
        elif posi: fs.append(F("ENDPOINT_ACHIEVEMENT","study","primary_endpoint",span=c,family="trial:endpoint_success",trace=tr))
      st=n(x["sentence"])
      if "genotype" in st:
        if "genotype" in t and "exposure" in t and hit(t,[r"association",r"relationship",r"correlat",r"link",r"tracks? with",r"increased",r"greater"]): fs.append(F("ASSOCIATION","genotype","drug_exposure",span=c,family="pgx:association",trace=tr))
        if "genotype-exposure relationship" in t: fs.append(F("ASSOCIATION","genotype","drug_exposure",span=c,family="pgx:association",trace=tr))
        if hit(t,[r"\bno\b[^.;]{0,70}(?:dose|dosing|therapeutic|management|patient-specific)[^.;]{0,70}(?:rule|directive|advice|instruction|recommendation)"]): fs.append(F("MANAGEMENT_RULE_AVAILABILITY","mechanism_or_pk_evidence","drug_pair_or_patient","NEGATIVE",span=c,mod="LIMITED",family="pgx:no_rule",trace=tr))
      if "lesion" in t or "finding" in t:
        cat=None
        m=re.search(r"(?:lesion|finding\s+[a-z0-9._-]+)[^.;]{0,70}?(?:is|as|to|category)\s+(benign|malignant|indeterminate)\b",t)
        if m:cat=m.group(1)
        if not cat:
          m=re.search(r"(?:assigns?|places?|classifies?|categorizes?|labels?|deems?|characterizes?|describes?)[^.;]{0,80}?(benign|malignant|indeterminate)\b",t); cat=m.group(1) if m else None
        if not cat and "rather than" in t:
          m=re.search(r"(?:lesion|finding)[^.;]{0,50}?\bis\s+(benign|malignant|indeterminate)\b\s+rather than",t); cat=m.group(1) if m else None
        if cat and hit(t,[r"classif",r"categoriz",r"label",r"deem",r"characteriz",r"describ",r"assign",r"place",r"diagnos",r"conclusion",r"category"]): fs.append(F("DIAGNOSTIC_CLASSIFICATION","lesion",cat,span=c,family="diagnosis:class",trace=tr))
      bm=re.search(r"\bbiomarker\s+([a-z0-9._-]+)\b",t); oc=re.search(r"\boutcome\s+([a-z0-9._-]+)\b",t)
      if bm and oc and hit(t,[r"association",r"associated",r"relationship",r"related",r"unrelated",r"observed"]):
        q=hit(t,[r"no(?:\s+\w+){0,4}\s+association",r"not associated",r"unrelated"])
        fs.append(F("ASSOCIATION",f"biomarker_{tok(bm.group(1))}",f"outcome_{tok(oc.group(1))}","NEGATIVE" if q else "POSITIVE",span=c,mod="LIMITED" if q else "ASSERTED",family="association:biomarker_outcome",trace={**tr,"argument_order":"canonical"}))
    for x in ns:
      c=x["text"]; t=n(c); tr={"node_id":x["node_id"],"direction":"surface_to_canonical"}; new=old=None
      m=re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:has\s+)?(?:replaces?|supersedes?|displaces?)\s+(guideline\s+[a-z0-9._-]+)",t)
      if m:new,old=n(m.group(1)),n(m.group(2))
      else:
        m=re.search(r"(guideline\s+[a-z0-9._-]+)[^.;]{0,90}?(?:retired\s+in\s+favor\s+of|replaced\s+by)\s+(?:guideline\s+)?([a-z0-9._-]+)",t)
        if m:old=n(m.group(1)); new="guideline "+tok(m.group(2))
      if new and old:
        fs += [F("SUPERSESSION",new,old,span=c,family="temporal:supersession",trace=tr)]
        if hit(t,[r"current",r"operative",r"in favor of",r"no longer"]): fs += [F("CURRENTNESS",new,"recommendation_source",span=c,family="temporal:current",trace=tr),F("CURRENTNESS",old,"recommendation_source","NEGATIVE",span=c,mod="LIMITED",family="temporal:stale",trace=tr)]
      refs=list(re.finditer(r"guideline\s+([a-z0-9._-]+)",t))
      if len(refs)==1:
        g=n(refs[0].group(0)); local=t[refs[0].start():refs[0].start()+90]; stale=bool(re.search(r"(?:no longer|not)[^.;]{0,30}(?:current|operative)",local))
        if stale: fs.append(F("CURRENTNESS",g,"recommendation_source","NEGATIVE",span=c,mod="LIMITED",family="temporal:stale",trace=tr))
        elif re.search(r"(?:remains?|is|serves? as|becomes)[^.;]{0,35}(?:current|operative)",local): fs.append(F("CURRENTNESS",g,"recommendation_source",span=c,family="temporal:current",trace=tr))
      o=option(t,r"(?:favors?|supports?|lends?\s+support\s+to)")
      if o and hit(t,[r"randomized",r"\btrial\b",r"\bstudy\b",r"experiment"]): fs.append(F("TRIAL_OPTION_SUPPORT","trial",o,span=c,family="guideline:trial_support",trace=tr))
      o=option(t,r"(?:recommends?|recommend|continues?\s+to\s+recommend)")
      if o and hit(t,[r"current guideline",r"still-current guideline",r"unchanged current guideline",r"guideline[^.;]{0,50}still recommends"]): fs.append(F("CURRENTNESS","current_guideline",o,span=c,family="guideline:current_recommendation",trace=tr))
    return dedupe(fs),ns

def dedupe(fs):
    out=[]; seen=set()
    for f in fs:
      p=v04.compile_frame(f); k=(p["subject"],p["predicate"],p["object"],p["polarity"],p.get("population"),tuple(sorted(tuple(sorted(c.items())) for c in p.get("conditions",[]))))
      if k not in seen:seen.add(k);out.append(f)
    return out

def extract(item,legacy_cfg):
    new,ns=detect(item); legacy=v04.detect_frames(item,legacy_cfg); override={f["event_type"] for f in new}; frames=dedupe(new+[f for f in legacy if f.get("event_type") not in override])
    props=v04.dedupe_props([v04.compile_frame(f) for f in frames]); unresolved=[]; t=n(item["text"])
    if hit(t,CRITICAL) and not any(f.get("event_type") in CRITICAL_TYPES for f in frames): unresolved=[{"text":item["text"],"reason":"critical semantic content detected but no v0.5/legacy frame emitted","potentially_critical":True}]
    return {"item_id":item["item_id"],"role":item.get("role","evidence"),"scope_nodes":ns,"semantic_frames":frames,"predicted_propositions":props,"abstain":bool(unresolved),"unresolved_spans":unresolved,"extractor_version":VERSION}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--legacy-config",default="medical/configs/s3a-semantic-frame-v0.4.json"); ap.add_argument("--out",required=True); a=ap.parse_args()
    doc=load(a.input); legacy=load(a.legacy_config); rows=[extract(i,legacy) for i in doc["items"]]; out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({"predictions":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"Wrote {len(rows)} S3a v0.5 compositional-frame records to {out}")
if __name__=="__main__": main()
