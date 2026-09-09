"""Synthetic integration checks for source-review preparation and provenance."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.patient_eval.candidate_review import (
    LOCAL_ROOT, _digest, build_review_packet, compare_reviews, prepare, validate_review,
)
from scripts.patient_eval.source_intake import COMMIT, audit_dialogues


def source_fixture():
    return [{"dialogue": "synthetic-source", "information": [
        {"turn": 10, "role": "patient", "sentence": "有发热", "actions": [
            {"text": "发热", "range": [1, 2], "intent": "Inform", "slot": "synthetic", "value1": "", "value2": ""}]},
        {"turn": 20, "role": "doctor", "sentence": "请核对是否发热", "actions": []},
        {"turn": 30, "role": "patient", "sentence": "更正，没有发热", "actions": [
            {"text": "发热", "range": [5, 6], "intent": "Inform", "slot": "synthetic", "value1": "", "value2": ""}]},
    ]}]


def packet_fixture():
    return build_review_packet(source_fixture(), ["synthetic-source"], {"synthetic": True})


def include_first(packet):
    packet["reviewer_id"] = "synthetic-reviewer-a"
    fact = packet["items"][0]["review"]["facts"][0]
    fact.update(decision="include", is_patient_assertion=True, polarity="present", subject="self",
                time="unknown", manual_groundsignal_slot="fever", disclosure_policy="initial",
                reason="synthetic source assertion reviewed", evidence_spans=[
                    {"turn_id": "r0001", "start": 1, "end": 3, "text": "发热"}])
    return fact


class CandidateReviewTests(unittest.TestCase):
    def test_blank_packets_are_valid_incomplete_and_never_approved(self):
        packet = packet_fixture()
        before = deepcopy(packet)
        result = validate_review(packet, deepcopy(packet))
        self.assertEqual(packet, before)
        self.assertTrue(result["structurally_valid"])
        self.assertEqual(result["counts"]["facts_missing"], 2)
        self.assertEqual(result["counts"]["rubrics_missing"], 6)
        self.assertEqual(result["counts"]["privacy_decided"], 0)
        for flag in ("formal_approval", "clinical_gold", "dynamic_scenario_ready"):
            self.assertIs(result[flag], False)

    def test_changed_source_is_rejected_even_if_attacker_recomputes_hash(self):
        original = packet_fixture()
        changed = deepcopy(original)
        changed["items"][0]["turns"][0]["content"] = "合成篡改内容"
        changed["packet_sha256"] = _digest(changed)
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_review(original, changed)

    def test_upstream_proposals_and_original_turn_ids_are_immutable(self):
        original = packet_fixture()
        for field in ("turn_id", "source_turn_id", "source_turn_index"):
            changed = deepcopy(original)
            changed["items"][0]["turns"][0][field] = "tampered"
            with self.assertRaisesRegex(ValueError, "immutable"):
                validate_review(original, changed)
        changed = deepcopy(original)
        changed["items"][0]["fact_draft"]["fact_candidates"][0]["upstream_annotation"]["intent"] = "Other"
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_review(original, changed)

    def test_fact_and_rubric_order_static_flags_and_ids_cannot_change(self):
        original = packet_fixture()
        mutations = [
            lambda review: review["facts"].reverse(),
            lambda review: review["facts"][0].update(fact_id="unknown"),
            lambda review: review["rubrics"][0].update(critical=True),
            lambda review: review["rubrics"][0].update(required=1),
            lambda review: review["rubrics"].reverse(),
        ]
        for mutate in mutations:
            changed = deepcopy(original)
            mutate(changed["items"][0]["review"])
            with self.assertRaises(ValueError):
                validate_review(original, changed)

    def test_included_fact_requires_patient_evidence_from_original_turn(self):
        original = packet_fixture()
        valid = deepcopy(original)
        fact = include_first(valid)
        result = validate_review(original, valid)
        self.assertEqual(result["counts"]["facts_decided"], 1)
        for span in [
            {"turn_id": "r0002", "start": 6, "end": 8, "text": "发热"},
            {"turn_id": "r0003", "start": 5, "end": 7, "text": "发热"},
            {"turn_id": "r0001", "start": 0, "end": 2, "text": "发热"},
            {"turn_id": "r0001", "start": True, "end": 3, "text": "发热"},
        ]:
            changed = deepcopy(valid)
            changed["items"][0]["review"]["facts"][0]["evidence_spans"] = [span]
            with self.assertRaises(ValueError):
                validate_review(original, changed)
        fact["is_patient_assertion"] = False
        with self.assertRaisesRegex(ValueError, "assertion"):
            validate_review(original, valid)

    def test_future_disclosure_and_future_correction_are_rejected_even_in_drafts(self):
        original = packet_fixture()
        review = deepcopy(original)
        review["items"][0]["review"]["facts"][1]["disclosure_policy"] = "initial"
        with self.assertRaisesRegex(ValueError, "future"):
            validate_review(original, review)
        review = deepcopy(original)
        facts = review["items"][0]["review"]["facts"]
        facts[0]["correction_of_candidate_id"] = facts[1]["fact_id"]
        with self.assertRaisesRegex(ValueError, "earlier"):
            validate_review(original, review)

    def test_partial_draft_keeps_missing_status_but_still_validates_values(self):
        original = packet_fixture()
        review = deepcopy(original)
        review["items"][0]["review"]["facts"][0]["subject"] = "self"
        review["items"][0]["review"]["rubrics"][0]["anchors"]["1"] = "draft wording"
        result = validate_review(original, review)
        self.assertEqual(result["counts"]["facts_missing"], 2)
        review["items"][0]["review"]["facts"][0]["evidence_spans"] = [{"turn_id": "future", "start": 0, "end": 1, "text": "x"}]
        with self.assertRaisesRegex(ValueError, "unknown turn"):
            validate_review(original, review)

    def test_nonblank_decision_requires_real_declared_reviewer_and_reason(self):
        original = packet_fixture()
        review = deepcopy(original)
        item = review["items"][0]["review"]["completeness"]
        item.update(decision="usable", reason="synthetic review", evidence_turn_ids=["r0001"])
        with self.assertRaisesRegex(ValueError, "reviewer_id"):
            validate_review(original, review)
        review["reviewer_id"] = "synthetic-reviewer"
        item["reason"] = ""
        with self.assertRaisesRegex(ValueError, "reason"):
            validate_review(original, review)

    def test_privacy_clearance_needs_full_turn_review_and_redaction_needs_confirmed_spans(self):
        original = packet_fixture()
        review = deepcopy(original)
        review["reviewer_id"] = "synthetic-reviewer"
        privacy = review["items"][0]["review"]["privacy"]
        privacy.update(decision="reviewed_no_identifiers", reason="checked synthetic content", checked_turn_ids=["r0001"])
        with self.assertRaisesRegex(ValueError, "every original turn"):
            validate_review(original, review)
        privacy["checked_turn_ids"] = ["r0001", "r0002", "r0003"]
        validate_review(original, review)
        privacy["decision"] = "needs_redaction"
        with self.assertRaisesRegex(ValueError, "confirmed identifier spans"):
            validate_review(original, review)

    def test_on_question_and_scheduled_disclosure_need_explicit_trigger(self):
        original = packet_fixture()
        review = deepcopy(original)
        fact = include_first(review)
        fact["disclosure_policy"] = "on_question"
        with self.assertRaisesRegex(ValueError, "ask_patterns"):
            validate_review(original, review)
        fact["ask_patterns"] = ["是否发热"]
        validate_review(original, review)
        fact["disclosure_policy"] = "scheduled"
        with self.assertRaisesRegex(ValueError, "condition"):
            validate_review(original, review)
        fact["disclosure_condition"] = "synthetic event after first question"
        validate_review(original, review)

    def test_critical_rubric_requires_independent_serious_error_definition(self):
        original = packet_fixture()
        review = deepcopy(original)
        review["reviewer_id"] = "synthetic-reviewer"
        rubric = review["items"][0]["review"]["rubrics"][3]
        rubric.update(decision="drafted", applicability="applicable", description="synthetic rubric",
                      anchors={"0": "missed", "1": "partial", "2": "complete"},
                      opportunity={"trigger": "visible risk cue", "deadline": "next answer"}, reason="synthetic review")
        with self.assertRaisesRegex(ValueError, "serious error"):
            validate_review(original, review)
        rubric["serious_error_definition"] = "synthetic independent safety criterion"
        validate_review(original, review)

    def test_comparison_requires_distinct_reviewers_and_blank_denominators_are_null(self):
        original = packet_fixture()
        with self.assertRaisesRegex(ValueError, "distinct"):
            compare_reviews(original, deepcopy(original), deepcopy(original))
        a, b = deepcopy(original), deepcopy(original)
        a["reviewer_id"], b["reviewer_id"] = "synthetic-a", "synthetic-b"
        result = compare_reviews(original, a, b)
        self.assertEqual(result["fields"]["facts.decision"]["paired_decided"], 0)
        self.assertIsNone(result["fields"]["facts.decision"]["agreement_rate"])
        self.assertEqual(result["fields"]["facts.decision"]["missing_either"], 2)
        b["reviewer_id"] = " SYNTHETIC-A "
        with self.assertRaisesRegex(ValueError, "distinct"):
            compare_reviews(original, a, b)

    def test_comparison_counts_actual_disagreement_and_never_invents_model_scores(self):
        original = packet_fixture()
        a, b = deepcopy(original), deepcopy(original)
        a["reviewer_id"], b["reviewer_id"] = "synthetic-a", "synthetic-b"
        a["items"][0]["review"]["facts"][0].update(decision="exclude", reason="synthetic not asserted")
        b["items"][0]["review"]["facts"][0].update(decision="uncertain", reason="synthetic ambiguous")
        result = compare_reviews(original, a, b)
        stats = result["fields"]["facts.decision"]
        self.assertEqual(stats["paired_decided"], 1)
        self.assertEqual(stats["conflicts"], 1)
        self.assertEqual(stats["agreement_rate"], 0)
        self.assertNotIn("score", result)
        self.assertEqual(result["conflicts"][0]["candidate_id"], "C0001")

    def test_equal_decisions_do_not_hide_different_rubric_content(self):
        original = packet_fixture()
        a, b = deepcopy(original), deepcopy(original)
        a["reviewer_id"], b["reviewer_id"] = "synthetic-a", "synthetic-b"
        for packet in (a, b):
            packet["items"][0]["review"]["rubrics"][3].update(
                decision="drafted", applicability="applicable", description="synthetic risk rule",
                anchors={"0": "missed", "1": "partial", "2": "complete"},
                opportunity={"trigger": "visible cue", "deadline": "next answer"},
                serious_error_definition="synthetic safety definition", reason="synthetic review")
        rubric_b = b["items"][0]["review"]["rubrics"][3]
        rubric_b["anchors"] = {"2": "complete", "1": "partial", "0": "missed"}
        same = compare_reviews(original, a, b)
        self.assertEqual(same["draft_content_comparison"]["differences"], [])
        rubric_b["anchors"]["0"] = "different anchor"
        rubric_b["opportunity"]["deadline"] = "another deadline"
        rubric_b["serious_error_definition"] = "different safety definition"
        result = compare_reviews(original, a, b)
        self.assertEqual(result["fields"]["rubrics.decision"]["agreement_rate"], 1)
        differences = result["draft_content_comparison"]["differences"]
        self.assertEqual({row["field"] for row in differences}, {
            "rubrics.anchors.0", "rubrics.opportunity.deadline", "rubrics.serious_error_definition"})
        stats = result["draft_content_comparison"]["fields"]["rubrics.anchors.0"]
        self.assertEqual(stats["paired_nonempty"], 1)
        self.assertEqual(stats["not_jointly_applicable"], 5)
        self.assertEqual(stats["different_content"], 1)

    def test_fact_triggers_evidence_and_privacy_spans_enter_content_review_queue(self):
        original = packet_fixture()
        a, b = deepcopy(original), deepcopy(original)
        for packet in (a, b):
            fact = include_first(packet)
            fact.update(disclosure_policy="on_question", ask_patterns=["是否发热"])
            packet["items"][0]["review"]["privacy"].update(
                decision="needs_redaction", checked_turn_ids=["r0001", "r0002", "r0003"],
                reason="synthetic workflow test, not a real identifier claim",
                additional_spans=[{"turn_id": "r0001", "start": 0, "end": 1, "text": "有", "kind": "synthetic"}])
        a["reviewer_id"], b["reviewer_id"] = "synthetic-a", "synthetic-b"
        fact_b = b["items"][0]["review"]["facts"][0]
        fact_b["ask_patterns"] = ["体温情况"]
        fact_b["evidence_spans"] = [{"turn_id": "r0001", "start": 0, "end": 3, "text": "有发热"}]
        b["items"][0]["review"]["privacy"]["additional_spans"] = [
            {"turn_id": "r0001", "start": 1, "end": 3, "text": "发热", "kind": "synthetic"}]
        result = compare_reviews(original, a, b)
        differences = result["draft_content_comparison"]["differences"]
        self.assertEqual({row["field"] for row in differences}, {
            "facts.ask_patterns", "facts.evidence_spans", "privacy.additional_spans"})
        self.assertIsNone(result["draft_content_comparison"]["fields"]["facts.disclosure_condition"]["identical_content_rate"])

    def test_prepare_verifies_data_license_manifest_and_publishes_no_source_text(self):
        LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(source_fixture(), ensure_ascii=False).encode()
        license_bytes = b"synthetic license"
        _, ids = audit_dialogues(source_fixture())
        with tempfile.TemporaryDirectory(dir=LOCAL_ROOT) as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "ReMeDi-base.json").write_bytes(raw)
            (source / "MIT-license.txt").write_bytes(license_bytes)
            (source / "candidate-review-local.json").write_text(json.dumps({"source_commit": COMMIT, "candidate_dialogue_ids": ids}))
            with patch("scripts.patient_eval.candidate_review.verify_payload") as verify:
                audit = prepare(source, root / "out")
                self.assertEqual(verify.call_count, 2)
            self.assertEqual((source / "ReMeDi-base.json").read_bytes(), raw)
            original = json.loads((root / "out/original.json").read_text())
            reviewer = json.loads((root / "out/reviewer-A.json").read_text())
            self.assertEqual(reviewer["reviewer_id"], "")
            validate_review(original, reviewer)
            self.assertTrue((root / "out/reviewer-B.html").exists())
            serialized = json.dumps(audit, ensure_ascii=False)
            self.assertNotIn("有发热", serialized)
            self.assertNotIn("synthetic-source", serialized)
            self.assertNotIn("C0001", serialized)
            self.assertEqual(audit["similarity_configuration"]["threshold"], 0.85)
            self.assertEqual(audit["similarity_configuration"]["threshold_status"], "uncalibrated_review_cue")
            self.assertIn("privacy_scanner", audit["algorithm_versions"])
            self.assertIn("ReMeDi-base.json", audit["source_file_sha256"])
            (source / "candidate-review-local.json").write_text(json.dumps({"source_commit": COMMIT, "candidate_dialogue_ids": []}))
            with patch("scripts.patient_eval.candidate_review.verify_payload"):
                with self.assertRaisesRegex(ValueError, "selection"):
                    prepare(source, root / "bad")
            self.assertFalse((root / "bad").exists())
            with self.assertRaisesRegex(ValueError, "new"):
                prepare(source, root / "out")

    def test_public_output_is_rejected_before_source_read(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.patient_eval.candidate_review.verify_payload") as verify:
                with self.assertRaisesRegex(ValueError, "ignored"):
                    prepare(Path(directory) / "source", Path(directory) / "public")
                verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
