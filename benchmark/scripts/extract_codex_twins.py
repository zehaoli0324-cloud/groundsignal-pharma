# -*- coding: utf-8 -*-
"""Extract Codex twin answers from /tmp/v04twinout into runs/twins, print summaries."""
import glob, os, re

RUNS = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/runs/twins"
for f in sorted(glob.glob("/tmp/v04twinout/*.out")):
    tid = os.path.basename(f).replace(".out", "")
    text = open(f, encoding="utf-8").read()
    m = text.rfind("tokens used")
    end = m if m != -1 else len(text)
    start = text.rfind("\ncodex\n", 0, end)
    ans = text[start + 7:end].strip() if start != -1 else text[max(0, end - 3000):end].strip()
    out = os.path.join(RUNS, f"2026-08-27-v04-codex-{tid}.md")
    with open(out, "w", encoding="utf-8") as wf:
        wf.write(f"# Codex — {tid} (twin run)\n\n2026-08-27\n\n## Answer\n\n{ans}\n")
    print("=" * 22)
    print(tid, f"({len(ans)} chars)")
    print(ans[:330].replace("\n", " "))
    print()
