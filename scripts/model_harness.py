#!/usr/bin/env python3
"""GroundSignal medical model harness.

Runs one or more clinical cases against a matrix of model configurations and
writes reproducible JSONL run records. Uses only Python stdlib.

Supported providers:
- fixture: deterministic local response for pipeline tests
- openai_compatible: POST /chat/completions to an OpenAI-compatible endpoint

This harness intentionally does not make clinical decisions for real patients.
It operates on benchmark/evaluation cases.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def iter_case_paths(case_path: Path) -> Iterable[Path]:
    if case_path.is_file():
        yield case_path
        return
    if not case_path.is_dir():
        raise FileNotFoundError(case_path)
    for path in sorted(case_path.glob("*.json")):
        yield path


def evidence_map(evidence_path: Path | None) -> Dict[str, Dict[str, Any]]:
    if evidence_path is None:
        return {}
    rows = load_jsonl(evidence_path)
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        passage_id = row.get("passage_id")
        if passage_id:
            out[str(passage_id)] = row
    return out


def compact_patient_context(case: Dict[str, Any]) -> str:
    return json.dumps(case.get("patient_context", {}), ensure_ascii=False, indent=2)


def render_evidence(case: Dict[str, Any], model_cfg: Dict[str, Any], passages: Dict[str, Dict[str, Any]]) -> tuple[str, List[str]]:
    rag_cfg = model_cfg.get("rag", {}) or {}
    if not rag_cfg.get("enabled", False):
        return "", []

    allowed = case.get("evidence_snapshot", {}).get("allowed_passage_ids", []) or []
    top_k = rag_cfg.get("top_k") or len(allowed)
    chosen = [str(pid) for pid in allowed[: int(top_k)]]

    missing = [pid for pid in chosen if pid not in passages]
    if missing:
        raise ValueError(
            "RAG/evidence injection enabled but passage ids are missing from the evidence index: "
            + ", ".join(missing)
        )

    blocks: List[str] = []
    for pid in chosen:
        p = passages[pid]
        proposition = p.get("normalized_proposition") or p.get("verbatim_excerpt") or ""
        locator = p.get("locator") or {}
        blocks.append(
            f"[{pid}] source={p.get('source_family')} | document={p.get('document_title')} | "
            f"locator={locator.get('kind')}:{locator.get('value')}\n{proposition}"
        )
    return "\n\n".join(blocks), chosen


def build_user_prompt(case: Dict[str, Any], injected_evidence: str) -> str:
    interaction = case.get("interaction", {})
    prompt = interaction.get("prompt", "")
    prior_turns = interaction.get("prior_turns", []) or []

    parts = [
        f"CASE_ID: {case.get('case_id')}",
        "PATIENT_CONTEXT:\n" + compact_patient_context(case),
    ]
    if prior_turns:
        parts.append("PRIOR_TURNS:\n" + json.dumps(prior_turns, ensure_ascii=False, indent=2))
    if injected_evidence:
        parts.append("INJECTED_EVIDENCE:\n" + injected_evidence)
    parts.append("TASK:\n" + str(prompt))
    return "\n\n".join(parts)


def parse_openai_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("OpenAI-compatible response contains no choices")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text_parts.append(str(item.get("text", "")))
        return "\n".join(text_parts)
    return str(content)


def call_openai_compatible(model_cfg: Dict[str, Any], system_prompt: str, user_prompt: str) -> tuple[str, Dict[str, Any]]:
    base_url = str(model_cfg.get("base_url", "")).rstrip("/")
    if not base_url:
        raise ValueError("openai_compatible model requires base_url")
    api_key_env = model_cfg.get("api_key_env")
    api_key = os.environ.get(str(api_key_env), "") if api_key_env else ""
    if api_key_env and not api_key:
        raise EnvironmentError(f"Missing API key environment variable: {api_key_env}")

    body = {
        "model": model_cfg["model_id"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": model_cfg.get("temperature", 0),
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=float(model_cfg.get("timeout_seconds", 120))) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model HTTP {exc.code}: {detail}") from exc
    return parse_openai_content(payload), payload.get("usage") or {}


def run_model(model_cfg: Dict[str, Any], system_prompt: str, user_prompt: str) -> tuple[str, Dict[str, Any]]:
    provider = model_cfg.get("provider")
    if provider == "fixture":
        return str(model_cfg.get("fixture_response", "")), {}
    if provider == "openai_compatible":
        return call_openai_compatible(model_cfg, system_prompt, user_prompt)
    raise ValueError(f"Unsupported provider: {provider}")


def run_case(
    case: Dict[str, Any],
    model_cfg: Dict[str, Any],
    global_cfg: Dict[str, Any],
    passages: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    injected, retrieved_ids = render_evidence(case, model_cfg, passages)
    user_prompt = build_user_prompt(case, injected)
    system_prompt = str(model_cfg.get("system_prompt") or global_cfg.get("system_prompt") or "")

    start = time.perf_counter()
    response, usage = run_model(model_cfg, system_prompt, user_prompt)
    latency_ms = int((time.perf_counter() - start) * 1000)

    rag_cfg = model_cfg.get("rag", {}) or {}
    tools_cfg = model_cfg.get("tools", {}) or {"enabled": []}
    return {
        "run_id": str(uuid.uuid4()),
        "case_id": case["case_id"],
        "model_id": model_cfg["model_id"],
        "provider": model_cfg["provider"],
        "model_version": model_cfg.get("model_version"),
        "prompt_version": model_cfg.get("prompt_version") or global_cfg.get("prompt_version", "unknown"),
        "rag": {
            "enabled": bool(rag_cfg.get("enabled", False)),
            "retriever_version": rag_cfg.get("retriever_version"),
            "top_k": rag_cfg.get("top_k"),
            "retrieved_passage_ids": retrieved_ids,
        },
        "tools": {
            "enabled": tools_cfg.get("enabled", []),
            "trace": [],
        },
        "temperature": model_cfg.get("temperature", 0),
        "snapshot_id": case.get("evidence_snapshot", {}).get("snapshot_id", "unknown"),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response,
        "latency_ms": latency_ms,
        "usage": usage,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GroundSignal medical cases across a model matrix")
    parser.add_argument("--cases", required=True, type=Path, help="Clinical case JSON file or directory of JSON files")
    parser.add_argument("--config", required=True, type=Path, help="Model matrix JSON")
    parser.add_argument("--evidence", type=Path, default=None, help="Evidence passage JSONL index (required for RAG-enabled configs)")
    parser.add_argument("--out", required=True, type=Path, help="Output JSONL run records")
    args = parser.parse_args()

    cfg = load_json(args.config)
    passages = evidence_map(args.evidence)
    models = cfg.get("models") or []
    if not models:
        raise ValueError("Config must contain a non-empty models list")

    cases = [load_json(p) for p in iter_case_paths(args.cases)]
    if not cases:
        raise ValueError("No case JSON files found")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.out.open("w", encoding="utf-8") as f:
        for case in cases:
            for model_cfg in models:
                record = run_case(case, model_cfg, cfg, passages)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                n += 1
                print(f"[{n}] {record['case_id']} × {record['model_id']} -> {record['run_id']}")

    print(f"Wrote {n} run records to {args.out}")


if __name__ == "__main__":
    main()
