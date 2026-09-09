"""Synthetic checks for deterministic development candidate selection."""

from copy import deepcopy
import json
import unittest

from scripts.patient_eval.candidate_blockers import build_public_blocker_queue
from scripts.patient_eval.candidate_review import build_review_packet
from scripts.patient_eval.candidate_selection import build_development_selection


SOURCE_SHA = "3" * 64
REVIEW_SHA = "4" * 64
PRIVATE_SENTINEL = "PRIVATE_" + "PATIENT_SELECTION_SENTINEL"


def selection_fixture(count=5):
    dialogues = []
    for index in range(count):
        marker = chr(ord("A") + index)
        information = [
            {"turn": 1, "role": "patient", "sentence": f"有发热{marker}", "actions": [
                {"text": "发热", "range": [1, 2], "intent": "Inform", "slot": "synthetic", "value1": "", "value2": ""}]},
            {"turn": 2, "role": "doctor", "sentence": "请补充情况", "actions": []},
            {"turn": 3, "role": "patient", "sentence": f"仍发热{marker}", "actions": [
                {"text": "发热", "range": [1, 2], "intent": "Inform", "slot": "synthetic", "value1": "", "value2": ""}]},
        ]
        for extra in range(index):
            information.extend([
                {"turn": 4 + extra * 2, "role": "doctor", "sentence": "继续询问", "actions": []},
                {"turn": 5 + extra * 2, "role": "patient", "sentence": f"补充{marker}{extra}", "actions": []},
            ])
        dialogues.append({"dialogue": f"private-source-{marker}", "information": information})
    original = build_review_packet(
        dialogues, [row["dialogue"] for row in dialogues], {"synthetic": True})
    review = deepcopy(original)
    review["reviewer_id"] = "private-reviewer-" + PRIVATE_SENTINEL
    for index, item in enumerate(review["items"]):
        human = item["review"]
        turns = [turn["turn_id"] for turn in item["turns"]]
        human["privacy"].update(
            decision="reviewed_no_identifiers", checked_turn_ids=turns,
            reason="private privacy " + PRIVATE_SENTINEL,
        )
        human["completeness"].update(
            decision="usable", evidence_turn_ids=["r0001"],
            reason="private completeness " + PRIVATE_SENTINEL,
        )
        first, second = human["facts"][:2]
        first.update(
            decision="include", is_patient_assertion=True, polarity="present", subject="self",
            time="unknown", manual_groundsignal_slot="fever", disclosure_policy="initial",
            reason="private initial " + PRIVATE_SENTINEL,
            evidence_spans=[{"turn_id": "r0001", "start": 1, "end": 3, "text": "发热"}],
        )
        second.update(
            decision="include", is_patient_assertion=True,
            polarity="absent" if index % 2 else "unknown", subject="self", time="later",
            manual_groundsignal_slot="fever", disclosure_policy="on_question",
            ask_patterns=["synthetic question"], reason="private later " + PRIVATE_SENTINEL,
            evidence_spans=[{"turn_id": "r0003", "start": 1, "end": 3, "text": "发热"}],
        )
    blockers = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
    return original, review, blockers


class CandidateSelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_and_capped(self):
        original, review, blockers = selection_fixture()
        first = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=3)
        second = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=3)
        self.assertEqual(first, second)
        self.assertEqual(first["validation"]["selected_count"], 3)
        self.assertEqual(first["decision_reason_counts"]["STRUCTURAL_DIVERSITY_SELECTION"], 3)
        self.assertEqual(first["decision_reason_counts"]["FIXED_SELECTION_CAP"], 2)

    def test_selected_cases_remain_exposed_and_clinically_blocked(self):
        original, review, blockers = selection_fixture()
        result = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=2)
        self.assertTrue(all(row["development_exposed"] for row in result["selected_candidates"]))
        self.assertTrue(all(row["clinical_runnable"] == "BLOCKED" for row in result["selected_candidates"]))
        self.assertFalse(result["admission"]["gold_approved"])
        self.assertFalse(result["admission"]["clinical_gold"])
        self.assertEqual(result["admission"]["s6_automatic_trust"], "BLOCKED")

    def test_tampered_blocker_queue_fails_closed(self):
        original, review, blockers = selection_fixture()
        changed = deepcopy(blockers)
        changed["candidates"][0]["states"]["dynamic_authoring"] = "BLOCKED"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_development_selection(
                original, review, changed, SOURCE_SHA, REVIEW_SHA, requested_count=2)

    def test_private_text_source_ids_and_identity_do_not_enter_manifest(self):
        original, review, blockers = selection_fixture()
        result = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=2)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(PRIVATE_SENTINEL, serialized)
        self.assertNotIn("private-source", serialized)
        self.assertNotIn(review["reviewer_id"], serialized)
        self.assertNotIn("发热", serialized)

    def test_similarity_groups_are_guardrails_not_invented_families(self):
        original, review, blockers = selection_fixture()
        result = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=2)
        audit = result["source_and_similarity_audit"]
        self.assertEqual(audit["family_pair_design"], "UNSUPPORTED_DO_NOT_INVENT")
        self.assertEqual(audit["source_group_suggestion_count"], 0)
        self.assertEqual(audit["selected_unique_source_dialogue_count"], 2)

    def test_missing_initial_disclosure_is_not_filled_from_future_facts(self):
        original, review, _ = selection_fixture()
        fact = review["items"][0]["review"]["facts"][0]
        fact["disclosure_policy"] = "on_question"
        fact["ask_patterns"] = ["synthetic opening question"]
        blockers = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
        result = build_development_selection(
            original, review, blockers, SOURCE_SHA, REVIEW_SHA, requested_count=5)
        self.assertEqual(result["validation"]["dynamic_authoring_gate_ready_count"], 5)
        self.assertEqual(result["validation"]["eligible_selection_count"], 4)
        self.assertEqual(result["validation"]["selected_count"], 4)
        self.assertEqual(result["decision_reason_counts"]["INITIAL_DISCLOSURE_MISSING"], 1)
        self.assertEqual(result["selection_status"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
