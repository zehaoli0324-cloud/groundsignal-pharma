# -*- coding: utf-8 -*-
"""Land v0.4-updated cases: Visible Task / Hidden Evaluator / Counterfactual Twins separation.

Source: /mnt/d/xiazai/GroundSignal_Decision_Intelligence_Model_Diagnosis_v0.4_updated.md
Output per case:
  case.md                 # VISIBLE only: user_role / user_question / evidence_bundle / output_constraints
  hidden-evaluator.yaml   # HIDDEN: must_notice / forbidden_shortcuts / critical_errors / counterfactual_expectation
  counterfactual-twins.yaml
"""
import json
import os
import re

SRC = "/mnt/d/xiazai/GroundSignal_Decision_Intelligence_Model_Diagnosis_v0.4_updated.md"
BASE = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/cases"

text = open(SRC, encoding="utf-8").read()

# case sections are "# 6. Case 01 — ..." through "# 11. Case 06 — ..."
case_headers = list(re.finditer(r"^# (6|7|8|9|10|11)\. Case 0(\d) — (.+)$", text, re.M))
print("found:", [(m.group(2), m.group(3)) for m in case_headers])

DIRS = {
    "1": "case-001-competitive-impact",
    "2": "case-002-regulatory-conflict",
    "3": "case-003-licensing-bd",
    "4": "case-004-due-diligence",
    "5": "case-005-safety-signal",
    "6": "case-006-temporal-watchlist",
}


def sec(body, title, stop_levels=("###", "##", "#")):
    """Extract content under a heading; stop at any heading of >= level."""
    m = re.search(rf"^### {re.escape(title)}\s*$", body, re.M)
    if not m:
        return ""
    nxt = re.search(r"^#{1,3} ", body[m.end():], re.M)
    end = m.end() + (nxt.start() if nxt else len(body) - m.end())
    return body[m.end():end].strip()


def parse_yaml(body):
    m = re.search(r"```yaml\n(.*?)\n```", body, re.DOTALL)
    if not m:
        return {}
    out = {}
    cur = None
    for line in m.group(1).splitlines():
        ls = line.strip()
        if ls.startswith("- ") and cur is not None and isinstance(out.get(cur), list):
            out[cur].append(ls[2:].strip())
        elif ":" in line:
            k, v = line.split(":", 1)
            cur = k.strip()
            v = v.strip().strip("'\"")
            out[cur] = v if v else []
    return out


def extract_twins(body):
    """Extract '### [Counterfactual ]Twin CXX-B ...' sections (source uses both formats)."""
    twins = {}
    for m in re.finditer(r"^### (?:Counterfactual )?Twin (C\d+-[A-Z])\s*\n(.*?)(?=^### |^## |^# |\Z)",
                         body, re.M | re.DOTALL):
        twins[m.group(1)] = m.group(2).strip()
    return twins


for i, m in enumerate(case_headers):
    num = m.group(2)
    title = m.group(3)
    start = m.start()
    end = case_headers[i + 1].start() if i + 1 < len(case_headers) else len(text)
    body = text[start:end]

    meta = parse_yaml(body)
    user_q = sec(body, "User question")
    evb = sec(body, "Evidence Bundle") or sec(body, "Event Bundle")
    if not evb:
        # case-006 style: Existing Theses + Event Bundle
        th = sec(body, "Existing Theses")
        ev = sec(body, "Event Bundle")
        evb = (th + "\n\n" + ev) if (th or ev) else ""
    outc = sec(body, "Output Constraint")
    he = sec(body, "Hidden Evaluator")
    twins = extract_twins(body)

    d = os.path.join(BASE, DIRS[num])
    os.makedirs(os.path.join(d, "scores"), exist_ok=True)

    # VISIBLE case.md
    case_md = f"""# Case {num} — {title}

```yaml
case_id: {meta.get('case_id', f'C0{num}')}
track: {meta.get('track', 'B')}
user_role: {meta.get('user_role', '')}
```

> Visible task（v0.4 updated 落地生成）。Hidden evaluator / twins 见同目录 hidden 文件，对模型不可见。

## User question

{user_q}

## Evidence Bundle

{evb}

## Output Constraint

{outc}
"""
    open(os.path.join(d, "case.md"), "w", encoding="utf-8").write(case_md)

    # HIDDEN evaluator
    hidden = {"case_id": meta.get("case_id", ""), "user_role": meta.get("user_role", ""),
              "hidden_evaluator": he, "counterfactual_expectation": "见 twins 文件",
              "must_notice": [ln[2:].strip() for ln in he.splitlines() if ln.strip().startswith("- ")][:20]}
    open(os.path.join(d, "hidden-evaluator.yaml"), "w", encoding="utf-8").write(
        "---\n" + json.dumps(hidden, ensure_ascii=False, indent=2) + "\n")

    # TWINS
    open(os.path.join(d, "counterfactual-twins.yaml"), "w", encoding="utf-8").write(
        "---\n" + json.dumps({"case_id": meta.get("case_id", ""), "twins": twins},
                             ensure_ascii=False, indent=2) + "\n")

    print(f"generated {DIRS[num]}: {len(twins)} twins, visible={len(user_q)}ch bundle={len(evb)}ch")

print("DONE")
