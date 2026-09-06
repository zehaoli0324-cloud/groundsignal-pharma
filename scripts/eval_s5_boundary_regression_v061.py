#!/usr/bin/env python3
"""S5 v0.6.1 exposed repair regression for v0.6 F20-F23.

This is NOT fresh evidence. The immutable v0.6 first observation remains FAIL.
The evaluator checks generic repairs for canonical identity, transformed-source
lineage, and authority-file check/read races, while requiring v0.5.1 regression
to remain green.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.6"
FIRST_OBS = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.6.json"
FIRST_OBS_BLOB = "f855e853ea2af9705cd3db478a3a40848459e0ea"
CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"
DERIVED_SOURCE = EVAL_ROOT / "attack-sources/derived-heldout-ordinary.json"
TOCTOU_SOURCE = EVAL_ROOT / "attack-sources/toctou-ordinary.json"
UNICODE_ORDINARY = EVAL_ROOT / "attack-sources/unicode-collision-ordinary.json"
UNICODE_SUITE = EVAL_ROOT / "unicode-authority/suite-unicode-v0.6.json"
UNICODE_ROOT = EVAL_ROOT / "unicode-authority/families"
ORDINARY_SOURCE = ROOT / "medical/examples/clinical-medication-safety-001.json"
TOCTOU_CASE_ID = "S5FRESH-BND6-TOCTOU-ORD-001"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def approved_eval(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic v0.6.1 exposed regression response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}
    except Exception as exc:
        return {
            "blocked": False,
            "exported": False,
            "error_type": type(exc).__name__,
            "unexpected_error": str(exc),
        }


def run_v051() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v061-v051-") as td:
        out = Path(td) / "v051.json"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/eval_s5_boundary_regression_v051.py"), "--out", str(out)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if not out.is_file():
            return {
                "returncode": proc.returncode,
                "regression_gate": "NO_RESULT",
                "failed_gates": ["NO_RESULT"],
                "pass": False,
            }
        data = load_json(out)
        return {
            "returncode": proc.returncode,
            "regression_gate": data.get("regression_gate"),
            "failed_gates": data.get("failed_gates"),
            "pass": bool(
                proc.returncode == 0
                and data.get("regression_gate") == "PASS"
                and data.get("failed_gates") == []
            ),
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v061")
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v061")

    observed_first_blob = git_blob_sha1(FIRST_OBS)
    preservation = {
        "expected_git_blob_sha1": FIRST_OBS_BLOB,
        "observed_git_blob_sha1": observed_first_blob,
        "pass": observed_first_blob == FIRST_OBS_BLOB,
    }
    trust_root = exporter.trust_root_status()
    trust_root = {
        "registry_version": trust_root.get("registry_version"),
        "registry_git_blob_sha1": trust_root.get("registry_git_blob_sha1"),
        "default_policy_id": trust_root.get("default_policy_id"),
        "default_policy_git_blob_sha1": trust_root.get("default_policy_git_blob_sha1"),
        "pass": bool(trust_root.get("pass")),
    }
    prior_regression = run_v051()

    # F20: transformed benchmark-derived content should be rejected generically
    # by semantic-core lineage, without hard-coding a case id.
    f20_builder_rejected = False
    f20_validator_rejected = False
    f20_policy = None
    try:
        f20_policy = trust.build_policy(
            [(CARRIER_SUITE, CARRIER_ROOT)],
            ordinary_sources=[DERIVED_SOURCE],
            policy_version="s5-trust-root-v0.6.1-derived-regression",
        )
    except ValueError:
        f20_builder_rejected = True
    if f20_policy is not None:
        try:
            exporter._validate_policy_content(
                f20_policy, "s5-trust-root-v0.6.1-derived-regression"
            )
        except PermissionError:
            f20_validator_rejected = True
    f20 = {
        "policy_builder_rejected": f20_builder_rejected,
        "policy_content_validator_rejected": f20_validator_rejected,
        "pass": f20_builder_rejected or f20_validator_rejected,
    }

    # F21: raw-distinct but canonically equivalent identifiers should collide.
    f21_builder_rejected = False
    f21_validator_rejected = False
    f21_policy = None
    try:
        f21_policy = trust.build_policy(
            [(UNICODE_SUITE, UNICODE_ROOT)],
            ordinary_sources=[UNICODE_ORDINARY],
            policy_version="s5-trust-root-v0.6.1-unicode-regression",
        )
    except ValueError:
        f21_builder_rejected = True
    if f21_policy is not None:
        try:
            exporter._validate_policy_content(
                f21_policy, "s5-trust-root-v0.6.1-unicode-regression"
            )
        except PermissionError:
            f21_validator_rejected = True
    f21 = {
        "policy_builder_rejected": f21_builder_rejected,
        "policy_content_validator_rejected": f21_validator_rejected,
        "pass": f21_builder_rejected or f21_validator_rejected,
    }

    # F22: mutate the registry on disk immediately after its bytes are read.
    # Correct code hashes and parses that already-captured byte snapshot, so the
    # new registry cannot influence the same authentication decision.
    registry_path = exporter.TRUST_POLICY_REGISTRY_PATH
    registry_original = registry_path.read_text(encoding="utf-8")
    runtime_policy = EVAL_ROOT / "runtime-toctou-policy-v0.6.1.json"
    attack_policy_id = "s5-trust-root-v0.6.1-toctou-regression"
    attack_policy = trust.build_policy(
        ordinary_sources=[TOCTOU_SOURCE],
        policy_version=attack_policy_id,
    )
    runtime_policy.write_text(
        json.dumps(attack_policy, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    attack_registry = {
        "registry_version": exporter.TRUST_POLICY_REGISTRY_VERSION,
        "default_policy_id": attack_policy_id,
        "policies": {
            attack_policy_id: {
                "path": runtime_policy.relative_to(ROOT).as_posix(),
                "git_blob_sha1": git_blob_sha1(runtime_policy),
            }
        },
    }
    attack_registry_text = json.dumps(
        attack_registry, ensure_ascii=False, separators=(",", ":")
    ) + "\n"
    original_read_bytes = Path.read_bytes
    f22_state = {"triggered": False}

    def registry_race_read_bytes(self: Path) -> bytes:
        data = original_read_bytes(self)
        if self.resolve() == registry_path.resolve() and not f22_state["triggered"]:
            registry_path.write_text(attack_registry_text, encoding="utf-8")
            f22_state["triggered"] = True
        return data

    Path.read_bytes = registry_race_read_bytes
    try:
        try:
            case = exporter.load_cases(TOCTOU_SOURCE)[TOCTOU_CASE_ID]
            f22_result = export_probe(exporter, case)
        except PermissionError as exc:
            f22_result = {
                "blocked": True,
                "exported": False,
                "error_type": type(exc).__name__,
            }
    finally:
        Path.read_bytes = original_read_bytes
        registry_path.write_text(registry_original, encoding="utf-8")
        runtime_policy.unlink(missing_ok=True)
    f22 = {
        "race_triggered": f22_state["triggered"],
        **f22_result,
        "pass": bool(f22_state["triggered"] and f22_result["blocked"]),
    }

    # F23: mutate an allowlisted source immediately after one source snapshot is
    # captured. The captured payload must not become the malicious bytes, and a
    # later export re-authentication must reject the changed backing file.
    ordinary_original = ORDINARY_SOURCE.read_text(encoding="utf-8")
    malicious = json.loads(ordinary_original)
    marker = "S5_V061_POST_SNAPSHOT_SOURCE_REPLACEMENT"
    malicious["interaction"]["prompt"] += f" [{marker}]"
    malicious_text = json.dumps(malicious, ensure_ascii=False, separators=(",", ":")) + "\n"
    original_read_bytes = Path.read_bytes
    f23_state = {"triggered": False}
    marker_loaded = False

    def source_race_read_bytes(self: Path) -> bytes:
        data = original_read_bytes(self)
        if self.resolve() == ORDINARY_SOURCE.resolve() and not f23_state["triggered"]:
            ORDINARY_SOURCE.write_text(malicious_text, encoding="utf-8")
            f23_state["triggered"] = True
        return data

    Path.read_bytes = source_race_read_bytes
    try:
        try:
            loaded = exporter.load_cases(ORDINARY_SOURCE)["clinical-medication-safety-001"]
            marker_loaded = marker in str(loaded.get("interaction", {}).get("prompt", ""))
            f23_result = export_probe(exporter, loaded)
        except PermissionError as exc:
            f23_result = {
                "blocked": True,
                "exported": False,
                "error_type": type(exc).__name__,
            }
    finally:
        Path.read_bytes = original_read_bytes
        ORDINARY_SOURCE.write_text(ordinary_original, encoding="utf-8")
    f23 = {
        "race_triggered": f23_state["triggered"],
        "mutated_payload_loaded": marker_loaded,
        **f23_result,
        "pass": bool(
            f23_state["triggered"]
            and not marker_loaded
            and f23_result["blocked"]
        ),
    }

    gates = {
        "historical_v06_first_observation_preservation": preservation,
        "authenticated_trust_root": trust_root,
        "prior_v051_exposed_regression": prior_regression,
        "S5-F20": f20,
        "S5-F21": f21,
        "S5-F22": f22,
        "S5-F23": f23,
    }
    failed = [name for name, gate in gates.items() if not gate.get("pass")]
    passed = not failed
    result = {
        "stage": "S5",
        "version": "v0.6.1",
        "eval_name": "identity-lineage-toctou-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "source_fresh_suite": "S5 v0.6 first observation; now exposed",
        **gates,
        "historical_failure_disposition": {
            "S5-F20": "REPAIRED_EXPOSED_REGRESSION" if f20["pass"] else "OPEN",
            "S5-F21": "REPAIRED_EXPOSED_REGRESSION" if f21["pass"] else "OPEN",
            "S5-F22": "REPAIRED_EXPOSED_REGRESSION" if f22["pass"] else "OPEN",
            "S5-F23": "REPAIRED_EXPOSED_REGRESSION" if f23["pass"] else "OPEN",
        },
        "failed_gates": failed,
        "regression_gate": "PASS" if passed else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_fresh_requirement": (
            "freeze v0.6.1, then author a genuinely new post-freeze S5 suite; "
            "v0.6 remains exposed forever"
        ),
        "notes": [
            "v0.6 first-observation FAIL is preserved exactly and is never relabeled fresh.",
            "Canonical case identity uses Unicode NFC at policy and export boundaries.",
            "Benchmark-derived ordinary-source laundering is blocked by a stable semantic-core fingerprint, not a case-id patch.",
            "Security-sensitive JSON authority is hashed and parsed from one byte snapshot, eliminating the tested check/read race.",
            "No expert approval, clinical validation, real-user evidence, or model-training gain is inferred."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
