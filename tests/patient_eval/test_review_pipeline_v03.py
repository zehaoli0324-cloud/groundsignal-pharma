"""Synthetic software checks: these labels are not medical assessments."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.agreement import rater_agreement
from scripts.patient_eval.patient_intent import DEFAULT_CLASSIFIER_VERSION, LEGACY_CLASSIFIER_VERSION
from scripts.patient_eval.pilot import (advance_collection, apply_review, compare_intervention, load_pilot_suite,
                                       make_review_packet, new_collection, review_rating_rows, score_pilot)
from scripts.patient_eval.pilot_cli import ProtocolFixtureClient
from scripts.patient_eval.reporting import render_report
from scripts.patient_eval.review_contract import REVIEW_VERSION
from scripts.patient_eval.study import run_dialogue


class ReviewPipelineV03Tests(unittest.TestCase):
    def setUp(self):
        self.suite = load_pilot_suite()
        self.scenario = self.suite["scenarios"][0]
        self.session = run_dialogue(self.scenario, ProtocolFixtureClient(), "baseline")

    def packet(self, directory, sessions=None):
        make_review_packet(self.suite, sessions or [self.session], directory, review_version=REVIEW_VERSION)
        return (json.loads((directory / "reviewer-packet.json").read_text()),
                json.loads((directory / "operator-key.json").read_text()))

    def rate(self, item, rating=1, outcome="unassessed", serious=None):
        item.update(rating=rating, outcome=outcome, serious_error=serious,
                    quality_status="assessed", reviewer_id="synthetic-A", reason="Synthetic pipeline label only",
                    evidence_turn_ids=["u1", "a1"], opportunity={"status": "occurred", "trigger_turn_id": "u1",
                    "response_turn_id": "a1", "deadline_reached": True, "reason": "Synthetic observed answer",
                    "noncompletion_reason": None})

    def test_partial_review_survives_import_and_keeps_missing_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review")
            self.rate(packet["items"][0])
            sessions = apply_review(self.suite, [self.session], packet, key)
            self.assertEqual(len(sessions[0]["observations"]), 1)
            bundle = score_pilot(self.suite, sessions)
            summary = bundle["aggregate"]["independent_review"]
            self.assertEqual(summary["quality"]["assessed"], 1)
            self.assertEqual(summary["quality"]["eligible"], len(self.scenario["criteria"]))
            self.assertEqual(summary["safety"]["assessed"], 0)
            self.assertEqual(summary["quality"]["mean_rating"], 1)
            self.assertIn("质量、安全与评分机会（v0.3）", render_report(bundle))
            self.assertIsNone(bundle["scores"][0]["critical_failure"])
            # Direct imports with a versioned observation must not shrink the
            # denominator merely because the session-level marker was omitted.
            sessions[0]["metadata"].pop("review_version")
            direct = score_pilot(self.suite, sessions)["aggregate"]["independent_review"]
            self.assertEqual(direct["quality"]["eligible"], len(self.scenario["criteria"]))
            self.assertEqual(direct["quality"]["assessed"], 1)

    def test_ordinary_critical_quality_failure_does_not_invent_serious_error(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review")
            item = next(i for i in packet["items"] if i["criterion"]["critical"])
            self.rate(item, outcome="fail", serious=False)
            result = score_pilot(self.suite, apply_review(self.suite, [self.session], packet, key))
            self.assertNotEqual(result["scores"][0]["critical_failure"], True)
            self.assertEqual(result["aggregate"]["independent_review"]["safety"]["serious_errors"], 0)

    def test_blank_packet_is_explicitly_unreviewed_and_exports_missing_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review")
            sessions = apply_review(self.suite, [self.session], packet, key)
            self.assertEqual(sessions[0]["observations"], [])
            summary = score_pilot(self.suite, sessions)["aggregate"]["independent_review"]
            self.assertIsNone(summary["quality"]["mean_rating"])
            self.assertIsNone(summary["task_completion"]["completion_rate"])
            self.assertEqual(summary["task_completion"]["completion_rate_lower_bound"], 0)
            self.assertEqual(summary["v03_criteria"], len(self.scenario["criteria"]))
            rows = review_rating_rows(packet, "A") + review_rating_rows(packet, "B")
            agreement = rater_agreement(rows, "A", "B")
            self.assertEqual(agreement["paired_rated_items"], 0)
            self.assertEqual(len(agreement["incomplete_items"]), len(self.scenario["criteria"]))
            self.assertIsNone(agreement["linear_weighted_cohen_kappa"])

    def test_partial_review_requires_provenance_and_original_text(self):
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review")
            self.rate(packet["items"][0])
            packet["items"][0]["reviewer_id"] = ""
            with self.assertRaises(ValueError):
                apply_review(self.suite, [self.session], packet, key)
            with self.assertRaises(ValueError):
                review_rating_rows(packet, "synthetic-A")
            packet["items"][0]["reviewer_id"] = "synthetic-A"
            packet["items"][0]["turns"][1]["content"] += " edited"
            with self.assertRaises(ValueError):
                apply_review(self.suite, [self.session], packet, key)

    def test_quality_comparison_preserves_units_and_rejects_missing_or_version_drift(self):
        sessions = [self.session, run_dialogue(self.scenario, ProtocolFixtureClient(), "state_augmented")]
        criterion = self.scenario["criteria"][0]["id"]
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review", sessions)
            for item in packet["items"]:
                if item["criterion"]["id"] == criterion:
                    arm = key["mapping"][item["item_id"].split(":")[0]]["session_id"].split(":")[1]
                    self.rate(item, rating=0 if arm == "baseline" else 2)
            reviewed = apply_review(self.suite, sessions, packet, key)
            comparison = compare_intervention(self.suite, reviewed, criterion, metric="quality")
            self.assertEqual(comparison["mean_delta_rating_points"], 2)
            self.assertEqual(comparison["mean_delta"], 1)
            self.assertIsNone(comparison["confidence_interval_95"])
            bad = deepcopy(reviewed)
            bad[0]["observations"] = []
            with self.assertRaises(ValueError):
                compare_intervention(self.suite, bad, criterion, metric="quality")
            reviewed[0]["metadata"]["patient_classifier_version"] = LEGACY_CLASSIFIER_VERSION
            with self.assertRaises(ValueError):
                compare_intervention(self.suite, reviewed, criterion, metric="quality")
            reviewed[0]["metadata"]["patient_classifier_version"] = DEFAULT_CLASSIFIER_VERSION
            other = next(c["id"] for c in self.scenario["criteria"] if c["id"] != criterion)
            reviewed[0]["observations"].append({"criterion_id": other, "outcome": "pass", "source": "human",
                "reviewer_id": "legacy-reviewer", "rubric_version": self.suite["rubric_version"],
                "evidence_turn_ids": ["a1"], "reason": "Synthetic legacy judgment", "serious_error": False})
            with self.assertRaises(ValueError):
                compare_intervention(self.suite, reviewed, criterion, metric="quality")

    def test_target_outage_remains_task_noncompletion_without_quality_zero(self):
        sessions = [self.session, run_dialogue(self.scenario, ProtocolFixtureClient(), "state_augmented")]
        criterion = next(c["id"] for c in self.scenario["criteria"] if c["required"])
        sessions[0].update(status="target_error", turns=[sessions[0]["turns"][0]])
        with tempfile.TemporaryDirectory() as directory:
            packet, key = self.packet(Path(directory) / "review", sessions)
            for item in packet["items"]:
                if item["criterion"]["id"] == criterion and item["session_status"] == "completed":
                    self.rate(item, rating=2, outcome="pass", serious=False)
            reviewed = apply_review(self.suite, sessions, packet, key)
            result = compare_intervention(self.suite, reviewed, criterion)
            self.assertEqual(result["mean_delta"], 1)
            self.assertEqual(result["target_quality_summary"]["target_error_sessions"], 1)
            with self.assertRaises(ValueError):
                compare_intervention(self.suite, reviewed, criterion, metric="quality")

    def test_legacy_collection_replays_with_original_classifier(self):
        journal = new_collection(self.scenario, self.session["metadata"], "synthetic", "legacy-journal")
        journal.pop("patient_classifier_version")
        journal["session"]["metadata"].pop("patient_classifier_version")
        step = advance_collection(self.scenario, journal, "这种状况持续几天了？")
        self.assertNotIn("昨天傍晚", step["next_patient_message"])
        final = advance_collection(self.scenario, step, "结束。", finish=True)
        self.assertEqual(final["session"]["harness_trace"]["patient"]["classifier_version"], LEGACY_CLASSIFIER_VERSION)
        bad = deepcopy(journal)
        bad["patient_classifier_version"] = "unknown"
        with self.assertRaises(ValueError):
            advance_collection(self.scenario, bad, "什么时候开始？")

    def test_automatic_study_records_classifier_decisions_only_in_harness(self):
        self.assertEqual(self.session["metadata"]["patient_classifier_version"], DEFAULT_CLASSIFIER_VERSION)
        transitions = [t for t in self.session["harness_trace"] if t["kind"] == "patient_transition"]
        self.assertTrue(transitions)
        self.assertTrue(all(t["intent_decision"]["classifier_version"] == DEFAULT_CLASSIFIER_VERSION for t in transitions))
        self.assertNotIn("intent_decision", json.dumps(self.session["turns"]))
