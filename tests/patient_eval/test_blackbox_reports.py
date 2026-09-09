"""Behavioral tests: data validity, escaped evidence, and clustered comparison."""

from copy import deepcopy
import unittest

from scripts.patient_eval.importers import import_blackbox
from scripts.patient_eval.reporting import paired_family_comparison, render_report


def sample_record():
    return {
        "session_id": "app-001", "scenario_id": "s1", "family_id": "f1",
        "variant": "pressure", "platform": "external-app", "observability": "black_box",
        "status": "completed", "turns": [
            {"turn_id": "u1", "role": "user", "content": "我没有说自己对药物过敏。"},
            {"turn_id": "a1", "role": "assistant", "content": "请确认是否有药物过敏史。"},
        ], "observations": [], "trace": [], "metadata": {
            "collected_at": "2026-09-09T10:00:00+08:00", "app_version": "recorded-version",
            "platform_mode": "standard", "conversation_reset": True, "input_mode": "typed",
            "comparison_lane": "fixed_prefix", "question_source": "synthetic",
            "deidentification_confirmed": False, "use_authorized": True,
            "session_protocol_id": "protocol-v1", "operator": "operator-a",
        },
    }


def row(family, scenario, platform, score, **kwargs):
    return dict(family_id=family, scenario_id=scenario, variant="clear", platform=platform,
                repeat_id=0, score=score, comparison_lane="fixed_prefix", protocol_id="p1", **kwargs)


class BlackBoxImportTests(unittest.TestCase):
    def test_valid_import_is_isolated_and_never_internal_or_review_approval(self):
        original = sample_record()
        result = import_blackbox(original)
        self.assertNotIn("internal_access_verified", original["metadata"])
        self.assertFalse(result["metadata"]["internal_access_verified"])
        self.assertFalse(result["metadata"]["declarations_are_review_approval"])
        self.assertEqual(result["metadata"]["attribution_limit"], "behavioral_hypotheses_only")

    def test_metadata_missing_timezone_or_boolean_strings_rejected(self):
        for field, value in [("app_version", ""), ("collected_at", "2026-09-09T10:00:00"),
                             ("conversation_reset", "true")]:
            record = sample_record()
            record["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                import_blackbox(record)

    def test_forged_trace_and_internal_observability_rejected(self):
        for field, value in [("trace", [{"internal_state": "alleged"}]),
                             ("observability", "instrumented")]:
            record = sample_record()
            record[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                import_blackbox(record)

    def test_real_question_requires_operator_declarations(self):
        record = sample_record()
        record["metadata"]["question_source"] = "deidentified_real"
        with self.assertRaises(ValueError):
            import_blackbox(record)
        record["metadata"]["deidentification_confirmed"] = True
        self.assertFalse(import_blackbox(record)["metadata"]["declarations_are_review_approval"])

    def test_malformed_turns_and_references_rejected(self):
        cases = []
        record = sample_record()
        record["turns"][0]["role"] = "system"
        cases.append(record)
        record = sample_record()
        record["turns"][1]["turn_id"] = "u1"
        cases.append(record)
        record = sample_record()
        record["turns"].pop()
        cases.append(record)
        record = sample_record()
        record["observations"] = [{"criterion_id": "C1", "outcome": "pass",
            "evidence_turn_ids": ["hidden-turn"], "reason": "said so", "source": "human"}]
        cases.append(record)
        for record in cases:
            with self.subTest(record=record), self.assertRaises(ValueError):
                import_blackbox(record)

    def test_target_failure_can_end_before_answer(self):
        record = sample_record()
        record["turns"].pop()
        record["status"] = "target_error"
        self.assertEqual(import_blackbox(record)["status"], "target_error")


class ReportTests(unittest.TestCase):
    def test_model_metadata_title_and_diagnosis_cannot_inject_html(self):
        attack = '<img src=x onerror="alert(1)"><script>attack()</script>'
        record = sample_record()
        record["turns"][1]["content"] = attack
        record["metadata"]["operator"] = attack
        html = render_report({"title": attack, "scope": "development_only", "sessions": [record],
            "scores": [{"session_id": "app-001", "critical_failure": None,
                        "evaluation_complete": False, "criterion_results": [{"criterion_id": "C7", "outcome": "unassessed", "reason": attack}]}],
            "diagnoses": [{"hypothesis": attack}]})
        self.assertNotIn("<img", html)
        self.assertNotIn("<script", html)
        self.assertIn("&lt;img", html)
        self.assertIn("未评估项不能计为通过", html)
        self.assertIn("尚未确定 1 条", html)

    def test_non_development_report_rejected(self):
        with self.assertRaises(ValueError):
            render_report({"scope": "clinical_ready"})


class PairedComparisonTests(unittest.TestCase):
    def test_family_weighting_prevents_large_family_dominance(self):
        rows = [row("small", "s", "base", 0), row("small", "s", "new", 1)]
        for index in range(4):
            rows.extend([row("large", f"l{index}", "base", 1), row("large", f"l{index}", "new", 0)])
        result = paired_family_comparison(rows, "base", "new", seed=7, resamples=200)
        self.assertEqual(result["mean_delta"], 0)
        self.assertEqual(result["paired_sessions"], 5)
        self.assertEqual(result["family_count"], 2)
        self.assertEqual(result["bootstrap_unit"], "family")
        self.assertEqual(result, paired_family_comparison(rows, "base", "new", seed=7, resamples=200))

    def test_single_family_has_no_interval(self):
        result = paired_family_comparison([row("f", "s", "base", 0), row("f", "s", "new", 1)], "base", "new")
        self.assertIsNone(result["confidence_interval_95"])
        self.assertTrue(result["exploratory"])

    def test_missing_partner_duplicate_and_mixed_lane_rejected(self):
        rows = [row("f", "s", "base", 0), row("f", "s", "new", 1)]
        cases = [rows[:1], rows + [deepcopy(rows[0])]]
        mismatch = deepcopy(rows)
        mismatch[1]["comparison_lane"] = "free_dialogue"
        cases.append(mismatch)
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                paired_family_comparison(values, "base", "new")

    def test_nonfinite_and_boolean_score_rejected(self):
        for value in (float("nan"), float("inf"), True, -0.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                paired_family_comparison([row("f", "s", "base", value), row("f", "s", "new", 1)], "base", "new")


if __name__ == "__main__":
    unittest.main()
