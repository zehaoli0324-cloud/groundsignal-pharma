"""Synthetic checks for fail-closed dynamic case authoring drafts."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.patient_eval.candidate_blockers import build_public_blocker_queue
from scripts.patient_eval.candidate_review import LOCAL_ROOT
from scripts.patient_eval.candidate_selection import build_development_selection
from scripts.patient_eval.dynamic_case_drafts import build_dynamic_case_drafts
from tests.patient_eval.test_candidate_selection import selection_fixture


SOURCE_SHA = "5" * 64
REVIEW_SHA = "6" * 64
PRIVATE_SENTINEL = "PRIVATE_" + "DYNAMIC_CASE_SENTINEL"


def draft_fixture(count=4, selected=3):
    original, review, _ = selection_fixture(count)
    review["reviewer_id"] += PRIVATE_SENTINEL
    for item in review["items"]:
        rubric = item["review"]["rubrics"][0]
        rubric.update(
            decision="drafted",
            applicability="applicable",
            description="private synthetic scoring " + PRIVATE_SENTINEL,
            anchors={"0": "miss", "1": "partial", "2": "complete"},
            opportunity={"trigger": "synthetic cue", "deadline": "next response"},
            reason="private rubric review " + PRIVATE_SENTINEL,
        )
    blockers = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
    selection = build_development_selection(
        original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=selected)
    return original, review, blockers, selection


class DynamicCaseDraftTests(unittest.TestCase):
    def test_public_state_machine_contract_matches_generated_drafts(self):
        contract_path = Path("medical/patient-eval/schemas/dynamic-case-state-machine-v0.4.json")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        original, review, blockers, selection = draft_fixture()
        private, public = build_dynamic_case_drafts(
            original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
        self.assertEqual(public["fsm_contract_version"], contract["schema_version"])
        self.assertEqual(contract["states"], ["NOT_OPENED", "ACTIVE", "CLOSED"])
        self.assertFalse(contract["automatic_natural_language_matching"])
        self.assertTrue(all(
            case["finite_state_machine"]["contract_version"] == contract["schema_version"]
            for case in private["cases"]))
        self.assertEqual(contract["admission"], public["admission"])

    def test_builds_one_operator_confirmed_state_machine_per_frozen_case(self):
        original, review, blockers, selection = draft_fixture()
        private, public = build_dynamic_case_drafts(
            original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
        self.assertEqual(len(private["cases"]), 3)
        self.assertEqual(public["summary"]["private_case_draft_count"], 3)
        for case in private["cases"]:
            self.assertEqual(case["clinical_runnable"], "BLOCKED")
            self.assertFalse(case["finite_state_machine"]["automatic_natural_language_matching"])
            self.assertTrue(all(
                event["trigger"]["mode"] == "OPERATOR_CONFIRMATION_REQUIRED"
                for event in case["disclosure_events"]))
            self.assertEqual(case["finite_state_machine"]["transitions"][-1]["to"], "CLOSED")

    def test_future_and_never_facts_cannot_enter_opening(self):
        original, review, blockers, selection = draft_fixture()
        private, _ = build_dynamic_case_drafts(
            original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
        for case in private["cases"]:
            facts = {row["fact_id"]: row for row in case["facts"]}
            opening = set(case["opening"]["slot_ids"])
            self.assertTrue(opening)
            self.assertTrue(all(facts[row]["disclosure_policy"] == "initial" for row in opening))
            event_slots = {row["slot_id"] for row in case["disclosure_events"]}
            self.assertFalse(opening & event_slots)
            self.assertFalse(opening & set(case["permanently_hidden_fact_ids"]))

    def test_scoring_text_remains_private_and_structured_mapping_is_unknown(self):
        original, review, blockers, selection = draft_fixture()
        private, public = build_dynamic_case_drafts(
            original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
        private_text = json.dumps(private, ensure_ascii=False)
        public_text = json.dumps(public, ensure_ascii=False)
        self.assertIn(PRIVATE_SENTINEL, private_text)
        self.assertIn("发热", private_text)
        self.assertNotIn(PRIVATE_SENTINEL, public_text)
        self.assertNotIn("发热", public_text)
        self.assertEqual(public["summary"]["structured_scoring_opportunity_count"], 0)
        self.assertFalse(public["privacy"]["contains_patient_text"])

    def test_all_admission_flags_remain_fail_closed(self):
        original, review, blockers, selection = draft_fixture()
        private, public = build_dynamic_case_drafts(
            original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)
        for artifact in (private, public):
            self.assertFalse(artifact["admission"]["gold_approved"])
            self.assertFalse(artifact["admission"]["clinical_gold"])
            self.assertFalse(artifact["admission"]["dynamic_scenario_ready"])
            self.assertEqual(artifact["admission"]["s6_automatic_trust"], "BLOCKED")

    def test_tampered_selection_or_blocker_queue_is_rejected(self):
        original, review, blockers, selection = draft_fixture()
        changed_selection = deepcopy(selection)
        changed_selection["selected_candidates"].reverse()
        with self.assertRaisesRegex(ValueError, "selection does not match"):
            build_dynamic_case_drafts(
                original, review, blockers, changed_selection, SOURCE_SHA, REVIEW_SHA)
        changed_blockers = deepcopy(blockers)
        changed_blockers["candidates"][0]["states"]["clinical_runnable"] = "READY"
        with self.assertRaisesRegex(ValueError, "blocker queue does not match"):
            build_dynamic_case_drafts(
                original, review, changed_blockers, selection, SOURCE_SHA, REVIEW_SHA)

    def test_cli_rejects_private_output_outside_ignored_local_root(self):
        original, review, blockers, selection = draft_fixture(count=2, selected=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "original.json": original,
                "review.json": review,
                "blockers.json": blockers,
                "selection.json": selection,
            }
            for name, value in payloads.items():
                (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            (root / "source.json").write_text("source", encoding="utf-8")
            run = subprocess.run([
                sys.executable, "-m", "scripts.patient_eval.dynamic_case_drafts",
                "--original", str(root / "original.json"),
                "--review", str(root / "review.json"),
                "--source-review", str(root / "source.json"),
                "--expected-source-sha256", "0" * 64,
                "--blockers", str(root / "blockers.json"),
                "--selection", str(root / "selection.json"),
                "--private-out", str(root / "private.json"),
                "--public-out", str(root / "public.json"),
            ], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse((root / "private.json").exists())
            self.assertFalse((root / "public.json").exists())
            self.assertNotIn(PRIVATE_SENTINEL, run.stdout)

    def test_cli_writes_private_bundle_only_under_ignored_root(self):
        original, review, blockers, selection = draft_fixture(count=2, selected=1)
        LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as public_dir, tempfile.TemporaryDirectory(dir=LOCAL_ROOT) as local_dir:
            public_root = Path(public_dir)
            local_root = Path(local_dir)
            payloads = {
                "original.json": original,
                "review.json": review,
                "blockers.json": blockers,
                "selection.json": selection,
            }
            for name, value in payloads.items():
                (public_root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            source = public_root / "source.json"
            source.write_text("source", encoding="utf-8")
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            review_sha = hashlib.sha256((public_root / "review.json").read_bytes()).hexdigest()
            # Rebuild the hash-bound public inputs for this CLI invocation.
            blockers = build_public_blocker_queue(original, review, source_sha, review_sha)
            selection = build_development_selection(
                original, review, blockers, source_sha, review_sha, requested_count=1)
            (public_root / "blockers.json").write_text(json.dumps(blockers), encoding="utf-8")
            (public_root / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
            private_out = local_root / "private.json"
            public_out = public_root / "public.json"
            run = subprocess.run([
                sys.executable, "-m", "scripts.patient_eval.dynamic_case_drafts",
                "--original", str(public_root / "original.json"),
                "--review", str(public_root / "review.json"),
                "--source-review", str(source),
                "--expected-source-sha256", source_sha,
                "--blockers", str(public_root / "blockers.json"),
                "--selection", str(public_root / "selection.json"),
                "--private-out", str(private_out),
                "--public-out", str(public_out),
            ], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(private_out.exists())
            self.assertTrue(public_out.exists())
            self.assertIn(PRIVATE_SENTINEL, private_out.read_text(encoding="utf-8"))
            self.assertNotIn(PRIVATE_SENTINEL, public_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
