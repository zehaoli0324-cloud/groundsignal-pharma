#!/usr/bin/env python3
"""A1 batch 2: offline synthetic helper probes; no training candidates exported.

Exit 2 records observed product invariant failures. Output must be a new directory.
Freeze verdict composition is isolated with labelled stub results, never real
receipts or approval. Authentication constants and production files are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_training_data as exporter
import export_training_data_v091 as candidate_exporter
import s5_v091_freeze_control as freeze


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_probes():
    rows = []

    def record(pid, finding, expected, actual, passed):
        rows.append({"probe_id": pid, "finding_id": finding, "expected": expected,
                     "actual": actual, "invariant_pass": bool(passed)})

    run = {"run_id": "synthetic-run-A", "case_id": "synthetic-case-A", "model_id": "synthetic-model-A", "response": "synthetic marker A"}
    score = {k: run[k] for k in ("run_id", "case_id", "model_id")}
    error = None; index = None
    try:
        index = exporter.run_index([run, {**run, "response": "synthetic marker overwritten"}])
    except ValueError as exc:
        error = str(exc)
    record("duplicate_run_id", "A1-008", "Reject duplicate run IDs before indexing",
           {"error": error, "selected": index[0].get(run["run_id"]) if index else None}, error is not None)

    index = exporter.run_index([run])
    for pid, changes in [("missing_explicit_run", {"run_id": "synthetic-missing-run"}),
                         ("wrong_case_same_run", {"case_id": "synthetic-case-B"}),
                         ("wrong_model_same_run", {"model_id": "synthetic-model-B"})]:
        selected = None; error = None
        try:
            selected = exporter.find_run({**score, **changes}, *index)
        except (ValueError, KeyError) as exc:
            error = str(exc)
        record(pid, "A1-008", "Explicit identity mismatch must not select another response",
               {"requested": {**score, **changes}, "selected": selected, "error": error}, selected is None)
    selected = exporter.find_run(score, *index)
    record("correct_run_binding", None, "Matching identity selects original response", {"selected": selected}, selected == run)

    with tempfile.TemporaryDirectory(prefix="groundsignal-a1-export-synthetic-") as temp:
        root = Path(temp)
        existing = root / "existing-marker.jsonl"
        old_bytes = b'{"audit_marker":"old generic record"}\n'
        existing.write_bytes(old_bytes)
        error = None
        try:
            exporter.write_jsonl(existing, [])
        except (FileExistsError, ValueError) as exc:
            error = str(exc)
        record("existing_output_overwrite", "A1-009", "Existing output is preserved without explicit overwrite authorization",
               {"error": error, "old_size": len(old_bytes), "new_size": existing.stat().st_size, "old_bytes_preserved": existing.read_bytes() == old_bytes}, existing.read_bytes() == old_bytes)

        failed = root / "serialization-marker.jsonl"
        failed.write_bytes(old_bytes)
        error = None
        try:
            exporter.write_jsonl(failed, [{"audit_marker": "new generic record"}, {"audit_marker": object()}])
        except TypeError as exc:
            error = type(exc).__name__
        record("serialization_failure_preserves_output", "A1-009", "Serialization failure cannot destroy the previous file or publish a partial replacement",
               {"error": error, "content_after_failure": failed.read_text(), "old_bytes_preserved": failed.read_bytes() == old_bytes}, failed.read_bytes() == old_bytes)
        new = root / "new-marker.jsonl"
        exporter.write_jsonl(new, [{"audit_marker": "roundtrip"}])
        record("new_output_roundtrip", None, "Generic marker roundtrips in a new output file", {"content": json.loads(new.read_text())}, json.loads(new.read_text()) == {"audit_marker": "roundtrip"})

        skipped = exporter.export_row({"training_candidate": {"review_status": "draft", "type": "sft"}}, {"case_id": "synthetic-unreviewed"}, None)
        record("unapproved_candidate_skipped", None, "Draft candidate returns no training row", {"returned": skipped}, skipped is None)

        authority = root / "synthetic-authority.json"
        dump(authority, {"audit_marker": "synthetic pinned bytes"})
        blob = exporter.git_blob_sha1(authority)
        checked, digest = exporter._authenticated_json(authority, blob, "synthetic audit snapshot")
        record("exact_snapshot_authenticated", None, "Explicit expected bytes are hashed and parsed consistently",
               {"parsed": checked, "sha256": digest}, checked == {"audit_marker": "synthetic pinned bytes"} and digest == hashlib.sha256(authority.read_bytes()).hexdigest())
        dump(authority, {"audit_marker": "synthetic altered bytes"})
        rejected = False
        try:
            exporter._authenticated_json(authority, blob, "synthetic audit snapshot")
        except PermissionError:
            rejected = True
        record("modified_snapshot_rejected", None, "Different bytes fail the original expected digest", {"rejected": rejected}, rejected)
        rejected = False
        try:
            exporter._resolve_repo_path(str(root / "outside-authority.json"))
        except PermissionError:
            rejected = True
        record("off_repository_authority_rejected", None, "Off-repository authority path is rejected", {"rejected": rejected}, rejected)

        # A stub marker is deliberately not a valid S5 receipt. Only result
        # composition is under test; no Git state or real authority is changed.
        marker = root / "not-a-real-receipt.json"
        dump(marker, {"audit_marker": "synthetic composition stub"})
        for pid, attestation_gate, control_gate, use_marker in [
            ("failed_attestation_disallows", "FAIL", "PASS", True),
            ("failed_control_plane_disallows", "PASS", "FAIL", True),
            ("ready_composition_authoring_only", "PASS", "PASS", True),
            ("missing_receipt_blocks", "PASS", "PASS", False),
        ]:
            with patch.object(freeze, "verify_current_attestation", return_value=({}, {"verification_gate": attestation_gate}, freeze.EXPECTED_ATTESTATION_BLOB)), \
                 patch.object(freeze, "verify_current_control_plane", return_value=({}, {"verification_gate": control_gate}, "synthetic-control-blob")), \
                 patch.object(freeze, "validate_receipt", return_value=(True, [])):
                result = freeze.evaluate_admission(marker if use_marker else root / "missing.json", root / "absent-fresh-assets")
            actual = {k: result[k] for k in ("fresh_authoring_allowed", "admission_decision", "guard_gate", "failures", "gold_approved", "s6_automatic_trust")}
            actual["mock_scope"] = "subcheck statuses and receipt acceptance only; not end-to-end authority validation"
            failing_precheck = attestation_gate == "FAIL" or control_gate == "FAIL"
            if failing_precheck:
                record(pid, "A1-010", "Any failed current check makes authoring_allowed false", actual, result["fresh_authoring_allowed"] is False)
            elif use_marker:
                record(pid, None, "Ready composition permits authoring but never clinical gold or S6", actual,
                       result["fresh_authoring_allowed"] is True and result["gold_approved"] is False and result["s6_automatic_trust"] == "BLOCKED")
            else:
                record(pid, None, "Missing receipt keeps authoring blocked", actual, result["fresh_authoring_allowed"] is False)

    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("audit prohibits network")), patch.object(socket, "create_connection", side_effect=RuntimeError("audit prohibits network")):
        rows = run_probes()
    failures = sum(not r["invariant_pass"] for r in rows)
    result = {"scope": "A1 S1/S5/S9 interface helpers; synthetic only", "checks": len(rows), "invariants_passed": len(rows)-failures,
              "invariants_failed": failures, "project_audit_complete": False, "project_tests_complete": False,
              "training_candidate_rows_created": 0, "real_case_runs": 0, "model_calls": 0, "real_receipts_created": 0,
              "inheritance": {name: {key: str(Path(getattr(module, key).__code__.co_filename).relative_to(ROOT))
                             for key in ("run_index", "find_run", "write_jsonl", "export_row")}
                              for name, module in [("default_v081", exporter), ("candidate_v091", candidate_exporter)]}, "rows": rows}
    dump(out / "observations.json", result)
    paths = ["scripts/audit_admission_export_contracts.py", "scripts/export_training_data.py", "scripts/export_training_data_v091.py",
             "scripts/export_training_data_v061.py", "scripts/s5_lineage_detector_v091.py", "scripts/s5_lineage_detector_v081.py",
             "scripts/s5_lineage_detector_v073.py", "scripts/s5_v091_freeze_control.py"]
    dump(out / "run-manifest.json", {"argv": [sys.executable, *sys.argv], "cwd": str(Path.cwd()), "python": platform.python_version(),
         "input_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         "input_git_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
         "file_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
         "probe_script_uncommitted_at_first_execution": True, "input_scope": "new authored synthetic markers only",
         "network": "blocked in process", "freeze_subchecks": "explicit stubs; real receipt validation not executed",
         "auth_scope": "helper digest/path checks only; production policy registry not replaced or used for export",
         "output": str(out), "expected_exit_code_at_audit_baseline": 2, "actual_exit_code": 2 if failures else 0,
         "result": "FAIL" if failures else "PASS", "training_candidate_rows_created": 0})
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "inheritance")}, ensure_ascii=False, indent=2))
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
