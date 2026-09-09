import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from scripts.patient_eval.extraction import VisibleFactExtractor
from scripts.patient_eval.study import make_schedule, run_dialogue, run_study
from scripts.patient_eval.transport import ChatClient


def scenario():
    return {
        "scenario_id": "onset.clear", "family_id": "onset", "variant": "clear",
        "protocol_id": "test-protocol", "source": "synthetic", "split": "development",
        "criteria": [{"id": "HIDDEN_CRITERION_CANARY", "expected": "HIDDEN_GOLD_CANARY"}],
        "patient": {
            "initial_user_message": "是否发热不清楚。", "initial_disclosed": ["fever"],
            "facts": {
                "fever": {"value": None, "status": "unknown", "answer": "是否发热不清楚。", "ask_patterns": ["发热"]},
                "onset": {"value": "昨天", "status": "confirmed", "answer": "症状开始时间是昨天。", "ask_patterns": ["开始时间", "什么时候开始"]},
                "private": {"value": "HIDDEN_VALUE_CANARY", "status": "confirmed", "answer": "HIDDEN_ANSWER_CANARY", "ask_patterns": ["绝不会问的私有槽"]},
            },
            "events": [{"id": "HIDDEN_EVENT_CANARY", "kind": "correction", "after_disclosed": ["onset"],
                        "min_assistant_turn": 2, "content": "更正，症状开始时间是今天。",
                        "updates": [{"slot": "onset", "value": "今天", "status": "confirmed", "answer": "症状开始时间是今天。"}]}],
            "max_assistant_turns": 4, "closing_message": "谢谢。",
        },
    }


class RecordingClient:
    platform = "local/test-target"
    model = "test-target"

    def __init__(self):
        self.requests = []

    def public_config(self):
        return {"model": self.model, "platform": self.platform, "max_tokens": 800, "temperature": 0}

    def __call__(self, messages):
        self.requests.append(copy.deepcopy(messages))
        # Deliberately includes a false assistant claim: extractor must never
        # absorb it as a user observation.
        content = "症状开始时间是明天。什么时候开始？"
        return {"content": content, "error": None, "attempts": [{"attempt": 1, "error": None, "elapsed_seconds": 0}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}}


class ExtractionTests(unittest.TestCase):
    def test_unknown_and_negative_are_separate_and_unknown_can_resolve(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "是否发热不清楚。")
        self.assertEqual(parser.snapshot()["facts"]["fever"]["status"], "unknown")
        self.assertIsNone(parser.snapshot()["facts"]["fever"]["value"])
        parser.observe("u2", "没有发热。")
        fact = parser.snapshot()["facts"]["fever"]
        self.assertIs(fact["value"], False)
        self.assertEqual(fact["history"][-1]["supersedes"], "u1")

    def test_explicit_correction_supersedes_but_bare_disagreement_conflicts(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "服药时间是昨天早上。")
        parser.observe("u2", "服药时间是今天早上。")
        self.assertEqual(parser.snapshot()["facts"]["medication_time"]["status"], "conflict")
        parser.observe("u3", "更正，刚才说错了，服药时间是昨晚。")
        fact = parser.snapshot()["facts"]["medication_time"]
        self.assertEqual((fact["value"], fact["status"]), ("昨晚", "confirmed"))
        self.assertEqual(fact["history"][-1]["supersedes"], "u2")

    def test_unsupported_double_negation_question_and_hedge_do_not_create_facts(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "不是没有发热。可能没有发热。服药时间是可能昨晚。是否发热？没说清楚。")
        self.assertEqual(parser.snapshot()["facts"], {})
        self.assertEqual(len(parser.snapshot()["unparsed"]), 5)

    def test_proxy_identity_correction_and_subject_qualified_unknown(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "我是替父亲问的。母亲是否服药不清楚。")
        parser.observe("u2", "更正，刚才说错了，我是替妈妈问的。")
        facts = parser.snapshot()["facts"]
        self.assertEqual(facts["patient_subject"]["value"], "mother")
        self.assertEqual(facts["mother.medication_taken"]["status"], "unknown")
        self.assertNotIn("medication_taken", facts)

    def test_within_turn_conflict_is_not_silently_last_value_wins(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "没有发热，有发热。")
        self.assertNotIn("fever", parser.snapshot()["facts"])
        self.assertEqual(parser.snapshot()["unparsed"][-1]["reason"], "within_turn_conflict")

    def test_question_or_wrong_teach_back_does_not_become_confirmed_fact(self):
        parser = VisibleFactExtractor()
        parser.observe("u1", "是否发热不清楚。")
        parser.observe("u2", "发热？没有发热？服药时间是昨天？服药时间是昨晚，对吗？")
        self.assertEqual(parser.snapshot()["facts"]["fever"]["status"], "unknown")
        self.assertNotIn("medication_time", parser.snapshot()["facts"])

    def test_question_particles_without_punctuation_preserve_sentence_scope(self):
        for question in ("服药时间是昨天吗", "服药时间是昨天，对吗", "服药时间是昨天，对不对",
                         "服药时间是昨天呢", "服药时间是昨天么", "服药时间是否是昨天"):
            with self.subTest(question=question):
                parser = VisibleFactExtractor()
                parser.observe("u1", question)
                self.assertNotIn("medication_time", parser.snapshot()["facts"])
                self.assertEqual(parser.snapshot()["unparsed"][-1]["reason"], "question_not_declaration")
        parser = VisibleFactExtractor()
        parser.observe("u1", "没有发热。服药时间是昨天吗")
        self.assertIs(parser.snapshot()["facts"]["fever"]["value"], False)
        self.assertNotIn("medication_time", parser.snapshot()["facts"])
        parser.observe("u2", "是否服药不清楚。")
        self.assertEqual(parser.snapshot()["facts"]["medication_taken"]["status"], "unknown")


class StudyTests(unittest.TestCase):
    def test_dynamic_disclosure_and_correction_use_only_legal_user_text(self):
        target = RecordingClient()
        session = run_dialogue(scenario(), target, "state_augmented")
        requests = json.dumps(target.requests, ensure_ascii=False)
        self.assertNotIn("HIDDEN_", requests)
        self.assertTrue(all(set(message) == {"role", "content"} for request in target.requests for message in request))
        fact = session["harness_state"]["facts"]["symptom_onset"]
        self.assertEqual(fact["value"], "今天")
        self.assertNotIn("明天", json.dumps(session["harness_state"], ensure_ascii=False))
        self.assertEqual(session["observability"], "black_box")
        self.assertEqual(session["trace"], [])
        self.assertEqual(session["observations"], [])
        self.assertIsNone(session["metadata"]["task_success"])
        self.assertEqual(session["metadata"]["termination_reason"], "turn_budget")
        self.assertEqual(session["metadata"]["fired_event_ids"], ["HIDDEN_EVENT_CANARY"])
        self.assertEqual(session["turns"][-1]["role"], "assistant")

    def test_both_arms_preserve_complete_history_and_match_output_budget(self):
        targets = [RecordingClient(), RecordingClient()]
        sessions = [run_dialogue(scenario(), target, arm) for target, arm in zip(targets, ("baseline", "state_augmented"))]
        for target, session in zip(targets, sessions):
            for index, messages in enumerate(target.requests):
                actual = [message for message in messages if message["role"] != "system"]
                expected = [{"role": turn["role"], "content": turn["content"]} for turn in session["turns"][:2 * index + 1]]
                self.assertEqual(actual, expected)
        self.assertEqual(targets[0].requests[0][0], targets[1].requests[0][0])
        self.assertEqual(sessions[0]["metadata"]["target_config"], sessions[1]["metadata"]["target_config"])
        self.assertEqual(sessions[0]["metadata"]["memory_characters_total"], 0)
        self.assertGreater(sessions[1]["metadata"]["memory_characters_total"], 0)

    def test_failed_questioning_leaves_required_events_unreached(self):
        target = lambda messages: {"content": "好的。", "error": None, "attempts": []}
        session = run_dialogue(scenario(), target, "baseline")
        self.assertEqual(session["metadata"]["unreached_event_ids"], ["HIDDEN_EVENT_CANARY"])
        self.assertNotIn("症状开始时间是昨天", json.dumps(session["turns"], ensure_ascii=False))
        self.assertFalse(session["metadata"]["usage_complete"])

    def test_target_error_and_simulator_error_have_different_denominators(self):
        target = lambda messages: {"content": None, "error": "transport_error", "attempts": []}
        session = run_dialogue(scenario(), target, "baseline")
        self.assertEqual(session["status"], "target_error")
        self.assertEqual(session["turns"][-1]["role"], "user")
        self.assertNotIn("invalid_reason", session)
        with patch("scripts.patient_eval.patient.PatientSimulator.respond", side_effect=RuntimeError("must not leak")):
            invalid = run_dialogue(scenario(), RecordingClient(), "baseline")
        self.assertEqual(invalid["status"], "measurement_invalid")
        self.assertEqual(invalid["invalid_component"], "simulator")
        self.assertNotIn("must not leak", json.dumps(invalid))

    def test_candidate_extractor_and_assembly_failures_count_against_target(self):
        target = RecordingClient()
        with patch("scripts.patient_eval.extraction.VisibleFactExtractor.observe", side_effect=RuntimeError("must not leak")):
            initial = run_dialogue(scenario(), target, "state_augmented")
        self.assertEqual(initial["status"], "target_error")
        self.assertEqual(initial["metadata"]["termination_reason"], "state_extraction_error")
        self.assertEqual(initial["turns"][-1]["role"], "user")
        self.assertEqual(target.requests, [])
        self.assertNotIn("invalid_reason", initial)
        self.assertNotIn("must not leak", json.dumps(initial))

        original = VisibleFactExtractor.observe
        def fail_second(parser, turn_id, text):
            if turn_id == "u2":
                raise RuntimeError("extractor bug")
            return original(parser, turn_id, text)
        with patch.object(VisibleFactExtractor, "observe", new=fail_second):
            later = run_dialogue(scenario(), RecordingClient(), "state_augmented")
        self.assertEqual(later["status"], "target_error")
        self.assertEqual(later["turns"][-1]["turn_id"], "u2")
        with patch("scripts.patient_eval.study._messages", side_effect=RuntimeError("assembly bug")):
            assembly = run_dialogue(scenario(), RecordingClient(), "state_augmented")
        self.assertEqual(assembly["status"], "target_error")
        self.assertEqual(assembly["metadata"]["termination_reason"], "state_assembly_error")

    def test_snapshot_failure_cannot_erase_an_observed_target_failure(self):
        target = lambda messages: {"content": None, "error": "transport_error", "attempts": []}
        with patch("scripts.patient_eval.patient.PatientSimulator.snapshot", side_effect=RuntimeError("snapshot bug")):
            session = run_dialogue(scenario(), target, "baseline")
        self.assertEqual(session["status"], "target_error")
        self.assertEqual(session["metadata"]["termination_reason"], "transport_error")
        self.assertNotIn("invalid_reason", session)
        self.assertFalse(session["metadata"]["simulator_audit_complete"])
        self.assertEqual(session["metadata"]["audit_errors"], ["simulator_snapshot_exception"])
        self.assertEqual(session["metadata"]["unreached_event_ids"], ["HIDDEN_EVENT_CANARY"])
        self.assertEqual(session["harness_trace"][-1]["kind"], "audit_error")

        with patch("scripts.patient_eval.patient.PatientSimulator.snapshot", side_effect=RuntimeError("snapshot bug")):
            completed = run_dialogue(scenario(), RecordingClient(), "baseline")
        self.assertEqual(completed["status"], "measurement_invalid")
        self.assertEqual(completed["metadata"]["termination_reason"], "simulator_snapshot_exception")
        with patch("scripts.patient_eval.patient.PatientSimulator.respond", side_effect=RuntimeError("simulator bug")), \
                patch("scripts.patient_eval.patient.PatientSimulator.snapshot", side_effect=RuntimeError("snapshot bug")):
            invalid = run_dialogue(scenario(), RecordingClient(), "baseline")
        self.assertEqual(invalid["status"], "measurement_invalid")
        self.assertEqual(invalid["metadata"]["termination_reason"], "simulator_exception")
        self.assertEqual(invalid["invalid_reason"], "patient simulator failed")

    def test_one_missing_usage_record_is_not_reported_as_complete(self):
        target = RecordingClient()
        def partial(messages):
            result = target(messages)
            if len(target.requests) == 2:
                result.pop("usage")
            return result
        session = run_dialogue(scenario(), partial, "baseline")
        self.assertIn("prompt_tokens", session["metadata"]["usage"])
        self.assertFalse(session["metadata"]["usage_complete"])

    def test_retry_success_usage_cannot_claim_complete_provider_cost(self):
        target = RecordingClient()
        def retried(messages):
            result = target(messages)
            result["attempts"] = [{"attempt": 1, "error": "transport_error", "elapsed_seconds": 1},
                                  {"attempt": 2, "error": None, "elapsed_seconds": 1}]
            return result
        session = run_dialogue(scenario(), retried, "baseline")
        self.assertTrue(session["metadata"]["successful_response_usage_complete"])
        self.assertFalse(session["metadata"]["usage_complete"])
        self.assertEqual(session["metadata"]["attempt_usage_unknown"], 4)
        self.assertEqual(session["metadata"]["attempts_total"], 8)

    def test_schedule_is_reproducible_and_has_exact_paired_blocks(self):
        scenarios = [{"scenario_id": str(index)} for index in range(6)]
        first = make_schedule(scenarios, repeats=3, seed=11)
        self.assertEqual(first, make_schedule(scenarios, repeats=3, seed=11))
        self.assertNotEqual(first, make_schedule(scenarios, repeats=3, seed=12))
        self.assertEqual(len(first), 36)
        for left, right in zip(first[::2], first[1::2]):
            self.assertEqual(left["scenario_id"], right["scenario_id"])
            self.assertEqual(left["repeat_id"], right["repeat_id"])
            self.assertEqual({left["arm"], right["arm"]}, {"baseline", "state_augmented"})

    def test_checkpoint_hashes_and_existing_directory_fail_before_calls(self):
        suite = {"scope": "development_only", "scenarios": [scenario()]}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "study"
            target = RecordingClient()
            manifest = run_study(suite, target, directory)
            self.assertEqual(manifest["completed_sessions"], 2)
            self.assertEqual(len(list(directory.glob("session-*.json"))), 2)
            self.assertEqual(len(json.loads((directory / "sessions.json").read_text())), 2)
            self.assertEqual(len(manifest["suite_sha256"]), 64)
            self.assertEqual(len(manifest["config_sha256"]), 64)
            count = len(target.requests)
            with self.assertRaises(FileExistsError):
                run_study(suite, target, directory)
            self.assertEqual(count, len(target.requests))

    def test_all_scenarios_preflight_before_first_network_call(self):
        invalid = scenario()
        invalid["scenario_id"] = "invalid"
        invalid["split"] = "sealed_test"
        target = RecordingClient()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                run_study({"scope": "development_only", "scenarios": [scenario(), invalid]}, target, Path(temp) / "study")
            invalid["split"] = "development"
            invalid.pop("family_id")
            with self.assertRaises(ValueError):
                run_study({"scope": "development_only", "scenarios": [scenario(), invalid]}, target, Path(temp) / "study")
        self.assertEqual(target.requests, [])


class TransportTests(unittest.TestCase):
    @patch.dict(os.environ, {"PATIENT_STUDY_KEY": "secret-do-not-record"})
    def test_transport_parameters_and_visible_request_are_exact(self):
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": "示例回复"}}], "usage": {"prompt_tokens": 10}}).encode())
        with patch("urllib.request.OpenerDirector.open", return_value=response) as opener:
            client = ChatClient("https://example.org/v1", "test-model", "PATIENT_STUDY_KEY", max_tokens=600)
            result = client([{"role": "user", "content": "你好"}])
        payload = json.loads(opener.call_args.args[0].data)
        self.assertEqual(payload["max_tokens"], 600)
        self.assertEqual(payload["messages"], [{"role": "user", "content": "你好"}])
        self.assertIsNone(result["error"])
        self.assertNotIn("secret-do-not-record", json.dumps(result) + json.dumps(client.public_config()))

    @patch.dict(os.environ, {"PATIENT_STUDY_KEY": "secret-do-not-record"})
    def test_timeout_is_bounded_schema_does_not_retry_and_redirect_cannot_forward_key(self):
        client = ChatClient("https://example.org/v1", "test-model", "PATIENT_STUDY_KEY", retries=2)
        with patch("urllib.request.OpenerDirector.open", side_effect=TimeoutError()) as opener, patch("time.sleep"):
            result = client([{"role": "user", "content": "你好"}])
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(result["error"], "transport_error")
        with patch("urllib.request.OpenerDirector.open", return_value=io.BytesIO(b'{"choices": []}')) as opener:
            malformed = client([{"role": "user", "content": "你好"}])
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(malformed["error"], "invalid_response_schema")
        from scripts.patient_eval.adapters import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example"))

    def test_missing_key_plain_http_and_bad_budgets_fail_without_calls(self):
        with patch.dict(os.environ, {}, clear=True), patch("urllib.request.OpenerDirector.open") as opener:
            with self.assertRaises(ValueError):
                ChatClient("https://example.org/v1", "model", "MISSING_TEST_KEY")
            with self.assertRaises(ValueError):
                ChatClient("http://example.org/v1", "model", "MISSING_TEST_KEY")
            with self.assertRaises(ValueError):
                ChatClient("https://example.org/v1", "model", "MISSING_TEST_KEY", retries=True)
        opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
