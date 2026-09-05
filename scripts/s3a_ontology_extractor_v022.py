#!/usr/bin/env python3
"""S3a ontology-guided extractor v0.2.2.

Repairs comparison-operator binding so phrases such as `under eGFR 45`
remain LT 45 rather than being collapsed to an EQ 45 point value.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import s3a_ontology_extractor_v021 as base

VERSION = "s3a-ontology-guided-v0.2.2"
base.VERSION = VERSION


def egfr_conditions(text: str):
    t = base.norm(text)
    for pat in [
        r"egfr\s*(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)",
        r"from\s+egfr\s*(\d+(?:\.\d+)?)\s*(?:through|to|-)\s*(\d+(?:\.\d+)?)",
        r"between\s+(?:egfr\s*)?(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, t)
        if m:
            lo = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            hi = float(m.group(2)) if "." in m.group(2) else int(m.group(2))
            return [{"variable": "egfr", "operator": "RANGE", "low": lo, "high": hi}]

    # Comparison markers must be resolved before plain point-value parsing.
    for pat in [
        r"(?:below|under|less than|lower than|<)\s+egfr\s*(\d+(?:\.\d+)?)",
        r"egfr\s*(?:is\s+)?(?:below|under|less than|lower than|<)\s*(\d+(?:\.\d+)?)",
        r"(?:below|under|less than|lower than|<)\s*(\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, t)
        if m:
            v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            return [{"variable": "egfr", "operator": "LT", "value": v}]

    m = re.search(r"egfr\s*(?:of|=|is|at)?\s*(\d+(?:\.\d+)?)", t)
    if m:
        v = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
        return [{"variable": "egfr", "operator": "EQ", "value": v}]
    return []


# Patch the imported extractor's binding function so all existing semantic-family
# extractors use the corrected operator semantics.
base.egfr_conditions = egfr_conditions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        r = base.extract_item(item)
        r["extractor_version"] = VERSION
        rows.append({"item_id": item["item_id"], "role": item.get("role", "evidence"), **r})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} S3a v0.2.2 extraction records to {out}")


if __name__ == "__main__":
    main()
