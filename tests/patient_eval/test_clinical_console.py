"""Synthetic-only regression checks; no patient execution or clinical claims."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import unittest

from scripts.patient_eval.candidate_review import _digest, validate_review
from scripts.patient_eval.clinical_console import (
    ASSETS, FLAGS, demo_packet, independent_packet, render_console, validate_handoff,
)


class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag in {"script", "link", "img", "iframe"}:
            self.links.extend(values[k] for k in ("src", "href") if k in values)


def handoff_fixture(packet):
    return {"schema_version": "clinical-console-handoff/v0.1", "local_only": True,
            "packet_sha256": packet["packet_sha256"], "reviewer_id": packet["reviewer_id"],
            "authority": "self_declared_unsigned_not_approval", "runtime_observations": 0,
            "opportunity_plans": [{"candidate_id": i["candidate_id"], "criterion_id": r["criterion_id"],
                "status": "unreviewed", "trigger": "", "response": "", "deadline": "", "reason": ""}
                for i in packet["items"] for r in i["review"]["rubrics"]], **FLAGS}


class ClinicalConsoleTests(unittest.TestCase):
    def setUp(self):
        self.original = demo_packet()
        self.review = independent_packet(self.original)
        self.review["reviewer_id"] = "reviewer-A"

    def test_blank_independent_packet_is_compatible(self):
        result = validate_review(self.original, self.review)
        self.assertEqual(result["counts"]["facts_missing"], 2)
        self.assertFalse(result["dynamic_scenario_ready"])

    def test_prior_reviews_are_removed_and_source_is_unchanged(self):
        previous = deepcopy(self.review)
        previous["items"][0]["review"]["facts"][0].update(decision="exclude", reason="previous opinion")
        snapshot = deepcopy(previous)
        clean = independent_packet(previous)
        self.assertEqual(previous, snapshot)
        self.assertEqual(clean["reviewer_id"], "")
        self.assertEqual(clean["items"][0]["review"]["facts"][0]["decision"], "unreviewed")
        self.assertEqual(clean["packet_sha256"], previous["packet_sha256"])

    def test_tampered_source_digest_is_rejected(self):
        self.original["items"][0]["turns"][0]["content"] = "changed"
        with self.assertRaises(ValueError):
            render_console(self.original)

    def test_source_script_injection_is_escaped(self):
        self.original["items"][0]["turns"][0]["content"] = '</script><img src="x" onerror="bad()">'
        self.original["packet_sha256"] = _digest(self.original)
        html = render_console(self.original)
        self.assertNotIn('</script><img', html)
        self.assertIn('\\u003c/script\\u003e', html)

    def test_self_contained_page_has_unique_ids_and_no_external_assets(self):
        html = render_console()
        parser = ScriptParser()
        parser.feed(html)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertFalse(parser.links)
        self.assertIn("connect-src 'none'", html)
        self.assertNotIn('__CONSOLE_DATA__', html)
        self.assertIn('"packet": null', html)

    def test_app_does_not_store_or_send_source(self):
        js = ASSETS.joinpath("app.js").read_text()
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "indexedDB", ".innerHTML", "eval("):
            self.assertNotIn(forbidden, js)

    def test_handoff_can_be_incomplete_without_admission(self):
        result = validate_handoff(self.original, self.review, handoff_fixture(self.review))
        self.assertEqual(result["plan_count"], 6)
        self.assertFalse(result["clinical_credentials_verified"])
        self.assertEqual(result["s6_automatic_trust"], "BLOCKED")

    def test_handoff_cannot_claim_approval_or_runtime_results(self):
        for key, value in {**{k: True for k in FLAGS if k != "s6_automatic_trust"},
                           "s6_automatic_trust": "PASS", "runtime_observations": 1,
                           "authority": "clinical_signed"}.items():
            h = handoff_fixture(self.review)
            h[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_handoff(self.original, self.review, h)

    def test_handoff_reviewer_and_source_binding(self):
        for key in ("reviewer_id", "packet_sha256"):
            h = handoff_fixture(self.review)
            h[key] = "different"
            with self.assertRaises(ValueError):
                validate_handoff(self.original, self.review, h)

    def test_handoff_requires_full_unique_rule_set(self):
        for operation in (lambda x: x.pop(), lambda x: x.append(deepcopy(x[0]))):
            h = handoff_fixture(self.review)
            operation(h["opportunity_plans"])
            with self.assertRaises(ValueError):
                validate_handoff(self.original, self.review, h)

    def test_proposed_plan_requires_four_fields(self):
        h = handoff_fixture(self.review)
        row = h["opportunity_plans"][0]
        row["status"] = "proposed"
        with self.assertRaises(ValueError):
            validate_handoff(self.original, self.review, h)
        row.update(trigger="patient event", response="next model response", deadline="before stop", reason="synthetic plan")
        self.assertTrue(validate_handoff(self.original, self.review, h)["structurally_valid"])

    def test_node_core_roundtrip_passes_authoritative_python_validator(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(["node", "tests/patient_eval/clinical_console_core.cjs"],
                                cwd=root, input=json.dumps(self.original), text=True,
                                capture_output=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["checks"], 10)
        validate_review(self.original, data["review"])


if __name__ == "__main__":
    unittest.main()
