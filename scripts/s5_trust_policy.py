#!/usr/bin/env python3
"""External trust-root policy helpers for GroundSignal S5 training export.

The policy is deliberately separate from benchmark cases. A case cannot make itself
trusted by copying or rewriting local provenance. Operators/evaluators explicitly
select trusted suites or ordinary sources before export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_VERSION = "s5-trust-root-v0.3.1"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def repo_path(path: Path | str) -> Path:
    raw = Path(path)
    resolved = raw.resolve() if raw.is_absolute() else (ROOT / raw).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"trust-policy path escapes repository: {path!s}") from exc
    return resolved


def repo_rel(path: Path | str) -> str:
    return repo_path(path).relative_to(ROOT.resolve()).as_posix()


def build_suite_entry(suite_path: Path, family_root: Path) -> tuple[str, dict[str, Any]]:
    suite_path = repo_path(suite_path)
    family_root = repo_path(family_root)
    suite = load_json(suite_path)
    suite_id = str(suite.get("suite_id") or "")
    if not suite_id:
        raise ValueError(f"{suite_path}: suite_id is required")
    family_ids = [str(x) for x in suite.get("family_ids") or []]
    if not family_ids:
        raise ValueError(f"{suite_path}: family_ids must be non-empty")

    families: dict[str, Any] = {}
    for family_id in family_ids:
        manifest_path = family_root / family_id / "manifest.json"
        manifest = load_json(manifest_path)
        if str(manifest.get("family_id") or "") != family_id:
            raise ValueError(f"{manifest_path}: family_id mismatch")
        cases: dict[str, Any] = {}
        for ref in manifest.get("cases") or []:
            case_id = str(ref.get("case_id") or "")
            rel = str(ref.get("path") or "")
            split = str(ref.get("split") or "")
            variant_type = str(ref.get("variant_type") or "")
            if not case_id or not rel or split not in {"dev", "regression", "heldout"}:
                raise ValueError(f"{manifest_path}: invalid case ref {ref!r}")
            case_path = manifest_path.parent / rel
            cases[case_id] = {
                "source_case_path": repo_rel(case_path),
                "source_case_git_blob_sha1": git_blob_sha1(case_path),
                "split": split,
                "variant_type": variant_type,
            }
        families[family_id] = {
            "manifest_path": repo_rel(manifest_path),
            "manifest_git_blob_sha1": git_blob_sha1(manifest_path),
            "cases": cases,
        }

    return suite_id, {
        "suite_path": repo_rel(suite_path),
        "suite_git_blob_sha1": git_blob_sha1(suite_path),
        "family_root": repo_rel(family_root),
        "families": families,
    }


def build_policy(
    suite_specs: list[tuple[Path, Path]] | None = None,
    ordinary_sources: list[Path] | None = None,
) -> dict[str, Any]:
    suites: dict[str, Any] = {}
    for suite_path, family_root in suite_specs or []:
        suite_id, entry = build_suite_entry(suite_path, family_root)
        if suite_id in suites:
            raise ValueError(f"duplicate trusted suite_id: {suite_id}")
        suites[suite_id] = entry

    ordinary: dict[str, Any] = {}
    for source in ordinary_sources or []:
        path = repo_path(source)
        rel = repo_rel(path)
        ordinary[rel] = {"git_blob_sha1": git_blob_sha1(path)}

    return {
        "policy_version": POLICY_VERSION,
        "benchmark_suites": suites,
        "ordinary_training_sources": ordinary,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build an explicit external S5 export trust policy")
    p.add_argument("--suite", action="append", type=Path, default=[])
    p.add_argument("--family-root", action="append", type=Path, default=[])
    p.add_argument("--ordinary-source", action="append", type=Path, default=[])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if len(args.suite) != len(args.family_root):
        raise SystemExit("--suite and --family-root must be supplied the same number of times")
    policy = build_policy(list(zip(args.suite, args.family_root)), args.ordinary_source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(policy, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
