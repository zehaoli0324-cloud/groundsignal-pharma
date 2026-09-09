"""Synthetic examples for candidate preparation; never clinical gold."""

from copy import deepcopy
import json
import unittest

from scripts.patient_eval.candidate_facts import build_fact_draft


def turn(identifier, role, text, actions=None):
    return {"turn": identifier, "role": role, "sentence": text, "actions": actions or []}


def annotation(text, start, end, intent="Inform"):
    return {"text": text, "range": [start, end], "intent": intent,
            "slot": "synthetic", "value1": "synthetic-value", "value2": ""}


class CandidateFactTests(unittest.TestCase):
    def test_doctor_content_never_becomes_candidate_or_baseline(self):
        source = {"dialogue": "synthetic", "information": [
            turn(8, "patient", "想咨询一下"),
            turn(9, "doctor", "没有发热", [annotation("发热", 2, 3)]),
            turn(10, "patient", "谢谢"),
        ]}
        result = build_fact_draft(source)
        self.assertEqual(result["fact_candidates"], [])
        self.assertEqual(result["legacy_baseline"]["final_snapshot"]["facts"], {})
        self.assertNotIn("没有发热", json.dumps(result, ensure_ascii=False))
        self.assertEqual([row["source_turn_id"] for row in result["source_turn_order"]], [8, 9, 10])

    def test_mismatched_range_cannot_be_repaired_by_searching(self):
        source = {"dialogue": 1, "information": [turn(1, "patient", "没有发热", [
            annotation("发热", 0, 1), annotation("发热", 2, 3),
            {"text": "发热"}, annotation("发热", 2, 4),
        ])]}
        result = build_fact_draft(source)
        checks = [item["span_check"] for item in result["fact_candidates"]]
        self.assertEqual([check["status"] for check in checks], ["mismatch", "exact", "missing", "mismatch"])
        self.assertIsNone(checks[0]["evidence_span"])
        self.assertEqual(checks[1]["evidence_span"], {
            "source_turn_id": 1, "source_turn_index": 0,
            "start": 2, "end_exclusive": 4, "text": "发热",
        })
        for item in result["fact_candidates"]:
            self.assertFalse(item["asserted_as_fact"])
            self.assertIsNone(item["review"]["polarity"])

    def test_question_annotation_is_not_a_patient_fact(self):
        source = {"dialogue": 1, "information": [turn(1, "patient", "发热吗？", [
            annotation("发热", 0, 1, "Inquire"),
        ])]}
        result = build_fact_draft(source)
        candidate = result["fact_candidates"][0]
        self.assertTrue(candidate["upstream_question_intent"])
        self.assertFalse(candidate["asserted_as_fact"])
        self.assertIsNone(candidate["review"]["is_patient_assertion"])
        self.assertEqual(result["legacy_baseline"]["final_snapshot"]["facts"], {})

    def test_future_correction_never_changes_opening(self):
        source = {"dialogue": "synthetic", "information": [
            turn(10, "patient", "有发热", [annotation("发热", 1, 2)]),
            turn(11, "patient", "症状开始时间是昨天"),
            turn(20, "doctor", "请核对"),
            turn(30, "patient", "更正，没有发热", [annotation("发热", 5, 6)]),
        ]}
        result = build_fact_draft(source)
        self.assertEqual(result["opening_boundary"]["source_turn_ids"], [10, 11])
        self.assertTrue(result["legacy_baseline"]["opening_snapshot"]["facts"]["fever"]["value"])
        self.assertFalse(result["legacy_baseline"]["final_snapshot"]["facts"]["fever"]["value"])
        later = result["fact_candidates"][-1]
        self.assertTrue(later["later_fact_candidate"])
        self.assertIsNone(later["review"]["correction_of_candidate_id"])
        self.assertIsNone(later["review"]["disclosure_policy"])
        self.assertFalse(result["runtime_export_allowed"])

    def test_cues_are_exact_local_spans_with_no_scope_resolution(self):
        sentence = "妈妈昨天可能没有发热，我刚才说错了"
        result = build_fact_draft({"dialogue": 1, "information": [turn(1, "patient", sentence)]})
        cues = result["patient_turns"][0]["review_cues"]
        self.assertEqual({cue["category"] for cue in cues}, {"person", "time", "uncertainty", "negation", "correction"})
        for cue in cues:
            self.assertEqual(cue["text"], sentence[cue["start"]:cue["end_exclusive"]])
            self.assertFalse(cue["scope_resolved"])
        self.assertEqual(result["fact_candidates"], [])

    def test_source_and_detached_original_annotations_remain_unchanged(self):
        source = {"dialogue": "synthetic", "information": [
            turn("one", "patient", "没有发热", [annotation("发热", 2, 3)]),
        ]}
        before = deepcopy(source)
        result = build_fact_draft(source)
        self.assertEqual(source, before)
        result["fact_candidates"][0]["upstream_annotation"]["range"][0] = 100
        self.assertEqual(source, before)
        self.assertEqual(result["patient_turns"][0]["original_text"], before["information"][0]["sentence"])

    def test_leading_doctor_turn_means_no_initial_patient_prefix(self):
        result = build_fact_draft({"dialogue": 1, "information": [
            turn(1, "doctor", "请描述"),
            turn(2, "patient", "发热", [annotation("发热", 0, 1)]),
        ]})
        self.assertEqual(result["opening_boundary"]["source_turn_ids"], [])
        self.assertEqual(result["legacy_baseline"]["opening_snapshot"]["facts"], {})
        self.assertTrue(result["fact_candidates"][0]["later_fact_candidate"])

    def test_missing_annotations_and_blank_patient_text_are_counted(self):
        result = build_fact_draft({"dialogue": 1, "information": [
            {"turn": 1, "role": "patient", "sentence": " ", "actions": None},
            turn(2, "patient", "合成", [3, {"text": "合成", "range": [True, 1]}]),
        ]})
        self.assertEqual(result["counters"]["empty_patient_turns"], 1)
        self.assertEqual(result["counters"]["malformed_actions"], 1)
        self.assertEqual(result["counters"]["mismatch_spans"], 1)
        self.assertEqual(result["legacy_baseline"]["counters"]["observed_patient_turns"], 1)

    def test_ambiguous_source_identity_is_rejected(self):
        for source in [None, {"dialogue": True, "information": []},
                       {"dialogue": 1, "information": [turn(1, "patient", "一"), turn(1, "doctor", "二")]}]:
            with self.assertRaises(ValueError):
                build_fact_draft(source)


if __name__ == "__main__":
    unittest.main()
