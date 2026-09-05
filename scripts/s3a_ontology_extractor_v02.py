#!/usr/bin/env python3
"""Ontology-guided deterministic baseline for S3a semantic proposition extraction.

This is intentionally separate from the historical end-to-end parser. It maps
free-text evidence/candidate statements into the constrained proposition ontology
used by S3b. It is still a deterministic baseline, not a substitute for a fully
validated semantic model.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "s3a-ontology-guided-v0.2.0"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("–", "-").replace("—", "-")).strip()


def prop(subject: str, predicate: str, object_: str, polarity: str, *, conditions=None, population=None, source_span=None, confidence=1.0):
    return {
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "polarity": polarity,
        "conditions": conditions or [],
        "population": population,
        "confidence": confidence,
        "source_span": source_span,
    }


def dedupe(props: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for p in props:
        key = (
            p.get("subject"), p.get("predicate"), p.get("object"), p.get("polarity"),
            tuple(sorted(tuple(sorted(c.items())) for c in p.get("conditions", []))),
            p.get("population"),
        )
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def egfr_conditions(text: str) -> list[dict[str, Any]]:
    t = norm(text)
    # Range forms: eGFR 30 through 45 / from eGFR 30 to 45 / between 30 and 45.
    for pat in [
        r"egfr\s*(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)",
        r"from\s+egfr\s*(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)",
        r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, t)
        if m:
            return [{"variable": "egfr", "operator": "RANGE", "low": float(m.group(1)) if "." in m.group(1) else int(m.group(1)), "high": float(m.group(2)) if "." in m.group(2) else int(m.group(2))}]

    # Point value generally appears in candidate statements.
    m = re.search(r"egfr\s*(?:of|=|is|at)?\s*(\d+(?:\.\d+)?)", t)
    if m and not re.search(r"(?:below|under|less than|lower than|<)\s*" + re.escape(m.group(1)), t):
        v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
        return [{"variable": "egfr", "operator": "EQ", "value": v}]

    m = re.search(r"(?:egfr[^.;,]{0,35})?(?:below|under|less than|lower than|<)\s*(\d+(?:\.\d+)?)", t)
    if m:
        v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
        return [{"variable": "egfr", "operator": "LT", "value": v}]
    return []


def clause_conditions(text: str, keyword: str) -> list[dict[str, Any]]:
    """Bind an eGFR condition to the clause containing a semantic keyword."""
    pieces = re.split(r"[;.]|\bbut\b|\bwhile\b|\bwhereas\b", text, flags=re.I)
    for piece in pieces:
        if keyword in norm(piece):
            c = egfr_conditions(piece)
            if c:
                return c
    return egfr_conditions(text)


def population_from_text(text: str) -> str | None:
    t = norm(text)
    if any(x in t for x in ["existing user", "already taking", "already receiving", "currently taking"]):
        return "existing_user"
    if any(x in t for x in ["new patient", "treatment initiation", "starting treatment", "initiation", "newly starting"]):
        return "new_or_initiating_user"
    return None


def canonical_token(raw: str) -> str:
    x = raw.lower().strip().strip(".,;:()[]{}")
    x = re.sub(r"[^a-z0-9]+", "_", x)
    return x.strip("_")


def add_management(text: str, props: list[dict[str, Any]], *, candidate: bool):
    t = norm(text)
    pop = population_from_text(text)

    if re.search(r"(?:initiation|starting treatment|start(?:ing)?)\b[^.;]{0,80}\bnot recommended\b|\bnot-recommended\s+interval", t):
        props.append(prop("drug_initiation", "INITIATION_NOT_RECOMMENDED", "initiation", "POSITIVE",
                          conditions=clause_conditions(text, "not recommended"), population=pop if pop != "existing_user" else pop,
                          source_span=text))

    if "contraindicat" in t:
        neg = bool(re.search(r"(?:does\s+not\s+constitute|does\s+not\s+make|not\s+contraindicated|not\s+an?\s+contraindication|no\s+contraindication)", t))
        props.append(prop("drug_use", "CONTRAINDICATED", "use", "NEGATIVE" if neg else "POSITIVE",
                          conditions=clause_conditions(text, "contraindicat"), population=None, source_span=text))

    if re.search(r"reassess(?:ed|ment|ing)?[^.;]{0,50}(?:benefit|risk)|benefit[- ]risk\s+reassessment", t):
        props.append(prop("drug_use", "REASSESS_BENEFIT_RISK", "benefit_risk", "POSITIVE",
                          conditions=clause_conditions(text, "reassess"), population=pop, source_span=text))

    if re.search(r"\bdiscontinu(?:e|ed|ation)\b|\bstop(?:ping)?\b", t):
        neg = bool(re.search(r"\b(?:not|no)\b[^.;]{0,30}(?:discontinu|stop)|without\s+(?:automatic\s+)?(?:discontinu|stop)", t))
        props.append(prop("drug_use", "DISCONTINUE", "drug", "NEGATIVE" if neg else "POSITIVE",
                          conditions=clause_conditions(text, "discontinu" if "discontinu" in t else "stop"), population=pop,
                          source_span=text))


def add_signal_causality_incidence(text: str, props: list[dict[str, Any]]):
    t = norm(text)
    if "signal" in t and any(x in t for x in ["identify", "detect", "detection", "contribute", "raise"]):
        props.append(prop("spontaneous_report_system", "SUPPORTS_SIGNAL_DETECTION", "safety_signal", "POSITIVE", source_span=text))

    causal_limit = bool(re.search(r"(?:cannot|does not|do not|not able to|fails to)\s+(?:by itself\s+|alone\s+|on its own\s+)?(?:establish|prove|distinguish)[^.;]{0,60}(?:causal|causation|caused|causality)|cannot\s+distinguish\s+causal\s+attribution", t))
    if causal_limit:
        props.append(prop("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "NEGATIVE", source_span=text))
    elif re.search(r"\b(?:proves?|establishes?)\b[^.;]{0,40}\bcaus(?:e|ed|al|ality)", t):
        props.append(prop("evidence", "ESTABLISHES_CAUSALITY", "causal_relation", "POSITIVE", source_span=text))

    if any(x in t for x in ["report count", "report counts", "raw report counts", "spontaneous-report count"]):
        if ("incidence" in t or "event rate" in t) and any(x in t for x in ["cannot", "does not", "no complete", "lacks a complete", "without a complete", "neither a complete"]):
            props.append(prop("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "NEGATIVE", source_span=text))
        elif ("incidence" in t or "event rate" in t) and any(x in t for x in ["estimate", "yield", "provides", "gives", "converted"]):
            props.append(prop("report_count", "ESTIMATES_TRUE_INCIDENCE", "event_incidence", "POSITIVE", source_span=text))


def add_trial(text: str, props: list[dict[str, Any]]):
    t = norm(text)
    # Study status.
    status_map = [
        ("active, not recruiting", "active_not_recruiting"),
        ("completed", "completed"),
        ("recruiting", "recruiting"),
        ("terminated", "terminated"),
    ]
    if "study" in t or "trial" in t:
        for phrase, status in status_map:
            if phrase in t:
                props.append(prop("study", "HAS_STATUS", status, "POSITIVE", source_span=text))
                break

    if re.search(r"(?:primary\s+(?:endpoint|outcome))\s+(?:is\s+)?(?:named|identified|prespecified|listed)|(?:names|identifies|lists)\s+(?:the\s+)?(?:prespecified\s+)?primary\s+(?:endpoint|outcome)", t):
        props.append(prop("study", "HAS_PRIMARY_ENDPOINT", "primary_endpoint", "POSITIVE", source_span=text))

    endpoint_limit = bool(re.search(r"(?:no|without)\s+(?:study[- ]?)?(?:result|evidence)[^.;]{0,70}(?:endpoint|outcome)[^.;]{0,40}(?:met|achieved)|(?:does not|cannot)\s+(?:establish|show)[^.;]{0,60}(?:endpoint|outcome)[^.;]{0,30}(?:met|achieved)", t))
    if endpoint_limit:
        props.append(prop("evidence", "ESTABLISHES_ENDPOINT_ACHIEVEMENT", "primary_endpoint", "NEGATIVE", source_span=text))
    elif re.search(r"(?:primary\s+)?(?:endpoint|outcome)\s+(?:was|is|has been)\s+(?:successfully\s+)?(?:met|achieved)", t):
        props.append(prop("study", "ACHIEVES_ENDPOINT", "primary_endpoint", "POSITIVE", source_span=text))


def add_temporal_guideline(text: str, props: list[dict[str, Any]]):
    t = norm(text)
    # Named guideline replacement: Guideline H replaces/supersedes Guideline G.
    m = re.search(r"(guideline\s+[a-z0-9._-]+)\s+(?:explicitly\s+)?(?:replaces|supersedes)\s+(guideline\s+[a-z0-9._-]+)", t)
    if m:
        newer = m.group(1)
        older = m.group(2)
        props.append(prop(newer, "SUPERSEDES", older, "POSITIVE", source_span=text))
        if any(x in t for x in ["current", "operative"]):
            props.append(prop(newer, "IS_CURRENT", "recommendation_source", "POSITIVE", source_span=text))
            props.append(prop(older, "IS_CURRENT", "recommendation_source", "NEGATIVE", source_span=text))

    # Current guideline recommendation preserved despite new trial evidence.
    m = re.search(r"(?:unchanged\s+)?current\s+guideline[^.;]{0,60}(?:still\s+)?recommends\s+([a-z0-9._-]+)", t)
    if m:
        obj = canonical_token(m.group(1))
        props.append(prop("current_guideline", "IS_CURRENT", obj, "POSITIVE", source_span=text))

    m = re.search(r"(?:randomized\s+)?trial[^.;]{0,50}(?:favors|supports)\s+(?:option\s+|treatment\s+)?([a-z0-9._-]+)", t)
    if m:
        props.append(prop("trial", "SUPPORTS_OPTION", canonical_token(m.group(1)), "POSITIVE", source_span=text))


def add_pgx_and_association(text: str, props: list[dict[str, Any]]):
    t = norm(text)
    if "genotype" in t and "exposure" in t and any(x in t for x in ["associated", "association", "higher", "increased"]):
        props.append(prop("genotype", "ASSOCIATED_WITH", "drug_exposure", "POSITIVE", source_span=text))
        if any(x in t for x in ["no therapeutic dose recommendation", "no dose recommendation", "no therapeutic-management recommendation", "no dosing rule"]):
            props.append(prop("mechanism_or_pk_evidence", "PROVIDES_MANAGEMENT_RULE", "drug_pair_or_patient", "NEGATIVE", source_span=text))

    # Explicit biomarker association/non-association.
    m = re.search(r"(biomarker\s+[a-z0-9._-]+)\s+is\s+(?:explicitly\s+)?(not\s+)?associated\s+with\s+(outcome\s+[a-z0-9._-]+)", t)
    if m:
        props.append(prop(canonical_token(m.group(1)), "ASSOCIATED_WITH", canonical_token(m.group(3)), "NEGATIVE" if m.group(2) else "POSITIVE", source_span=text))

    # Generic factor/exposure association, excluding genotype/biomarker cases already normalized above.
    if "genotype" not in t and "biomarker" not in t:
        m = re.search(r"(?:exposure\s+|factor\s+)?([a-z0-9._-]+)\s+(?:is\s+)?associated\s+with\s+(?:outcome\s+)?([a-z0-9._-]+)", t)
        if m:
            props.append(prop(canonical_token(m.group(1)), "ASSOCIATED_WITH", canonical_token(m.group(2)), "POSITIVE", source_span=text))


def add_diagnostic_category(text: str, props: list[dict[str, Any]]):
    t = norm(text)
    m = re.search(r"(?:pathology\s+summary|report|summary)[^.;]{0,60}(?:classifies|classified|labels)\s+(?:finding\s+[a-z0-9._-]+|lesion)\s+as\s+(benign|malignant|indeterminate)", t)
    if not m:
        m = re.search(r"(?:finding\s+[a-z0-9._-]+|lesion)\s+(?:is\s+)?(?:explicitly\s+)?(?:classified\s+as\s+)?(benign|malignant|indeterminate)", t)
    if m:
        props.append(prop("lesion", "CLASSIFIED_AS", m.group(1), "POSITIVE", source_span=text))


def extract_item(item: dict[str, Any]) -> dict[str, Any]:
    text = item["text"]
    candidate = item.get("role") == "candidate"
    props: list[dict[str, Any]] = []
    add_management(text, props, candidate=candidate)
    add_signal_causality_incidence(text, props)
    add_trial(text, props)
    add_temporal_guideline(text, props)
    add_pgx_and_association(text, props)
    add_diagnostic_category(text, props)
    props = dedupe(props)

    t = norm(text)
    critical_markers = ["contraindicat", "discontinu", "reassess", "causal", "incidence", "endpoint", "guideline", "dose", "benign", "malignant", "not associated"]
    unresolved = []
    if not props and any(x in t for x in critical_markers):
        unresolved.append({"text": text, "reason": "critical semantic content not mapped to canonical proposition", "potentially_critical": True})
    return {
        "predicted_propositions": props,
        "abstain": bool(unresolved),
        "unresolved_spans": unresolved,
        "extractor_version": VERSION,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        r = extract_item(item)
        rows.append({"item_id": item["item_id"], "role": item.get("role", "evidence"), **r})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.2 extraction records to {out}")


if __name__ == "__main__":
    main()
