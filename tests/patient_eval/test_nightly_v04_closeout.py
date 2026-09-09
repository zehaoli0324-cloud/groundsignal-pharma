import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.patient_eval.nightly_v04_closeout import build_evidence_index


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "medical" / "patient-eval" / "data-sources" / "v0.2"
FILES = (
    "semantic-review-validation-public-v0.1.json",
    "candidate-blockers-public-v0.1.json",
    "candidate-development-selection-public-v0.1.json",
    "dynamic-case-draft-audit-public-v0.1.json",
    "dynamic-case-offline-readiness-public-v0.1.json",
)


def evidence_fixture():
    return [json.loads((DATA / name).read_text(encoding="utf-8")) for name in FILES]


class NightlyV04CloseoutTest(unittest.TestCase):
    def test_current_public_chain_closes_with_explicit_denominators(self):
        result = build_evidence_index(*evidence_fixture())
        self.assertEqual(result["evidence_chain"]["artifact_pass_count"], 5)
        self.assertEqual(result["stage_denominators"]["N5"]["unassessed_opportunities"], "57/57")
        self.assertEqual(result["stage_denominators"]["N5"]["source_execution_attempts"], "0/12")
        self.assertEqual(result["admission"]["s6_automatic_trust"], "BLOCKED")
        self.assertEqual(result["next_gate"]["engineering_execution_before_resolution"], "BLOCKED")

    def test_admission_upgrade_fails_closed(self):
        artifacts = evidence_fixture()
        artifacts[3]["admission"]["clinical_gold"] = True
        with self.assertRaisesRegex(ValueError, "admission field clinical_gold"):
            build_evidence_index(*artifacts)

    def test_tampered_cross_stage_hash_fails_closed(self):
        artifacts = evidence_fixture()
        artifacts[2]["blocker_queue_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact N2 blocker queue"):
            build_evidence_index(*artifacts)

    def test_candidate_identity_drift_fails_closed(self):
        artifacts = evidence_fixture()
        artifacts[4]["cases"] = list(reversed(artifacts[4]["cases"]))
        artifacts[4]["n4_public_audit_sha256"] = artifacts[4]["n4_public_audit_sha256"]
        with self.assertRaisesRegex(ValueError, "candidate order or identity"):
            build_evidence_index(*artifacts)

    def test_unrun_case_cannot_be_upgraded_to_assessed(self):
        artifacts = evidence_fixture()
        artifacts[4]["summary"]["quality_assessed_case_count"] = 1
        with self.assertRaisesRegex(ValueError, "non-execution, unknown, or unassessed"):
            build_evidence_index(*artifacts)

    def test_extra_input_text_is_not_copied_to_public_index(self):
        artifacts = evidence_fixture()
        sentinel = "SENSITIVE_INPUT_SENTINEL"
        artifacts[0]["limitations"].append(sentinel)
        result = build_evidence_index(*artifacts)
        self.assertNotIn(sentinel, json.dumps(result, ensure_ascii=False))

    def test_cli_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "already-exists.json"
            output.write_text("{}", encoding="utf-8")
            command = [sys.executable, "-m", "scripts.patient_eval.nightly_v04_closeout"]
            for option, filename in zip(
                    ("--validation", "--blockers", "--selection", "--draft-audit", "--readiness-audit"),
                    FILES):
                command.extend((option, str(DATA / filename)))
            command.extend(("--out", str(output)))
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
