#!/usr/bin/env python3
"""Fail closed on v0.10 authoring until v0.9.1 is canonically frozen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from s5_v091_freeze_control import NEXT_FRESH_ROOT_REL, RECEIPT_REL, ROOT, evaluate_admission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=ROOT / RECEIPT_REL)
    parser.add_argument("--fresh-root", type=Path, default=ROOT / NEXT_FRESH_ROOT_REL)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_admission(args.receipt, args.fresh_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["guard_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
