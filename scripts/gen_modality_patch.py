# -*- coding: utf-8 -*-
"""Add modality field to pharma product notes (alignment with clinical domain model)."""
import os, re

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/pharma/02-产品"

MODALITY = {
    "替尔泊肽": "peptide（GLP-1R/GIPR 双激动剂）",
    "司美格鲁肽": "peptide（GLP-1R 激动剂）",
    "玛仕度肽": "peptide（GLP-1R/GCGR 双激动剂）",
    "卡瑞利珠单抗": "monoclonal antibody",
    "替雷利珠单抗": "monoclonal antibody",
    "信迪利单抗": "monoclonal antibody",
    "特瑞普利单抗": "monoclonal antibody",
    "泽布替尼": "small molecule",
    "西达基奥仑赛": "CAR-T（cell therapy）",
    "阿基仑赛": "CAR-T（cell therapy）",
    "德曲妥珠单抗": "ADC",
    "mRNA疫苗": "mRNA（RNA therapeutics）",
    "CRO服务": "service（研究外包）",
    "CDMO服务": "service（生产外包）",
}

changed = 0
for fname, mod in MODALITY.items():
    p = os.path.join(BASE, f"{fname}.md")
    if not os.path.exists(p):
        print("MISSING:", fname)
        continue
    text = open(p, encoding="utf-8").read()
    if "modality:" in text.split("---", 2)[1]:
        print("SKIP (already has modality):", fname)
        continue
    # insert after 'target:' or 'company:' line in frontmatter
    fm_end = text.index("---", 2)
    fm = text[:fm_end]
    if "target:" in fm:
        fm_new = re.sub(r"(target: [^\n]+\n)", r"\1" + f"modality: {mod}\n", fm, count=1)
    else:
        fm_new = re.sub(r"(company: [^\n]+\n)", r"\1" + f"modality: {mod}\n", fm, count=1)
    text = fm_new + text[fm_end:]
    # add to metadata section
    text = text.replace(
        "- entity_id: ",
        f"- modality: {mod}\n- entity_id: ", 1)
    open(p, "w", encoding="utf-8").write(text)
    changed += 1
    print("patched:", fname)

print("changed:", changed)
