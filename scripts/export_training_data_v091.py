#!/usr/bin/env python3
"""S5 export-boundary candidate for the v0.9.1 exposed lineage repair."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_legacy = _load("export_training_data_v061_v091_legacy", _HERE / "export_training_data_v061.py")
_lineage = _load("s5_lineage_detector_v091_export", _HERE / "s5_lineage_detector_v091.py")
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

_orig_validate_policy_content = _legacy._validate_policy_content


def canonical_case_id(value: Any) -> str:
    return _lineage.canonical_case_id(value)


def _require_canonical_case_id(value: Any, label: str) -> str:
    try:
        return _lineage.require_compatibility_safe_case_id(value, label)
    except ValueError as exc:
        raise PermissionError(f"S5 export blocked: {exc}") from exc


def _collect_authenticated_policy_records(
    policy: Dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    benchmark: list[dict[str, Any]] = []
    for suite_id, suite in (policy.get("benchmark_suites") or {}).items():
        for family_id, family in (suite.get("families") or {}).items():
            for case_id, entry in (family.get("cases") or {}).items():
                path = _legacy._resolve_repo_path(entry.get("source_case_path"))
                case, _ = _legacy._authenticated_json(
                    path,
                    str(entry.get("source_case_git_blob_sha1") or ""),
                    f"v0.9.1 lineage source case {case_id!r}",
                )
                benchmark.append({
                    "case_id": str(case_id),
                    "split": str(entry.get("split") or ""),
                    "case": case,
                    "source": f"{suite_id}/{family_id}/{case_id}",
                })
    ordinary: list[dict[str, Any]] = []
    for rel, entry in (policy.get("ordinary_training_sources") or {}).items():
        path = _legacy._resolve_repo_path(rel)
        case, _ = _legacy._authenticated_json(
            path,
            str((entry or {}).get("git_blob_sha1") or ""),
            f"v0.9.1 lineage ordinary source {rel!r}",
        )
        ordinary.append({"case": case, "source": rel})
    return benchmark, ordinary


def _validate_policy_content(policy: Dict[str, Any], expected_policy_id: str) -> None:
    _orig_validate_policy_content(policy, expected_policy_id)
    benchmark, ordinary = _collect_authenticated_policy_records(policy)
    try:
        _lineage.validate_policy_records(benchmark, ordinary)
    except ValueError as exc:
        raise PermissionError(f"S5 export blocked: v0.9.1 lineage policy violation: {exc}") from exc


_legacy.canonical_case_id = canonical_case_id
_legacy._require_canonical_case_id = _require_canonical_case_id
_legacy._validate_policy_content = _validate_policy_content
LINEAGE_METHOD_VERSION = _lineage.METHOD_VERSION


if __name__ == "__main__":
    _legacy.main()

