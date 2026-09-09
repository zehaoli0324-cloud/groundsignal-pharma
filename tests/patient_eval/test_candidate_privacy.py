"""Invented contact-like strings only; no source patient data or clinical gold."""

import unittest

from scripts.patient_eval.candidate_privacy import redact_spans, scan_text


class CandidatePrivacyTests(unittest.TestCase):
    def test_offsets_are_original_unicode_and_metadata_has_no_captured_value(self):
        text = "🧪合成邮件：demo@example.invalid，电话：+86 138-0000-0000。"
        spans = scan_text(text)
        self.assertEqual([s["kind"] for s in spans], ["email", "mobile"])
        self.assertEqual([text[s["start"]:s["end"]] for s in spans],
                         ["demo@example.invalid", "+86 138-0000-0000"])
        self.assertTrue(all(s["review_required"] for s in spans))
        self.assertNotIn("demo", str(spans))
        self.assertNotIn("138", str(spans))

    def test_clinical_numbers_and_dates_are_preserved(self):
        text = "体温38.5，血压138/86，年龄68岁；2026年9月9日，剂量1.5mg，每日3次。"
        self.assertEqual(scan_text(text), [])
        self.assertEqual(redact_spans(text, []), {"text": text, "replacements": []})
        for numeric in ("123456789012345678", "138000000000", "A13800000000B"):
            self.assertEqual(scan_text(numeric), [])

    def test_national_id_requires_plausible_date_and_exact_boundaries(self):
        # Fabricated structural example; not a real resident identifier.
        fake = "11000020000102001X"
        self.assertEqual([s["kind"] for s in scan_text("合成证件：" + fake)], ["national_id"])
        self.assertEqual(scan_text("11000020001302001X"), [])
        self.assertEqual(scan_text("9" + fake), [])
        self.assertEqual(scan_text(fake + "A"), [])

    def test_contextual_and_url_cues_do_not_include_labels(self):
        text = "姓名：张某某，住址：示例路测试楼，微信号：fixture_user；https://example.invalid/a。"
        spans = scan_text(text)
        self.assertEqual([s["kind"] for s in spans], ["name", "address", "contact_handle", "url"])
        self.assertEqual([text[s["start"]:s["end"]] for s in spans],
                         ["张某某", "示例路测试楼", "fixture_user", "https://example.invalid/a"])
        self.assertEqual(scan_text("张某某描述情况，医生建议观察。"), [])

    def test_redaction_requires_explicit_spans_and_leaves_other_cues(self):
        text = "电话13800000000，邮箱demo@example.invalid，体温38.5。"
        phone = next(s for s in scan_text(text) if s["kind"] == "mobile")
        result = redact_spans(text, [phone])
        self.assertEqual(result["text"], "电话[REDACTED_MOBILE_1]，邮箱demo@example.invalid，体温38.5。")
        self.assertEqual(result["replacements"], [{"start": phone["start"], "end": phone["end"],
                                                  "kind": "mobile", "replacement": "[REDACTED_MOBILE_1]"}])

    def test_repeated_values_have_stable_placeholders_across_messages(self):
        mapping = {}
        first = "13800000000、13800000000、13900000000"
        out = redact_spans(first, scan_text(first), mapping)
        self.assertEqual(out["text"], "[REDACTED_MOBILE_1]、[REDACTED_MOBILE_1]、[REDACTED_MOBILE_2]")
        later = "联系13900000000"
        self.assertEqual(redact_spans(later, scan_text(later), mapping)["text"], "联系[REDACTED_MOBILE_2]")
        self.assertNotIn("13900000000", str(out["replacements"]))

    def test_invalid_and_overlapping_spans_fail_before_mutating_mapping(self):
        for start, end in [(-1, 1), (0, 4), (1, 1), (True, 2), (0, 1.0)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                redact_spans("abc", [{"start": start, "end": end, "kind": "name"}])
        spans = [{"start": 0, "end": 2, "kind": "name"}, {"start": 1, "end": 3, "kind": "name"}]
        mapping = {}
        with self.assertRaisesRegex(ValueError, "overlap"):
            redact_spans("abc", spans, mapping)
        self.assertEqual(mapping, {})
        spans[1]["start"] = 2
        result = redact_spans("abc", list(reversed(spans)))
        self.assertEqual(result["text"], "[REDACTED_NAME_1][REDACTED_NAME_2]")

    def test_malformed_inputs_do_not_coerce_offsets_or_return_raw_mapping_values(self):
        for value in (None, 123):
            with self.assertRaises(ValueError):
                scan_text(value)
        with self.assertRaises(ValueError):
            redact_spans("abc", [{"start": 0, "end": 1, "kind": "BAD KIND"}])
        with self.assertRaisesRegex(ValueError, "placeholder"):
            redact_spans("abc", [{"start": 0, "end": 1, "kind": "name"}], {("name", "a"): "unredacted"})


if __name__ == "__main__":
    unittest.main()
