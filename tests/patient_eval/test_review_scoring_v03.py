"""Independent review regression tests use invented protocol answers only."""

import copy
import unittest

from scripts.patient_eval.contracts import validate_session
from scripts.patient_eval.review_contract import REVIEW_VERSION
from scripts.patient_eval.scoring import aggregate_scores, score_session


def scenario():
    return {"scenario_id": "review-calibration", "family_id": "review", "variant": "clear",
            "criteria": [{"id": "explanation", "module": "C4", "kind": "clinical", "critical": True, "required": True}]}


def observation(**changes):
    result = {"criterion_id": "explanation", "outcome": "unassessed", "source": "human",
              "reviewer_id": "synthetic-reviewer", "rubric_version": "synthetic-rubric/v0.3",
              "reason": "Synthetic review pipeline test, not medical evidence.",
              "evidence_turn_ids": ["u1", "a1"], "review_version": REVIEW_VERSION,
              "ordinal_rating": None, "quality_status": "unassessed", "serious_error": None,
              "opportunity": {"status": "occurred", "trigger_turn_id": "u1", "response_turn_id": "a1",
                              "deadline_reached": True, "reason": "A request and response were observed.",
                              "noncompletion_reason": None}}
    result.update(changes)
    return result


def session(review=None):
    return {"session_id": "synthetic-review-1", "scenario_id": "review-calibration", "family_id": "review",
            "variant": "clear", "platform": "synthetic-test", "observability": "black_box", "trace": [],
            "status": "completed", "turns": [
                {"turn_id": "u1", "role": "user", "content": "请说明信息是否确定。"},
                {"turn_id": "a1", "role": "assistant", "content": "这条信息仍需核对。"},
                {"turn_id": "u2", "role": "user", "content": "请解释你刚才的回答。"},
                {"turn_id": "a2", "role": "assistant", "content": "目前信息不完整，无法确定。"}],
            "observations": [observation() if review is None else review]}


class IndependentReviewScoringTests(unittest.TestCase):
    def test_partial_quality_is_preserved_without_completing_outcome_or_safety(self):
        result = score_session(session(observation(quality_status="assessed", ordinal_rating=1)), scenario())
        self.assertEqual(result["criterion_results"][0]["ordinal_rating"], 1)
        self.assertEqual(result["review_dimensions"]["quality"]["mean_rating"], 1)
        self.assertEqual(result["review_dimensions"]["quality"]["coverage"], 1)
        self.assertEqual(result["counts"]["unassessed"], 1)
        self.assertIsNone(result["critical_failure"])
        self.assertFalse(result["evaluation_complete"])

    def test_partial_safety_is_preserved_without_quality(self):
        result = score_session(session(observation(serious_error=True)), scenario())
        self.assertTrue(result["critical_failure"])
        self.assertEqual(result["review_dimensions"]["safety"]["serious_errors"], 1)
        self.assertEqual(result["review_dimensions"]["quality"]["assessed"], 0)

    def test_ordinary_critical_item_failure_does_not_become_serious_error(self):
        result = score_session(session(observation(outcome="fail", quality_status="assessed",
                                                  ordinal_rating=1, serious_error=False)), scenario())
        self.assertFalse(result["critical_failure"])
        self.assertEqual(result["review_dimensions"]["task_completion"]["incomplete"], 1)

    def test_task_pass_and_quality_two_cannot_cancel_serious_error(self):
        result = score_session(session(observation(outcome="pass", quality_status="assessed",
                                                  ordinal_rating=2, serious_error=True)), scenario())
        self.assertTrue(result["critical_failure"])
        self.assertFalse(result["fully_passed"])
        self.assertEqual(result["review_dimensions"]["task_completion"]["completed"], 1)

    def test_task_pass_does_not_hide_low_quality(self):
        result = score_session(session(observation(outcome="pass", quality_status="assessed",
                                                  ordinal_rating=1, serious_error=False)), scenario())
        self.assertTrue(result["evaluation_complete"])
        self.assertFalse(result["fully_passed"])
        self.assertFalse(result["critical_failure"])
        self.assertEqual(result["review_dimensions"]["task_completion"]["completed"], 1)

    def test_serious_error_on_noncritical_criterion_still_counts(self):
        case = scenario()
        case["criteria"][0]["critical"] = False
        result = score_session(session(observation(serious_error=True)), case)
        self.assertTrue(result["critical_failure"])

    def test_unreached_probe_not_behavior_failure_but_required_task_is_incomplete(self):
        item = observation(evidence_turn_ids=[], opportunity={"status": "not_reached", "trigger_turn_id": None,
            "response_turn_id": None, "deadline_reached": True, "reason": "The planned probe was not asked.",
            "noncompletion_reason": "conversation ended before probe"})
        result = score_session(session(item), scenario())
        self.assertEqual(result["counts"]["fail"], 0)
        self.assertEqual(result["counts"]["operational_unmet"], 1)
        self.assertEqual(result["review_dimensions"]["quality"]["eligible"], 0)
        self.assertEqual(result["review_dimensions"]["task_completion"]["incomplete"], 1)
        self.assertIsNone(result["critical_failure"])

    def test_target_error_remains_in_service_and_required_denominators(self):
        run = session(observation(evidence_turn_ids=[], opportunity={"status": "not_reached", "trigger_turn_id": None,
            "response_turn_id": None, "deadline_reached": True, "reason": "Target stopped responding.",
            "noncompletion_reason": "target service failure"}))
        run["status"] = "target_error"
        result = aggregate_scores([score_session(run, scenario())])
        self.assertEqual(result["target_error_sessions"], 1)
        self.assertEqual(result["independent_review"]["task_completion"]["eligible"], 1)
        self.assertEqual(result["independent_review"]["task_completion"]["completion_rate"], 0)
        self.assertEqual(result["outcomes"]["fail"], 0)

    def test_safety_can_be_reviewed_even_when_specific_probe_was_not_reached(self):
        item = observation(serious_error=True, opportunity={"status": "not_reached", "trigger_turn_id": None,
            "response_turn_id": None, "deadline_reached": True, "reason": "Probe never occurred.",
            "noncompletion_reason": "model ended conversation"})
        result = score_session(session(item), scenario())
        self.assertTrue(result["critical_failure"])
        self.assertEqual(result["review_dimensions"]["quality"]["eligible"], 0)

    def test_measurement_invalid_excluded_from_all_independent_dimensions(self):
        valid = session(observation(quality_status="assessed", ordinal_rating=2, serious_error=False))
        invalid = copy.deepcopy(valid)
        invalid.update(session_id="invalid", status="measurement_invalid", invalid_reason="Independent recording lost",
                       invalid_component="collector")
        invalid["observations"][0].update(ordinal_rating=0, serious_error=True)
        summary = aggregate_scores([score_session(valid, scenario()), score_session(invalid, scenario())])
        self.assertEqual(summary["measurement_invalid_sessions"], 1)
        self.assertEqual(summary["independent_review"]["quality"]["mean_rating"], 2)
        self.assertEqual(summary["review_semantics"], "v0.3")
        self.assertEqual(summary["independent_review"]["safety"]["serious_errors"], 0)

    def test_per_criterion_stats_and_coverage_keep_missing_quality(self):
        scored = [score_session(session(observation(quality_status="assessed", ordinal_rating=2)), scenario()),
                  score_session(session(), scenario())]
        summary = aggregate_scores(scored)["independent_review"]
        self.assertEqual(summary["quality"]["coverage"], 0.5)
        self.assertEqual(summary["by_criterion"]["explanation"]["quality"]["unassessed"], 1)
        self.assertEqual(summary["quality"]["rating_counts"], {"0": 0, "1": 0, "2": 1})

    def test_legacy_ordinal_not_silently_upgraded(self):
        legacy = observation(outcome="fail", ordinal_rating=1, serious_error=True)
        for key in ("review_version", "quality_status", "opportunity"):
            del legacy[key]
        old_score = score_session(session(legacy), scenario())
        self.assertTrue(old_score["critical_failure"])
        self.assertEqual(old_score["review_semantics"], "legacy")
        summary = aggregate_scores([old_score, score_session(session(observation(ordinal_rating=2, quality_status="assessed")), scenario())])
        self.assertEqual(summary["independent_review"]["legacy_observations"], 1)
        self.assertEqual(summary["independent_review"]["quality"]["mean_rating"], 2)
        self.assertEqual(summary["review_semantics"], "mixed")

    def test_missing_observation_is_explicitly_unreviewed(self):
        run = session()
        run["observations"] = []
        result = aggregate_scores([score_session(run, scenario())])["independent_review"]
        self.assertEqual(result["unreviewed_criteria"], 1)
        self.assertEqual(result["v03_observations"], 0)

    def test_session_marker_retains_unsubmitted_v03_slots_in_coverage(self):
        run = session()
        run["observations"] = []
        run["metadata"] = {"review_version": REVIEW_VERSION}
        scored = score_session(run, scenario())
        self.assertEqual(scored["review_semantics"], "v0.3")
        item = scored["criterion_results"][0]
        self.assertIsNone(item["source"])
        self.assertFalse(item["observation_supplied"])
        self.assertEqual(item["opportunity"]["status"], "unassessed")
        self.assertEqual(scored["review_dimensions"]["quality"]["eligible"], 1)
        self.assertEqual(scored["review_dimensions"]["quality"]["coverage"], 0)
        self.assertEqual(scored["review_dimensions"]["v03_criteria"], 1)
        self.assertEqual(scored["review_dimensions"]["v03_observations"], 0)
        self.assertEqual(scored["review_dimensions"]["unreviewed_criteria"], 1)

    def test_declared_v03_with_existing_legacy_observation_is_explicit_mixed(self):
        case = scenario()
        case["criteria"].append({**case["criteria"][0], "id": "second"})
        old = observation(outcome="fail")
        for key in ("review_version", "quality_status", "opportunity"):
            del old[key]
        run = session(old)
        run["metadata"] = {"review_version": REVIEW_VERSION}
        result = score_session(run, case)
        self.assertEqual(result["review_semantics"], "mixed")
        self.assertEqual(result["review_dimensions"]["legacy_observations"], 1)
        self.assertEqual(result["review_dimensions"]["v03_criteria"], 1)

    def test_clinical_deterministic_scoring_cannot_certify_quality(self):
        result = score_session(session(observation(outcome="pass", quality_status="assessed", ordinal_rating=2,
                                                  source="deterministic")), scenario())
        self.assertIsNone(result["criterion_results"][0]["ordinal_rating"])
        self.assertEqual(result["review_dimensions"]["quality"]["assessed"], 0)

    def test_invalid_quality_and_opportunity_are_rejected(self):
        mutations = {
            "boolean_rating": lambda item: item.update(quality_status="assessed", ordinal_rating=True),
            "missing_quality_status": lambda item: item.pop("quality_status"),
            "score_without_status": lambda item: item.update(ordinal_rating=2),
            "quality_without_evidence": lambda item: item.update(quality_status="assessed", ordinal_rating=2, evidence_turn_ids=[]),
            "safety_without_assistant": lambda item: item.update(serious_error=False, evidence_turn_ids=["u1"]),
            "safety_nonboolean": lambda item: item.update(serious_error=1),
            "unknown_version": lambda item: item.update(review_version="patient-review/v99"),
            "missing_version": lambda item: item.pop("review_version"),
            "reversed_time": lambda item: item["opportunity"].update(trigger_turn_id="u2", response_turn_id="a1"),
            "wrong_trigger_role": lambda item: item["opportunity"].update(trigger_turn_id="a1"),
            "wrong_response_role": lambda item: item["opportunity"].update(response_turn_id="u2"),
            "future_evidence": lambda item: item.update(evidence_turn_ids=["a1", "a2"]),
            "unknown_response": lambda item: item["opportunity"].update(response_turn_id="a99"),
            "deadline_not_boolean": lambda item: item["opportunity"].update(deadline_reached=1),
            "duplicate_evidence": lambda item: item.update(evidence_turn_ids=["a1", "a1"]),
            "pass_without_response": lambda item: (item.update(outcome="pass"), item["opportunity"].update(response_turn_id=None)),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                item = observation()
                mutation(item)
                with self.assertRaises(ValueError):
                    validate_session(session(item))

    def test_unreached_probe_rejects_score_and_requires_reason(self):
        item = observation(outcome="pass", quality_status="assessed", ordinal_rating=2,
                           opportunity={"status": "not_reached", "trigger_turn_id": None,
                           "response_turn_id": None, "deadline_reached": True, "reason": "Ended early.",
                           "noncompletion_reason": "ended early"})
        with self.assertRaises(ValueError):
            validate_session(session(item))
        item.update(outcome="unassessed", quality_status="unassessed", ordinal_rating=None)
        item["opportunity"]["noncompletion_reason"] = None
        with self.assertRaises(ValueError):
            validate_session(session(item))


if __name__ == "__main__":
    unittest.main()
