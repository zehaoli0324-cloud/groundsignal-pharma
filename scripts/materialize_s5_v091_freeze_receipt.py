#!/usr/bin/env python3
"""Materialize an S5 v0.9.1 receipt only from explicitly approved canonical main."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from s5_v091_freeze_control import build_receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt, failures = build_receipt(args.freeze_commit, args.approval_reference)
    if failures or receipt is None:
        print(json.dumps({"receipt_created": False, "failures": failures}, indent=2))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
