#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.4-updated eval: visible-only prompt (user question + evidence bundle + output constraint).

Protocol: NO Q1/Q2/Q3 hints, NO rubric leakage in system prompt. Model sees only what a real user would see.

Usage:
  python3 benchmark/scripts/eval_cases_v04.py genprompts  # write codex prompts to /tmp/v04prompts
  python3 benchmark/scripts/eval_cases_v04.py deepseek    # run DeepSeek on 6 cases
"""
import json, os, re, subprocess, sys, datetime

REPO = "/home/zehaoli0324/projects/groundsignal-pharma"
CASES_DIR = os.path.join(REPO, "benchmark/cases")
RUNS_DIR = os.path.join(REPO, "benchmark/runs")
CASE_IDS = [
    "case-001-competitive-impact", "case-002-regulatory-conflict",
    "case-003-licensing-bd", "case-004-due-diligence",
    "case-005-safety-signal", "case-006-temporal-watchlist",
]

SYSTEM_MINIMAL = "你是医药行业分析师。请直接回答用户的问题。"


def load_visible(cid):
    """Parse VISIBLE parts only from case.md."""
    text = open(os.path.join(CASES_DIR, cid, "case.md"), encoding="utf-8").read()
    def sec(title):
        m = re.search(rf"^## {re.escape(title)}\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.M)
        return m.group(1).strip() if m else ""
    return {
        "case_id": cid,
        "user_question": sec("User question"),
        "evidence_bundle": sec("Evidence Bundle"),
        "output_constraint": sec("Output Constraint"),
    }


def build_prompt(c):
    return f"""{c['user_question']}

## Evidence

{c['evidence_bundle']}

## Output 要求

{c['output_constraint']}"""


def load_env():
    env = {}
    p = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call_deepseek(system, user):
    key = load_env().get("DEEPSEEK_API_KEY", "")
    auth = "Bearer " + key
    payload = {"model": "deepseek-chat", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.3, "max_tokens": 3000}
    r = subprocess.run(
        ["curl", "-s", "--noproxy", "*", "--max-time", "180", "-X", "POST",
         "https://api.deepseek.com/chat/completions",
         "-H", "Content-Type: application/json",
         "-H", ("Authorization: " + auth),
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": f"curl exit {r.returncode}"}
    try:
        d = json.loads(r.stdout)
        if "choices" in d:
            return {"answer": d["choices"][0]["message"]["content"], "usage": d.get("usage", {})}
        return {"error": str(d.get("error", d))[:300]}
    except Exception:
        return {"error": "non-json"}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "genprompts"
    cases = [load_visible(c) for c in CASE_IDS]
    today = datetime.date.today().isoformat()
    os.makedirs(RUNS_DIR, exist_ok=True)

    if mode == "genprompts":
        os.makedirs("/tmp/v04prompts", exist_ok=True)
        for c in cases:
            p = os.path.join("/tmp/v04prompts", f"{c['case_id']}.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write(SYSTEM_MINIMAL + "\n\n---\n\n" + build_prompt(c))
            print("prompt:", p)
        return

    if mode == "deepseek":
        for c in cases:
            print(f"=== DeepSeek {c['case_id']} ===")
            r = call_deepseek(SYSTEM_MINIMAL, build_prompt(c))
            if "error" in r:
                print("ERROR:", r["error"]); continue
            ans = r["answer"]
            print(ans[:150].replace("\n", " ") + "...")
            out = os.path.join(RUNS_DIR, f"{today}-v04-deepseek-{c['case_id']}.md")
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# DeepSeek — {c['case_id']} (v0.4 updated, visible-only)\n\n{today}\n\n## Prompt\n\n{SYSTEM_MINIMAL}\n\n{build_prompt(c)}\n\n## Answer\n\n{ans}\n\n## Usage\n\n{json.dumps(r.get('usage', {}), ensure_ascii=False)}\n")
            print("saved:", out)


if __name__ == "__main__":
    main()
