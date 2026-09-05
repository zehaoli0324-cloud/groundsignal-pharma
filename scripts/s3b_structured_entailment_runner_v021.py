#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s3b_entailment_engine_v021 as engine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in doc["items"]:
        evidence = item["evidence_propositions"]
        candidate = item["candidate_propositions"]
        verdicts = [engine.classify_proposition(evidence, cp) for cp in candidate]
        relation, cues = engine.aggregate(verdicts)
        rows.append({
            "item_id": item["item_id"],
            "predicted_relation": relation,
            "proposition_verdicts": verdicts,
            "cues": cues,
            "engine_version": engine.ENGINE_VERSION,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"predictions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote S3b v0.2.1 predictions for {len(rows)} items to {out}")


if __name__ == "__main__":
    main()
