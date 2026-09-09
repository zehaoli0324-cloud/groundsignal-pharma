"""Synthetic checks for text-free candidate blocker projection."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.patient_eval.candidate_blockers import build_public_blocker_queue
from tests.patient_eval.test_candidate_review import include_first, packet_fixture


SOURCE_SHA = "1" * 64
REVIEW_SHA = "2" * 64
SECRET = "PRIVATE_" + "PATIENT_TEXT_SENTINEL"
WORKSPACE_PREFIX = "/" + "workspace/"
LIBRARY_ID_PREFIX = "lib" + "file_"


def reviewed_packet():
    original = packet_fixture()
    review = deepcopy(original)
    review["reviewer_id"] = "private-reviewer-" + SECRET
    turns = [turn["turn_id"] for turn in review["items"][0]["turns"]]
    review["items"][0]["review"]["privacy"].update(
        decision="reviewed_no_identifiers", checked_turn_ids=turns,
        reason="private privacy reason " + SECRET,
    )
    review["items"][0]["review"]["completeness"].update(
        decision="usable", evidence_turn_ids=["r0001"],
        reason="private completeness reason " + SECRET,
    )
    fact = include_first(review)
    fact["reason"] += SECRET
    return original, review


class CandidateBlockerTests(unittest.TestCase):
    def test_ready_is_development_only_and_never_clinical_admission(self):
        original, review = reviewed_packet()
        result = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["states"]["candidate_selection"], "READY")
        self.assertEqual(candidate["states"]["dynamic_authoring"], "READY")
        self.assertEqual(candidate["states"]["clinical_runnable"], "BLOCKED")
        self.assertFalse(result["admission"]["gold_approved"])
        self.assertFalse(result["admission"]["clinical_gold"])
        self.assertEqual(result["admission"]["s6_automatic_trust"], "BLOCKED")
        self.assertEqual(result["summary"]["observed_feature_counts"]["included_conflict_polarities"], 0)

    def test_all_expected_human_blockers_are_separated_without_auto_fix(self):
        original, review = reviewed_packet()
        human = review["items"][0]["review"]
        human["privacy"].update(
            decision="needs_redaction", reason="private identifier reason " + SECRET,
            additional_spans=[{"turn_id": "r0001", "start": 1, "end": 3, "text": "发热"}],
        )
        human["facts"][0].update(decision="uncertain", reason="private uncertainty " + SECRET)
        later = human["facts"][1]
        later.update(
            decision="include", is_patient_assertion=True, polarity="conflict", subject="self",
            time="unknown", manual_groundsignal_slot="fever", disclosure_policy="scheduled",
            disclosure_condition="synthetic later correction", reason="private correction " + SECRET,
            correction_of_candidate_id=human["facts"][0]["fact_id"],
            evidence_spans=[{"turn_id": "r0003", "start": 5, "end": 7, "text": "发热"}],
        )
        risk = human["rubrics"][3]
        risk.update(
            decision="drafted", applicability="applicable", description="private rule " + SECRET,
            anchors={"0": "miss", "1": "partial", "2": "complete"},
            opportunity={"trigger": "cue", "deadline": "next answer"},
            serious_error_definition="private serious error " + SECRET,
            reason="private rubric reason " + SECRET,
        )
        result = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
        candidate = result["candidates"][0]
        codes = {row["code"] for row in candidate["blockers"]}
        self.assertEqual(codes, {
            "PRIVACY_REVIEW_REQUIRED", "FACT_DECISION_UNCERTAIN",
            "FACT_POLARITY_CONFLICT", "CORRECTION_RELATION_ADJUDICATION",
            "CLINICAL_RUBRIC_ADJUDICATION",
        })
        self.assertTrue(all(row["automatic_fix"] is False for row in candidate["blockers"]))
        self.assertEqual(candidate["states"]["candidate_selection"], "BLOCKED")
        self.assertEqual(candidate["states"]["dynamic_authoring"], "BLOCKED")
        self.assertEqual(result["summary"]["observed_feature_counts"]["included_conflict_polarities"], 1)

    def test_private_text_identity_and_paths_never_enter_public_projection(self):
        original, review = reviewed_packet()
        review["items"][0]["turns"][0]["content"] += SECRET
        original = deepcopy(review)
        original["reviewer_id"] = ""
        for item in original["items"]:
            item["review"] = packet_fixture()["items"][0]["review"]
        from scripts.patient_eval.candidate_review import _digest
        original["packet_sha256"] = _digest(original)
        review["packet_sha256"] = original["packet_sha256"]
        result = build_public_blocker_queue(original, review, SOURCE_SHA, REVIEW_SHA)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn("synthetic-source", serialized)
        self.assertNotIn(review["reviewer_id"], serialized)
        self.assertNotIn(WORKSPACE_PREFIX, serialized)
        self.assertNotIn(LIBRARY_ID_PREFIX, serialized)

    def test_duplicate_or_path_like_public_ids_fail_closed(self):
        original, review = reviewed_packet()
        for bad_id in ("../private", "/absolute", "contains space"):
            changed_original, changed_review = deepcopy(original), deepcopy(review)
            changed_original["items"][0]["candidate_id"] = bad_id
            changed_review["items"][0]["candidate_id"] = bad_id
            from scripts.patient_eval.candidate_review import _digest
            changed_original["packet_sha256"] = _digest(changed_original)
            changed_review["packet_sha256"] = changed_original["packet_sha256"]
            with self.assertRaisesRegex(ValueError, "bounded public identifier"):
                build_public_blocker_queue(changed_original, changed_review, SOURCE_SHA, REVIEW_SHA)

    def test_cli_rejects_wrong_source_hash_without_creating_output(self):
        original, review = reviewed_packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("original.json", original), ("review.json", review)):
                (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            (root / "source.json").write_text("{}", encoding="utf-8")
            output = root / "public.json"
            run = subprocess.run([
                sys.executable, "-m", "scripts.patient_eval.candidate_blockers",
                "--original", str(root / "original.json"), "--review", str(root / "review.json"),
                "--source-review", str(root / "source.json"),
                "--expected-source-sha256", "0" * 64, "--out", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(output.exists())
            self.assertNotIn(str(root), run.stdout)


if __name__ == "__main__":
    unittest.main()
