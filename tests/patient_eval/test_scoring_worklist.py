from copy import deepcopy
import json
import unittest

from scripts.patient_eval.dynamic_case_drafts import build_dynamic_case_drafts, _sha, _public_case_row
from scripts.patient_eval.scoring_worklist import prepare_worklist
from tests.patient_eval.test_dynamic_case_drafts import draft_fixture, SOURCE_SHA, REVIEW_SHA, PRIVATE_SENTINEL


class ScoringWorklistTests(unittest.TestCase):
    def setUp(self):
        original, review, blockers, selection = draft_fixture()
        self.private, self.audit = build_dynamic_case_drafts(original, review, blockers, selection, SOURCE_SHA, REVIEW_SHA)

    def rebind(self):
        self.audit["private_bundle_sha256"] = _sha(self.private)
        self.audit["cases"] = [_public_case_row(c) for c in self.private["cases"]]

    def test_preserves_existing_drafts_without_creating_review_or_mapping(self):
        before = deepcopy(self.private)
        worksheet, summary = prepare_worklist(self.private, self.audit)
        self.assertEqual(self.private, before)
        self.assertEqual(summary["prepared_draft_rows"], 3)
        self.assertEqual(summary["mapped_opportunities"], 0)
        self.assertEqual(summary["runtime_evaluated"], 0)
        self.assertEqual(summary["independently_reviewed"], 0)
        self.assertFalse(worksheet["admission"]["formal_approval"])
        for row, case in zip(worksheet["rows"], self.private["cases"]):
            self.assertEqual(row["existing_rule_draft"], case["scoring_drafts"][0])
            self.assertIsNone(row["runtime_turn_mapping"]["trigger_turn_id"])
            self.assertIsNone(row["mapping_proposal"]["target_response_policy"])
        worksheet["rows"][0]["existing_rule_draft"]["anchors"]["0"] = "changed"
        self.assertEqual(self.private, before)

    def test_public_summary_does_not_copy_private_text_or_rule_ids(self):
        self.private["cases"][0]["scoring_drafts"][0]["criterion_id"] = PRIVATE_SENTINEL
        self.rebind()
        worksheet, summary = prepare_worklist(self.private, self.audit)
        self.assertIn(PRIVATE_SENTINEL, json.dumps(worksheet))
        self.assertNotIn(PRIVATE_SENTINEL, json.dumps(summary))

    def test_hash_or_case_audit_mismatch_is_rejected(self):
        self.private["cases"][0]["scoring_drafts"][0]["description"] = "changed"
        with self.assertRaisesRegex(ValueError, "digest"):
            prepare_worklist(self.private, self.audit)
        self.rebind()
        self.audit["cases"].reverse()
        with self.assertRaisesRegex(ValueError, "audit mismatch"):
            prepare_worklist(self.private, self.audit)

    def test_admission_upgrade_is_rejected_even_with_updated_digest(self):
        self.private["admission"]["formal_approval"] = True
        self.rebind()
        with self.assertRaises(ValueError):
            prepare_worklist(self.private, self.audit)

    def test_existing_mapping_cannot_be_silently_erased(self):
        self.private["cases"][0]["scoring_drafts"][0]["structured_opportunity"]["trigger_turn"] = "u1"
        self.rebind()
        with self.assertRaisesRegex(ValueError, "mapping"):
            prepare_worklist(self.private, self.audit)

    def test_duplicate_rules_and_unsafe_public_ids_rejected(self):
        self.private["cases"][0]["scoring_drafts"].append(deepcopy(self.private["cases"][0]["scoring_drafts"][0]))
        self.rebind()
        with self.assertRaisesRegex(ValueError, "duplicate criterion"):
            prepare_worklist(self.private, self.audit)
        self.setUp()
        self.private["cases"][0]["candidate_id"] = PRIVATE_SENTINEL
        self.rebind()
        with self.assertRaisesRegex(ValueError, "public case ID"):
            prepare_worklist(self.private, self.audit)


if __name__ == "__main__":
    unittest.main()
