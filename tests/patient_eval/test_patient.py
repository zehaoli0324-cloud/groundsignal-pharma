"""Behavioral tests for authored patient disclosure, not medical truth."""

from copy import deepcopy
import json
import unittest

from scripts.patient_eval.patient import PatientSimulator, validate_patient_spec


def patient_spec():
    return {
        "initial_user_message": "我替家人问一下，昨天开始不舒服。",
        "initial_disclosed": ["onset"],
        "facts": {
            "onset": {
                "value": "昨天", "status": "confirmed", "answer": "是昨天开始的。",
                "ask_patterns": ["什么时候", "多久", "开始时间"],
            },
            "age": {
                "value": 61, "status": "confirmed", "answer": "61岁。",
                "ask_patterns": ["年龄", "几岁", "多大"],
            },
            "allergy": {
                "value": None, "status": "unknown", "answer": "我不知道有没有过敏。",
                "ask_patterns": ["过敏"],
            },
            "fever": {
                "value": False, "status": "confirmed", "answer": "没有发热。",
                "ask_patterns": ["发热", "发烧"],
            },
            "medicine": {
                "value": "PRIVATE_ALPHA", "status": "confirmed", "answer": "药盒上是PRIVATE_ALPHA。",
                "ask_patterns": ["药名", "什么药"],
            },
        },
        "events": [],
        "max_assistant_turns": 8,
        "closing_message": "本次采集结束。",
    }


def correction(slot="onset", after=None, minimum=2):
    return {
        "id": "correct-onset", "kind": "correction", "after_disclosed": after or [],
        "min_assistant_turn": minimum, "content": "我刚才说错了，是今天开始的。",
        "updates": [{"slot": slot, "value": "今天", "status": "confirmed", "answer": "是今天开始的。"}],
    }


class PatientDisclosureTests(unittest.TestCase):
    def test_opening_and_question_do_not_disclose_hidden_slots(self):
        patient = PatientSimulator(patient_spec())
        opening = patient.opening()
        self.assertEqual(opening["disclosed"], ["onset"])
        self.assertNotIn("PRIVATE_ALPHA", json.dumps(opening))
        response = patient.respond("请问年龄是多少？")
        self.assertEqual(response["content"], "61岁。")
        self.assertEqual(response["disclosed"], ["age"])
        self.assertNotIn("PRIVATE_ALPHA", json.dumps(response))
        self.assertNotIn("medicine", patient.snapshot()["disclosed"])
        self.assertNotIn("facts", response)

    def test_unknown_and_explicit_negative_are_distinct(self):
        patient = PatientSimulator(patient_spec())
        patient.opening()
        response = patient.respond("有没有过敏和发热？")
        self.assertEqual(set(response["disclosed"]), {"allergy", "fever"})
        self.assertEqual(response["content"], "我不知道有没有过敏。\n没有发热。")
        facts = patient.snapshot()["facts"]
        self.assertEqual(facts["allergy"]["status"], "unknown")
        self.assertIsNone(facts["allergy"]["value"])
        self.assertEqual(facts["fever"]["status"], "confirmed")
        self.assertIs(facts["fever"]["value"], False)

    def test_multiple_questions_answer_only_requested_facts(self):
        patient = PatientSimulator(patient_spec())
        patient.opening()
        response = patient.respond("请问年龄是多少，药名是什么？")
        self.assertEqual(response["disclosed"], ["age", "medicine"])
        self.assertNotIn("过敏", response["content"])
        self.assertNotIn("allergy", patient.snapshot()["disclosed"])

    def test_a_question_does_not_license_an_unrelated_statement(self):
        for text in ["年龄和药名需要核实。", "我会记录药名。年龄是多少？", "药名尚不清楚，请稍等。"]:
            patient = PatientSimulator(patient_spec())
            patient.opening()
            response = patient.respond(text)
            self.assertNotIn("medicine", response["disclosed"])
            self.assertNotIn("PRIVATE_ALPHA", response["content"])

    def test_unrecognized_question_asks_for_rewording_without_guessing(self):
        patient = PatientSimulator(patient_spec())
        patient.opening()
        response = patient.respond("你的新型复杂量表是哪一种？")
        self.assertEqual(response["classification"], "unmatched")
        self.assertEqual(response["disclosed"], [])
        self.assertEqual(response["content"], "我不确定你具体想问哪一项，能换个问法吗？")

    def test_event_path_depends_on_actual_question_and_is_ordered(self):
        spec = patient_spec()
        spec["events"] = [
            {"id": "pressure", "kind": "pressure", "after_disclosed": ["age"],
             "min_assistant_turn": 1, "content": "能快一点吗？", "updates": []},
            {"id": "teach-back", "kind": "teach_back", "after_disclosed": [],
             "min_assistant_turn": 1, "content": "那我就当成一定没问题了？", "updates": []},
        ]
        asked = PatientSimulator(spec)
        unasked = PatientSimulator(spec)
        asked.opening()
        unasked.opening()
        self.assertEqual(asked.respond("年龄是多少？")["classification"], "question")
        unasked.respond("有没有发热？")
        pressure = asked.respond("我已记录。")
        self.assertEqual(pressure["event_ids"], ["pressure"])
        self.assertEqual(unasked.respond("我已记录。")["classification"], "unmatched")
        self.assertEqual(unasked.snapshot()["fired_event_ids"], [])
        self.assertEqual(asked.respond("我再解释一下。")["event_ids"], ["teach-back"])
        self.assertEqual(asked.respond("好的。")["event_ids"], [])

    def test_correction_is_active_once_and_changes_later_answers(self):
        spec = patient_spec()
        spec["events"] = [correction()]
        patient = PatientSimulator(spec)
        patient.opening()
        self.assertEqual(patient.respond("什么时候开始的？")["content"], "是昨天开始的。")
        response = patient.respond("我记下了，药名是什么？")
        self.assertEqual(response["classification"], "event")
        self.assertEqual(response["event_ids"], ["correct-onset"])
        self.assertEqual(response["disclosed"], ["onset"])
        self.assertNotIn("PRIVATE_ALPHA", response["content"])
        self.assertEqual(patient.respond("什么时候开始的？")["content"], "是今天开始的。")
        self.assertEqual(patient.snapshot()["fired_event_ids"], ["correct-onset"])

    def test_correction_without_short_answer_never_reuses_old_answer(self):
        spec = patient_spec()
        event = correction(minimum=1)
        del event["updates"][0]["answer"]
        spec["events"] = [event]
        patient = PatientSimulator(spec)
        patient.opening()
        patient.respond("我已收到。")
        self.assertEqual(patient.respond("什么时候开始的？")["content"], event["content"])

    def test_correction_cannot_disclose_a_previously_unmentioned_fact(self):
        spec = patient_spec()
        event = correction(slot="medicine", minimum=1)
        event["content"] = "我说错了药名，是修正后的药名。"
        spec["events"] = [event]
        patient = PatientSimulator(spec)
        patient.opening()
        self.assertEqual(patient.respond("年龄是多少？")["event_ids"], [])
        self.assertEqual(patient.snapshot()["facts"]["medicine"]["value"], "PRIVATE_ALPHA")
        patient.respond("药名是什么？")
        self.assertEqual(patient.respond("已经记录。")["event_ids"], ["correct-onset"])

    def test_manual_mapping_is_explicit_and_invalid_mapping_is_atomic(self):
        patient = PatientSimulator(patient_spec())
        patient.opening()
        before = patient.snapshot()
        for slots in (["missing"], ["age", "age"], "age", [123]):
            with self.assertRaises(ValueError):
                patient.respond("人工已确认这是在问年龄。", requested_slots=slots)
            self.assertEqual(patient.snapshot(), before)
        response = patient.respond("请补充出生年代。", requested_slots=["age"])
        self.assertEqual(response["disclosed"], ["age"])
        self.assertEqual(patient.snapshot()["event_log"][-1]["mapping"], "explicit")
        self.assertEqual(patient.respond("药名是什么？", requested_slots=[])["classification"], "unmatched")

    def test_budget_and_target_stop_do_not_disclose_remaining_events(self):
        spec = patient_spec()
        spec["max_assistant_turns"] = 3
        spec["events"] = [correction(after=["age"])]
        patient = PatientSimulator(spec)
        patient.opening()
        patient.respond("有没有发热？")
        patient.respond("有没有过敏？")
        response = patient.respond("药名是什么？")
        self.assertEqual(response["classification"], "budget")
        self.assertTrue(response["done"])
        self.assertIsNone(response["content"])
        self.assertEqual(response["disclosed"], [])
        self.assertEqual(patient.snapshot()["not_reached_event_ids"], ["correct-onset"])
        snapshot = patient.snapshot()
        self.assertIsNone(patient.respond("药名是什么？")["content"])
        self.assertEqual(patient.snapshot(), snapshot)
        stopped = PatientSimulator(spec)
        stopped.opening()
        response = stopped.respond("年龄是多少？", stop=True)
        self.assertEqual(response["classification"], "stop")
        self.assertEqual(response["stop_reason"], "target_stop")
        self.assertEqual(stopped.snapshot()["disclosed"], ["onset"])

    def test_mutation_isolation_opening_and_reproducibility(self):
        spec = patient_spec()
        original = deepcopy(spec)
        patient = PatientSimulator(spec)
        spec["facts"]["medicine"]["value"] = "CORRUPTED"
        spec["facts"]["medicine"]["answer"] = "CORRUPTED"
        spec["initial_disclosed"].append("medicine")
        opening = patient.opening()
        opening["disclosed"].append("medicine")
        self.assertEqual(patient.opening()["disclosed"], ["onset"])
        snapshot = patient.snapshot()
        snapshot["facts"]["medicine"]["answer"] = "CORRUPTED"
        fresh = PatientSimulator(original)
        fresh.opening()
        for text in ["药名是什么？", "有没有过敏？", "年龄是多少？"]:
            self.assertEqual(patient.respond(text), fresh.respond(text))
        self.assertEqual(patient.snapshot(), fresh.snapshot())


class PatientValidationTests(unittest.TestCase):
    def test_patient_boundary_rejects_hidden_grading_fields_at_every_level(self):
        for location, key in [("root", "criteria"), ("fact", "expected"),
                              ("event", "gold"), ("update", "fault_id")]:
            spec = patient_spec()
            spec["events"] = [correction()]
            target = {"root": spec, "fact": spec["facts"]["age"],
                      "event": spec["events"][0], "update": spec["events"][0]["updates"][0]}[location]
            target[key] = "DO_NOT_LEAK"
            with self.assertRaises(ValueError):
                PatientSimulator(spec)

    def test_invalid_references_counts_and_events_are_rejected(self):
        base = patient_spec()
        base["events"] = [correction()]
        variants = []
        for value in [True, 0, -2, 2.5]:
            spec = deepcopy(base)
            spec["max_assistant_turns"] = value
            variants.append(spec)
        for field, value in [("initial_disclosed", ["missing"]), ("initial_disclosed", ["onset", "onset"])]:
            spec = deepcopy(base)
            spec[field] = value
            variants.append(spec)
        for field, value in [("after_disclosed", ["missing"]), ("min_assistant_turn", 8),
                             ("min_assistant_turn", True), ("kind", "invent_fact"), ("updates", [])]:
            spec = deepcopy(base)
            spec["events"][0][field] = value
            variants.append(spec)
        spec = deepcopy(base)
        spec["events"].append(deepcopy(spec["events"][0]))
        variants.append(spec)
        spec = deepcopy(base)
        spec["events"][0]["updates"][0]["slot"] = "missing"
        variants.append(spec)
        for spec in variants:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                validate_patient_spec(spec)

    def test_unknown_requires_null_and_values_are_finite_json(self):
        for value in [False, "no", []]:
            spec = patient_spec()
            spec["facts"]["allergy"]["value"] = value
            with self.assertRaises(ValueError):
                PatientSimulator(spec)
        for value in [None, float("nan"), float("inf"), (1, 2), {1: "not a JSON key"}]:
            spec = patient_spec()
            spec["facts"]["age"]["value"] = value
            with self.assertRaises(ValueError):
                PatientSimulator(spec)

    def test_respond_requires_opening_and_valid_argument_types(self):
        patient = PatientSimulator(patient_spec())
        with self.assertRaises(ValueError):
            patient.respond("年龄是多少？")
        patient.opening()
        with self.assertRaises(ValueError):
            patient.respond(None)
        with self.assertRaises(ValueError):
            patient.respond("年龄是多少？", stop=1)
        self.assertEqual(patient.snapshot()["assistant_turn_count"], 0)


if __name__ == "__main__":
    unittest.main()
