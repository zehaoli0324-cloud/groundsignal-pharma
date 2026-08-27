# -*- coding: utf-8 -*-
"""Extract sanitized trajectories from Codex rollout jsonl files."""
import json, os, re

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/trajectories"
os.makedirs(BASE, exist_ok=True)

ROLLOUTS = {
    "codex-v1": "/home/zehaoli0324/.codex/sessions/2026/08/27/rollout-2026-08-27T13-47-49-01a041c2-a0fe-7b60-8329-73db299b0a0e.jsonl",
    "codex-v2": "/home/zehaoli0324/.codex/sessions/2026/08/27/rollout-2026-08-27T13-51-34-01a041c6-0e77-7321-8f6e-d73fd4914d76.jsonl",
}

def sanitize_path(p):
    return p.replace("/home/zehaoli0324/projects/groundsignal-pharma", "<repo-root>")

def extract(path):
    items = []
    for ln in open(path, encoding="utf-8").read().strip().splitlines():
        try:
            items.append(json.loads(ln))
        except Exception:
            pass
    meta = {}
    user_prompt = ""
    assistant_response = ""
    reasoning_encrypted = False
    tokens = {}
    duration_ms = None
    for d in items:
        t = d.get("type")
        p = d.get("payload", {})
        if t == "session_meta":
            meta = {"timestamp_utc": d.get("timestamp"), "session_id": p.get("session_id", "")[:8],
                    "originator": p.get("originator"), "cli_version": p.get("cli_version"),
                    "model_provider": p.get("model_provider"), "cwd": sanitize_path(p.get("cwd", ""))}
            bi = p.get("base_instructions", {}).get("text", "")
            m = re.search(r"based on ([A-Za-z0-9.\-]+)", bi)
            meta["model"] = m.group(1) if m else "GPT-5(?)"
        elif t == "turn_context":
            meta["current_date"] = p.get("current_date")
            meta["timezone"] = p.get("timezone")
            meta["approval_policy"] = p.get("approval_policy")
        elif t == "response_item":
            if p.get("role") == "user":
                for c in p.get("content", []):
                    if c.get("type") == "input_text":
                        user_prompt = c.get("text", "")
            elif p.get("role") == "assistant":
                for c in p.get("content", []):
                    if c.get("type") == "output_text":
                        assistant_response = c.get("text", "")
            elif p.get("type") == "reasoning":
                reasoning_encrypted = True
                meta["reasoning_encrypted"] = True
        elif t == "event_msg":
            if p.get("type") == "token_count":
                tokens = p.get("info", {}).get("total_token_usage", {})
            elif p.get("type") == "task_complete":
                duration_ms = p.get("duration_ms")
    return meta, user_prompt, assistant_response, reasoning_encrypted, tokens, duration_ms

def write_md(name, meta, user_prompt, assistant_response, reasoning_encrypted, tokens, duration_ms):
    lines = [
        f"# {name} — Codex (GPT-5) trajectory",
        "",
        "## Session meta",
        "",
    ]
    for k, v in meta.items():
        lines.append(f"- {k}: {v}")
    lines += ["", f"- reasoning_visible: {'YES but encrypted (OpenAI 加密, 不可读)' if reasoning_encrypted else 'NO'}",
              f"- duration_ms: {duration_ms}", "", "## User prompt（脱敏，cwd 已替换）", "", "```", user_prompt[:4000], "```", "",
              "## Assistant response（最终回答）", "", "```", assistant_response, "```", "",
              "## Token usage", "", "| metric | value |", "|--------|-------|"]
    for k, v in tokens.items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 轨迹要点", "",
              "- 纯问答任务：无工具调用、无联网（prompt 明确禁止）",
              "- 中间推理：GPT-5 产生 reasoning（reasoning_output_tokens 可计数），OpenAI 加密存储不可读",
              "- 可复现性：存在加密 reasoning 与缓存，无法逐 token 复现；prompt 与最终回答可复现"]
    open(os.path.join(BASE, f"{name}.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("wrote", name)

for name, path in ROLLOUTS.items():
    meta, up, ar, re_, tok, dur = extract(path)
    write_md(name, meta, up, ar, re_, tok, dur)
    print(" ", name, "tokens:", tok.get("total_tokens"), "reasoning:", tok.get("reasoning_output_tokens"))
