#!/usr/bin/env python3
"""S5 trust-policy candidate for the v0.9.1 exposed lineage repair."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
POLICY_VERSION = "s5-trust-root-v0.9.1-exposed"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_legacy = _load("s5_trust_policy_v071_v091_legacy", _HERE / "s5_trust_policy_v071.py")
_lineage = _load("s5_lineage_detector_v091", _HERE / "s5_lineage_detector_v091.py")
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

POLICY_VERSION = "s5-trust-root-v0.9.1-exposed"
_orig_build_policy = _legacy.build_policy


def canonical_case_id(value: Any) -> str:
    return _lineage.canonical_case_id(value)


def require_canonical_case_id(value: Any, label: str) -> str:
    return _lineage.require_compatibility_safe_case_id(value, label)


def _collect_policy_records(policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    benchmark: list[dict[str, Any]] = []
    for suite_id, suite in (policy.get("benchmark_suites") or {}).items():
        for family_id, family in (suite.get("families") or {}).items():
            for case_id, entry in (family.get("cases") or {}).items():
                path = _legacy.repo_path(entry["source_case_path"])
                benchmark.append({
                    "case_id": str(case_id),
                    "split": str(entry.get("split") or ""),
                    "case": _legacy.load_json(path),
                    "source": f"{suite_id}/{family_id}/{case_id}",
                })
    ordinary = [
        {"case": _legacy.load_json(_legacy.repo_path(rel)), "source": rel}
        for rel in (policy.get("ordinary_training_sources") or {})
    ]
    return benchmark, ordinary


def build_policy(
    suite_specs: list[tuple[Path, Path]] | None = None,
    ordinary_sources: list[Path] | None = None,
    *,
    policy_version: str = POLICY_VERSION,
) -> dict[str, Any]:
    policy = _orig_build_policy(suite_specs, ordinary_sources, policy_version=policy_version)
    benchmark, ordinary = _collect_policy_records(policy)
    try:
        _lineage.validate_policy_records(benchmark, ordinary)
    except ValueError as exc:
        raise ValueError(f"S5 v0.9.1 exposed lineage policy rejected: {exc}") from exc
    return policy


_legacy.canonical_case_id = canonical_case_id
_legacy.require_canonical_case_id = require_canonical_case_id
_legacy.build_policy = build_policy
LINEAGE_METHOD_VERSION = _lineage.METHOD_VERSION


if __name__ == "__main__":
    raise SystemExit(_legacy.main())

