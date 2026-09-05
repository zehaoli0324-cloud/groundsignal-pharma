#!/usr/bin/env python3
"""S3a v0.4 semantic-frame extractor.

Architecture:
text -> clause segmentation -> semantic event/relation frames -> argument binding
-> polarity/modality -> canonical proposition emission -> abstention metadata.

This is an exposed-regression development version. It does not claim fresh
generalization and must not be used to mark S3 as passed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "s3a-semantic-frame-v0.4.0"


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(text: str) -> str:
    text = text.lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token(raw: str) -> str:
    x = norm(raw).strip(".,;:()[]{}")
    x = re.sub(r"^(?:option|strategy|treatment)\s+", "", x)
    x = re.sub(r"[^a-z0-9]+", "_", x)
    return x.strip("_")


def prop(subject: str, predicate: str, object_: str, polarity: str, *, conditions=None, population=None, source_span=None, confidence=1.0):
    return {"subject": subject, "predicate": predicate, "object": object_, "polarity": polarity, "conditions": conditions or [], "population": population, "confidence": confidence, "source_span": source_span}


def dedupe_props(props: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for p in props:
        key = (p.get("subject"), p.get("predicate"), p.get("object"), p.get("polarity"), p.get("population"), tuple(sorted(tuple(sorted(c.items())) for c in p.get("conditions", []))))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def split_clauses(text: str) -> list[str]:
    parts = re.split(r"\s*;\s*|(?<=[.!?])\s+|\s+\b(?:but|whereas|while|yet)\b\s+", text, flags=re.I)
    return [p.strip(" ,") for p in parts if p.strip(" ,")]


def match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def population(text: str, cfg: dict[str, Any]) -> str | None:
    t = norm(text)
    for label, patterns in cfg["population_patterns"].items():
        if match_any(t, patterns):
            return label
    return None


def egfr_condition(text: str, context_text: str | None = None) -> list[dict[str, Any]]:
    t = norm(text)
    context = norm(context_text or text)
    for pat in [r"(?:egfr(?:\s+values?)?\s*)?(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)", r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)"]:
        m = re.search(pat, t)
        if m and ("egfr" in t or "renal function" in t):
            low = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            high = float(m.group(2)) if "." in m.group(2) else int(m.group(2))
            return [{"variable": "egfr", "operator": "RANGE", "low": low, "high": high}]
    for pat in [r"egfr(?:\s+is|\s+falls|\s+drops)?\s*(?:below|under|less\s+than|lower\s+than|<)\s*(\d+(?:\.\d+)?)", r"(?:below|under|less\s+than|lower\s+than|<)\s*egfr\s*(\d+(?:\.\d+)?)", r"(?:renal\s+function\s+)?(?:falls|drops)\s+(?:below|under)\s+egfr\s*(\d+(?:\.\d+)?)", r"(?:under|below)\s+egfr\s*(\d+(?:\.\d+)?)"]:
        m = re.search(pat, t)
        if m:
            v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            return [{"variable": "egfr", "operator": "LT", "value": v}]
    if "egfr" in context:
        m = re.search(r"(?:below|under|less\s+than|lower\s+than|<)\s*(\d+(?:\.\d+)?)", t)
        if m:
            v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            return [{"variable": "egfr", "operator": "LT", "value": v}]
    for pat in [r"(?:at|with)\s+egfr\s*(\d+(?:\.\d+)?)", r"egfr\s*(?:of|=|is|at)?\s*(\d+(?:\.\d+)?)"]:
        m = re.search(pat, t)
        if m:
            v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            return [{"variable": "egfr", "operator": "EQ", "value": v}]
    return []


def frame(event_type: str, *, subject: str, object_: str, polarity: str = "POSITIVE", conditions=None, population=None, source_span=None, confidence=1.0, modality="ASSERTED") -> dict[str, Any]:
    return {"event_type": event_type, "subject": subject, "object": object_, "polarity": polarity, "conditions": conditions or [], "population": population, "modality": modality, "confidence": confidence, "source_span": source_span}


FRAME_TO_PREDICATE = {"INITIATION_RESTRICTION": "INITIATION_NOT_RECOMMENDED", "CONTRAINDICATION": "CONTRAINDICATED", "BENEFIT_RISK_REASSESSMENT": "REASSESS_BENEFIT_RISK", "DISCONTINUATION": "DISCONTINUE", "SIGNAL_DETECTION": "SUPPORTS_SIGNAL_DETECTION", "CAUSALITY_ESTABLISHMENT": "ESTABLISHES_CAUSALITY", "INCIDENCE_ESTIMATION": "ESTIMATES_TRUE_INCIDENCE", "STUDY_STATUS": "HAS_STATUS", "PRIMARY_ENDPOINT_DECLARATION": "HAS_PRIMARY_ENDPOINT", "ENDPOINT_ACHIEVEMENT_EVIDENCE": "ESTABLISHES_ENDPOINT_ACHIEVEMENT", "ENDPOINT_ACHIEVEMENT": "ACHIEVES_ENDPOINT", "SUPERSESSION": "SUPERSEDES", "CURRENTNESS": "IS_CURRENT", "TRIAL_OPTION_SUPPORT": "SUPPORTS_OPTION", "ASSOCIATION": "ASSOCIATED_WITH", "MANAGEMENT_RULE_AVAILABILITY": "PROVIDES_MANAGEMENT_RULE", "DIAGNOSTIC_CLASSIFICATION": "CLASSIFIED_AS"}


def compile_frame(f: dict[str, Any]) -> dict[str, Any]:
    return prop(f["subject"], FRAME_TO_PREDICATE[f["event_type"]], f["object"], f["polarity"], conditions=f.get("conditions"), population=f.get("population"), source_span=f.get("source_span"), confidence=f.get("confidence", 1.0))


def management_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    global_pop = population(text, cfg)
    for clause in split_clauses(text):
        t = norm(clause)
        cond = egfr_condition(clause, text)
        pop = population(clause, cfg) or global_pop
        if match_any(t, cfg["event_triggers"]["initiation_restriction"]):
            out.append(frame("INITIATION_RESTRICTION", subject="drug_initiation", object_="initiation", conditions=cond, population=pop, source_span=clause))
        if "contraindicat" in t:
            neg = match_any(t, cfg["negation_patterns"]["contraindication"])
            out.append(frame("CONTRAINDICATION", subject="drug_use", object_="use", polarity="NEGATIVE" if neg else "POSITIVE", conditions=cond, population=None, source_span=clause))
        if match_any(t, cfg["event_triggers"]["benefit_risk_reassessment"]):
            out.append(frame("BENEFIT_RISK_REASSESSMENT", subject="drug_use", object_="benefit_risk", conditions=cond, population=pop, source_span=clause))
        if match_any(t, cfg["event_triggers"]["discontinuation"]):
            neg = match_any(t, cfg["negation_patterns"]["discontinuation"])
            out.append(frame("DISCONTINUATION", subject="drug_use", object_="drug", polarity="NEGATIVE" if neg else "POSITIVE", conditions=cond, population=pop, source_span=clause))
    return out


def pharmacovigilance_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    reportish = match_any(t, cfg["domain_markers"]["report_system"])
    if reportish and "signal" in t and match_any(t, cfg["event_triggers"]["signal_detection"]):
        out.append(frame("SIGNAL_DETECTION", subject="spontaneous_report_system", object_="safety_signal", source_span=text))
    causalish = match_any(t, cfg["domain_markers"]["causality"])
    if causalish:
        if match_any(t, cfg["negation_patterns"]["causality"]):
            out.append(frame("CAUSALITY_ESTABLISHMENT", subject="evidence", object_="causal_relation", polarity="NEGATIVE", source_span=text))
        elif match_any(t, cfg["positive_patterns"]["causality"]):
            out.append(frame("CAUSALITY_ESTABLISHMENT", subject="evidence", object_="causal_relation", polarity="POSITIVE", source_span=text))
    countish = match_any(t, cfg["domain_markers"]["report_count"])
    if countish and match_any(t, cfg["domain_markers"]["incidence"]):
        neg = match_any(t, cfg["negation_patterns"]["incidence"])
        pos = match_any(t, cfg["positive_patterns"]["incidence"])
        if neg or pos:
            out.append(frame("INCIDENCE_ESTIMATION", subject="report_count", object_="event_incidence", polarity="NEGATIVE" if neg else "POSITIVE", source_span=text))
    return out


def trial_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    if match_any(t, cfg["domain_markers"]["study"]):
        for status, patterns in cfg["study_status_patterns"].items():
            if match_any(t, patterns):
                out.append(frame("STUDY_STATUS", subject="study", object_=status, source_span=text))
                break
    endpointish = match_any(t, cfg["domain_markers"]["primary_endpoint"])
    if endpointish and match_any(t, cfg["event_triggers"]["endpoint_declaration"]):
        out.append(frame("PRIMARY_ENDPOINT_DECLARATION", subject="study", object_="primary_endpoint", source_span=text))
    if endpointish and match_any(t, cfg["negation_patterns"]["endpoint_achievement"]):
        out.append(frame("ENDPOINT_ACHIEVEMENT_EVIDENCE", subject="evidence", object_="primary_endpoint", polarity="NEGATIVE", source_span=text))
    elif endpointish and match_any(t, cfg["positive_patterns"]["endpoint_achievement"]):
        out.append(frame("ENDPOINT_ACHIEVEMENT", subject="study", object_="primary_endpoint", polarity="POSITIVE", source_span=text))
    return out


def guideline_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    supersession = re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?(?:replaces|supersedes|displaces)\s+(guideline\s+[a-z0-9._-]+)", t)
    if supersession:
        newer, older = supersession.group(1), supersession.group(2)
        out.append(frame("SUPERSESSION", subject=newer, object_=older, source_span=text))
        if match_any(t, cfg["event_triggers"]["current_source"]):
            out.append(frame("CURRENTNESS", subject=newer, object_="recommendation_source", polarity="POSITIVE", source_span=text))
            out.append(frame("CURRENTNESS", subject=older, object_="recommendation_source", polarity="NEGATIVE", source_span=text))
    trial_support = re.search(r"(?:randomized\s+)?(?:trial|study|experiment)[^.;]{0,80}?(?:favors|supports)\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)", t)
    if trial_support:
        out.append(frame("TRIAL_OPTION_SUPPORT", subject="trial", object_=token(trial_support.group(1)), source_span=text))
    current_rec = re.search(r"(?:unchanged\s+)?current\s+guideline[^.;]{0,80}?(?:still\s+|continues?\s+to\s+)?recommends?\s+(?:option\s+|strategy\s+|treatment\s+)?([a-z0-9._-]+)", t)
    if current_rec:
        out.append(frame("CURRENTNESS", subject="current_guideline", object_=token(current_rec.group(1)), source_span=text))
    return out


def pgx_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    genotype_exposure = "genotype" in t and (("exposure" in t and match_any(t, cfg["event_triggers"]["association_positive"])) or "genotype-exposure relationship" in t)
    if genotype_exposure:
        out.append(frame("ASSOCIATION", subject="genotype", object_="drug_exposure", polarity="POSITIVE", source_span=text))
    if "genotype" in t and match_any(t, cfg["negation_patterns"]["management_rule"]):
        out.append(frame("MANAGEMENT_RULE_AVAILABILITY", subject="mechanism_or_pk_evidence", object_="drug_pair_or_patient", polarity="NEGATIVE", source_span=text))
    return out


def diagnostic_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    category = next((c for c in cfg["diagnostic_categories"] if re.search(rf"\b{re.escape(c)}\b", t)), None)
    if category and ("finding" in t or "lesion" in t) and match_any(t, cfg["event_triggers"]["diagnostic_classification"]):
        out.append(frame("DIAGNOSTIC_CLASSIFICATION", subject="lesion", object_=category, source_span=text))
    return out


def biomarker_frames(text: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    out = []
    patterns = [
        (r"(biomarker\s+[a-z0-9._-]+)\s+(?:is|was)?\s*(?:explicitly\s+)?(not\s+)?associated\s+with\s+(outcome\s+[a-z0-9._-]+)", 1, 3, "group2"),
        (r"(biomarker\s+[a-z0-9._-]+)\s+(?:shows?|showed)\s+no\s+association\s+with\s+(outcome\s+[a-z0-9._-]+)", 1, 2, "negative"),
        (r"(biomarker\s+[a-z0-9._-]+)\s+(?:is|was)\s+unrelated\s+to\s+(outcome\s+[a-z0-9._-]+)", 1, 2, "negative"),
        (r"no(?:\s+\w+){0,3}\s+association\s+between\s+(biomarker\s+[a-z0-9._-]+)\s+and\s+(outcome\s+[a-z0-9._-]+)", 1, 2, "negative"),
        (r"(?:a\s+)?relationship\s+between\s+(biomarker\s+[a-z0-9._-]+)\s+and\s+(outcome\s+[a-z0-9._-]+)", 1, 2, "positive")
    ]
    for pat, sidx, oidx, mode in patterns:
        m = re.search(pat, t)
        if not m:
            continue
        pol = "NEGATIVE" if mode == "negative" or (mode == "group2" and m.group(2)) else "POSITIVE"
        out.append(frame("ASSOCIATION", subject=token(m.group(sidx)), object_=token(m.group(oidx)), polarity=pol, source_span=text))
        break
    return out


def detect_frames(item: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    text = item["text"]
    frames = []
    frames.extend(management_frames(text, cfg))
    frames.extend(pharmacovigilance_frames(text, cfg))
    frames.extend(trial_frames(text, cfg))
    frames.extend(guideline_frames(text, cfg))
    frames.extend(pgx_frames(text, cfg))
    frames.extend(diagnostic_frames(text, cfg))
    frames.extend(biomarker_frames(text, cfg))
    seen = set(); out = []
    for f in frames:
        p = compile_frame(f)
        key = (p["subject"], p["predicate"], p["object"], p["polarity"], p.get("population"), tuple(sorted(tuple(sorted(c.items())) for c in p.get("conditions", []))))
        if key not in seen:
            seen.add(key); out.append(f)
    return out


def unresolved_critical(text: str, frames: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    t = norm(text)
    if not match_any(t, cfg["critical_markers"]):
        return []
    critical_events = set(cfg["critical_event_types"])
    if any(f["event_type"] in critical_events for f in frames):
        return []
    return [{"text": text, "reason": "critical semantic content detected but no canonical semantic frame emitted", "potentially_critical": True}]


def extract_item(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    frames = detect_frames(item, cfg)
    props = dedupe_props([compile_frame(f) for f in frames])
    unresolved = unresolved_critical(item["text"], frames, cfg)
    return {"item_id": item["item_id"], "role": item.get("role", "evidence"), "semantic_frames": frames, "predicted_propositions": props, "abstain": bool(unresolved), "unresolved_spans": unresolved, "extractor_version": VERSION}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", default="medical/configs/s3a-semantic-frame-v0.4.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = load_json(args.input); cfg = load_json(args.config)
    rows = [extract_item(item, cfg) for item in doc["items"]]
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.4 semantic-frame extraction records to {out}")


if __name__ == "__main__":
    main()
