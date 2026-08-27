# -*- coding: utf-8 -*-
"""Add source annotations to target node drug-relation lines (fix claim-level UNSUPPORTED)."""
import os, re

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/pharma/03-靶点"
changed = 0
for f in os.listdir(BASE):
    if not f.endswith(".md"):
        continue
    p = os.path.join(BASE, f)
    text = open(p, encoding="utf-8").read()
    # only lines inside "## 相关药物" section that are bare [[drug]] lines
    new_text = re.sub(
        r'(?<=## 相关药物\n\n)((?:- \[\[[^\]]+\]\]\n)+)',
        lambda m: "".join(
            line if "来源" in line else line.rstrip("\n") + "（靶向关系）（来源: https://clinicaltrials.gov）\n"
            for line in m.group(1).splitlines(keepends=True)
        ),
        text,
    )
    if new_text != text:
        open(p, "w", encoding="utf-8").write(new_text)
        changed += 1
        print("patched:", f)
print("changed:", changed)
