from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.clinical_reasoning.development import (
    DevelopmentSession, validate_case, validate_distractor_pair,
)

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "medical/patient-eval/clinical-reasoning-v1/cases"


def load(name="renal"):
    return json.loads((CASES / (name + ".json")).read_text())


class DevelopmentTests(unittest.TestCase):
    def test_both_families_use_same_environment(self):
        for name in ("renal", "anemia"):
            case = load(name)
            validate_case(case)
            env = DevelopmentSession(case)
            query = case["world"]["records"][0]["query"]
            content = case["world"]["records"][0]["content"]
            result = env.step({"action_id": "a1", "kind": "record", "query": query})
            self.assertEqual(result["messages"][-1]["content"], content)
            self.assertEqual(env.report()["outcome"], "unassessed")

    def test_model_projection_hides_future_and_evaluation(self):
        case = load()
        case["evaluation"]["hidden_marker"] = "EVALUATOR_CANARY"
        case["world"]["records"][0]["content"] += " FUTURE_CANARY"
        text = json.dumps(DevelopmentSession(case).model_view(), ensure_ascii=False)
        for forbidden in ("EVALUATOR_CANARY", "FUTURE_CANARY", case["family_id"], case["case_id"]):
            self.assertNotIn(forbidden, text)

    def test_model_view_is_not_mutable_state(self):
        env = DevelopmentSession(load())
        env.model_view()["messages"][0]["content"] = "changed"
        self.assertNotEqual(env.model_view()["messages"][0]["content"], "changed")

    def test_drop_separates_returned_from_delivered(self):
        case = load()
        clean, failed = DevelopmentSession(case), DevelopmentSession(case, fault="drop_record_delivery")
        action = {"action_id": "a1", "kind": "record", "query": case["world"]["records"][0]["query"]}
        clean.step(action)
        view = failed.step(action)
        a, b = clean.operator_trace()[0], failed.operator_trace()[0]
        self.assertEqual(a["returned_content"], b["returned_content"])
        self.assertIsNone(b["delivered_content"])
        self.assertTrue(b["fault_applied"])
        self.assertNotIn(b["returned_content"], json.dumps(view, ensure_ascii=False))
        self.assertEqual(failed.report()["causal_status"], "not_evaluated")

    def test_invalid_action_is_atomic_and_can_retry(self):
        env = DevelopmentSession(load())
        before = env.model_view()
        with self.assertRaises(ValueError):
            env.step({"action_id": "a1", "kind": "record", "query": None})
        self.assertEqual(env.model_view(), before)
        self.assertEqual(env.operator_trace(), [])
        env.step({"action_id": "a1", "kind": "ask", "query": "近期进食与胃肠症状"})
        self.assertEqual(env.report()["actions"], 1)

    def test_unsupported_does_not_become_negative(self):
        env = DevelopmentSession(load())
        result = env.step({"action_id": "a1", "kind": "record", "query": "不存在的资料"})
        self.assertIn("不能据此判断阴性", result["messages"][-1]["content"])
        self.assertEqual(env.operator_trace()[0]["delivery_status"], "unsupported")

    def test_duplicate_action_does_not_increase_count(self):
        env = DevelopmentSession(load())
        action = {"action_id": "a1", "kind": "ask", "query": "近期进食与胃肠症状"}
        env.step(action)
        with self.assertRaises(ValueError):
            env.step(action)
        self.assertEqual(env.report()["actions"], 1)

    def test_budget_exhaustion_is_not_success(self):
        env = DevelopmentSession(load(), action_budget=1)
        env.step({"action_id": "a1", "kind": "record", "query": "未定义主题"})
        self.assertEqual(env.report()["termination"], "action_budget")
        self.assertEqual(env.report()["outcome"], "unassessed")
        with self.assertRaises(ValueError):
            env.step({"action_id": "a2", "kind": "finish", "answer": "完成"})

    def test_finish_is_not_clinical_pass(self):
        env = DevelopmentSession(load())
        env.step({"action_id": "a1", "kind": "finish", "answer": "当前信息不足以定因。"})
        self.assertEqual(env.report()["termination"], "finished")
        self.assertIsNone(env.report()["quality"])
        self.assertIsNone(env.report()["serious_error"])
        self.assertEqual(env.report()["outcome"], "unassessed")

    def test_pair_accepts_only_registered_leaf(self):
        base, variant = load(), load("renal-distractor")
        self.assertTrue(validate_distractor_pair(base, variant)["mechanical_pair_valid"])
        for mutate in (lambda c: c["world"]["records"][0].update(content="changed lab"),
                       lambda c: c["opening"].update(task="another patient"),
                       lambda c: c["evaluation"].update(expected="changed gold"),
                       lambda c: c.update(family_id="different")):
            bad = deepcopy(variant)
            mutate(bad)
            with self.assertRaises(ValueError):
                validate_distractor_pair(base, bad)

    def test_pair_rejects_no_actual_factor_change(self):
        base = load()
        variant = deepcopy(base)
        variant["case_id"] = "another"
        with self.assertRaises(ValueError):
            validate_distractor_pair(base, variant)

    def test_no_self_declared_clinical_admission(self):
        case = load()
        case["clinical_review"] = "approved"
        with self.assertRaises(ValueError):
            DevelopmentSession(case)


if __name__ == "__main__":
    unittest.main()
