#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("import_unverified_interview_corpus.py")
SPEC = importlib.util.spec_from_file_location("interview_importer", MODULE_PATH)
assert SPEC and SPEC.loader
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class ProductManagerParserTest(unittest.TestCase):
    def test_toc_parsing_stops_before_body_duplicate(self) -> None:
        paragraphs = ["标题", "目录"]
        total = 0
        for numeral, section, count in [
            ("一", "甲类", 60),
            ("二", "乙类", 64),
            ("三", "丙类", 1),
        ]:
            paragraphs.append(f"{numeral}、{section}（{count}题） 1")
            for number in range(1, count + 1):
                if numeral == "三" and number == 1:
                    paragraphs.extend(["1.", "跨段问题？", "9"])
                else:
                    paragraphs.append(f"{number}. 问题{total + number}？ {number + 1}")
            total += count
        paragraphs += ["一、甲类（60题）", "1. 正文重复问题？"]
        rows = IMPORTER.parse_product_manager_toc(paragraphs)
        self.assertEqual(125, len(rows))
        self.assertEqual("跨段问题？", rows[-1]["question"])


class HotTopicsParserTest(unittest.TestCase):
    def test_prefers_complete_quoted_question(self) -> None:
        paragraphs = []
        for index, (section, count) in enumerate([
            ("政策改革类", 5),
            ("技术创新类", 4),
            ("公共卫生类", 4),
            ("临床实操类", 3),
            ("医患伦理类", 3),
            ("职业素养类", 4),
        ], 1):
            numeral = "一二三四五六"[index - 1]
            paragraphs.append(f"{numeral}、{section}（{count} 题）")
            for number in range(1, count + 1):
                paragraphs += [
                    f"{number}. 示例题：短标题",
                    "难易度：★★★",
                    f"考官：‘这是{section}第{number}个完整问题吗？’",
                ]
        rows = IMPORTER.parse_hot_topics(paragraphs)
        self.assertEqual(23, len(rows))
        self.assertIn("完整问题", rows[0]["question"])


class QuarantineClassificationTest(unittest.TestCase):
    def test_interview_only_material_is_excluded(self) -> None:
        self.assertTrue(IMPORTER.excluded_from_groundsignal("product_manager_125", "结构化面试", 1))
        self.assertTrue(IMPORTER.excluded_from_groundsignal("hot_topics_23", "职业素养类", 1))
        self.assertFalse(IMPORTER.excluded_from_groundsignal("hot_topics_23", "职业素养类", 4))

    def test_source_version_cannot_be_silently_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            (out_dir / "source-manifest.json").write_text(
                json.dumps({"sources": [{"source_id": "source-a", "sha256": "old"}]}),
                encoding="utf-8",
            )
            with self.assertRaises(PermissionError):
                IMPORTER.refuse_source_version_overwrite(out_dir, {"source-a": "new"})


if __name__ == "__main__":
    unittest.main()
