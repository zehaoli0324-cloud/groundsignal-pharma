#!/usr/bin/env python3
"""S3a semantic proposition extraction harness.

Backends:
- deterministic_baseline: current regex/rule extractor, for regression/lower-bound use
- openai_compatible: constrained semantic extraction through an OpenAI-compatible chat endpoint

This script parses benchmark/evaluation text only. It does not make clinical decisions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import model_harness
import s3_compositional_verifier_v054 as deterministic


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strip_json_wrapper(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```$", "", t)
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return t


def normalize_condition(c: dict[str, Any]) -> dict[str, Any]:
    out = {
        "variable": str(c.get("variable", "")).lower(),
        "operator": str(c.get("operator", "")).upper(),
    }
    for k in ["value", "low", "high"]:
        if c.get(k) is not None:
            out[k] = c[k]
    return out


def normalize_proposition(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": str(p.get("subject", "")).strip().lower(),
        "predicate": str(p.get("predicate", "")).strip().upper(),
        "object": p.get("object"),
        "polarity": str(p.get("polarity", "")).strip().upper(),
        "conditions": [normalize_condition(c) for c in (p.get("conditions") or [])],
        "population": p.get("population"),
        "confidence": float(p.get("confidence", 0.0)),
        "source_span": p.get("source_span"),
    }


def validate_semantic_output(payload: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    allowed_predicates = set(registry["predicates"])
    allowed_polarities = set(registry["allowed_polarities"])
    allowed_vars = set(registry.get("condition_variables", []))
    allowed_ops = set(registry.get("condition_operators", []))

    accepted = []
    unresolved = list(payload.get("unresolved_spans") or [])
    abstain = bool(payload.get("abstain", False))

    for raw in payload.get("propositions") or []:
        try:
            p = normalize_proposition(raw)
        except Exception as exc:
            unresolved.append({"text": str(raw), "reason": f"invalid proposition: {exc}", "potentially_critical": True})
            abstain = True
            continue

        errors = []
        if not p["subject"]:
            errors.append("empty subject")
        if p["predicate"] not in allowed_predicates:
            errors.append("predicate not in registry")
        if p["polarity"] not in allowed_polarities:
            errors.append("invalid polarity")
        if not 0.0 <= p["confidence"] <= 1.0:
            errors.append("confidence outside [0,1]")
        for c in p["conditions"]:
            if allowed_vars and c.get("variable") not in allowed_vars:
                errors.append("unknown condition variable")
            if c.get("operator") not in allowed_ops:
                errors.append("unknown condition operator")
            if c.get("operator") == "EQ" and c.get("value") is None:
                errors.append("EQ missing value")
            if c.get("operator") == "LT" and c.get("value") is None:
                errors.append("LT missing value")
            if c.get("operator") == "RANGE" and (c.get("low") is None or c.get("high") is None):
                errors.append("RANGE missing low/high")

        if errors:
            meta = registry.get("predicates", {}).get(p.get("predicate"), {})
            critical = bool(meta.get("critical", True))
            unresolved.append({
                "text": str(p.get("source_span") or raw),
                "reason": "; ".join(errors),
                "potentially_critical": critical,
            })
            abstain = abstain or critical
            continue
        accepted.append(p)

    if any(bool(x.get("potentially_critical")) for x in unresolved):
        abstain = True

    return {"propositions": accepted, "abstain": abstain, "unresolved_spans": unresolved}


def deterministic_extract(item: dict[str, Any]) -> dict[str, Any]:
    props = deterministic.parse_atomic(item["text"], candidate=item.get("role") == "candidate")
    normalized = []
    for p in props:
        q = {
            "subject": p.get("subject"),
            "predicate": p.get("predicate"),
            "object": p.get("object"),
            "polarity": p.get("polarity"),
            "conditions": p.get("conditions") or [],
            "population": p.get("population"),
            "confidence": float(p.get("confidence", 1.0)),
            "source_span": p.get("source_clause"),
        }
        normalized.append(q)
    return {"propositions": normalized, "abstain": False, "unresolved_spans": []}


def semantic_prompt(item: dict[str, Any], registry: dict[str, Any]) -> str:
    return (
        "PREDICATE_REGISTRY:\n"
        + json.dumps(registry, ensure_ascii=False, indent=2)
        + "\n\nTEXT_ROLE: "
        + str(item.get("role", "evidence"))
        + "\nTEXT:\n"
        + str(item["text"])
        + "\n\nReturn one JSON object matching the required output shape."
    )


def model_extract(item: dict[str, Any], cfg: dict[str, Any], registry: dict[str, Any], system_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    response, usage = model_harness.call_openai_compatible(cfg, system_prompt, semantic_prompt(item, registry))
    try:
        payload = json.loads(strip_json_wrapper(response))
    except json.JSONDecodeError as exc:
        return {
            "propositions": [],
            "abstain": True,
            "unresolved_spans": [{"text": response[:1000], "reason": f"invalid JSON: {exc}", "potentially_critical": True}],
        }, usage
    return payload, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--registry", default="medical/stage-evals/S3/proposition-registry-v0.1.json")
    ap.add_argument("--prompt", default="medical/stage-evals/S3/S3A_SEMANTIC_EXTRACTOR_PROMPT.md")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = load_json(args.input)
    cfg = load_json(args.config)
    registry = load_json(args.registry)
    system_prompt = Path(args.prompt).read_text(encoding="utf-8")
    backend = cfg.get("provider", "deterministic_baseline")

    rows = []
    for item in doc["items"]:
        usage: dict[str, Any] = {}
        if backend == "deterministic_baseline":
            raw = deterministic_extract(item)
        elif backend == "openai_compatible":
            raw, usage = model_extract(item, cfg, registry, system_prompt)
        else:
            raise ValueError(f"Unsupported S3a provider: {backend}")

        checked = validate_semantic_output(raw, registry)
        rows.append({
            "item_id": item["item_id"],
            "role": item.get("role", "evidence"),
            "predicted_propositions": checked["propositions"],
            "abstain": checked["abstain"],
            "unresolved_spans": checked["unresolved_spans"],
            "provider": backend,
            "model_id": cfg.get("model_id"),
            "usage": usage,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} constrained S3a extraction records to {out}")


if __name__ == "__main__":
    main()
