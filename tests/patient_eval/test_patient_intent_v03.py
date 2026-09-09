"""Finite intent/disclosure calibration; no clinical-truth claims."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.calibrate_patient import calibrate, DEFAULT_SAMPLES
from scripts.patient_eval.patient import PatientSimulator
from scripts.patient_eval.patient_intent import (
    DEFAULT_CLASSIFIER_VERSION, LEGACY_CLASSIFIER_VERSION, classify_requested_slots,
)
from tests.patient_eval.test_patient import patient_spec


class PatientIntentV03Tests(unittest.TestCase):
    def setUp(self):
        self.facts = patient_spec()["facts"]

    def slots(self, text):
        return classify_requested_slots(text, self.facts)["requested_slots"]

    def test_durations_are_supported_but_not_any_quantity(self):
        self.assertEqual(self.slots("这种状况持续几天了？"), ["onset"])
        self.assertEqual(self.slots("已经持续了几周？"), ["onset"])
        self.assertEqual(self.slots("你一天喝几杯水？"), [])

    def test_instruction_to_another_recipient_does_not_disclose(self):
        for text in ("先告诉医生起始时间，不必现在回复我。", "请向护士说明有没有发热。", "医生之前问你有没有过敏。"):
            with self.subTest(text=text):
                self.assertEqual(self.slots(text), [])
        self.assertEqual(self.slots("医生以后会再问。现在请告诉我年龄是多少？"), ["age"])

    def test_local_negative_scope_and_fact_negation_are_different(self):
        self.assertEqual(self.slots("暂时不用告诉我年龄和药名，但是是否过敏？"), ["allergy"])
        self.assertEqual(self.slots("我不是问是否发热，而是问药名是什么？"), ["medicine"])
        self.assertEqual(self.slots("没有发热吗？"), ["fever"])
        self.assertEqual(self.slots("没有过敏，对吗？"), ["allergy"])
        self.assertEqual(self.slots("不用回答药名。年龄是几岁？"), ["age"])
        self.assertEqual(self.slots("请不要在这里回答药名是什么。"), [])

    def test_cancellation_only_retracts_its_declared_scope(self):
        self.assertEqual(self.slots("年龄是多少？药名是什么？现在不用回答。"), ["age"])
        self.assertEqual(self.slots("年龄是多少？药名是什么？以上问题不必回答。"), [])
        self.assertEqual(self.slots("年龄是多少？药名不用说。"), ["age"])

    def test_quoted_questions_never_license_other_facts(self):
        for text in ('示例：“有没有过敏？”，请问年龄是多少？', '“药名是什么？”只是例子；你多大？', '「有没有发热」不需要复述，年龄是多少？'):
            self.assertEqual(self.slots(text), ["age"])
        self.assertEqual(self.slots('记录：“药名是什么？'), [])
        self.assertEqual(self.slots('医生说：“请问「药名是什么」。”你年龄是多少？'), ["age"])

    def test_statements_and_unrelated_questions_remain_unmapped(self):
        for text in ("我不知道你的年龄是多少。", "我会告诉你药名是什么。", "药名需要核实。", "请问今天的天气怎么样？", "稍后我会记录药名。", "好的，谢谢。"):
            self.assertEqual(self.slots(text), [])
        self.assertEqual(self.slots("我会记录药名。年龄是多少？"), ["age"])

    def test_specific_span_wins_over_nested_generic_different_slot(self):
        facts = {"forwarded_at": {"ask_patterns": ["日期"]}, "original_date": {"ask_patterns": ["原文日期"]}}
        decision = classify_requested_slots("原文日期是什么？", facts)
        self.assertEqual(decision["requested_slots"], ["original_date"])
        facts["original_date"]["ask_patterns"] = ["日期"]
        self.assertEqual(classify_requested_slots("日期是什么？", facts)["requested_slots"], [])

    def test_decisions_ignore_values_answers_target_and_grade(self):
        before = classify_requested_slots("年龄是多少？是否过敏？", self.facts)
        edited = deepcopy(self.facts)
        for fact in edited.values():
            fact.update(value="SECRET", answer="SECRET", target="MODEL", grade="PASS")
        after = classify_requested_slots("年龄是多少？是否过敏？", edited)
        self.assertEqual(before, after)
        self.assertNotIn("SECRET", json.dumps(after))

    def test_legacy_replay_is_explicit_and_unknown_version_rejected(self):
        spec = patient_spec()
        legacy = PatientSimulator(spec, classifier_version=LEGACY_CLASSIFIER_VERSION)
        current = PatientSimulator(spec)
        legacy.opening(); current.opening()
        self.assertEqual(legacy.respond("这种状况持续几天了？")["disclosed"], [])
        self.assertEqual(current.respond("这种状况持续几天了？")["disclosed"], ["onset"])
        self.assertEqual(legacy.snapshot()["classifier_version"], LEGACY_CLASSIFIER_VERSION)
        self.assertEqual(current.snapshot()["classifier_version"], DEFAULT_CLASSIFIER_VERSION)
        with self.assertRaises(AttributeError):
            current.classifier_version = LEGACY_CLASSIFIER_VERSION
        with self.assertRaises(ValueError):
            PatientSimulator(spec, classifier_version="pretend-v0.2")
        with self.assertRaises(ValueError):
            classify_requested_slots("药名是什么？", self.facts, "latest")

    def test_intent_evidence_is_operator_only_and_override_is_explicit(self):
        patient = PatientSimulator(patient_spec())
        patient.opening()
        response = patient.respond("请不要补充药名，年龄是多少？")
        self.assertEqual(response["disclosed"], ["age"])
        self.assertEqual(response["intent_decision"]["mode"], "automatic")
        self.assertNotIn("negated_request", response["content"])
        response["intent_decision"]["clauses"].clear()
        log = patient.snapshot()["event_log"][-1]
        self.assertEqual(log["intent_decision"]["mode"], "automatic")
        self.assertEqual(log["intent_decision"]["clauses"][0]["reason"], "negated_request")
        log["intent_decision"]["clauses"].clear()
        self.assertTrue(patient.snapshot()["event_log"][-1]["intent_decision"]["clauses"])
        patient.respond("无法识别的表达。", requested_slots=["allergy"])
        self.assertEqual(patient.snapshot()["event_log"][-1]["intent_decision"]["mode"], "explicit_override")

    def test_declared_calibration_counts_are_consistent_and_baseline_reproduced(self):
        report = calibrate()
        self.assertTrue(report["legacy_prechange_observations_reproduced"])
        self.assertFalse(report["provenance"]["independent_human_annotation"])
        for result in report["results"].values():
            total = result["overall"]["case_count"]
            self.assertEqual(total, 48)
            self.assertEqual(sum(s["case_count"] for s in result["by_category"].values()), total)
            self.assertEqual(sum(s["case_count"] for s in result["by_declared_split"].values()), total)
            self.assertLessEqual(result["overall"]["correctly_unmapped_case_count"], result["overall"]["unmapped_case_count"])
        self.assertEqual(report["results"][LEGACY_CLASSIFIER_VERSION]["overall"]["exact_match_count"], 23)

    def test_baseline_tampering_is_not_silently_accepted(self):
        samples = json.loads(DEFAULT_SAMPLES.read_text())
        samples["cases"][0]["legacy_observed_slots_before_change"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples.json"
            path.write_text(json.dumps(samples))
            with self.assertRaisesRegex(ValueError, "pre-change"):
                calibrate(path)


if __name__ == "__main__":
    unittest.main()
