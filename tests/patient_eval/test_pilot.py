from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.agreement import rater_agreement
from scripts.patient_eval.contracts import validate_session
from scripts.patient_eval.pilot import (DEFAULT_PILOT, advance_collection, apply_review, compare_intervention, load_pilot_suite,
                                        make_review_packet, new_collection, score_pilot)


def metadata():
    return {"collected_at": "2026-09-09T10:00:00+08:00", "app_version": "synthetic-example",
            "platform_mode": "text;memory-off;web-unknown", "conversation_reset": True,
            "input_mode": "text", "comparison_lane": "free_dialogue", "question_source": "synthetic",
            "deidentification_confirmed": True, "use_authorized": True,
            "session_protocol_id": "patient-pilot-v02-free-dialogue", "operator": "example-operator"}


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.suite = load_pilot_suite()
        self.scenario = self.suite["scenarios"][0]

    def journal(self):
        return new_collection(self.scenario, metadata(), "synthetic-platform", "example-session")

    def test_twelve_scenarios_share_six_families_and_frozen_facts(self):
        self.assertEqual(len(self.suite["scenarios"]), 12)
        self.assertEqual(len({s["family_id"] for s in self.suite["scenarios"]}), 6)
        self.assertTrue(all(s["source"] == "synthetic" for s in self.suite["scenarios"]))
        bad = deepcopy(self.suite)
        bad["scenarios"][1]["patient"]["facts"]["person"]["value"] = "different person"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "suite.json"
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                load_pilot_suite(path)
            bad = deepcopy(self.suite)
            bad["scenarios"][1]["patient"]["max_assistant_turns"] += 1
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                load_pilot_suite(path)

    def test_collection_preserves_actual_replies_and_ends_on_assistant(self):
        journal = self.journal()
        self.assertEqual(journal["session"]["status"], "in_progress")
        with self.assertRaises(ValueError):
            validate_session(journal["session"])
        next_step = advance_collection(self.scenario, journal, "请问什么时候开始？")
        self.assertIn("昨天傍晚", next_step["next_patient_message"])
        final = advance_collection(self.scenario, next_step, "这轮先记录到这里。", finish=True)
        self.assertTrue(final["done"])
        self.assertEqual(final["session"]["turns"][-1]["role"], "assistant")
        self.assertEqual(final["session"]["observations"], [])
        self.assertFalse(score_pilot(self.suite, [final["session"]])["scores"][0]["evaluation_complete"])

    def test_manual_classifier_override_is_audited_and_never_changes_facts(self):
        journal = self.journal()
        with self.assertRaises(ValueError):
            advance_collection(self.scenario, journal, "从何时起的呢", requested_slots=["onset"])
        step = advance_collection(self.scenario, journal, "从何时起的呢", requested_slots=["onset"],
                                  classification_note="操作员确认这是询问开始时间")
        self.assertIn("昨天傍晚", step["next_patient_message"])
        self.assertEqual(step["responses"][0]["requested_slots"], ["onset"])
        with self.assertRaises(ValueError):
            advance_collection(self.scenario, journal, "问题", requested_slots=["invented"], classification_note="test")

    def test_journal_and_script_changes_cannot_silently_replay(self):
        journal = self.journal()
        journal["session"]["turns"][0]["content"] += "额外提示"
        with self.assertRaises(ValueError):
            advance_collection(self.scenario, journal, "请问什么时候开始？")
        changed = deepcopy(self.scenario)
        changed["patient"]["initial_user_message"] += "changed"
        with self.assertRaises(ValueError):
            advance_collection(changed, self.journal(), "请问什么时候开始？")

    def test_target_outage_is_retained_without_fake_assistant_answer(self):
        final = advance_collection(self.scenario, self.journal(), "", target_error=True, patient_submitted=True)
        self.assertTrue(final["done"])
        self.assertEqual(final["session"]["status"], "target_error")
        self.assertEqual(len(final["session"]["turns"]), 1)
        bundle = score_pilot(self.suite, [final["session"]])
        self.assertEqual(bundle["aggregate"]["target_error_sessions"], 1)
        self.assertEqual(bundle["aggregate"]["measurement_invalid_sessions"], 0)

    def test_unsubmitted_draft_cannot_be_exported_as_a_model_input(self):
        with self.assertRaises(ValueError):
            advance_collection(self.scenario, self.journal(), "", target_error=True)
        pending = advance_collection(self.scenario, self.journal(), "", target_error=True, patient_submitted=False)
        self.assertFalse(pending["done"])
        self.assertEqual(pending["session"]["status"], "in_progress")
        self.assertEqual(pending["collector_issues"][0]["classification"], "collection_failure_not_target_evidence")
        with self.assertRaises(ValueError):
            score_pilot(self.suite, [pending["session"]])

    def test_direct_score_cannot_upgrade_ordinary_quality_failure_to_serious_error(self):
        session = advance_collection(self.scenario, self.journal(), "请核对具体信息。", finish=True)["session"]
        critical = next(c for c in self.scenario["criteria"] if c["critical"])
        session["observations"] = [{"criterion_id": critical["id"], "outcome": "fail", "source": "human",
            "reviewer_id": "reviewer-A", "rubric_version": self.suite["rubric_version"],
            "evidence_turn_ids": ["a1"], "reason": "普通不完整回答", "ordinal_rating": 1, "serious_error": False}]
        with self.assertRaises(ValueError):
            score_pilot(self.suite, [session])
        session["observations"][0]["serious_error"] = True
        self.assertTrue(score_pilot(self.suite, [session])["scores"][0]["critical_failure"])

    def packet(self, directory):
        session = advance_collection(self.scenario, self.journal(), "请核对具体信息。", finish=True)["session"]
        make_review_packet(self.suite, [session], directory)
        return session, json.loads((directory / "reviewer-packet.json").read_text()), json.loads((directory / "operator-key.json").read_text())

    def test_blind_packet_excludes_platform_and_hidden_patient_script(self):
        with tempfile.TemporaryDirectory() as directory:
            session, packet, key = self.packet(Path(directory) / "packet")
            text = json.dumps(packet, ensure_ascii=False)
            self.assertNotIn("synthetic-platform", text)
            self.assertNotIn('"ask_patterns"', text)
            self.assertNotIn('"harness_trace"', text)
            self.assertTrue(key["mapping"])
            self.assertTrue(all(i["outcome"] == "unassessed" for i in packet["items"]))
            packet["items"][0]["rating"] = 2
            result = apply_review(self.suite, [session], packet, key)
            self.assertEqual(result[0]["observations"], [])

    def test_human_review_is_bound_to_original_text_and_separate_safety_label(self):
        with tempfile.TemporaryDirectory() as directory:
            session, packet, key = self.packet(Path(directory) / "packet")
            item = next(i for i in packet["items"] if i["criterion"]["critical"])
            item.update(outcome="fail", rating=0, reviewer_id="expert-A", evidence_turn_ids=["a1"], reason="合成测试判定")
            with self.assertRaises(ValueError):
                apply_review(self.suite, [session], packet, key)
            item["serious_error"] = True
            result = apply_review(self.suite, [session], packet, key)
            self.assertTrue(score_pilot(self.suite, result)["scores"][0]["critical_failure"])
            item["turns"][0]["content"] = "edited evidence"
            with self.assertRaises(ValueError):
                apply_review(self.suite, [session], packet, key)

    def test_intervention_comparison_requires_labels_and_rejects_configuration_drift(self):
        from scripts.patient_eval.pilot_cli import ProtocolFixtureClient
        from scripts.patient_eval.study import run_dialogue
        sessions = [run_dialogue(self.scenario, ProtocolFixtureClient(), arm) for arm in ("baseline", "state_augmented")]
        with self.assertRaises(ValueError):
            compare_intervention(self.suite, sessions, "correction.absorbed")
        for session, outcome in zip(sessions, ("fail", "pass")):
            session["observations"] = [{"criterion_id": "correction.absorbed", "outcome": outcome, "source": "human",
                "reviewer_id": "synthetic-reviewer", "rubric_version": self.suite["rubric_version"],
                "evidence_turn_ids": [session["turns"][-1]["turn_id"]], "reason": "合成统计程序检查，非真实评分"}]
        result = compare_intervention(self.suite, sessions, "correction.absorbed")
        self.assertEqual(result["mean_delta"], 1)
        self.assertIsNone(result["confidence_interval_95"])
        self.assertEqual(result["target_quality_summary"]["critical_unassessed_sessions"], 2)
        sessions[1]["metadata"]["target_config"]["model"] = "different-model"
        with self.assertRaises(ValueError):
            compare_intervention(self.suite, sessions, "correction.absorbed")


class AgreementTests(unittest.TestCase):
    def rows(self, pairs):
        return [{"item_id": str(i), "reviewer_id": reviewer, "rubric_version": "v2", "rating": rating,
                 "serious_error": None} for i, pair in enumerate(pairs) for reviewer, rating in zip(("A", "B"), pair)]

    def test_perfect_non_degenerate_and_degenerate_margins(self):
        result = rater_agreement(self.rows([(0, 0), (1, 1), (2, 2)]), "A", "B")
        self.assertEqual(result["linear_weighted_cohen_kappa"], 1)
        degenerate = rater_agreement(self.rows([(2, 2), (2, 2)]), "A", "B")
        self.assertIsNone(degenerate["linear_weighted_cohen_kappa"])
        self.assertEqual(degenerate["exact_agreement"], 1)

    def test_missing_scores_do_not_disappear_and_serious_errors_are_separate(self):
        rows = self.rows([(0, 1), (2, None)])
        rows[0]["serious_error"], rows[1]["serious_error"] = True, False
        result = rater_agreement(rows, "A", "B")
        self.assertEqual(result["paired_rated_items"], 1)
        self.assertEqual(result["rating_coverage"], 0.5)
        self.assertEqual(result["serious_error_disagreements"], 1)
        self.assertEqual(result["serious_error_unknown_items"], 1)

    def test_duplicate_rating_boolean_and_mixed_versions_are_rejected(self):
        rows = self.rows([(0, 1)])
        with self.assertRaises(ValueError):
            rater_agreement(rows + rows[:1], "A", "B")
        rows[0]["rating"] = True
        with self.assertRaises(ValueError):
            rater_agreement(rows, "A", "B")
        rows = self.rows([(0, 1)])
        rows[0]["rubric_version"] = "different"
        with self.assertRaises(ValueError):
            rater_agreement(rows, "A", "B")


if __name__ == "__main__":
    unittest.main()
