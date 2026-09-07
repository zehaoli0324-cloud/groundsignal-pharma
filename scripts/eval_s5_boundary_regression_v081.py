#!/usr/bin/env python3
"""S5 v0.8.1 exposed builder/exporter regression for F28-F31."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIRST_OBS = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.8.json"
EXPECTED_FIRST_OBS_BLOB = "8d2d96890915aa981652f78e3ff52242c7c0f51c"
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.8"
SUITE = EVAL_ROOT / "suite-fresh-lineage-v0.8.json"
FAMILY_ROOT = EVAL_ROOT / "families"
ATTACK_ROOT = EVAL_ROOT / "attack-sources"
CLEAN_ROOT = EVAL_ROOT / "clean-sources"
GOLD_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
GOLD_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def probe(trust: Any, raw_builder: Any, exporter: Any, path: Path, expected: str) -> dict[str, Any]:
    version = f"s5-trust-root-v0.8.1-{path.stem}"
    builder_rejected = False
    try:
        trust.build_policy([(SUITE, FAMILY_ROOT)], [path], policy_version=version)
    except ValueError:
        builder_rejected = True
    raw_policy = raw_builder.build_policy([(SUITE, FAMILY_ROOT)], [path], policy_version=version)
    exporter_rejected = False
    try:
        exporter._validate_policy_content(raw_policy, version)
    except PermissionError:
        exporter_rejected = True
    observed = "BLOCK" if builder_rejected and exporter_rejected else "ALLOW"
    return {
        "source": path.relative_to(ROOT).as_posix(),
        "expected": expected,
        "builder_rejected": builder_rejected,
        "exporter_rejected": exporter_rejected,
        "observed": observed,
        "pass": observed == expected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v081_regression")
    raw_builder = load_module(ROOT / "scripts/s5_trust_policy_v071.py", "s5_raw_v071_regression")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_export_v081_regression")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v081_regression")

    first_observation = {
        "expected_blob": EXPECTED_FIRST_OBS_BLOB,
        "observed_blob": git_blob_sha(FIRST_OBS),
    }
    first_observation["pass"] = first_observation["expected_blob"] == first_observation["observed_blob"]
    attacks = {
        path.stem: probe(trust, raw_builder, exporter, path, "BLOCK")
        for path in sorted(ATTACK_ROOT.glob("*.json"))
    }
    clean = {
        path.stem: probe(trust, raw_builder, exporter, path, "ALLOW")
        for path in sorted(CLEAN_ROOT.glob("*.json"))
    }
    baseline_ok = True
    try:
        baseline = trust.build_policy([(SUITE, FAMILY_ROOT)], [], policy_version="s5-trust-root-v0.8.1-baseline")
        exporter._validate_policy_content(baseline, "s5-trust-root-v0.8.1-baseline")
    except (ValueError, PermissionError):
        baseline_ok = False

    gold = release_gate.evaluate(GOLD_SUITE, GOLD_ROOT)
    gold_containment = bool(
        gold.get("gold_approved_count") == 0
        and gold.get("pending_gold_count") == 1
        and gold.get("release_ready") is False
        and gold.get("decision") == "BLOCKED_GOLD_REVIEW"
    )
    failed = [f"attack:{name}" for name, row in attacks.items() if not row["pass"]]
    failed.extend(f"clean:{name}" for name, row in clean.items() if not row["pass"])
    if not first_observation["pass"]:
        failed.append("immutable-first-observation")
    if not baseline_ok:
        failed.append("fresh-suite-baseline")
    if not gold_containment:
        failed.append("gold-containment")
    result = {
        "stage": "S5", "version": "v0.8.1",
        "eval_name": "multilingual-mosaic-exposed-boundary-regression",
        "evidence_class": "repaired_exposed_regression", "fresh_evidence": False,
        "immutable_v08_first_observation": first_observation,
        "baseline_policy_accepted": baseline_ok,
        "attacks": attacks, "clean_controls": clean,
        "regression_gate": "PASS" if not failed else "FAIL",
        "failed_gates": failed,
        "gold_approved_count": gold.get("gold_approved_count"),
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
