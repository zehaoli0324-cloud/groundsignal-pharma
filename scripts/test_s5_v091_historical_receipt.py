#!/usr/bin/env python3
"""Regression tests for receipt verification after canonical main advances."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_s5_v091_historical_receipt as verifier


class HistoricalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.original = (verifier.ROOT / verifier.frozen.RECEIPT_REL).read_bytes()
        self.receipt = json.loads(self.original)
        attestation = json.loads(verifier.frozen.ATTESTATION.read_text())
        control = json.loads(verifier.frozen.CONTROL_PLANE.read_text())
        self.pins = {
            str(verifier.frozen.ATTESTATION.relative_to(verifier.ROOT)): verifier.frozen.EXPECTED_ATTESTATION_BLOB,
            str(verifier.frozen.CONTROL_PLANE.relative_to(verifier.ROOT)): self.receipt["control_plane_attestation_git_blob_sha1"],
            **{row["path"]: row["git_blob_sha1"] for row in attestation["pinned_artifacts"]},
            **{row["path"]: row["git_blob_sha1"] for row in control["pinned_control_plane_artifacts"]},
        }
        self.overrides = {}

    def fake_git(self, *args):
        if args in self.overrides:
            code, output = self.overrides[args]
            return subprocess.CompletedProcess(args, code, output, "")
        freeze, publication = verifier.FREEZE_COMMIT, verifier.PUBLICATION_COMMIT
        code, output = 1, ""
        if args == ("rev-parse", "--is-shallow-repository"):
            code, output = 0, "false\n"
        elif args == ("rev-parse", "origin/main"):
            code, output = 0, "d" * 40 + "\n"  # Main has advanced since the freeze.
        elif args in [("cat-file", "-e", f"{c}^{{commit}}") for c in (freeze, publication)]:
            code = 0
        elif args[:2] == ("merge-base", "--is-ancestor"):
            code = 0 if args[2] in (freeze, publication) and args[3] in ("HEAD", "origin/main") else 1
        elif args == ("rev-list", "--parents", "-n", "1", publication):
            code, output = 0, f"{publication} {freeze}\n"
        elif args == ("rev-parse", f"{publication}:{verifier.frozen.RECEIPT_REL}"):
            code, output = 0, verifier.RECEIPT_BLOB + "\n"
        elif args == ("show", "-s", "--format=%T", freeze):
            code, output = 0, self.receipt["freeze_tree_sha"] + "\n"
        elif args[0] == "rev-parse" and args[1].startswith(freeze + ":"):
            pin = self.pins.get(args[1].split(":", 1)[1])
            code, output = (0, pin + "\n") if pin else (1, "")
        return subprocess.CompletedProcess(args, code, output, "")

    def verify(self, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_bytes(self.original if data is None else data)
            with patch.object(verifier, "git", self.fake_git), patch.object(verifier.frozen, "git", self.fake_git):
                return verifier.verify(path)

    def assert_rejected(self, failure, data=None):
        result = self.verify(data)
        self.assertEqual(result["verification_gate"], "FAIL")
        self.assertIn(failure, result["failures"])

    def test_main_advanced_history_passes_materialization_still_rejects(self):
        self.assertEqual(self.verify()["verification_gate"], "PASS")
        with patch.object(verifier.frozen, "git", self.fake_git):
            receipt, failures = verifier.frozen.build_receipt(verifier.FREEZE_COMMIT, self.receipt["approval_reference"])
        self.assertIsNone(receipt)
        self.assertIn("FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP", failures)

    def test_shallow_history_rejected(self):
        self.overrides[("rev-parse", "--is-shallow-repository")] = (0, "true\n")
        self.assert_rejected("COMPLETE_GIT_HISTORY_REQUIRED")

    def test_missing_publication_object_rejected(self):
        self.overrides[("cat-file", "-e", f"{verifier.PUBLICATION_COMMIT}^{{commit}}")] = (1, "")
        self.assert_rejected(f"HISTORICAL_COMMIT_UNAVAILABLE:{verifier.PUBLICATION_COMMIT}")

    def test_unrelated_publication_rejected(self):
        for ref in ("origin/main", "HEAD"):
            with self.subTest(ref=ref):
                self.overrides = {("merge-base", "--is-ancestor", verifier.PUBLICATION_COMMIT, ref): (1, "")}
                self.assert_rejected(f"RECEIPT_PUBLICATION_NOT_ANCESTOR:{ref}")

    def test_wrong_publication_parent_rejected(self):
        self.overrides[("rev-list", "--parents", "-n", "1", verifier.PUBLICATION_COMMIT)] = (0, verifier.PUBLICATION_COMMIT + " " + "a" * 40)
        self.assert_rejected("RECEIPT_PUBLICATION_PARENT_MISMATCH")

    def test_published_receipt_changed_rejected(self):
        self.overrides[("rev-parse", f"{verifier.PUBLICATION_COMMIT}:{verifier.frozen.RECEIPT_REL}")] = (0, "a" * 40)
        self.assert_rejected("PUBLISHED_RECEIPT_BLOB_MISMATCH")

    def test_current_receipt_byte_drift_rejected(self):
        self.assert_rejected("CURRENT_RECEIPT_BLOB_MISMATCH", self.original + b"\n")

    def test_gold_escalation_rejected(self):
        altered = dict(self.receipt, gold_approved=True)
        self.assert_rejected("CURRENT_RECEIPT_BLOB_MISMATCH", json.dumps(altered).encode())

    def test_malformed_receipt_rejected(self):
        self.assert_rejected("RECEIPT_UNREADABLE", b"[]")

    def test_frozen_tree_drift_rejected(self):
        self.overrides[("show", "-s", "--format=%T", verifier.FREEZE_COMMIT)] = (0, "a" * 40)
        self.assert_rejected("FREEZE_TREE_MISMATCH")

    def test_frozen_implementation_pin_drift_rejected(self):
        rel = "scripts/s5_lineage_detector_v091.py"
        self.overrides[("rev-parse", f"{verifier.FREEZE_COMMIT}:{rel}")] = (0, "a" * 40)
        self.assert_rejected(f"FREEZE_ARTIFACT_MISMATCH:{rel}")

    def test_frozen_control_pin_drift_rejected(self):
        rel = "scripts/s5_v091_freeze_control.py"
        self.overrides[("rev-parse", f"{verifier.FREEZE_COMMIT}:{rel}")] = (0, "a" * 40)
        self.assert_rejected(f"FREEZE_CONTROL_PLANE_ARTIFACT_MISMATCH:{rel}")

    def test_current_control_drift_rejected(self):
        with patch.object(verifier.frozen, "verify_current_control_plane", return_value=({}, {"verification_gate": "FAIL"}, "")):
            self.assert_rejected("CURRENT_CONTROL_PLANE_NOT_READY")

    def test_fresh_assets_at_publication_rejected(self):
        self.overrides[("cat-file", "-e", f"{verifier.PUBLICATION_COMMIT}:{verifier.frozen.NEXT_FRESH_ROOT_REL}")] = (0, "")
        self.assert_rejected("FRESH_ASSETS_PREEXISTED_AT_RECEIPT_PUBLICATION")


if __name__ == "__main__":
    unittest.main()
