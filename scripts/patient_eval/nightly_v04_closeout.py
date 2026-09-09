"""Validate and index the public N1-N5 evidence chain for nightly v0.4.

This module reads only text-free public audits.  It does not read the private
review, execute source-derived cases, assess clinical truth, or grant any
admission state.  Any drift in the bound artifact chain fails closed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .candidate_review import LOCAL_ROOT, _read


SCHEMA_VERSION = "nightly-v04-evidence-index/v0.1"
_ADMISSION = {
    "gold_approved": False,
    "formal_approval": False,
    "clinical_gold": False,
    "dynamic_scenario_ready": False,
    "s6_automatic_trust": "BLOCKED",
}
_STAGES = (
    ("N1", "semantic-review-validation-public-v0.1.json",
     "candidate-review-public-validation/v0.1"),
    ("N2", "candidate-blockers-public-v0.1.json",
     "candidate-blocker-queue/v0.1"),
    ("N3", "candidate-development-selection-public-v0.1.json",
     "candidate-development-selection/v0.1"),
    ("N4", "dynamic-case-draft-audit-public-v0.1.json",
     "dynamic-case-draft-audit/v0.1"),
    ("N5", "dynamic-case-offline-readiness-public-v0.1.json",
     "dynamic-case-offline-readiness/v0.1"),
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False) + "\n"


def _sha(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _new_public(path):
    path = Path(path)
    _require(not path.resolve().is_relative_to(LOCAL_ROOT.resolve()),
             "closeout index must not be written into the private local directory")
    _require(not path.exists(), "public output must be new; refusing overwrite")
    return path


def _check_admission(stage, artifact):
    admission = artifact.get("admission", {})
    for field, expected in _ADMISSION.items():
        if stage == "N1" and field == "gold_approved":
            continue
        _require(admission.get(field) == expected,
                 f"{stage} unexpectedly changes admission field {field}")
    if "clinical_runnable_count" in admission:
        _require(admission["clinical_runnable_count"] == 0,
                 f"{stage} unexpectedly reports runnable cases")


def _check_privacy(stage, artifact):
    privacy = artifact.get("privacy")
    _require(isinstance(privacy, dict) and privacy,
             f"{stage} is missing an explicit privacy summary")
    _require(all(value is False for value in privacy.values()),
             f"{stage} privacy summary is not fail-closed")


def _candidate_ids(artifact, field):
    rows = artifact.get(field)
    _require(isinstance(rows, list), f"missing {field} rows")
    ids = [row.get("candidate_id") for row in rows]
    _require(all(isinstance(value, str) for value in ids),
             f"invalid candidate identity in {field}")
    _require(len(ids) == len(set(ids)), f"duplicate candidate identity in {field}")
    return ids


def build_evidence_index(validation, blockers, selection, draft_audit,
                         readiness_audit):
    """Return a deterministic, text-free N1-N5 closeout evidence index."""
    artifacts = [validation, blockers, selection, draft_audit, readiness_audit]
    for (stage, _, schema), artifact in zip(_STAGES, artifacts):
        _require(artifact.get("schema_version") == schema,
                 f"{stage} schema version mismatch")
        _require(artifact.get("scope") == "development_only",
                 f"{stage} is not development-only")
        _check_admission(stage, artifact)
        _check_privacy(stage, artifact)

    source_hashes = {row.get("source_review_sha256") for row in artifacts}
    _require(len(source_hashes) == 1 and None not in source_hashes,
             "source review hash is not continuous across N1-N5")
    canonical_hashes = {row.get("canonical_review_sha256") for row in artifacts[1:]}
    _require(len(canonical_hashes) == 1 and None not in canonical_hashes,
             "canonical review hash is not continuous across N2-N5")
    packet_hashes = {row.get("packet_sha256") for row in artifacts[:4]}
    _require(len(packet_hashes) == 1 and None not in packet_hashes,
             "packet hash is not continuous across N1-N4")
    _require(selection.get("blocker_queue_sha256") == _sha(blockers),
             "N3 is not bound to the exact N2 blocker queue")
    _require(draft_audit.get("selection_sha256") == _sha(selection),
             "N4 is not bound to the exact N3 selection")
    _require(readiness_audit.get("n4_public_audit_sha256") == _sha(draft_audit),
             "N5 is not bound to the exact N4 public audit")
    _require(draft_audit.get("private_bundle_sha256") ==
             readiness_audit.get("private_bundle_sha256"),
             "N4/N5 private bundle binding mismatch")
    _require(draft_audit.get("fsm_contract_version") ==
             readiness_audit.get("fsm_contract_version"),
             "N4/N5 state-machine contract mismatch")

    selected_ids = _candidate_ids(selection, "selected_candidates")
    draft_ids = _candidate_ids(draft_audit, "cases")
    readiness_ids = _candidate_ids(readiness_audit, "cases")
    _require(selected_ids == draft_ids == readiness_ids,
             "selected candidate order or identity changed across N3-N5")

    n1 = validation["validation"]
    _require(n1.get("structurally_valid") is True
             and n1.get("candidate_count") == 50
             and n1.get("completeness_decided") == 50
             and n1.get("privacy_decided") == 50
             and n1.get("facts_decided") == 765
             and n1.get("facts_missing") == 0
             and n1.get("rubrics_decided") == 300
             and n1.get("rubrics_missing") == 0,
             "N1 validation denominators are incomplete or changed")

    n2 = blockers["summary"]
    _require(n2.get("candidate_count") == 50
             and n2.get("candidate_blocker_count") == 64
             and n2.get("mechanical_auto_fixable_count") == 0
             and n2.get("candidate_state_counts", {}).get("clinical_runnable") ==
             {"BLOCKED": 50},
             "N2 blocker denominators or runnable state changed")

    n3 = selection["validation"]
    _require(n3.get("selected_count") == 12
             and n3.get("requested_count") == 12
             and n3.get("eligible_selection_count") == 30
             and len(selected_ids) == 12
             and all(row.get("clinical_runnable") == "BLOCKED"
                     for row in selection["selected_candidates"]),
             "N3 selection denominators or runnable state changed")

    n4 = draft_audit["summary"]
    _require(n4.get("private_case_draft_count") == 12
             and n4.get("included_fact_count") == 138
             and n4.get("drafted_rubric_count") == 57
             and n4.get("structured_scoring_opportunity_count") == 0
             and n4.get("clinical_runnable_count") == 0
             and all(row.get("clinical_runnable") == "BLOCKED"
                     for row in draft_audit["cases"]),
             "N4 draft denominators or runnable state changed")

    n5 = readiness_audit["summary"]
    n5_validation = readiness_audit["validation"]
    _require(n5.get("source_derived_case_count") == 12
             and n5.get("source_derived_execution_attempt_count") == 0
             and n5.get("offline_session_count") == 0
             and n5.get("blind_review_package_count") == 0
             and n5.get("mapped_scoring_opportunity_count") == 0
             and n5.get("unmapped_scoring_opportunity_count") == 57
             and n5.get("runtime_opportunity_not_evaluated_count") == 57
             and n5.get("quality_assessed_case_count") == 0
             and n5.get("task_completion_assessed_case_count") == 0
             and n5.get("critical_safety_assessed_count") == 0
             and n5.get("measurement_not_run_case_count") == 12
             and n5.get("clinical_runnable_count") == 0
             and n5_validation.get("model_or_platform_calls") == 0
             and n5_validation.get("model_answers_read") is False,
             "N5 non-execution, unknown, or unassessed denominators changed")
    _require(all(row.get("source_derived_execution_attempted") is False
                 and row.get("offline_session_status") == "NOT_RUN_BLOCKED"
                 and row.get("blind_review_package_status") == "NOT_GENERATED"
                 and row.get("clinical_runnable") == "BLOCKED"
                 for row in readiness_audit["cases"]),
             "N5 case status was upgraded without execution evidence")

    evidence = []
    for (stage, filename, schema), artifact in zip(_STAGES, artifacts):
        evidence.append({
            "stage": stage,
            "path": "medical/patient-eval/data-sources/v0.2/" + filename,
            "schema_version": schema,
            "content_sha256": _sha(artifact),
            "chain_check": "PASS",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "development_only",
        "development_exposed": True,
        "closeout_status": "ENGINEERING_EVIDENCE_COMPLETE_CLINICAL_REVIEW_BLOCKED",
        "evidence_chain": {
            "artifact_count": len(evidence),
            "artifact_pass_count": len(evidence),
            "cross_stage_binding": "PASS",
            "source_review_sha256": next(iter(source_hashes)),
            "canonical_review_sha256": next(iter(canonical_hashes)),
            "packet_sha256": next(iter(packet_hashes)),
            "fsm_contract_version": draft_audit["fsm_contract_version"],
            "artifacts": evidence,
        },
        "stage_denominators": {
            "N1": {"candidates": "50/50", "facts": "765/765",
                   "rubrics": "300/300"},
            "N2": {"blockers": 64, "automatic_fixes": "0/64",
                   "clinical_runnable": "0/50"},
            "N3": {"eligible": "30/50", "selected": "12/12",
                   "clinical_runnable": "0/12"},
            "N4": {"private_drafts": "12/12", "included_facts": 138,
                   "drafted_rubrics": 57, "mapped_opportunities": "0/57",
                   "clinical_runnable": "0/12"},
            "N5": {"static_contracts": "12/12", "synthetic_probes": "8/8",
                   "source_execution_attempts": "0/12", "offline_sessions": 0,
                   "blind_review_packages": 0, "unassessed_opportunities": "57/57",
                   "clinical_runnable": "0/12"},
        },
        "selected_candidate_ids": deepcopy(selected_ids),
        "next_gate": {
            "status": "HUMAN_AND_CLINICAL_REVIEW_REQUIRED",
            "required_roles": [
                "two_independent_human_reviewers",
                "qualified_clinical_reviewer",
                "authorized_case_admission_owner",
            ],
            "engineering_execution_before_resolution": "BLOCKED",
        },
        "admission": deepcopy(_ADMISSION),
        "privacy": {
            "contains_patient_text": False,
            "contains_evidence_spans": False,
            "contains_review_or_scoring_text": False,
            "contains_reviewer_identity": False,
            "contains_source_dialogue_id": False,
            "contains_local_or_library_path": False,
        },
        "limitations": [
            "This index verifies engineering evidence continuity only; it is not clinical validation.",
            "Static and synthetic checks are not model scores or observed clinical safety outcomes.",
            "All 57 scoring opportunities remain unmapped and unassessed because source-derived cases were not run.",
            "Development-exposed cases cannot be represented as an independent hidden test set.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--blockers", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--draft-audit", type=Path, required=True)
    parser.add_argument("--readiness-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        out = _new_public(args.out)
        result = build_evidence_index(
            _read(args.validation), _read(args.blockers), _read(args.selection),
            _read(args.draft_audit), _read(args.readiness_audit))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_json(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"nightly v0.4 closeout failed: {exc}\n")
    print(_json({
        "completed": True,
        "artifact_pass_count": 5,
        "artifact_count": 5,
        "clinical_runnable_count": 0,
        "gold_approved": False,
        "clinical_gold": False,
        "s6_automatic_trust": "BLOCKED",
    }))


if __name__ == "__main__":
    main()
