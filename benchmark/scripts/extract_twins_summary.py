# -*- coding: utf-8 -*-
"""Extract DeepSeek twin answers and print direction-relevant snippets per pair."""
import glob, os, re

RUNS = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/runs/twins"
files = sorted(glob.glob(os.path.join(RUNS, "2026-08-27-v04-deepseek-*.md")))

for f in files:
    name = os.path.basename(f).replace("2026-08-27-v04-deepseek-", "").replace(".md", "")
    text = open(f, encoding="utf-8").read()
    m = re.search(r"## Answer\n(.*)", text, re.DOTALL)
    ans = m.group(1).strip() if m else ""
    # strip usage json at end
    ans = re.sub(r"\n## Usage\n.*", "", ans, flags=re.DOTALL)
    print("=" * 22)
    print(name, f"({len(ans)} chars)")
    print(ans[:380].replace("\n", " "))
    print()
