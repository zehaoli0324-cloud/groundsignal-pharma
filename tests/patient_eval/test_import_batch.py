from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from scripts.patient_eval.cli import evaluate_sessions
from scripts.patient_eval.contracts import load_suite
from scripts.patient_eval.import_batch import digest_bytes, scenario_digest, validate_batch, import_file, write_new_json

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "medical/patient-eval/development/scenarios.json"
EXAMPLE = ROOT / "medical/patient-eval/development/manual-transcript.example.json"


class BoundImportTests(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite(SUITE)
        self.sha = digest_bytes(SUITE.read_bytes())
        self.record = json.loads(EXAMPLE.read_text())
        self.record["observations"] = []
        self.scenario = next(s for s in self.suite["scenarios"] if s["scenario_id"] == self.record["scenario_id"])
        self.record["metadata"].update(suite_sha256=self.sha, scenario_sha256=scenario_digest(self.scenario))

    def validate(self, *records):
        return validate_batch(list(records) or [self.record], self.suite, self.sha)

    def test_import_retains_unknown_reviews_and_reuses_scoring(self):
        original = deepcopy(self.record)
        result = self.validate()
        self.assertEqual(self.record, original)
        self.assertEqual(result[0]["observations"], [])
        bundle = evaluate_sessions(self.suite, result)
        self.assertTrue(all(r["outcome"] == "unassessed" for r in bundle["scores"][0]["criterion_results"]))
        self.assertFalse(result[0]["metadata"]["import_binding_is_admission"])

    def test_duplicate_session_rejected_but_declared_repeats_remain_separate(self):
        with self.assertRaisesRegex(ValueError, "duplicate session"):
            self.validate(self.record, self.record)
        repeat = deepcopy(self.record)
        repeat["session_id"] += "-repeat"
        self.assertEqual(len(self.validate(self.record, repeat)), 2)

    def test_version_identity_source_and_protocol_mismatches_rejected(self):
        for field, value in [("suite_sha256", None), ("scenario_sha256", "0" * 64),
                             ("session_protocol_id", "wrong"), ("question_source", "deidentified_real")]:
            record = deepcopy(self.record)
            record["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(record)
        for field in ("family_id", "variant", "scenario_id"):
            record = deepcopy(self.record)
            record[field] = "wrong"
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(record)

    def test_same_id_changed_case_content_cannot_reuse_old_binding(self):
        self.scenario["criteria"][0]["critical"] = not self.scenario["criteria"][0]["critical"]
        with self.assertRaisesRegex(ValueError, "scenario_sha256"):
            self.validate()

    def test_turn_order_missing_answer_and_unknown_criterion_rejected(self):
        changes = [lambda r: r["turns"].pop(),
                   lambda r: r["turns"].reverse(),
                   lambda r: r["turns"][0].update(content="different patient input"),
                   lambda r: r["turns"][1].update(turn_id=r["turns"][0]["turn_id"]),
                   lambda r: r.update(observations=[{"criterion_id": "unknown", "outcome": "unassessed",
                        "source": "deterministic", "reason": "test", "evidence_turn_ids": []}])]
        for change in changes:
            record = deepcopy(self.record)
            change(record)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(record)

    def test_failed_and_measurement_invalid_records_remain_failures(self):
        self.record["turns"].pop()
        self.record["status"] = "target_error"
        self.assertEqual(self.validate()[0]["status"], "target_error")
        self.record["status"] = "measurement_invalid"
        with self.assertRaises(ValueError):
            self.validate()
        self.record.update(invalid_component="collector", invalid_reason="capture interrupted")
        self.assertEqual(self.validate()[0]["status"], "measurement_invalid")

    def test_free_dialogue_allows_followups_but_checks_opening(self):
        self.record["metadata"]["comparison_lane"] = "free_dialogue"
        self.record["turns"][2]["content"] = "a different followup"
        self.validate()
        self.record["turns"][0]["content"] = "wrong opening"
        with self.assertRaises(ValueError):
            self.validate()

    def test_file_import_is_offline_atomic_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source, out = Path(directory) / "in.json", Path(directory) / "out.json"
            source.write_text(json.dumps([self.record]))
            before = source.read_bytes()
            with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
                summary = import_file(source, SUITE, out)
            saved = out.read_bytes()
            self.assertEqual(summary["sessions_without_observations"], 1)
            self.assertEqual(json.loads(saved)[0]["metadata"]["import_source_file_sha256"], digest_bytes(before))
            with self.assertRaises(ValueError):
                import_file(source, SUITE, out)
            with self.assertRaises(FileExistsError):
                write_new_json(out, {"replacement": True})
            self.assertEqual(out.read_bytes(), saved)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(list(Path(directory).iterdir())), 2)

    def test_invalid_batch_writes_nothing_even_after_valid_first_record(self):
        with tempfile.TemporaryDirectory() as directory:
            source, out = Path(directory) / "in.json", Path(directory) / "out.json"
            source.write_text(json.dumps([self.record, self.record]))
            with self.assertRaises(ValueError):
                import_file(source, SUITE, out)
            self.assertFalse(out.exists())

    def test_empty_batch_and_dynamic_drafts_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_batch([], self.suite, self.sha)
        with self.assertRaises(ValueError):
            validate_batch([self.record], {"schema_version": "dynamic-case-draft/v0.4"}, self.sha)


if __name__ == "__main__":
    unittest.main()
