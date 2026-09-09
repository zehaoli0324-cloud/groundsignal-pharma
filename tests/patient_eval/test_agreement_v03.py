"""Developer-authored checks of agreement arithmetic and missing-data handling."""

from copy import deepcopy
import unittest

from scripts.patient_eval.agreement import rater_agreement


class AgreementV03Tests(unittest.TestCase):
    def row(self, item, reviewer, criterion="explanation", rating=None,
            quality="unassessed", opportunity="unassessed", serious=None):
        return {
            "item_id": item, "reviewer_id": reviewer,
            "criterion_id": criterion, "review_version": "patient-review/v0.3",
            "rubric_version": "development/v0.3", "rating": rating,
            "quality_status": quality, "opportunity_status": opportunity,
            "serious_error": serious,
        }

    def test_grouped_kappa_is_primary_even_when_pooled_metric_looks_perfect(self):
        rows = [self.row(f"{criterion}-{i}", reviewer, criterion=criterion,
                         rating=rating, quality="assessed", opportunity="occurred")
                for criterion, rating in (("a", 0), ("b", 2))
                for i in range(2) for reviewer in ("A", "B")]
        result = rater_agreement(rows, "A", "B")
        self.assertEqual(result["linear_weighted_cohen_kappa"], 1)
        self.assertEqual(result["primary_agreement"], "by_criterion")
        self.assertEqual(result["pooled_metric_role"], "diagnostic_only")
        for stats in result["by_criterion"].values():
            self.assertIsNone(stats["linear_weighted_cohen_kappa"])
            self.assertEqual(stats["paired_rated_items"], 2)

    def test_safety_remains_measurable_when_quality_is_unassessed(self):
        rows = [self.row("one", "A", serious=True), self.row("one", "B", serious=False)]
        original = deepcopy(rows)
        result = rater_agreement(rows, "A", "B")
        self.assertEqual(result["rating_coverage"], 0)
        self.assertIsNone(result["exact_agreement"])
        self.assertIsNone(result["linear_weighted_cohen_kappa"])
        self.assertEqual(result["serious_error_paired_items"], 1)
        self.assertEqual(result["serious_error_disagreement_items"], ["one"])
        self.assertEqual(result["serious_error_confusion_matrix_false_true"], [[0, 0], [1, 0]])
        self.assertEqual(result["quality_status_agreement"]["exact_agreement"], 1)
        self.assertEqual(rows, original)

    def test_status_confusion_and_missing_reviewer_are_separate_from_missing_rating(self):
        rows = [
            self.row("one", "A", rating=1, quality="assessed", opportunity="occurred", serious=False),
            self.row("one", "B", quality="not_applicable", opportunity="not_reached", serious=False),
            self.row("two", "A", quality="not_applicable", opportunity="not_applicable"),
        ]
        result = rater_agreement(rows, "A", "B")
        self.assertEqual(result["total_items"], 2)
        self.assertEqual(result["incomplete_items"], ["one", "two"])
        self.assertEqual(result["missing_reviewer_items"], ["two"])
        self.assertEqual(result["serious_error_coverage"], .5)
        self.assertEqual(result["serious_error_exact_agreement"], 1)
        self.assertEqual(result["serious_error_missing_label_items"], ["two"])
        quality = result["quality_status_agreement"]
        self.assertEqual(quality["disagreement_items"], ["one"])
        self.assertEqual(quality["coverage"], .5)
        self.assertEqual(quality["confusion_matrix"], [[0, 0, 1], [0, 0, 0], [0, 0, 0]])
        opportunity = result["opportunity_status_agreement"]
        self.assertEqual(opportunity["confusion_matrix"][0][1], 1)
        self.assertEqual(opportunity["disagreement_items"], ["one"])

    def test_disjoint_reviewer_items_produce_unknown_agreement(self):
        result = rater_agreement([self.row("one", "A"), self.row("two", "B")], "A", "B")
        self.assertIsNone(result["quality_status_agreement"]["exact_agreement"])
        self.assertIsNone(result["opportunity_status_agreement"]["exact_agreement"])
        self.assertIsNone(result["serious_error_exact_agreement"])
        self.assertEqual(result["missing_reviewer_items"], ["one", "two"])

    def test_rejects_mixed_or_unknown_versions_and_changed_item_criterion(self):
        base = [self.row("one", "A"), self.row("one", "B")]
        for changes in ({"review_version": "future"}, {"criterion_id": "other"},
                        {"rubric_version": "another"}, {"criterion_id": ""}):
            rows = deepcopy(base)
            rows[1].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                rater_agreement(rows, "A", "B")
        rows = deepcopy(base)
        for field in ("review_version", "quality_status", "opportunity_status"):
            rows[1].pop(field)
        with self.assertRaises(ValueError):
            rater_agreement(rows, "A", "B")

    def test_rejects_unknown_status_and_inconsistent_quality_rating(self):
        for changes in ({"quality_status": "skipped"}, {"opportunity_status": "absent"},
                        {"quality_status": "assessed"}, {"rating": 2},
                        {"quality_status": "not_applicable", "rating": 0},
                        {"quality_status": "assessed", "rating": True},
                        {"serious_error": 0}):
            rows = [self.row("one", "A"), self.row("one", "B")]
            rows[0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                rater_agreement(rows, "A", "B")

    def test_status_fields_cannot_silently_use_legacy_semantics(self):
        row = self.row("one", "A")
        row.pop("review_version")
        with self.assertRaises(ValueError):
            rater_agreement([row], "A", "B")

    def test_packet_identity_prevents_reused_blind_ids_from_pairing(self):
        rows = [self.row("D0001:explanation", "A"), self.row("D0001:explanation", "B")]
        self.assertEqual(rater_agreement(rows, "A", "B")["review_set_identity_assurance"], "absent")
        rows[0]["review_set_sha256"] = "a" * 64
        for digest in (None, "b" * 64, "invalid"):
            if digest is not None:
                rows[1]["review_set_sha256"] = digest
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                rater_agreement(rows, "A", "B")
        rows[1]["review_set_sha256"] = "a" * 64
        result = rater_agreement(rows, "A", "B")
        self.assertEqual(result["review_set_sha256"], "a" * 64)
        self.assertEqual(result["review_set_identity_assurance"], "matching_supplied_sha256")

    def test_assessed_quality_requires_occurred_opportunity(self):
        for status in ("not_reached", "not_applicable", "unassessed"):
            rows = [self.row("one", "A", rating=1, quality="assessed", opportunity=status),
                    self.row("one", "B")]
            with self.subTest(status=status), self.assertRaises(ValueError):
                rater_agreement(rows, "A", "B")


if __name__ == "__main__":
    unittest.main()
