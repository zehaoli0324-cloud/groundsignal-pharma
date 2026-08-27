# -*- coding: utf-8 -*-
"""Extract Hermes session trajectory for the GroundSignal Pharma development session.

Source: ~/.hermes/state.db, session 20260827_121356_467dc9
Output: docs/development-trajectory/session_<id>.jsonl  (one line per user turn)
"""
import json
import os
import re
import sqlite3

DB = "/home/zehaoli0324/.hermes/state.db"
SESSION_ID = "20260827_121356_467dc9"
OUT_DIR = "/home/zehaoli0324/projects/groundsignal-pharma/docs/development-trajectory"
os.makedirs(OUT_DIR, exist_ok=True)


def trunc(s, n=600):
    s = s or ""
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("..." if len(s) > n else "")


def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT id, title, started_at, message_count, tool_call_count, model FROM sessions WHERE id=?", (SESSION_ID,))
    meta = dict(cur.fetchone())
    print("session:", meta["title"], "| msgs:", meta["message_count"], "| tools:", meta["tool_call_count"])

    cur.execute("""SELECT id, role, content, tool_calls, tool_name, timestamp, reasoning
                   FROM messages WHERE session_id=? ORDER BY id""", (SESSION_ID,))
    msgs = [dict(r) for r in cur.fetchall()]
    print("loaded", len(msgs), "messages")

    lines = []
    pending_results = {}  # tool_call_id -> result text

    for m in msgs:
        role = m["role"]
        content = m.get("content") or ""
        tool_calls = m.get("tool_calls")
        if tool_calls:
            try:
                tool_calls = json.loads(tool_calls) if isinstance(tool_calls, str) else tool_calls
            except Exception:
                tool_calls = []
        # collect tool results
        if role == "tool":
            tcid = m.get("tool_call_id") or ""
            pending_results[tcid] = trunc(content, 400)
            continue

        if role == "user":
            turn = {
                "user": trunc(content, 800),
                "steps": [],
                "tool_results": [],
            }
            lines.append(turn)
        elif role == "assistant" and lines:
            turn = lines[-1]
            step = {
                "type": "decision",
                "text": trunc(content, 500),
                "tool_calls": [],
            }
            for tc in (tool_calls or []):
                if isinstance(tc, dict):
                    step["tool_calls"].append({
                        "name": tc.get("name") or tc.get("function", {}).get("name", ""),
                        "args_preview": trunc(json.dumps(tc.get("arguments") or tc.get("function", {}).get("arguments", ""), ensure_ascii=False), 200),
                    })
            turn["steps"].append(step)
            # attach pending tool results for the tool calls in this step
            for tc in step["tool_calls"]:
                # match by order fallback: attach next unmatched result
                pass

    # attach tool results: iterate again mapping by tool_call_id
    cur.execute("""SELECT id, role, content, tool_call_id, tool_name FROM messages
                   WHERE session_id=? AND role='tool' ORDER BY id""", (SESSION_ID,))
    tool_msgs = {r["tool_call_id"]: trunc(r["content"], 350) for r in cur.fetchall()}

    # rebuild steps with results: easier second pass over assistant messages
    cur.execute("""SELECT id, role, content, tool_calls, tool_call_id, tool_name FROM messages
                   WHERE session_id=? ORDER BY id""", (SESSION_ID,))
    allm = [dict(r) for r in cur.fetchall()]
    # map: each assistant tool_call id -> tool result (tool_call_id field on tool rows)
    callid_result = {}
    for r in allm:
        if r["role"] == "tool" and r["tool_call_id"]:
            callid_result[r["tool_call_id"]] = trunc(r["content"], 350)

    # second pass: attach results to the correct turn (by user-turn boundaries)
    turn_idx = -1
    for m in allm:
        if m["role"] == "user":
            turn_idx += 1
            continue
        if m["role"] != "assistant" or turn_idx < 0 or turn_idx >= len(lines):
            continue
        tcs = m.get("tool_calls")
        if tcs:
            try:
                tcs = json.loads(tcs) if isinstance(tcs, str) else tcs
            except Exception:
                tcs = []
        turn = lines[turn_idx]
        for tc in (tcs or []):
            if isinstance(tc, dict):
                cid = tc.get("id", "")
                res = callid_result.get(cid, "")
                if res:
                    turn["tool_results"].append({"tool_call_id": cid[:8], "result": res})

    # dedupe: keep only turns that have steps
    out_path = os.path.join(OUT_DIR, f"session_{SESSION_ID}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for t in lines:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print("wrote", out_path, "|", len(lines), "user turns")

    # quick stats
    n_dec = sum(len(t["steps"]) for t in lines)
    n_res = sum(len(t["tool_results"]) for t in lines)
    print("decision steps:", n_dec, "| tool results captured:", n_res)


if __name__ == "__main__":
    main()
