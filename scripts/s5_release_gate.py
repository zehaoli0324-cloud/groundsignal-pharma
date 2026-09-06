#!/usr/bin/env python3
"""Machine-enforced S5 release predicate.

A family may be useful for development while still being ineligible for release.
This gate never infers expert or clinical approval from other metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(suite_path: Path, root: Path) -> dict[str, Any]:
    suite = load_json(suite_path)
    family_ids = [str(x) for x in suite.get("family_ids") or []]
    pending: list[dict[str, str | None]] = []
    approved: list[str] = []
    for family_id in family_ids:
        manifest = load_json(root / family_id / "manifest.json")
        status = manifest.get("status")
        if status == "gold_approved":
            approved.append(family_id)
        else:
            pending.append({"family_id": family_id, "status": status})

    result = {
        "stage": "S5",
        "gate_version": "s5-release-gate-v0.1.1",
        "suite_id": suite.get("suite_id"),
        "fresh_evidence": bool(suite.get("fresh_evidence", False)),
        "family_count": len(family_ids),
        "gold_approved_count": len(approved),
        "pending_gold_count": len(pending),
        "pending_gold": pending,
        "release_ready": len(family_ids) > 0 and not pending,
        "decision": "PASS" if len(family_ids) > 0 and not pending else "BLOCKED_GOLD_REVIEW",
        "rule": "release requires explicit status=gold_approved for every family; no approval is inferred",
    }
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", required=True, type=Path)
    p.add_argument("--root", default=ROOT / "medical/case-families", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    result = evaluate(args.suite, args.root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
