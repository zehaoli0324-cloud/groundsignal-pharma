from copy import deepcopy
import json
import unittest

from scripts.patient_eval.candidate_similarity import audit_candidate_similarity


def candidate(identifier, *patient_texts, doctor="共有的医生模板，不能影响患者相似度"):
    turns = [{"role": "patient", "content": content} for content in patient_texts]
    turns.append({"role": "doctor", "content": doctor})
    return {"candidate_id": identifier, "turns": turns}


class CandidateSimilarityTests(unittest.TestCase):
    def test_normalised_exact_patient_turns_and_no_text_output(self):
        records = [candidate("C1", "ＡＢＣ 甲乙丙"), candidate("C2", "abc甲乙丙", doctor="不同模板")]
        original = deepcopy(records)
        result = audit_candidate_similarity(records)
        self.assertEqual(result["exact_pair_count"], 1)
        self.assertEqual(result["near_duplicate_pairs"][0]["jaccard"], 1)
        self.assertEqual(result["near_duplicate_pairs"][0]["match_type"], "exact")
        self.assertNotIn("甲乙丙", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("模板", json.dumps(result, ensure_ascii=False))
        self.assertEqual(records, original)

    def test_high_lexical_overlap_is_near_not_claimed_semantic_match(self):
        result = audit_candidate_similarity([
            candidate("C1", "为了测试程序这是人工构造的一段患者表达今天比昨天明显好一些"),
            candidate("C2", "为了测试程序这是人工构造的一段患者表达今天比昨天明显好一点"),
        ])
        self.assertEqual(result["near_pair_count"], 1)
        self.assertGreaterEqual(result["near_duplicate_pairs"][0]["jaccard"], 0.85)
        self.assertEqual(result["threshold_status"], "uncalibrated_review_cue")

    def test_doctor_boilerplate_does_not_create_match(self):
        result = audit_candidate_similarity([
            candidate("C1", "苹果香蕉"), candidate("C2", "台灯电脑"),
        ])
        self.assertEqual(result["near_duplicate_pairs"], [])
        self.assertEqual(result["compared_pair_count"], 1)

    def test_empty_patient_data_is_missing_not_identical(self):
        result = audit_candidate_similarity([
            candidate("C1"), candidate("C2", " \t\n"),
            candidate("C3", "甲乙丙"), candidate("C4", "丁戊己"),
        ])
        self.assertEqual(result["candidate_count"], 4)
        self.assertEqual(result["eligible_candidate_count"], 2)
        self.assertEqual(result["possible_pair_count"], 6)
        self.assertEqual(result["compared_pair_count"], 1)
        self.assertEqual(result["skipped_pair_count"], 5)
        self.assertEqual(result["missing_patient_candidate_ids"], ["C1", "C2"])
        self.assertEqual(result["near_duplicate_pairs"], [])

    def test_transitive_group_does_not_assert_all_pairs_match(self):
        result = audit_candidate_similarity([
            candidate("C1", "abc"), candidate("C2", "abc", "xyz"), candidate("C3", "xyz"),
        ], threshold=0.5)
        self.assertEqual(len(result["near_duplicate_pairs"]), 2)
        group = result["source_group_suggestions"][0]
        self.assertEqual(group["candidate_ids"], ["C1", "C2", "C3"])
        self.assertFalse(group["pairwise_complete"])
        self.assertEqual(group["direct_pair_count"], 2)
        self.assertEqual(group["possible_pair_count"], 3)
        self.assertEqual(group["relation"], "transitive_similarity_component")

    def test_turn_order_ignored_by_jaccard_but_not_exact_identity(self):
        result = audit_candidate_similarity([
            candidate("C1", "abc", "xyz"), candidate("C2", "xyz", "abc"),
        ])
        pair = result["near_duplicate_pairs"][0]
        self.assertEqual(pair["jaccard"], 1)
        self.assertEqual(pair["match_type"], "near")

    def test_short_turns_fallback_and_no_cross_turn_grams(self):
        result = audit_candidate_similarity([
            candidate("C1", "甲"), candidate("C2", "甲"), candidate("C3", "甲乙"),
        ])
        self.assertEqual(result["exact_pair_count"], 1)
        self.assertEqual(result["near_pair_count"], 0)
        result = audit_candidate_similarity([
            candidate("C1", "ab", "c"), candidate("C2", "abc"),
        ])
        self.assertEqual(result["near_duplicate_pairs"], [])

    def test_threshold_bounds_nan_bool_and_types(self):
        records = [candidate("C1", "abc"), candidate("C2", "xyz")]
        self.assertEqual(len(audit_candidate_similarity(records, threshold=0)["near_duplicate_pairs"]), 1)
        self.assertEqual(audit_candidate_similarity(records, threshold=1)["near_duplicate_pairs"], [])
        for threshold in (True, False, -0.1, 1.1, float("nan"), float("inf"), "0.85", None):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                audit_candidate_similarity(records, threshold=threshold)

    def test_malformed_records_and_duplicate_ids(self):
        bad_inputs = [
            None, {}, [None], [{}], [{"candidate_id": "", "turns": []}],
            [{"candidate_id": "C1", "turns": "text"}],
            [{"candidate_id": "C1", "turns": ["text"]}],
            [{"candidate_id": "C1", "turns": [{"role": "user", "content": "abc"}]}],
            [{"candidate_id": "C1", "turns": [{"role": "patient", "content": None}]}],
            [candidate("C1", "abc"), candidate("C1", "xyz")],
        ]
        for records in bad_inputs:
            with self.subTest(records=records), self.assertRaises(ValueError):
                audit_candidate_similarity(records)

    def test_empty_collection_and_stable_output_order(self):
        self.assertEqual(audit_candidate_similarity([])["possible_pair_count"], 0)
        records = [candidate("C3", "abc"), candidate("C1", "abc"), candidate("C2", "abc")]
        result = audit_candidate_similarity(records)
        self.assertEqual(result, audit_candidate_similarity(list(reversed(records))))
        self.assertTrue(result["source_group_suggestions"][0]["pairwise_complete"])
        self.assertEqual(result["possible_pair_count"], 3)


if __name__ == "__main__":
    unittest.main()
