#!/usr/bin/env python3
"""Shared fail-closed freeze and v0.10 authoring controls for S5 v0.9.1."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ATTESTATION = ROOT / "medical/stage-evals/S5/freeze-readiness-v0.9.1.json"
ATTESTATION_VERIFIER = ROOT / "scripts/verify_s5_v091_freeze_readiness.py"
CONTROL_PLANE = ROOT / "medical/stage-evals/S5/control-plane-readiness-v0.9.1.json"
CONTROL_PLANE_VERIFIER = ROOT / "scripts/verify_s5_v091_control_plane_readiness.py"
RECEIPT_REL = "medical/stage-evals/S5/freeze-receipt-v0.9.1.json"
NEXT_FRESH_ROOT_REL = "medical/stage-evals/S5/fresh-lineage-v0.10"
EXPECTED_ATTESTATION_BLOB = "ebf61ef53419490a77c1182a0190efd44bd3d246"
EXPECTED_PR = 7
GENERATOR_VERSION = "s5-v091-freeze-receipt-v0.1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
APPROVAL_RE = re.compile(r"^user-approval:[A-Za-z0-9._:/#-]{8,}$")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_current_attestation() -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    try:
        data = ATTESTATION.read_bytes()
        blob = git_blob_sha1(data)
        manifest = json.loads(data)
        verifier = load_module(ATTESTATION_VERIFIER, "s5_v091_attestation_verifier")
        result = verifier.verify(ATTESTATION)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError):
        return None, None, ""
    return manifest, result, blob


def verify_current_control_plane() -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    try:
        data = CONTROL_PLANE.read_bytes()
        blob = git_blob_sha1(data)
        manifest = json.loads(data)
        verifier = load_module(CONTROL_PLANE_VERIFIER, "s5_v091_control_plane_verifier")
        result = verifier.verify(CONTROL_PLANE)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError):
        return None, None, ""
    return manifest, result, blob


def _verify_commit_pins(
    commit: str,
    attestation: dict[str, Any],
    control_plane: dict[str, Any],
    control_plane_blob: str,
    failures: list[str],
) -> tuple[int, int]:
    attestation_blob = git("rev-parse", f"{commit}:{ATTESTATION.relative_to(ROOT)}")
    if attestation_blob.returncode != 0 or attestation_blob.stdout.strip() != EXPECTED_ATTESTATION_BLOB:
        failures.append("ATTESTATION_PIN_MISMATCH")
    control_blob = git("rev-parse", f"{commit}:{CONTROL_PLANE.relative_to(ROOT)}")
    if control_blob.returncode != 0 or control_blob.stdout.strip() != control_plane_blob:
        failures.append("CONTROL_PLANE_ATTESTATION_PIN_MISMATCH")

    verified = 0
    for row in attestation.get("pinned_artifacts", []):
        rel = str(row.get("path") or "")
        observed = git("rev-parse", f"{commit}:{rel}")
        if observed.returncode != 0 or observed.stdout.strip() != row.get("git_blob_sha1"):
            failures.append(f"FREEZE_ARTIFACT_MISMATCH:{rel}")
        else:
            verified += 1
    control_verified = 0
    for row in control_plane.get("pinned_control_plane_artifacts", []):
        rel = str(row.get("path") or "")
        observed = git("rev-parse", f"{commit}:{rel}")
        if observed.returncode != 0 or observed.stdout.strip() != row.get("git_blob_sha1"):
            failures.append(f"FREEZE_CONTROL_PLANE_ARTIFACT_MISMATCH:{rel}")
        else:
            control_verified += 1
    return verified, control_verified


def build_receipt(freeze_commit: str, approval_reference: str) -> tuple[dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    if not COMMIT_RE.fullmatch(freeze_commit):
        failures.append("FREEZE_COMMIT_INVALID")
    if not APPROVAL_RE.fullmatch(approval_reference):
        failures.append("APPROVAL_REFERENCE_INVALID")
    if failures:
        return None, failures

    attestation, attestation_check, attestation_blob = verify_current_attestation()
    if attestation is None or attestation_check is None:
        return None, ["CURRENT_ATTESTATION_UNAVAILABLE"]
    if attestation_blob != EXPECTED_ATTESTATION_BLOB:
        return None, ["CURRENT_ATTESTATION_BLOB_MISMATCH"]
    if attestation_check.get("verification_gate") != "PASS":
        return None, ["CURRENT_ATTESTATION_NOT_READY"]
    control_plane, control_check, control_plane_blob = verify_current_control_plane()
    if control_plane is None or control_check is None:
        return None, ["CURRENT_CONTROL_PLANE_UNAVAILABLE"]
    if control_check.get("verification_gate") != "PASS":
        return None, ["CURRENT_CONTROL_PLANE_NOT_READY"]

    if git("cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
        return None, ["FREEZE_COMMIT_UNAVAILABLE"]
    canonical = git("rev-parse", "origin/main")
    if canonical.returncode != 0:
        return None, ["CANONICAL_MAIN_UNAVAILABLE"]
    if canonical.stdout.strip() != freeze_commit:
        failures.append("FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP")
    if git("merge-base", "--is-ancestor", freeze_commit, "origin/main").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN")
    if git("cat-file", "-e", f"{freeze_commit}:{RECEIPT_REL}").returncode == 0:
        failures.append("RECEIPT_PREEXISTED_AT_FREEZE")
    if git("cat-file", "-e", f"{freeze_commit}:{NEXT_FRESH_ROOT_REL}").returncode == 0:
        failures.append("NEXT_FRESH_ASSETS_PREEXISTED_AT_FREEZE")

    verified, control_verified = _verify_commit_pins(
        freeze_commit, attestation, control_plane, control_plane_blob, failures
    )
    tree = git("show", "-s", "--format=%T", freeze_commit)
    if tree.returncode != 0:
        failures.append("FREEZE_TREE_UNAVAILABLE")
    if failures:
        return None, failures

    pinned_count = len(attestation.get("pinned_artifacts", []))
    control_count = len(control_plane.get("pinned_control_plane_artifacts", []))
    return {
        "stage": "S5",
        "version": "v0.9.1",
        "receipt_type": "canonical_freeze_receipt",
        "generator_version": GENERATOR_VERSION,
        "candidate_frozen": True,
        "control_plane_frozen": True,
        "merged_pr": EXPECTED_PR,
        "explicit_merge_approval": True,
        "approval_reference": approval_reference,
        "attestation_git_blob_sha1": EXPECTED_ATTESTATION_BLOB,
        "control_plane_attestation_git_blob_sha1": control_plane_blob,
        "freeze_commit": freeze_commit,
        "freeze_tree_sha": tree.stdout.strip(),
        "pinned_artifact_count": pinned_count,
        "verified_artifact_count": verified,
        "control_plane_pinned_artifact_count": control_count,
        "control_plane_verified_artifact_count": control_verified,
        "freeze_receipt_absent_at_freeze": True,
        "next_fresh_assets_absent_at_freeze": True,
        "fresh_evidence": False,
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_step": "Commit this receipt after the canonical freeze; only then may v0.10 authoring admission be evaluated.",
    }, []


def validate_receipt(
    receipt: dict[str, Any],
    attestation: dict[str, Any],
    control_plane: dict[str, Any],
    control_plane_blob: str,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    freeze_commit = str(receipt.get("freeze_commit") or "")
    required = {
        "stage": "S5",
        "version": "v0.9.1",
        "receipt_type": "canonical_freeze_receipt",
        "generator_version": GENERATOR_VERSION,
        "candidate_frozen": True,
        "control_plane_frozen": True,
        "merged_pr": EXPECTED_PR,
        "explicit_merge_approval": True,
        "attestation_git_blob_sha1": EXPECTED_ATTESTATION_BLOB,
        "control_plane_attestation_git_blob_sha1": control_plane_blob,
        "freeze_receipt_absent_at_freeze": True,
        "next_fresh_assets_absent_at_freeze": True,
        "fresh_evidence": False,
        "gold_approved": False,
        "bounded_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            failures.append(f"RECEIPT_FIELD_INVALID:{key}")
    if not APPROVAL_RE.fullmatch(str(receipt.get("approval_reference") or "")):
        failures.append("APPROVAL_REFERENCE_INVALID")
    if not COMMIT_RE.fullmatch(freeze_commit):
        failures.append("FREEZE_COMMIT_INVALID")
        return False, failures
    if git("cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
        failures.append("FREEZE_COMMIT_UNAVAILABLE")
        return False, failures
    if git("merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ANCESTOR")
    if git("merge-base", "--is-ancestor", freeze_commit, "origin/main").returncode != 0:
        failures.append("FREEZE_COMMIT_NOT_ON_CANONICAL_MAIN")
    if git("cat-file", "-e", f"{freeze_commit}:{RECEIPT_REL}").returncode == 0:
        failures.append("RECEIPT_PREEXISTED_AT_FREEZE")
    if git("cat-file", "-e", f"{freeze_commit}:{NEXT_FRESH_ROOT_REL}").returncode == 0:
        failures.append("NEXT_FRESH_ASSETS_PREEXISTED_AT_FREEZE")
    tree = git("show", "-s", "--format=%T", freeze_commit)
    if tree.returncode != 0 or tree.stdout.strip() != receipt.get("freeze_tree_sha"):
        failures.append("FREEZE_TREE_MISMATCH")
    verified, control_verified = _verify_commit_pins(
        freeze_commit, attestation, control_plane, control_plane_blob, failures
    )
    if receipt.get("pinned_artifact_count") != len(attestation.get("pinned_artifacts", [])):
        failures.append("PINNED_ARTIFACT_COUNT_MISMATCH")
    if receipt.get("verified_artifact_count") != verified:
        failures.append("VERIFIED_ARTIFACT_COUNT_MISMATCH")
    if receipt.get("control_plane_pinned_artifact_count") != len(control_plane.get("pinned_control_plane_artifacts", [])):
        failures.append("CONTROL_PLANE_PINNED_ARTIFACT_COUNT_MISMATCH")
    if receipt.get("control_plane_verified_artifact_count") != control_verified:
        failures.append("CONTROL_PLANE_VERIFIED_ARTIFACT_COUNT_MISMATCH")
    return not failures, failures


def evaluate_admission(receipt_path: Path, fresh_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    attestation, attestation_check, attestation_blob = verify_current_attestation()
    if attestation is None or attestation_check is None:
        failures.append("CURRENT_ATTESTATION_UNAVAILABLE")
        attestation = {"pinned_artifacts": []}
    elif attestation_blob != EXPECTED_ATTESTATION_BLOB or attestation_check.get("verification_gate") != "PASS":
        failures.append("CURRENT_ATTESTATION_NOT_READY")
    control_plane, control_check, control_plane_blob = verify_current_control_plane()
    if control_plane is None or control_check is None:
        failures.append("CURRENT_CONTROL_PLANE_UNAVAILABLE")
        control_plane = {"pinned_control_plane_artifacts": []}
    elif control_check.get("verification_gate") != "PASS":
        failures.append("CURRENT_CONTROL_PLANE_NOT_READY")

    receipt_present = receipt_path.is_file()
    receipt_valid = False
    freeze_commit: str | None = None
    if receipt_present:
        try:
            receipt = load_json(receipt_path)
            freeze_commit = str(receipt.get("freeze_commit") or "") or None
            receipt_valid, receipt_failures = validate_receipt(
                receipt, attestation, control_plane, control_plane_blob
            )
            failures.extend(receipt_failures)
        except (OSError, ValueError, json.JSONDecodeError):
            failures.append("RECEIPT_UNREADABLE")

    assets = sorted(
        path.relative_to(fresh_root).as_posix() for path in fresh_root.rglob("*") if path.is_file()
    ) if fresh_root.is_dir() else []
    protocol_valid = False
    receipt_publication_commit: str | None = None
    if assets:
        if not receipt_valid:
            failures.append("UNAUTHORIZED_FRESH_ASSETS_BEFORE_VERIFIED_FREEZE")
        protocol_path = fresh_root / "protocol-v0.10.json"
        if not protocol_path.is_file():
            failures.append("FRESH_PROTOCOL_MISSING")
        else:
            try:
                protocol = load_json(protocol_path)
                receipt_publication_commit = str(protocol.get("freeze_receipt_materialization_commit") or "") or None
                protocol_valid = bool(
                    protocol.get("stage") == "S5"
                    and protocol.get("version") == "v0.10"
                    and protocol.get("fresh_evidence") is True
                    and protocol.get("authored_after_freeze") is True
                    and protocol.get("target_implementation_freeze_commit") == freeze_commit
                    and receipt_publication_commit
                    and COMMIT_RE.fullmatch(receipt_publication_commit)
                )
                if protocol_valid:
                    receipt_blob = git_blob_sha1(receipt_path.read_bytes())
                    chronology = bool(
                        git("cat-file", "-e", f"{receipt_publication_commit}^{{commit}}").returncode == 0
                        and git("merge-base", "--is-ancestor", str(freeze_commit), receipt_publication_commit).returncode == 0
                        and git("merge-base", "--is-ancestor", receipt_publication_commit, "HEAD").returncode == 0
                        and git("rev-parse", f"{receipt_publication_commit}:{RECEIPT_REL}").stdout.strip() == receipt_blob
                        and git("cat-file", "-e", f"{receipt_publication_commit}:{NEXT_FRESH_ROOT_REL}").returncode != 0
                    )
                    protocol_valid = chronology
            except (OSError, ValueError, json.JSONDecodeError):
                protocol_valid = False
            if not protocol_valid:
                failures.append("FRESH_PROTOCOL_OR_CHRONOLOGY_INVALID")

    allowed = bool(receipt_valid and (not assets or protocol_valid))
    if failures:
        decision, gate = "FAIL_CLOSED", "FAIL"
    elif allowed:
        decision, gate = "ALLOW_AFTER_VERIFIED_FREEZE", "PASS"
    else:
        decision, gate = "BLOCKED_NOT_FROZEN", "PASS"
    return {
        "stage": "S5",
        "version": "v0.10-admission-v0.1",
        "guard": "next-fresh-authoring-admission",
        "evidence_class": "development_process_guard",
        "fresh_evidence": False,
        "first_observation": False,
        "receipt_path": receipt_path.relative_to(ROOT).as_posix() if receipt_path.is_relative_to(ROOT) else str(receipt_path),
        "receipt_present": receipt_present,
        "receipt_valid": receipt_valid,
        "freeze_commit": freeze_commit,
        "fresh_root": fresh_root.relative_to(ROOT).as_posix() if fresh_root.is_relative_to(ROOT) else str(fresh_root),
        "fresh_asset_count": len(assets),
        "fresh_assets_present": bool(assets),
        "fresh_assets": assets,
        "fresh_protocol_valid": protocol_valid,
        "receipt_publication_commit": receipt_publication_commit,
        "fresh_authoring_allowed": allowed,
        "admission_decision": decision,
        "failures": failures,
        "guard_gate": gate,
        "gold_approved": False,
        "stage_release": "BLOCKED_NEXT_FRESH_AND_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "rule": "No v0.10 asset may exist before a canonical v0.9.1 freeze receipt; exposed v0.9/v0.9.1 data never qualifies as v0.10 fresh.",
    }
