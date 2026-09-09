"""Synthetic structural fixtures only; these are not patient data or clinical gold."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.patient_eval.source_intake import (
    MAX_BYTES, _read_bounded, audit_dialogues, intake, verify_payload,
)


def fixture():
    return [{"dialogue": "synthetic-a", "information": [
        {"turn": 1, "role": "patient", "sentence": "合成用户表达", "message": "", "actions": []},
        {"turn": 2, "role": "patient", "sentence": "合成补充", "message": "", "actions": []},
        {"turn": 3, "role": "doctor", "sentence": "合成回复", "message": "synthetic", "actions": [{"intent": "fixture"}]},
    ]}]


class SourceIntakeTests(unittest.TestCase):
    def test_structure_audit_preserves_sequence_and_never_exports_text(self):
        source = fixture()
        before = copy.deepcopy(source)
        audit, candidates = audit_dialogues(source)
        self.assertEqual(source, before)
        self.assertEqual(audit["counts"]["adjacent_same_role_pairs"], 1)
        self.assertEqual(audit["counts"]["schema_usable_unique_dialogues"], 1)
        self.assertEqual(audit["counts"]["actions_nonempty_turns"], 1)
        self.assertEqual(candidates, ["synthetic-a"])
        serialized = json.dumps(audit, ensure_ascii=False)
        self.assertNotIn("synthetic-a", serialized)
        self.assertNotIn("合成用户表达", serialized)

    def test_normalized_duplicate_selection_is_unique_and_repeatable(self):
        source = fixture()
        source[0]["information"][0]["sentence"] = "Ａ  B"
        duplicate = copy.deepcopy(source[0])
        duplicate["dialogue"] = "synthetic-b"
        duplicate["information"][0]["sentence"] = "A\tB"
        source.append(duplicate)
        audit, candidates = audit_dialogues(source)
        self.assertEqual(audit["counts"]["exact_normalized_duplicate_dialogues"], 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(audit_dialogues(source), audit_dialogues(source))

    def test_anomalies_are_counted_without_patient_content(self):
        source = fixture()
        source[0]["information"].extend([
            {"turn": 3, "role": "nurse", "sentence": "  ", "actions": None},
            {"role": "patient", "sentence": "合成文本", "actions": [42]},
            10,
        ])
        source.extend([copy.deepcopy(source[0]), {"dialogue": True, "information": []}, 3])
        audit, candidates = audit_dialogues(source)
        counts = audit["counts"]
        self.assertEqual(counts["duplicate_dialogue_ids"], 1)
        self.assertEqual(counts["duplicate_turn_ids"], 2)
        self.assertEqual(counts["invalid_roles"], 2)
        self.assertEqual(counts["empty_sentences"], 2)
        self.assertEqual(counts["malformed_turns"], 2)
        self.assertEqual(counts["malformed_dialogues"], 1)
        self.assertEqual(counts["missing_dialogue_ids"], 1)
        self.assertEqual(counts["nondict_action_entries"], 2)
        self.assertEqual(candidates, [])

    def test_pin_rejects_modified_bytes_even_with_same_length(self):
        payload = b"synthetic"
        expected = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                    "git_blob": hashlib.sha1(b"blob 9\0" + payload).hexdigest()}
        verify_payload(payload, expected)
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            verify_payload(b"Synthetic", expected)

    def test_read_is_bounded(self):
        class Oversized:
            def read(self, size):
                self.size = size
                return b"x" * size
        stream = Oversized()
        with self.assertRaisesRegex(ValueError, "32 MiB"):
            _read_bounded(stream)
        self.assertEqual(stream.size, MAX_BYTES + 1)

    def test_reject_invalid_root_and_selection_size(self):
        for source in (None, {}, []):
            with self.assertRaises(ValueError):
                audit_dialogues(source)
        for size in (-1, 51, True):
            with self.assertRaises(ValueError):
                audit_dialogues(fixture(), size)

    def test_intake_keeps_original_bytes_and_candidates_local(self):
        local = Path(__file__).resolve().parents[2] / "medical/patient-eval/local"
        local.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(fixture(), indent=1).encode()
        with tempfile.TemporaryDirectory(dir=local) as tmp:
            out = Path(tmp) / "new"
            with patch("scripts.patient_eval.source_intake._payload", side_effect=[raw, b"synthetic license"]):
                audit = intake(out)
            self.assertEqual((out / "ReMeDi-base.json").read_bytes(), raw)
            self.assertEqual((out / "MIT-license.txt").read_bytes(), b"synthetic license")
            self.assertFalse(audit["clinical_gold"])
            self.assertFalse(audit["dynamic_scenario_ready"])
            self.assertFalse(audit["independent_held_out"])
            self.assertNotIn("synthetic-a", (out / "audit.json").read_text())
            self.assertIn("synthetic-a", (out / "candidate-review-local.json").read_text())
            with self.assertRaisesRegex(ValueError, "new directory"):
                intake(out)

    def test_intake_refuses_public_destination_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.patient_eval.source_intake._payload") as fetch:
                with self.assertRaisesRegex(ValueError, "ignored"):
                    intake(Path(tmp) / "public")
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
