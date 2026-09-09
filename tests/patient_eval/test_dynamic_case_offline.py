"""Synthetic tests for N5 readiness auditing and fixture-only execution."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.patient_eval.dynamic_case_drafts import build_dynamic_case_drafts
from scripts.patient_eval.dynamic_case_offline import (
    SyntheticContractExecutor,
    _audit_case,
    _scoring_status,
    _synthetic_case,
    build_offline_readiness,
    run_synthetic_contract_probe,
)
from tests.patient_eval.test_dynamic_case_drafts import (
    PRIVATE_SENTINEL,
    REVIEW_SHA,
    SOURCE_SHA,
    draft_fixture,
)


def offline_fixture():
    original, review, blockers, selection = draft_fixture(count=4, selected=3)
    private, public = build_dynamic_case_drafts(
        original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
    return original, review, blockers, selection, private, public


class DynamicCaseOfflineTests(unittest.TestCase):
    def test_synthetic_probe_covers_all_expected_fail_closed_behaviors(self):
        result = run_synthetic_contract_probe()
        self.assertEqual(result["passed_count"], result["total_count"])
        self.assertEqual(result["total_count"], 8)
        self.assertEqual({row["result"] for row in result["checks"]}, {"PASS"})
        self.assertEqual(result["model_or_platform_calls"], 0)

    def test_opening_does_not_disclose_future_or_never_facts(self):
        executor = SyntheticContractExecutor(_synthetic_case())
        opened = executor.open()
        self.assertEqual(opened["disclosed"], ["F-INITIAL"])
        self.assertNotIn("F-QUESTION", executor.snapshot()["disclosed_fact_ids"])
        self.assertNotIn("F-SCHEDULED", executor.snapshot()["disclosed_fact_ids"])
        self.assertNotIn("F-NEVER", executor.snapshot()["disclosed_fact_ids"])

    def test_duplicate_disclosure_and_post_stop_activity_are_rejected(self):
        executor = SyntheticContractExecutor(_synthetic_case())
        executor.open()
        executor.confirm("E-QUESTION")
        with self.assertRaisesRegex(ValueError, "already fired"):
            executor.confirm("E-QUESTION")
        executor.stop()
        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            executor.confirm("E-SCHEDULED")

    def test_cross_case_state_isolation_and_unreached_events_are_preserved(self):
        first = SyntheticContractExecutor(_synthetic_case("SYNTHETIC-A"))
        second = SyntheticContractExecutor(_synthetic_case("SYNTHETIC-B"))
        first.open()
        second.open()
        first.confirm("E-QUESTION")
        self.assertEqual(second.snapshot()["fired_event_ids"], [])
        stopped = second.stop()
        self.assertEqual(stopped["unreached_event_ids"], ["E-QUESTION", "E-SCHEDULED"])

    def test_source_derived_case_is_categorically_rejected_by_executor(self):
        *_, private, _ = offline_fixture()
        with self.assertRaisesRegex(ValueError, "synthetic fixtures only"):
            SyntheticContractExecutor(private["cases"][0])

    def test_real_readiness_is_text_free_and_keeps_all_outcomes_unassessed(self):
        original, review, blockers, selection, private, n4_public = offline_fixture()
        result = build_offline_readiness(
            original, review, blockers, selection, private, n4_public,
            SOURCE_SHA, REVIEW_SHA)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(PRIVATE_SENTINEL, serialized)
        self.assertNotIn("发热", serialized)
        self.assertEqual(result["summary"]["source_derived_execution_attempt_count"], 0)
        self.assertEqual(result["summary"]["offline_session_count"], 0)
        self.assertEqual(result["summary"]["blind_review_package_count"], 0)
        self.assertEqual(result["summary"]["quality_assessed_case_count"], 0)
        self.assertEqual(result["summary"]["critical_safety_assessed_count"], 0)
        self.assertTrue(all(row["scoring"]["safety_status"] == "UNASSESSED"
                            for row in result["cases"]))

    def test_static_audit_rejects_future_leak_and_duplicate_event(self):
        *_, private, _ = offline_fixture()
        leaked = deepcopy(private["cases"][0])
        leaked["opening"]["slot_ids"].append(leaked["disclosure_events"][0]["slot_id"])
        with self.assertRaisesRegex(ValueError, "future fact"):
            _audit_case(leaked)
        duplicated = deepcopy(private["cases"][0])
        duplicated["disclosure_events"].append(deepcopy(duplicated["disclosure_events"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate disclosure"):
            _audit_case(duplicated)

    def test_partial_scoring_is_not_upgraded_to_pass(self):
        case = _synthetic_case()
        status = _scoring_status(case)
        self.assertEqual(status["mapped_opportunity_count"], 0)
        self.assertEqual(status["unmapped_opportunity_count"], 1)
        self.assertEqual(status["runtime_opportunity_not_reached_count"], 0)
        self.assertEqual(status["runtime_opportunity_not_evaluated_count"], 1)
        self.assertEqual(status["quality_status"], "UNASSESSED")
        self.assertEqual(status["task_completion_status"], "UNASSESSED")
        self.assertEqual(status["safety_status"], "UNASSESSED")
        self.assertEqual(status["measurement_status"], "NOT_RUN")

    def test_tampered_private_or_public_n4_artifact_fails_exact_recomputation(self):
        original, review, blockers, selection, private, n4_public = offline_fixture()
        changed_private = deepcopy(private)
        changed_private["cases"][0]["clinical_runnable"] = "READY"
        with self.assertRaisesRegex(ValueError, "private draft bundle"):
            build_offline_readiness(
                original, review, blockers, selection, changed_private, n4_public,
                SOURCE_SHA, REVIEW_SHA)
        changed_public = deepcopy(n4_public)
        changed_public["summary"]["clinical_runnable_count"] = 1
        with self.assertRaisesRegex(ValueError, "N4 public audit"):
            build_offline_readiness(
                original, review, blockers, selection, private, changed_public,
                SOURCE_SHA, REVIEW_SHA)

    def test_cli_rejects_wrong_source_hash_without_writing_output(self):
        original, review, blockers, selection, private, n4_public = offline_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "original.json": original,
                "review.json": review,
                "blockers.json": blockers,
                "selection.json": selection,
                "private.json": private,
                "n4.json": n4_public,
            }
            for name, value in payloads.items():
                (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            source = root / "source.json"
            source.write_text("synthetic", encoding="utf-8")
            output = root / "public.json"
            run = subprocess.run([
                sys.executable, "-m", "scripts.patient_eval.dynamic_case_offline",
                "--original", str(root / "original.json"),
                "--review", str(root / "review.json"),
                "--source-review", str(source),
                "--expected-source-sha256", "0" * 64,
                "--blockers", str(root / "blockers.json"),
                "--selection", str(root / "selection.json"),
                "--private-drafts", str(root / "private.json"),
                "--n4-audit", str(root / "n4.json"),
                "--out", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(output.exists())
            self.assertNotIn(PRIVATE_SENTINEL, run.stdout)


if __name__ == "__main__":
    unittest.main()
