#!/usr/bin/env python3
"""S5 trust-policy entry point, v0.7.2 exposed repair.

The direct v0.7.1 deterministic implementation is preserved byte-for-byte in
`s5_trust_policy_v071.py`. This entry point keeps its NFKC/cross-split rules and
adds generic explainable lineage checks for paraphrase and partial-field reuse.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
POLICY_VERSION = "s5-trust-root-v0.7.2"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_legacy = _load("s5_trust_policy_v071_legacy", _HERE / "s5_trust_policy_v071.py")
_lineage = _load("s5_lineage_detector_v072", _HERE / "s5_lineage_detector.py")

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

# New version marker overrides the re-exported v0.7.1 constant.
POLICY_VERSION = "s5-trust-root-v0.7.2"
_orig_build_policy = _legacy.build_policy


def canonical_case_id(value: Any) -> str:
    return _lineage.canonical_case_id(value)


def require_canonical_case_id(value: Any, label: str) -> str:
    try:
        return _lineage.require_compatibility_safe_case_id(value, label)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _collect_policy_records(policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    benchmark: list[dict[str, Any]] = []
    for suite_id, suite in (policy.get("benchmark_suites") or {}).items():
        for family_id, family in (suite.get("families") or {}).items():
            for case_id, entry in (family.get("cases") or {}).items():
                path = _legacy.repo_path(entry["source_case_path"])
                benchmark.append(
                    {
                        "case_id": str(case_id),
                        "split": str(entry.get("split") or ""),
                        "case": _legacy.load_json(path),
                        "source": f"{suite_id}/{family_id}/{case_id}",
                    }
                )
    ordinary: list[dict[str, Any]] = []
    for rel in (policy.get("ordinary_training_sources") or {}):
        path = _legacy.repo_path(rel)
        ordinary.append({"case": _legacy.load_json(path), "source": rel})
    return benchmark, ordinary


def _validate_lineage(policy: dict[str, Any]) -> dict[str, Any]:
    benchmark, ordinary = _collect_policy_records(policy)
    return _lineage.validate_policy_records(benchmark, ordinary)


def build_policy(
    suite_specs: list[tuple[Path, Path]] | None = None,
    ordinary_sources: list[Path] | None = None,
    *,
    policy_version: str = POLICY_VERSION,
) -> dict[str, Any]:
    policy = _orig_build_policy(
        suite_specs,
        ordinary_sources,
        policy_version=policy_version,
    )
    try:
        _validate_lineage(policy)
    except ValueError as exc:
        raise ValueError(f"S5 v0.7.2 lineage policy rejected: {exc}") from exc
    return policy


_legacy.canonical_case_id = canonical_case_id
_legacy.require_canonical_case_id = require_canonical_case_id
_legacy.build_policy = build_policy

LINEAGE_METHOD_VERSION = _lineage.METHOD_VERSION


if __name__ == "__main__":
    raise SystemExit(_legacy.main())
