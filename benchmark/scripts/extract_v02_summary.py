# -*- coding: utf-8 -*-
"""Extract compact summaries from v0.2 run files for rapid scoring."""
import glob, os, re, sys

pattern = sys.argv[1] if len(sys.argv) > 1 else "*"
files = sorted(glob.glob(f"/home/zehaoli0324/projects/groundsignal-pharma/benchmark/runs/2026-08-27-v02-{pattern}*.md"))

for f in files:
    text = open(f, encoding="utf-8").read()
    name = os.path.basename(f)
    # strip prompt section (up to ## Answer)
    m = re.search(r"## Answer\n(.*)", text, re.DOTALL)
    body = m.group(1) if m else text
    print("=" * 30)
    print(name)
    print("=" * 30)
    # Executive Judgment section
    ej = re.search(r"## Executive Judgment\n(.*?)(?=\n##|\n---|\Z)", body, re.DOTALL)
    if ej:
        print("EJ:", ej.group(1).strip().replace("\n", " ")[:400])
    # each Q answer first line
    for qm in re.finditer(r"## (Q\d)\..*?\n(.*?)(?=\n## |\Z)", body, re.DOTALL):
        ans = qm.group(2).strip().replace("\n", " ")
        print(f"{qm.group(1)}:", ans[:180])
    print()
