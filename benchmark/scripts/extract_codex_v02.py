# -*- coding: utf-8 -*-
"""Extract Codex answers from /tmp/v02codex/*.out into runs/, print compact summaries."""
import glob, os, re

RUNS = "/home/zehaoli0324/projects/groundsignal-pharma/benchmark/runs"
files = sorted(glob.glob("/tmp/v02codex/case-*.out"))
for f in files:
    case_id = os.path.basename(f).replace(".out", "")
    text = open(f, encoding="utf-8").read()
    # answer starts after the instruction line "请先给 Executive Judgment，再逐题回答。"
    m = text.rfind("请先给 Executive Judgment，再逐题回答。")
    if m == -1:
        # fallback: everything after last warning line
        m = text.rfind("bubblewrap")
    ans = text[m + 20:] if m != -1 else text[-3000:]
    ans = ans.strip()
    out = os.path.join(RUNS, f"2026-08-27-v02-codex-{case_id}.md")
    with open(out, "w", encoding="utf-8") as wf:
        wf.write(f"# Codex (GPT-5-family via Codex CLI) — {case_id}\n\n2026-08-27\n\n## Answer\n\n{ans}\n")
    print("=" * 30)
    print(case_id, f"({len(ans)} chars)")
    # summary: Executive Judgment + first Q lines
    body = ans
    ej = re.search(r"#{0,4} Executive Judgment[:\s]*(.*?)(?=\n#{0,4} |\n---|\Z)", body, re.DOTALL)
    if ej:
        print("EJ:", ej.group(1).strip().replace("\n", " ")[:350])
    for qm in re.finditer(r"(Q\d)[\.:：]?\s*(.*?)(?=\nQ\d|\n#{1,4} |\Z)", body, re.DOTALL):
        txt = qm.group(2).strip().replace("\n", " ")
        if txt and len(txt) > 20:
            print(f"{qm.group(1)}:", txt[:150])
            break  # only first Q for preview
    print()
