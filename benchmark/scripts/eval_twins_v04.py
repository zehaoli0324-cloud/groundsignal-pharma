#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Counterfactual Twins eval: base + twin prompts run independently (randomized), no 'counterfactual' leakage.

Usage:
  python3 benchmark/scripts/eval_twins_v04.py genprompts   # write codex prompts
  python3 benchmark/scripts/eval_twins_v04.py deepseek     # run DeepSeek on all twins
"""
import json, os, random, re, subprocess, sys, datetime

REPO = "/home/zehaoli0324/projects/groundsignal-pharma"
CASES_DIR = os.path.join(REPO, "benchmark/cases")
RUNS_DIR = os.path.join(REPO, "benchmark/runs/twins")
CASE_IDS = [
    "case-001-competitive-impact", "case-002-regulatory-conflict",
    "case-003-licensing-bd", "case-004-due-diligence",
    "case-005-safety-signal", "case-006-temporal-watchlist",
]
SYSTEM_MINIMAL = "你是医药行业分析师。请直接回答用户的问题。"


def load_base(cid):
    text = open(os.path.join(CASES_DIR, cid, "case.md"), encoding="utf-8").read()
    def sec(title):
        m = re.search(rf"^## {re.escape(title)}\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.M)
        return m.group(1).strip() if m else ""
    return {"case_id": cid,
            "user_question": sec("User question"),
            "evidence_bundle": sec("Evidence Bundle"),
            "output_constraint": sec("Output Constraint")}


def load_twins(cid):
    p = os.path.join(CASES_DIR, cid, "counterfactual-twins.yaml")
    if not os.path.exists(p):
        return {}
    import yaml
    d = yaml.safe_load(open(p, encoding="utf-8"))
    return d.get("twins", {})


def build_base_prompt(c):
    return f"{c['user_question']}\n\n## Evidence\n\n{c['evidence_bundle']}\n\n## Output 要求\n\n{c['output_constraint']}"


def build_twin_prompt(base_prompt, twin_text):
    return f"{base_prompt}\n\n---\n\n补充信息（最新更新）：\n{twin_text}"


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


def call_deepseek(user):
    key = load_env().get("DEEPSEEK_API_KEY", "")
    auth = "Bearer " + key
    auth_header = "Authorization: " + auth
    payload = {"model": "deepseek-chat", "messages": [
        {"role": "system", "content": SYSTEM_MINIMAL},
        {"role": "user", "content": user}],
        "temperature": 0.3, "max_tokens": 3000}
    r = subprocess.run(
        ["curl", "-s", "--noproxy", "*", "--max-time", "180", "-X", "POST",
         "https://api.deepseek.com/chat/completions",
         "-H", "Content-Type: application/json",
         "-H", auth_header,
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": f"curl exit {r.returncode}"}
    try:
        d = json.loads(r.stdout)
        if "choices" in d:
            return {"answer": d["choices"][0]["message"]["content"], "usage": d.get("usage", {})}
        return {"error": str(d.get("error", d))[:200]}
    except Exception:
        return {"error": "non-json"}


def all_tasks():
    """(task_id, prompt) for base + twins, randomized order."""
    tasks = []
    for cid in CASE_IDS:
        base = load_base(cid)
        bp = build_base_prompt(base)
        tasks.append((f"{cid}__BASE", bp))
        twins = load_twins(cid)
        for tid, ttext in twins.items():
            tasks.append((f"{cid}__{tid}", build_twin_prompt(bp, ttext)))
    random.seed(20260827)
    random.shuffle(tasks)
    return tasks


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "genprompts"
    tasks = all_tasks()
    today = datetime.date.today().isoformat()
    os.makedirs(RUNS_DIR, exist_ok=True)

    if mode == "genprompts":
        outdir = "/tmp/v04twinprompts"
        os.makedirs(outdir, exist_ok=True)
        for tid, prompt in tasks:
            fn = tid.replace("/", "_")
            with open(os.path.join(outdir, f"{fn}.txt"), "w", encoding="utf-8") as f:
                f.write(SYSTEM_MINIMAL + "\n\n---\n\n" + prompt)
        print(f"{len(tasks)} prompts -> {outdir}")
        return

    if mode == "deepseek":
        ok = 0
        for tid, prompt in tasks:
            print(f"=== DeepSeek {tid} ===")
            r = call_deepseek(prompt)
            if "error" in r:
                print("ERROR:", r["error"]); continue
            ans = r["answer"]
            fn = tid.replace("/", "_")
            out = os.path.join(RUNS_DIR, f"{today}-v04-deepseek-{fn}.md")
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# DeepSeek — {tid} (twin run)\n\n{today}\n\n## Prompt\n\n{prompt}\n\n## Answer\n\n{ans}\n")
            ok += 1
            print("saved:", out, f"({len(ans)} chars)")
        print(f"DONE {ok}/{len(tasks)}")


if __name__ == "__main__":
    main()
