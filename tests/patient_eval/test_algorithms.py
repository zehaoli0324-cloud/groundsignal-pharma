"""Synthetic engineering checks; none of these fixtures is a clinical case."""

import unittest

from scripts.patient_eval.retrieval import rank_evidence
from scripts.patient_eval.state import FactState


class FactStateTests(unittest.TestCase):
    def test_unknown_is_not_negative_and_requires_explicit_resolution(self):
        state = FactState()
        state.apply({"key": "synthetic_flag", "value": None, "status": "unknown"}, "t1")
        fact = state.snapshot()["facts"]["synthetic_flag"]
        self.assertIsNone(fact["value"])
        self.assertEqual(fact["status"], "unknown")
        with self.assertRaises(ValueError):
            state.apply({"key": "synthetic_flag", "value": False, "status": "confirmed"}, "t2")
        state.apply({"key": "synthetic_flag", "value": False, "status": "confirmed", "supersedes": "t1"}, "t2")
        self.assertIs(state.snapshot()["facts"]["synthetic_flag"]["value"], False)
        with self.assertRaises(ValueError):
            state.apply({"key": "other", "value": False, "status": "unknown"}, "t3")

    def test_correction_preserves_history_and_original_turn(self):
        state = FactState()
        state.apply({"key": "code", "value": "A", "status": "confirmed"}, "t1")
        state.apply({"key": "code", "value": "B", "status": "confirmed", "supersedes": "t1"}, "t2")
        fact = state.snapshot()["facts"]["code"]
        self.assertEqual(fact["value"], "B")
        self.assertEqual([event["value"] for event in fact["history"]], ["A", "B"])
        self.assertEqual(fact["history"][1]["supersedes"], "t1")
        with self.assertRaises(ValueError):
            state.apply({"key": "code", "value": "C", "status": "confirmed", "supersedes": "t1"}, "t3")
        self.assertEqual(state.snapshot()["facts"]["code"], fact)

    def test_conflict_keeps_alternatives_until_explicit_resolution(self):
        state = FactState()
        state.apply({"key": "code", "value": "A", "status": "confirmed"}, "t1")
        with self.assertRaises(ValueError):
            state.apply({"key": "code", "value": "B", "status": "confirmed"}, "t2")
        state.apply({"key": "code", "value": "B", "status": "conflict"}, "t2")
        self.assertEqual(state.snapshot()["facts"]["code"]["alternatives"], ["A", "B"])
        state.apply({"key": "code", "value": "C", "status": "conflict"}, "t3")
        self.assertEqual(state.snapshot()["facts"]["code"]["alternatives"], ["A", "B", "C"])
        state.apply({"key": "code", "value": "B", "status": "confirmed", "supersedes": "t3"}, "t4")
        fact = state.snapshot()["facts"]["code"]
        self.assertNotIn("alternatives", fact)
        self.assertEqual(len(fact["history"]), 4)

    def test_supersedes_cannot_reference_other_key_or_missing_turn(self):
        state = FactState()
        state.apply({"key": "one", "value": "A", "status": "confirmed"}, "t1")
        state.apply({"key": "two", "value": "B", "status": "confirmed"}, "t2")
        for update in [
            {"key": "one", "value": "C", "status": "confirmed", "supersedes": "t2"},
            {"key": "new", "value": "C", "status": "confirmed", "supersedes": "t1"},
            {"key": "two", "value": "C", "status": "confirmed", "supersedes": "missing"},
        ]:
            with self.assertRaises(ValueError):
                state.apply(update, "t3")

    def test_external_mutations_and_repeated_observations(self):
        value = ["visible"]
        state = FactState()
        state.apply({"key": "items", "value": value, "status": "confirmed"}, "t1")
        value.append("hidden")
        first = state.snapshot()
        first["facts"]["items"]["history"].clear()
        state.apply({"key": "items", "value": ["visible"], "status": "confirmed"}, "t2")
        fact = state.snapshot()["facts"]["items"]
        self.assertEqual(fact["value"], ["visible"])
        self.assertEqual(len(fact["history"]), 2)
        with self.assertRaises(ValueError):
            state.apply({"key": "items", "value": ["visible"], "status": "confirmed"}, "t2")


class RetrievalTests(unittest.TestCase):
    def test_chinese_bigrams_and_latin_tokens_change_input_order_ranking(self):
        passages = [
            {"id": "irrelevant", "text": "合成样本 蓝色文件夹"},
            {"id": "partial", "text": "合成标签 alpha"},
            {"id": "relevant", "text": "红色标签 alpha"},
        ]
        ranked = rank_evidence("红色标签 ALPHA", passages)
        self.assertEqual(ranked[0]["id"], "relevant")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        self.assertNotIn("irrelevant", [item["id"] for item in ranked])
        self.assertNotIn("score", passages[0])

    def test_temporal_filter_excludes_high_scoring_stale_and_future(self):
        passages = [
            {"id": "stale", "text": "alpha alpha alpha", "valid_to": "2025-12-31"},
            {"id": "future", "text": "alpha alpha", "valid_from": "2027-01-01"},
            {"id": "current", "text": "alpha beta", "valid_from": "2026-01-01", "valid_to": "2026-12-31"},
        ]
        self.assertEqual(rank_evidence("alpha", passages)[0]["id"], "stale")
        filtered = rank_evidence("alpha", passages, as_of="2026-09-09")
        self.assertEqual([item["id"] for item in filtered], ["current"])
        boundary = rank_evidence("alpha", passages, as_of="2025-12-31")
        self.assertEqual([item["id"] for item in boundary], ["stale"])

    def test_population_is_explicit_hard_filter_not_a_guess(self):
        passages = [
            {"id": "unknown", "text": "alpha alpha alpha"},
            {"id": "other", "text": "alpha alpha", "population": "synthetic-b"},
            {"id": "matching", "text": "alpha", "population": ["synthetic-a", "synthetic-c"]},
            {"id": "universal", "text": "alpha", "population": "all"},
        ]
        self.assertEqual(
            {item["id"] for item in rank_evidence("alpha", passages, population="SYNTHETIC-A")},
            {"matching", "universal"},
        )

    def test_ties_empty_queries_and_determinism(self):
        passages = [{"id": "b", "text": "alpha"}, {"id": "a", "text": "alpha"}]
        self.assertEqual([item["id"] for item in rank_evidence("alpha", passages)], ["a", "b"])
        self.assertEqual(rank_evidence("alpha", passages), rank_evidence("alpha", list(reversed(passages))))
        self.assertEqual(rank_evidence("", passages), [])
        self.assertEqual(rank_evidence("unmatched", passages), [])
        self.assertEqual(rank_evidence("alpha", passages, top_k=0), [])
        self.assertEqual(rank_evidence("alpha", [{"id": "empty", "text": ""}]), [])

    def test_invalid_metadata_fails_instead_of_silent_exclusion(self):
        bad_passages = [
            [{"id": "a", "text": "alpha", "valid_from": "2026-02-30"}],
            [{"id": "a", "text": "alpha", "valid_from": "2026-09-10", "valid_to": "2026-09-09"}],
            [{"id": "a", "text": "alpha"}, {"id": "a", "text": "beta"}],
            [{"id": "a", "text": "alpha", "population": []}],
        ]
        for passages in bad_passages:
            with self.assertRaises(ValueError):
                rank_evidence("alpha", passages)
        for top_k in [-1, True, 1.5]:
            with self.assertRaises(ValueError):
                rank_evidence("alpha", [], top_k=top_k)


if __name__ == "__main__":
    unittest.main()
