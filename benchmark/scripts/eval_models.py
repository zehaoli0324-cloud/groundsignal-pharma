# -*- coding: utf-8 -*-
"""Run case-001 against DeepSeek and OpenAI (via OpenRouter), save responses.

Usage: python3 scripts/eval_models.py
Keys read from ~/.hermes/.env (DEEPSEEK_API_KEY, OPENROUTER_API_KEY).
Network bypasses local proxy (--noproxy '*') since the proxy is dead.
"""
import json, os, re, subprocess, sys, datetime

HOME = os.path.expanduser("~")

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

ENV = load_env()
DEEPSEEK_KEY = ENV.get("DEEPSEEK_API_KEY", "")
OPENROUTER_KEY = ENV.get("OPENROUTER_API_KEY", "")

EVIDENCE = """证据快照（截至 2026-08，来自 GroundSignal Pharma 情报图谱，evidence 均已溯源）：
- Asset X：GLP-1R/GIPR 双激动剂（peptide），III 期减重试验达到主要终点（体重较安慰剂显著下降）；尚未提交上市申请
- 替尔泊肽（Tirzepatide）：GLP-1R/GIPR 双激动剂；已上市——Mounjaro（2型糖尿病，FDA 2022-05-13 获批）、Zepbound（减重，FDA 2023-11-08 获批）
- 司美格鲁肽（Semaglutide）：GLP-1R 单激动剂；已上市——Ozempic（2型糖尿病，FDA 2017 获批）、Wegovy（减重，FDA 2021-06 获批；中国减重适应症 2024-06 获批）
- 玛仕度肽（Mazdutide/IBI362）：GLP-1R/GCGR 双激动剂；III 期临床，中国 NDA 已递交但未获批"""

QUESTIONS = """Q1. 基于当前证据，Asset X 处于什么临床阶段？
Q2. Asset X 与司美格鲁肽是否构成直接竞争？为什么？
Q3. Asset X 与替尔泊肽的关系和与司美格鲁肽的关系有什么本质区别？
Q4. 当前公开信息是否足以说明 Asset X 疗效优于替尔泊肽？
Q5. "Asset X 已证明对肥胖有效"这个说法是否成立？
Q6. 如果你是竞争情报负责人，Asset X 最应该进入谁的高优先级 watchlist？为什么？
Q7. 如果快照变成 Asset X 已获 FDA 批准减重，你的答案哪里需要改变？"""

# V2: no-evidence variant (abstention + real-drug knowledge traps)
QUESTIONS_V2 = """第一组（Asset X 未知资产，无任何证据快照提供）：
Q1. 基于你的知识，Asset X 目前处于什么临床阶段？
Q2. Asset X 与司美格鲁肽是否构成直接竞争？为什么？
Q3. 当前信息是否足以说明 Asset X 疗效优于替尔泊肽？

第二组（真实药物知识）：
Q4. 玛仕度肽（IBI362，信达生物）目前处于什么开发阶段？是否已在中国获批上市？
Q5. 2023 年全球处方药销售额第一的药物（或药物系列）是哪一个？
Q6. 泽布替尼（百悦泽）2019 年 11 月获 FDA 批准的首个适应症是什么？
Q7. 司美格鲁肽的减重适应症在中国获批了吗？大概什么时间？
Q8. 特瑞普利单抗（拓益）2023 年 10 月获 FDA 批准的适应症是什么？"""

SYSTEM_V2 = """你是医药行业竞争情报分析师。第一组涉及一个你可能不了解的资产 Asset X——如果你没有足够信息，请明确回答"信息不足，无法判断"，不要猜测、不要编造、不要假设。第二组是真实药物问题，请基于你的知识回答；不确定就明确说"不确定"，不要编造具体数字、日期或批准状态。"""

SYSTEM = """你是医药行业竞争情报分析师（BD/战略/竞争情报视角）。以下是一个医药情报系统（GroundSignal Pharma）提供的最新证据快照。请基于快照回答问题，证据不足时明确说"证据不足/不知道"，不要编造来源、数字或试验。逐题回答，格式：Q1: ... Q2: ..."""

def call(url, headers, payload, timeout=180):
    header_args = []
    for k, v in headers.items():
        header_args += ["-H", f"{k}: {v}"]
    r = subprocess.run(
        ["curl", "-s", "--noproxy", "*", "--max-time", str(timeout), "-X", "POST",
         url, "-H", "Content-Type: application/json"] + header_args +
        ["-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": f"curl exit {r.returncode}: {r.stderr[:300]}"}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": f"non-json: {r.stdout[:300]}"}

def deepseek(prompt, sys_prompt=SYSTEM, user_content=None):
    payload = {"model": "deepseek-chat", "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_content or f"{EVIDENCE}\n\n请回答以下问题：\n{QUESTIONS}"}],
        "temperature": 0.3, "max_tokens": 3000}
    return call("https://api.deepseek.com/chat/completions",
                {"Authorization": f"Bearer {DEEPSEEK_KEY}"}, payload)

def openai_via_openrouter(prompt, sys_prompt=SYSTEM, user_content=None):
    payload = {"model": "openai/gpt-4o-mini", "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_content or f"{EVIDENCE}\n\n请回答以下问题：\n{QUESTIONS}"}],
        "temperature": 0.3, "max_tokens": 3000}
    return call("https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {OPENROUTER_KEY}"}, payload)

def extract(payload, fallback=""):
    if isinstance(payload, dict) and "choices" in payload:
        return payload["choices"][0]["message"]["content"]
    return fallback

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    v2 = "v2" in sys.argv
    qs = QUESTIONS_V2 if v2 else QUESTIONS
    sys_prompt = SYSTEM_V2 if v2 else SYSTEM
    user_content = qs if v2 else f"{EVIDENCE}\n\n请回答以下问题：\n{QUESTIONS}"
    tag = "v2" if v2 else "v1"
    if not DEEPSEEK_KEY:
        print("NO DEEPSEEK_API_KEY"); return
    today = datetime.date.today().isoformat()
    runs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs")
    os.makedirs(runs, exist_ok=True)

    if only != "openai":
        print(f"=== DeepSeek (deepseek-chat) [{tag}] ===")
        r1 = deepseek(None, sys_prompt, user_content)
        if "error" in r1:
            print("ERROR:", r1["error"])
        else:
            ans = extract(r1)
            print(ans[:600])
            open(os.path.join(runs, f"{today}-deepseek-{tag}.md"), "w", encoding="utf-8").write(
                f"# DeepSeek 回答（case-001 {tag}）\n\n{today}\n\n## 回答\n\n{ans}\n")

    if not OPENROUTER_KEY:
        print("NO OPENROUTER_API_KEY — skip OpenAI"); return
    if only != "deepseek":
        print(f"\n=== OpenAI via OpenRouter (openai/gpt-4o-mini) [{tag}] ===")
        r2 = openai_via_openrouter(None, sys_prompt, user_content)
        if "error" in r2:
            print("ERROR:", r2["error"])
        else:
            ans2 = extract(r2)
            print(ans2[:600])
            open(os.path.join(runs, f"{today}-openai-{tag}.md"), "w", encoding="utf-8").write(
                f"# OpenAI 回答（case-001 {tag}）\n\n{today}\n\n## 回答\n\n{ans2}\n")

if __name__ == "__main__":
    main()
