from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.patient_eval.relations import (DEFAULT_RELATIONS, DEFAULT_SUITE,
                                            _diff, _digest, audit_relations, main)


class PressureRelationTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(DEFAULT_RELATIONS.read_text(encoding="utf-8"))
        self.suite = json.loads(DEFAULT_SUITE.read_text(encoding="utf-8"))

    def audit(self):
        return audit_relations(self.spec, self.suite)

    def redeclare(self, relation, before, after):
        changes = _diff(before, after)
        relation["changed_fields"] = changes
        relation["permitted_changes"] = [{"path": p, "factor_id": relation["controlled_factor"]["id"]}
                                          for p in changes]

    def test_declarations_do_not_claim_model_success_or_extra_families(self):
        original_spec, original_suite = deepcopy(self.spec), deepcopy(self.suite)
        report = self.audit()
        self.assertEqual(report["relation_counts"], {"invariant": 6, "directional": 1,
                                                      "information_insufficient": 1})
        self.assertEqual(report["source_family_count"], 6)
        self.assertFalse(report["model_evaluation_performed"])
        self.assertFalse(report["clinical_approval"])
        self.assertNotIn("success_rate", report)
        self.assertEqual(self.spec, original_spec)
        self.assertEqual(self.suite, original_suite)

    def test_source_fingerprint_prevents_silent_suite_replacement(self):
        self.suite["description"] += "changed"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.audit()

    def test_invariant_rejects_fact_change_even_when_declared_and_unprotected(self):
        relation = self.spec["relations"][0]
        a, b = self.suite["scenarios"][:2]
        b["patient"]["facts"]["person"]["value"] = "家属"
        relation["protected_facts"].remove("/facts/person")
        self.redeclare(relation, a["patient"], b["patient"])
        self.spec["source_suite_sha256"] = _digest(self.suite)
        with self.assertRaisesRegex(ValueError, "false invariant"):
            self.audit()

    def test_invariant_protects_correction_truth_and_trigger_policy(self):
        relation = self.spec["relations"][0]
        a, b = self.suite["scenarios"][:2]
        b["patient"]["events"][0]["min_assistant_turn"] += 1
        self.redeclare(relation, a["patient"], b["patient"])
        self.spec["source_suite_sha256"] = _digest(self.suite)
        with self.assertRaisesRegex(ValueError, "non-surface"):
            self.audit()

    def test_multiple_surface_fields_cannot_hide_as_one_factor(self):
        relation = self.spec["relations"][0]
        a, b = self.suite["scenarios"][:2]
        b["patient"]["events"][1]["content"] += "额外催促"
        self.redeclare(relation, a["patient"], b["patient"])
        self.spec["source_suite_sha256"] = _digest(self.suite)
        with self.assertRaisesRegex(ValueError, "exactly one surface"):
            self.audit()

    def test_actual_fields_and_control_factor_must_be_declared(self):
        relation = self.spec["relations"][0]
        saved = deepcopy(relation)
        relation["changed_fields"] = []
        with self.assertRaisesRegex(ValueError, "actual changes"):
            self.audit()
        self.spec["relations"][0] = saved
        saved["permitted_changes"][0]["factor_id"] = "extra_factor"
        with self.assertRaisesRegex(ValueError, "additional factor"):
            self.audit()

    def test_unknown_criterion_and_unprotected_fact_are_rejected(self):
        relation = self.spec["relations"][0]
        relation["criterion_id"] = "invented.correctness"
        with self.assertRaisesRegex(ValueError, "unknown criterion"):
            self.audit()
        relation["criterion_id"] = "completion.summary"
        relation["protected_facts"].remove("/facts/fever")
        with self.assertRaisesRegex(ValueError, "lacks protection"):
            self.audit()

    def test_developer_fact_change_cannot_claim_frozen_pilot_eligibility(self):
        self.spec["relations"][6]["eligible_for_pilot_comparison"] = True
        with self.assertRaisesRegex(ValueError, "frozen pilot"):
            self.audit()

    def test_two_fact_factors_cannot_hide_in_one_declared_factor(self):
        relation = self.spec["relations"][6]
        pair = relation["developer_pair"]
        pair["variant"]["facts"]["person"]["value"] = "家属"
        relation["protected_facts"].remove("/facts/person")
        self.redeclare(relation, pair["baseline"], pair["variant"])
        with self.assertRaisesRegex(ValueError, "exactly one fact"):
            self.audit()

    def test_fact_change_must_be_visible_and_prior_history_stays_fixed(self):
        relation = self.spec["relations"][6]
        pair = relation["developer_pair"]
        pair["variant"]["visible_prefix"] = deepcopy(pair["baseline"]["visible_prefix"])
        self.redeclare(relation, pair["baseline"], pair["variant"])
        with self.assertRaisesRegex(ValueError, "last-user-message change"):
            self.audit()

    def test_information_removal_requires_unknown_not_another_known_value(self):
        relation = self.spec["relations"][7]
        pair = relation["developer_pair"]
        pair["variant"]["facts"]["onset"] = {"value": "今天早上", "status": "confirmed"}
        self.redeclare(relation, pair["baseline"], pair["variant"])
        with self.assertRaisesRegex(ValueError, "remove previously known"):
            self.audit()

    def test_cli_writes_reviewable_audit_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            with redirect_stdout(io.StringIO()):
                main(["--out", str(path)])
            original = path.read_bytes()
            self.assertEqual(json.loads(original)["relation_count"], 8)
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                main(["--out", str(path)])
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
