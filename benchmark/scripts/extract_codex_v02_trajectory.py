# -*- coding: utf-8 -*-
"""Extract v0.2 Codex rollout metrics (token/duration/reasoning) into trajectory summary."""
import json, os, re

SESSIONS = "/home/zehaoli0324/.codex/sessions/2026/08/27"
OUT = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/trajectories/v02-codex-rollout-summary.json"

# chronological order matches case-001..006
rollouts = sorted(
    [os.path.join(SESSIONS, f) for f in os.listdir(SESSIONS) if f.startswith("rollout-2026-08-27T14")],
    key=lambda p: p)
case_ids = [
    "case-001-competitive-impact",
    "case-002-regulatory-conflict",
    "case-003-licensing-bd",
    "case-004-due-diligence",
    "case-005-safety-signal",
    "case-006-temporal-watchlist",
]

rows = []
for i, path in enumerate(rollouts[:6]):
    items = []
    for ln in open(path, encoding="utf-8").read().strip().splitlines():
        try:
            items.append(json.loads(ln))
        except Exception:
            pass
    meta = {"session_id": "", "model": "", "cwd": ""}
    tokens = {}
    duration_ms = None
    reasoning_encrypted = False
    last_msg = ""
    for d in items:
        t = d.get("type")
        p = d.get("payload", {})
        if t == "session_meta":
            meta["session_id"] = p.get("session_id", "")[:8]
            bi = p.get("base_instructions", {}).get("text", "")
            m = re.search(r"based on ([A-Za-z0-9.\-]+)", bi)
            meta["model"] = m.group(1) if m else "GPT-5-family(?)"
            meta["cwd"] = p.get("cwd", "").replace("/home/zehaoli0324/projects/groundsignal-pharma", "<repo>")
            meta["cli_version"] = p.get("cli_version")
        elif t == "response_item" and p.get("type") == "reasoning":
            reasoning_encrypted = True
        elif t == "event_msg":
            if p.get("type") == "token_count":
                tokens = p.get("info", {}).get("total_token_usage", {})
            elif p.get("type") == "task_complete":
                duration_ms = p.get("duration_ms")
                last_msg = p.get("last_agent_message", "")[:100]
    rows.append({
        "case": case_ids[i] if i < len(case_ids) else f"case-{i+1}",
        "session_id": meta["session_id"],
        "model": meta["model"],
        "cli_version": meta["cli_version"],
        "input_tokens": tokens.get("input_tokens"),
        "output_tokens": tokens.get("output_tokens"),
        "reasoning_tokens": tokens.get("reasoning_output_tokens"),
        "total_tokens": tokens.get("total_tokens"),
        "duration_ms": duration_ms,
        "reasoning_encrypted": reasoning_encrypted,
        "last_msg_preview": last_msg,
    })
    print(rows[-1])

json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("saved:", OUT)
