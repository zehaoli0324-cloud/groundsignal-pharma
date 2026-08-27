# -*- coding: utf-8 -*-
"""Land Decision Intelligence 6 Cases v0.2 into benchmark/cases/ recommended structure.

Source: /mnt/d/xiazai/GroundSignal_Decision_Intelligence_6_Cases_v0.2.md
Output per case: case.md + gold-behavior.yaml + eval-items.json
"""
import json
import os
import re

SRC = "/mnt/d/xiazai/GroundSignal_Decision_Intelligence_6_Cases_v0.2.md"
BASE = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/cases"

text = open(SRC, encoding="utf-8").read()

# split into case sections by "# Case-00X —"
case_headers = list(re.finditer(r"^# Case-00(\d) — (.+)$", text, re.M))
print("found cases:", [(m.group(1), m.group(2)) for m in case_headers])

DIR_NAMES = {
    "1": "case-001-competitive-impact",
    "2": "case-002-regulatory-conflict",
    "3": "case-003-licensing-bd",
    "4": "case-004-due-diligence",
    "5": "case-005-safety-signal",
    "6": "case-006-temporal-watchlist",
}

def extract_section(body, title):
    """Extract section content under a heading (## level); stop at next # or ## heading."""
    m = re.search(rf"^## {re.escape(title)}\s*$", body, re.M)
    if not m:
        return ""
    nxt = re.search(r"^#{1,2} ", body[m.end():], re.M)
    end = m.end() + (nxt.start() if nxt else len(body) - m.end())
    return body[m.end():end].strip()

def parse_yaml_header(body):
    m = re.search(r"```yaml\n(.*?)\n```", body, re.DOTALL)
    if not m:
        return {}
    out = {}
    cur_key = None
    for line in m.group(1).splitlines():
        ls = line.strip()
        if ls.startswith("- ") and cur_key is not None and isinstance(out.get(cur_key), list):
            out[cur_key].append(ls[2:].strip())
        elif ":" in line:
            k, v = line.split(":", 1)
            cur_key = k.strip()
            v = v.strip().strip("'\"")
            out[cur_key] = v if v else []
    return out

def parse_list_items(section):
    """Parse '- **Q1**：xxx' or '- xxx' style list into items."""
    items = []
    for line in section.splitlines():
        ls = line.strip()
        if ls.startswith("- "):
            items.append(ls[2:].strip())
    return items

def parse_anchors(section):
    """Parse U1-U5 anchor lines: '- **U1 xxx**：2 = ...'"""
    anchors = {}
    for line in section.splitlines():
        m = re.match(r"- \*\*(U\d)\s*([^*]*)\*\*：(.+)", line.strip())
        if m:
            anchors[m.group(1)] = {"name": m.group(2).strip(), "text": m.group(3).strip()}
    return anchors

for i, m in enumerate(case_headers):
    num = m.group(1)
    title = m.group(2)
    start = m.start()
    end = case_headers[i + 1].start() if i + 1 < len(case_headers) else len(text)
    body = text[start:end]

    meta = parse_yaml_header(body)
    user_task = extract_section(body, "用户真实任务")
    snapshot = extract_section(body, "冻结 Evidence Snapshot")
    brief = extract_section(body, "GroundSignal 理想 Intelligence Brief（Gold）")
    eval_items = parse_list_items(extract_section(body, "Eval Items"))
    critical_errors = parse_list_items(extract_section(body, "Critical Errors"))
    anchors = parse_anchors(extract_section(body, "用户视角评分 Anchors"))

    d = os.path.join(BASE, DIR_NAMES[num])
    os.makedirs(os.path.join(d, "scores"), exist_ok=True)

    case_md = f"""# {title}

```yaml
case_id: {meta.get('case_id','')}
user_role: {meta.get('user_role','')}
track: {meta.get('track','')}
snapshot_id: {meta.get('snapshot_id','')}
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

{user_task}

## 冻结 Evidence Snapshot

{snapshot}

## GroundSignal 理想 Intelligence Brief（Gold）

{brief}

## Eval Items

"""
    for q in eval_items:
        case_md += f"- {q}\n"
    case_md += "\n## Critical Errors\n\n"
    for c in critical_errors:
        case_md += f"- {c}\n"
    case_md += "\n## 用户视角评分 Anchors\n\n"
    for u, a in anchors.items():
        case_md += f"- **{u} {a['name']}**：{a['text']}\n"
    open(os.path.join(d, "case.md"), "w", encoding="utf-8").write(case_md)

    pc = meta.get("primary_capabilities", [])
    if isinstance(pc, str):
        pc = [c for c in pc.split(",") if c]
    gold = {
        "case_id": meta.get("case_id", ""),
        "user_role": meta.get("user_role", ""),
        "primary_capabilities": pc,
        "critical_errors": critical_errors,
        "anchors": anchors,
        "gold_brief_notes": "详见 case.md 的 GroundSignal 理想 Intelligence Brief",
    }
    open(os.path.join(d, "gold-behavior.yaml"), "w", encoding="utf-8").write(
        "---\n" + json.dumps(gold, ensure_ascii=False, indent=2) + "\n")

    eval_json = {"case_id": meta.get("case_id", ""), "eval_items": eval_items}
    open(os.path.join(d, "eval-items.json"), "w", encoding="utf-8").write(
        json.dumps(eval_json, ensure_ascii=False, indent=2))

    print(f"generated {DIR_NAMES[num]}: {len(eval_items)} eval items, {len(anchors)} U-anchors")

print("DONE")
