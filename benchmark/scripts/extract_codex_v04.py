# -*- coding: utf-8 -*-
"""Extract Codex v0.4 answers from /tmp/v04codex into runs/, print compact summaries."""
import glob, os, re

RUNS = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/runs"
for f in sorted(glob.glob("/tmp/v04codex/case-*.out")):
    case_id = os.path.basename(f).replace(".out", "")
    text = open(f, encoding="utf-8").read()
    m = text.rfind("tokens used")
    end = m if m != -1 else len(text)
    # answer starts right after the "codex" prompt line
    start = text.rfind("\ncodex\n", 0, end)
    if start != -1:
        ans = text[start + 7:end].strip()
    else:
        ans = text[max(0, end - 3000):end].strip()
    ans = ans.strip()
    out = os.path.join(RUNS, f"2026-08-27-v04-codex-{case_id}.md")
    with open(out, "w", encoding="utf-8") as wf:
        wf.write(f"# Codex (GPT-5-family) — {case_id} (v0.4 updated, visible-only)\n\n2026-08-27\n\n## Answer\n\n{ans}\n")
    print("=" * 25)
    print(case_id, f"({len(ans)} chars)")
    print(ans[:400].replace("\n", " "))
    print()
