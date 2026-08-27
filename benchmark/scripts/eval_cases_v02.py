# -*- coding: utf-8 -*-
"""Run Decision Intelligence 6 Cases v0.2 against DeepSeek (API) and generate Codex prompts.

Usage:
  python3 benchmark/scripts/eval_cases_v02.py deepseek   # run DeepSeek on all 6 cases
  python3 benchmark/scripts/eval_cases_v02.py genprompts # write codex prompt files to /tmp
"""
import json
import os
import re
import subprocess
import sys
import datetime

HOME = os.path.expanduser("~")
REPO = "/home/zehaoli0324/projects/groundsignal-pharma"
CASES_DIR = os.path.join(REPO, "benchmark/cases")
RUNS_DIR = os.path.join(REPO, "benchmark/runs")

CASE_IDS = [
    "case-001-competitive-impact",
    "case-002-regulatory-conflict",
    "case-003-licensing-bd",
    "case-004-due-diligence",
    "case-005-safety-signal",
    "case-006-temporal-watchlist",
]

SYSTEM = """你是医药行业竞争情报分析师。你的回答将直接给一位真实专业用户（药企 BD / 战略 / 竞争情报 / VC 投委会 / 临床开发）看，用于会议和决策。

回答要求（用户视角评分标准）：
1. Decision Fit：先直接回答用户的核心决策，给明确判断/推荐/优先级，不要只罗列信息
2. Trust：每个关键判断有证据支撑；事实/推断/假设分层（OBSERVED / DERIVED / HYPOTHESIS）
3. Prioritization：明确 High / Medium / Low 排序并解释为什么
4. Actionability：给出具体下一步、触发条件、需补证据、应监控的变量
5. Uncertainty：明确哪些证据不足、什么会改变结论、有哪些风险/竞争解释

只使用提供的 Evidence Snapshot，不要编造快照中不存在的来源、数字、试验、批准状态或交易关系。证据不足时明确说"证据不足"。不要联网搜索。

输出格式：先给一段 Executive Judgment（3-5 句核心判断），然后逐题回答 Q1...Q6。"""


def load_case(cid):
    d = os.path.join(CASES_DIR, cid)
    case_md = open(os.path.join(d, "case.md"), encoding="utf-8").read()
    items = json.load(open(os.path.join(d, "eval-items.json"), encoding="utf-8"))["eval_items"]
    # extract user task and snapshot from case.md
    def sec(title):
        m = re.search(rf"## {re.escape(title)}\s*\n(.*?)(?=\n## |\n# |\Z)", case_md, re.DOTALL)
        return m.group(1).strip() if m else ""
    user_task = sec("用户真实任务")
    snapshot = sec("冻结 Evidence Snapshot")
    return {"case_id": cid, "user_task": user_task, "snapshot": snapshot, "items": items}


def build_prompt(case):
    qs = "\n".join(f"Q{i+1}. {it}" for i, it in enumerate(case["items"]))
    return f"""{case['user_task']}

## 冻结 Evidence Snapshot

{case['snapshot']}

## 问题

{qs}

请先给 Executive Judgment，再逐题回答。"""


def load_env():
    env = {}
    p = os.path.join(HOME, ".hermes", ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call_deepseek(system, user):
    key = load_env().get("DEEPSEEK_API_KEY", "")
    payload = {"model": "deepseek-chat", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.3, "max_tokens": 4000}
    r = subprocess.run(
        ["curl", "-s", "--noproxy", "*", "--max-time", "180", "-X", "POST",
         "https://api.deepseek.com/chat/completions",
         "-H", "Content-Type: application/json",
         "-H", f"Authorization: Bearer {key}",
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": f"curl exit {r.returncode}"}
    try:
        d = json.loads(r.stdout)
        if "choices" in d:
            return {"answer": d["choices"][0]["message"]["content"],
                    "usage": d.get("usage", {})}
        return {"error": str(d.get("error", d))[:300]}
    except Exception as e:
        return {"error": f"non-json: {r.stdout[:200]}"}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
    cases = [load_case(c) for c in CASE_IDS]
    today = datetime.date.today().isoformat()
    os.makedirs(RUNS_DIR, exist_ok=True)

    if mode == "genprompts":
        os.makedirs("/tmp/v02prompts", exist_ok=True)
        for c in cases:
            p = os.path.join("/tmp/v02prompts", f"{c['case_id']}.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write(SYSTEM + "\n\n---\n\n" + build_prompt(c))
            print("prompt:", p)
        return

    if mode == "deepseek":
        for c in cases:
            print(f"=== DeepSeek {c['case_id']} ===")
            r = call_deepseek(SYSTEM, build_prompt(c))
            if "error" in r:
                print("ERROR:", r["error"])
                continue
            ans = r["answer"]
            print(ans[:200].replace("\n", " ") + "...")
            out = os.path.join(RUNS_DIR, f"{today}-v02-deepseek-{c['case_id']}.md")
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# DeepSeek — {c['case_id']}\n\n{today}\n\n## Prompt\n\n{SYSTEM}\n\n{build_prompt(c)}\n\n## Answer\n\n{ans}\n\n## Usage\n\n{json.dumps(r.get('usage', {}), ensure_ascii=False)}\n")
            print("saved:", out)


if __name__ == "__main__":
    main()
