from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from scripts.patient_eval.event_mapping import map_candidates, transcript_digest, main
from scripts.patient_eval.import_batch import digest_bytes, scenario_digest
from scripts.patient_eval.readiness_pipeline import fixtures, run_drill


class EventMappingTests(unittest.TestCase):
    def setUp(self):
        self.suite, self.records, self.plan = fixtures()

    def mapped(self):
        return map_candidates(self.records, self.suite, self.plan["suite_sha256"], self.plan)

    def test_distinct_denominators_without_automatic_reviews(self):
        original = deepcopy((self.records, self.suite, self.plan))
        result = self.mapped()
        self.assertEqual(result["summary"]["statuses"], {"ready_for_review": 3,
            "event_not_reached": 1, "response_missing": 1, "event_log_unknown": 1,
            "measurement_invalid": 1})
        self.assertEqual((self.records, self.suite, self.plan), original)
        self.assertTrue(all(r["ordinal_rating"] is None and not r["is_review"] for r in result["candidates"]))

    def test_later_answer_cannot_replace_first_response(self):
        self.records[0]["turns"] += [{"turn_id": "u3", "role": "user", "content": "再次纠正。"},
                                     {"turn_id": "a3", "role": "assistant", "content": "这是后来修复。"}]
        self.plan["session_events"][0]["transcript_sha256"] = transcript_digest(self.records[0])
        row = self.mapped()["candidates"][0]
        self.assertEqual(row["response_turn_id"], "a2")
        self.assertNotIn("a3", row["evidence_turn_ids"])

    def test_stale_transcript_even_same_ids_rejected(self):
        self.records[0]["turns"][3]["content"] = "changed response"
        with self.assertRaisesRegex(ValueError, "stale transcript"):
            self.mapped()

    def test_wrong_content_role_and_kind_rejected(self):
        for change in ({"content_sha256": "0" * 64}, {"turn_id": "a2"},
                       {"event_kind": "unknown"}, {"turn_id": "missing"}):
            with self.subTest(change=change):
                self.setUp()
                self.plan["session_events"][0]["events"][0].update(change)
                with self.assertRaises(ValueError):
                    self.mapped()

    def test_duplicate_or_missing_event_logs_rejected(self):
        for mode in ("duplicate", "missing", "unknown"):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "duplicate":
                    self.plan["session_events"].append(deepcopy(self.plan["session_events"][0]))
                elif mode == "missing":
                    self.plan["session_events"].pop()
                else:
                    self.plan["session_events"][0]["session_id"] = "unknown"
                with self.assertRaises(ValueError):
                    self.mapped()

    def test_duplicate_unknown_events_and_criteria_rejected(self):
        for mode in ("event", "criterion", "unknown-event", "unknown-criterion"):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "event":
                    log = self.plan["session_events"][0]
                    log["events"].append(deepcopy(log["events"][0]))
                elif mode == "criterion":
                    self.plan["rules"].append(deepcopy(self.plan["rules"][0]))
                elif mode == "unknown-event":
                    self.plan["session_events"][0]["events"][0]["event_id"] = "unknown"
                else:
                    self.plan["rules"][0]["criterion_id"] = "unknown"
                with self.assertRaises(ValueError):
                    self.mapped()

    def test_unmapped_criterion_stays_in_denominator(self):
        scenario = self.suite["scenarios"][0]
        extra = deepcopy(scenario["criteria"][0])
        extra["id"] = "unmapped"
        scenario["criteria"].append(extra)
        self.plan["rules"][0]["scenario_sha256"] = scenario_digest(scenario)
        for record in self.records[:5]:
            record["metadata"]["scenario_sha256"] = scenario_digest(scenario)
        result = self.mapped()
        self.assertEqual(result["summary"]["planned_items"], 12)
        self.assertEqual(result["summary"]["statuses"]["unmapped"], 4)
        self.assertEqual(result["summary"]["statuses"]["measurement_invalid"], 2)

    def test_suite_scenario_and_response_policy_binding(self):
        for field, value in (("suite_sha256", "0" * 64), ("scenario_sha256", "0" * 64),
                             ("response_policy", "last_assistant")):
            with self.subTest(field=field):
                self.setUp()
                if field == "suite_sha256":
                    self.plan[field] = value
                    with self.assertRaises(ValueError):
                        map_candidates(self.records, self.suite, "1" * 64, self.plan)
                else:
                    self.plan["rules"][0][field] = value
                    with self.assertRaises(ValueError):
                        self.mapped()

    def test_real_source_and_dynamic_drafts_rejected(self):
        self.suite["scenarios"][0]["source"] = "deidentified_real"
        with self.assertRaisesRegex(ValueError, "synthetic scenarios only"):
            self.mapped()
        self.setUp()
        self.suite["schema_version"] = "dynamic-case-draft/v0.4"
        with self.assertRaises(ValueError):
            self.mapped()

    def test_no_automatic_semantic_matching_or_absence_inference(self):
        log = self.plan["session_events"][0]
        log["events"] = []
        log["complete"] = False
        row = self.mapped()["candidates"][0]
        self.assertEqual(row["candidate_status"], "event_log_unknown")
        self.assertIsNone(row["trigger_turn_id"])
        log["complete"] = "yes"
        with self.assertRaises(ValueError):
            self.mapped()

    def test_mapping_cli_rejects_overwrite_and_invalid_batch_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, value in (("suite", self.suite), ("records", self.records), ("plan", self.plan)):
                (d / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            args = ["--input", str(d / "records"), "--suite", str(d / "suite"),
                    "--plan", str(d / "plan"), "--out", str(d / "out")]
            main(args)
            before = (d / "out").read_bytes()
            with self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code, 2)
            self.assertEqual((d / "out").read_bytes(), before)
            self.plan["session_events"][-1]["transcript_sha256"] = "0" * 64
            (d / "plan").write_text(json.dumps(self.plan))
            args[-1] = str(d / "bad-out")
            with self.assertRaises(SystemExit):
                main(args)
            self.assertFalse((d / "bad-out").exists())

    def test_complete_offline_pipeline_and_existing_output_protected(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "drill"
            with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
                report = run_drill(out)
            self.assertEqual(report["passed"], report["total"])
            self.assertEqual(report["denominators"]["mock_rated_over_valid_planned"], "3/6")
            self.assertEqual(report["independent_reviewers"], 0)
            before = (out / "report.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run_drill(out)
            self.assertEqual((out / "report.json").read_bytes(), before)

    def test_failed_drill_retains_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.patient_eval.readiness_pipeline.mock_review_sessions", side_effect=lambda s, m: deepcopy(s)):
                with self.assertRaisesRegex(ValueError, "evidence preserved"):
                    run_drill(Path(d) / "drill")
            report = json.loads((Path(d) / "drill/report.json").read_bytes())
            self.assertLess(report["passed"], report["total"])


if __name__ == "__main__":
    unittest.main()
