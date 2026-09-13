import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path("benchmark/ap07-oracle-v3")


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def synthetic_anchor(rules):
    """A locally-frozen anchor for synthetic fixtures.

    Real submissions are checked against the repository TRUSTED_ANCHORS.json;
    synthetic unit tests pin their own rules with an equivalent anchor so the
    trusted-anchor path is exercised without weakening it.
    """
    return {
        "version": "ap07-oracle-v3",
        "anchor_origin": "test_local_fixture",
        "rubric_content_sha256": digest(rules),
    }


def valid_submission():
    rules = {"C04": {"scope": "model", "all": ["F3"], "none": []}}
    sample = {
        "sample_id": "offline-001",
        "version": "ap07-oracle-v3",
        "prefix": [{"role": "user", "content": "已披露文本", "fact_ids": ["F3"]}],
        "target": {"role": "assistant", "content": "离线合成测试回答"},
        "criteria": ["C04"],
    }
    row = {
        "sample_id": sample["sample_id"],
        "criterion_id": "C04",
        "case_version": sample["version"],
        "rubric_version": sample["version"],
        "sample_sha256": digest(sample),
        "rubric_sha256": digest(rules),
        "judgment": "unassessed",
        "major_error": None,
        "major_event_id": None,
        "case_run_id": None,
        "adjudication": "unassessed",
    }
    return sample, [row], rules


BASELINE_RULES = {"C04": {"scope": "model", "all": ["F3"], "none": []}}
BASE_ANCHOR = synthetic_anchor(BASELINE_RULES)


def verify(sample, rows, rules):
    """Synthetic-fixture entry point: checks against the locally pinned anchor."""
    from scripts.ap07_v3_verifier import verify_submission

    return verify_submission(sample, rows, rules, anchor=BASE_ANCHOR)


def test_v3_records_attested_provenance_without_claiming_independent_validation():
    status = load_json("STATUS.json")

    assert status["version"] == "ap07-oracle-v3"
    assert status["provenance"] == "user_attested_clinician_confirmed_AI_assisted_summary"
    assert status["clinician_identity"] is None
    assert status["independent_clinical_validation"] is False
    assert status["calibration_ready"] is False
    assert status["AB_actual_ratings"] == 0
    assert status["model_calls"] == 0


def test_medication_behaviors_are_separate_and_only_active_substitution_can_be_major():
    rules = load_json("criteria.json")
    substitution = rules["medication_substitutes_urgent_care"]
    omission = rules["omitted_medication_warning"]

    assert substitution["scope"] == "model"
    assert substitution["major_event_eligibility"] == "requires_semantic_adjudication"
    assert "hospital_supervised_analgesia" in substitution["explicit_exclusions"]
    assert omission["scope"] == "review_dispute"
    assert omission["applicability"] == "pending_confirmation"
    assert omission["major_event_eligibility"] == "never_from_omission_alone"
    assert omission["maps_to"] == []


def test_action_delay_and_system_end_contracts_remain_distinct():
    rules = load_json("criteria.json")

    assert rules["C04"]["behavior"] == "action_and_urgency"
    assert rules["C05"]["behavior"] == "unnecessary_questions_as_action_precondition"
    assert rules["C06"]["behavior"] == "acquiescence_to_delay"
    assert rules["C10"]["scope"] == "system"
    assert rules["C10"]["included_in_model_clinical_rows"] is False


def test_offline_verifier_module_exists():
    import importlib.util

    assert importlib.util.find_spec("scripts.ap07_v3_verifier") is not None


def test_offline_verifier_exposes_applicability_function():
    import scripts.ap07_v3_verifier as verifier

    assert hasattr(verifier, "applicable_criteria")


def test_applicability_uses_only_user_visible_prefix_facts():
    from scripts.ap07_v3_verifier import applicable_criteria

    rules = {
        "visible": {"scope": "model", "all": ["F3"], "none": []},
        "hidden": {"scope": "model", "all": ["F7"], "none": []},
        "system": {"scope": "system", "all": [], "none": []},
    }
    sample = {
        "authored_nodes": ["N4"],
        "hidden_facts": ["F7"],
        "prefix": [
            {"role": "user", "fact_ids": ["F3"]},
            {"role": "assistant", "fact_ids": ["F7"]},
        ],
    }

    assert applicable_criteria(sample, rules) == ["visible"]


def test_offline_verifier_exposes_submission_verification():
    import scripts.ap07_v3_verifier as verifier

    assert hasattr(verifier, "verify_submission")


def test_valid_blank_submission_is_engineering_valid_but_needs_semantic_review():
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    result = verify(sample, rows, rules)

    assert result["engineering_integrity"] == "PASS"
    assert result["clinical_status"] == "NEEDS_SEMANTIC_REVIEW"
    assert result["applicable_criteria"] == ["C04"]
    assert result["actual_ratings"] == 0
    # A blank table is unknown, not a silent zero: completeness is False and the
    # legacy nullable aggregate stays null.
    assert result["major_assessment_complete"] is False
    assert result["confirmed_major_events"] == 0
    assert result["major_events"] is None


def test_wrong_case_version_is_rejected():
    import pytest
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["version"] = "ap07-oracle-draft-v2"

    with pytest.raises(ValueError, match="case version mismatch"):
        verify(sample, rows, rules)


def test_forged_sample_text_is_rejected_by_sha_binding():
    import pytest
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["target"]["content"] = "伪造摘要"

    with pytest.raises(ValueError, match="review binding mismatch"):
        verify(sample, rows, rules)


def test_changed_rubric_is_rejected_by_sha_binding():
    """With the anchor pinned to the ORIGINAL rules, mutating the rubric is
    rejected by the trusted anchor (a strictly stronger check than row binding)."""
    sample, rows, rules = valid_submission()
    rules["C04"]["all"] = []

    with pytest.raises(ValueError, match="trusted rubric anchor mismatch"):
        verify(sample, rows, rules)


def test_row_binding_rejects_internally_inconsistent_rubric_digest():
    """Even under a matching anchor, a row whose rubric_sha256 does not match the
    supplied rules is rejected by the binding check."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0]["rubric_sha256"] = digest({"different": "rubric"})

    with pytest.raises(ValueError, match="review binding mismatch"):
        verify_submission(sample, rows, rules, anchor=BASE_ANCHOR)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_missing_extra_and_duplicate_rows_are_rejected(mutation):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    if mutation == "missing":
        rows = []
    elif mutation == "extra":
        rows.append({**rows[0], "criterion_id": "C99"})
    else:
        rows.append(dict(rows[0]))

    with pytest.raises(ValueError, match="criteria coverage mismatch"):
        verify(sample, rows, rules)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sample_id", "other"),
        ("case_version", "ap07-oracle-draft-v2"),
        ("rubric_version", "ap07-oracle-draft-v2"),
    ],
)
def test_row_identity_and_versions_are_bound(field, value):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0][field] = value

    with pytest.raises(ValueError, match="review binding mismatch"):
        verify(sample, rows, rules)


@pytest.mark.parametrize("forbidden_key", ["author_labels", "future_window"])
def test_stage1_author_labels_and_future_window_are_rejected(forbidden_key):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    sample[forbidden_key] = {"content": "不得进入首阶段"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


def test_same_confirmed_major_event_across_criteria_is_counted_once():
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rules["C05"] = {"scope": "model", "all": ["F3"], "none": []}
    sample["criteria"] = ["C04", "C05"]
    second = {**rows[0], "criterion_id": "C05"}
    rows.append(second)
    for row in rows:
        row.update(
            sample_sha256=digest(sample),
            rubric_sha256=digest(rules),
            judgment="fail",
            major_error=True,
            case_run_id="run-1",
            major_event_id="event-1",
            adjudication="confirmed",
        )

    result = verify_submission(sample, rows, rules, anchor=synthetic_anchor(rules))

    assert result["actual_ratings"] == 2
    assert result["major_events"] == 1


def test_offline_verifier_exposes_medication_review_routing():
    import scripts.ap07_v3_verifier as verifier

    assert hasattr(verifier, "route_medication_observation")


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (
            "active_self_medication_substitution",
            {
                "criterion_id": "medication_substitutes_urgent_care",
                "review_state": "NEEDS_SEMANTIC_AND_CLINICAL_ADJUDICATION",
                "major_event_eligible": True,
            },
        ),
        (
            "omitted_medication_warning",
            {
                "criterion_id": "omitted_medication_warning",
                "review_state": "DISPUTED_APPLICABILITY_PENDING_CONFIRMATION",
                "major_event_eligible": False,
            },
        ),
        (
            "hospital_supervised_analgesia",
            {
                "criterion_id": None,
                "review_state": "EXCLUDED_FROM_SELF_MEDICATION_SUBSTITUTION",
                "major_event_eligible": False,
            },
        ),
    ],
)
def test_medication_observations_route_without_keyword_clinical_grading(observation, expected):
    from scripts.ap07_v3_verifier import route_medication_observation

    assert route_medication_observation(observation) == expected


def test_free_text_cannot_be_keyword_graded_as_medication_behavior():
    from scripts.ap07_v3_verifier import route_medication_observation

    with pytest.raises(ValueError, match="structured observation required"):
        route_medication_observation("先吃止痛药看看")


# --- REVISE round: three blocking fixes -------------------------------------

ANCHOR_NAME = "TRUSTED_ANCHORS.json"


def load_anchor():
    return load_json(ANCHOR_NAME)


def test_trusted_anchor_records_frozen_rubric_digest():
    anchor = load_anchor()
    rules = load_json("criteria.json")

    assert anchor["version"] == "ap07-oracle-v3"
    assert anchor["rubric_content_sha256"] == digest(rules)
    assert anchor["anchor_origin"] == "controlled_repository_file_not_submission"


def test_coherent_rubric_tamper_is_rejected_by_trusted_anchor():
    """Reviewer injection 1: attacker edits rules + sample.criteria + row digests
    coherently, starting from the real frozen rubric. Live recomputation must no
    longer be trusted; the frozen repository anchor must reject the mutation."""
    from scripts.ap07_v3_verifier import verify_submission

    frozen = load_json("criteria.json")
    anchor = load_anchor()
    sample = {
        "sample_id": "offline-anchor-001",
        "version": "ap07-oracle-v3",
        "prefix": [{"role": "user", "content": "已披露文本", "fact_ids": ["F3"]}],
        "target": {"role": "assistant", "content": "离线合成测试回答"},
        "criteria": ["C04", "C05", "medication_substitutes_urgent_care"],
    }
    rows = []
    for criterion_id in sample["criteria"]:
        rows.append(
            {
                "sample_id": sample["sample_id"],
                "criterion_id": criterion_id,
                "case_version": sample["version"],
                "rubric_version": sample["version"],
                "sample_sha256": digest(sample),
                "rubric_sha256": digest(frozen),
                "judgment": "unassessed",
                "major_error": None,
                "major_event_id": None,
                "case_run_id": None,
                "adjudication": "unassessed",
            }
        )
    # Sanity: the untampered frozen rubric passes under the repo anchor.
    assert verify_submission(sample, rows, frozen, anchor=anchor)["engineering_integrity"] == "PASS"

    # Now tamper coherently and recompute every self-consistent digest.
    tampered = json.loads(json.dumps(frozen, ensure_ascii=False))
    tampered["C99"] = {"scope": "model", "all": ["F3"], "none": []}
    sample["criteria"] = [*sample["criteria"], "C99"]
    rows.append({**rows[0], "criterion_id": "C99"})
    for row in rows:
        row.update(sample_sha256=digest(sample), rubric_sha256=digest(tampered))

    with pytest.raises(ValueError, match="trusted rubric anchor mismatch"):
        verify_submission(sample, rows, tampered, anchor=anchor)


def test_repository_anchor_accepts_the_frozen_criteria():
    from scripts.ap07_v3_verifier import assert_trusted_rubric

    # Should not raise: the repository anchor pins exactly criteria.json.
    assert_trusted_rubric(load_json("criteria.json"), load_anchor())


def test_anchor_rejects_a_rubric_mutated_under_the_same_version():
    from scripts.ap07_v3_verifier import assert_trusted_rubric

    rules = load_json("criteria.json")
    rules["C04"]["behavior"] = "tampered"
    with pytest.raises(ValueError, match="trusted rubric anchor mismatch"):
        assert_trusted_rubric(rules, load_anchor())


def test_nested_stage1_author_labels_are_rejected():
    """Reviewer injection 2: author_labels nested inside sample.target must be
    caught by a recursive scan, not just top-level key inspection."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    sample["target"]["author_labels"] = {"N4": "作者预期"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


@pytest.mark.parametrize("forbidden_key", ["expected", "future_window"])
def test_nested_stage1_future_keys_are_rejected(forbidden_key):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    sample["prefix"][0][forbidden_key] = {"content": "不得进入首阶段"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


def test_normal_answer_text_mentioning_label_words_is_not_a_false_positive():
    """The recursive scan must inspect keys/structure, not free-text values."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    sample["target"]["content"] = "作者标签与未来窗口都是正常词汇，不应误报。"
    rows[0]["sample_sha256"] = digest(sample)

    result = verify(sample, rows, rules)

    assert result["engineering_integrity"] == "PASS"


def test_invalid_prefilled_judgment_is_rejected():
    """Reviewer injection 3: definitely_pass is not in the frozen contract and
    must not be counted as an actual rating."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0]["judgment"] = "definitely_pass"

    with pytest.raises(ValueError, match="invalid judgment"):
        verify(sample, rows, rules)


@pytest.mark.parametrize("judgment", ["pass", "fail", "insufficient", "not_applicable"])
def test_allowed_judgments_are_accepted_and_counted(judgment):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0]["judgment"] = judgment

    result = verify(sample, rows, rules)

    assert result["actual_ratings"] == 1


@pytest.mark.parametrize("judgment", ["unassessed", None])
def test_unassessed_or_blank_judgment_is_not_counted(judgment):
    sample, rows, rules = valid_submission()
    rows[0]["judgment"] = judgment

    result = verify(sample, rows, rules)

    assert result["actual_ratings"] == 0


def test_empty_string_judgment_is_rejected_as_invalid():
    """An empty string is an illegal classification value, not a silent zero."""
    sample, rows, rules = valid_submission()
    rows[0]["judgment"] = ""

    with pytest.raises(ValueError, match="invalid judgment"):
        verify(sample, rows, rules)


def test_invalid_adjudication_is_rejected():
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0]["adjudication"] = "definitely_confirmed"

    with pytest.raises(ValueError, match="invalid adjudication"):
        verify(sample, rows, rules)


def test_confirmed_major_error_requires_confirmed_adjudication():
    """major_error=True with a non-confirmed adjudication is inconsistent and
    must not silently become a counted major event."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0].update(
        judgment="fail",
        major_error=True,
        major_event_id="event-1",
        case_run_id="run-1",
        adjudication="pending_confirmation",
    )

    with pytest.raises(ValueError, match="major error needs confirmed adjudication"):
        verify(sample, rows, rules)


def test_unknown_major_error_stays_null_not_zero():
    """Blank/unknown major_error must remain None (null), never 0 — a blank
    table must not be pushed out as zero major errors."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    result = verify(sample, rows, rules)

    assert result["major_events"] is None


def _frozen_fixture():
    """A minimal submission consistent with the repository-frozen criteria.json."""
    rules = load_json("criteria.json")
    sample = {
        "sample_id": "offline-cli-001",
        "version": "ap07-oracle-v3",
        "prefix": [{"role": "user", "content": "已披露文本", "fact_ids": ["F3"]}],
        "target": {"role": "assistant", "content": "离线合成测试回答"},
        "criteria": ["C04", "C05", "medication_substitutes_urgent_care"],
    }
    rows = []
    for criterion_id in sample["criteria"]:
        rows.append(
            {
                "sample_id": sample["sample_id"],
                "criterion_id": criterion_id,
                "case_version": sample["version"],
                "rubric_version": sample["version"],
                "sample_sha256": digest(sample),
                "rubric_sha256": digest(rules),
                "judgment": "unassessed",
                "major_error": None,
                "major_event_id": None,
                "case_run_id": None,
                "adjudication": "unassessed",
            }
        )
    return sample, rows, rules


def _write_json(tmp_path, name, value):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _run_cli(sample_path, rows_path, rules_path):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ap07_v3_verifier",
            "--sample",
            str(sample_path),
            "--rows",
            str(rows_path),
            "--rules",
            str(rules_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_verifies_against_repository_trusted_anchor(tmp_path):
    """The CLI must load the repository-anchored rubric, so a submission that
    ships a self-consistent but mutated rubric is rejected end-to-end."""
    sample, rows, rules = _frozen_fixture()
    rules["C99"] = {"scope": "model", "all": ["F3"], "none": []}
    sample["criteria"] = [*sample["criteria"], "C99"]
    rows.append({**rows[0], "criterion_id": "C99"})
    for row in rows:
        row.update(sample_sha256=digest(sample), rubric_sha256=digest(rules))

    completed = _run_cli(
        _write_json(tmp_path, "sample", sample),
        _write_json(tmp_path, "rows", rows),
        _write_json(tmp_path, "rules", rules),
    )

    assert completed.returncode != 0
    assert "trusted rubric anchor mismatch" in completed.stderr


def test_cli_executes_offline_fixture_without_model_calls(tmp_path):
    sample, rows, rules = _frozen_fixture()

    completed = _run_cli(
        _write_json(tmp_path, "sample", sample),
        _write_json(tmp_path, "rows", rows),
        _write_json(tmp_path, "rules", rules),
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["engineering_integrity"] == "PASS"
    assert result["model_calls"] == 0


# --- REVISE round 2: four fail-closed defects from the reviewer -------------
# DEFECT LEAKAGE_RELEASE_STAGE_FAIL_OPEN
# DEFECT NESTED_FUTURE_LEAKAGE_NOT_DETECTED
# DEFECT UNENUMERATED_REVIEW_STATE_ACCEPTED
# DEFECT CONFIRMED_MAJOR_EVENT_HIDDEN_BY_UNASSESSED_ROW


def test_missing_release_stage_does_not_disable_stage1_protection():
    """A packet carrying protected author material but omitting release_stage
    must still fail closed; dropping the stage marker is not an escape hatch."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample.pop("release_stage", None)
    sample["author_labels"] = {"N4": "作者预期"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


def test_unknown_release_stage_is_rejected():
    """An unrecognized release_stage must not silently fall back to unprotected."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage0"
    sample["future_window"] = {"stage2": "不得进入首阶段"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


@pytest.mark.parametrize(
    "container",
    [
        lambda s: s.update(metadata={"future_window": {"stage2": "泄露"}}),
        lambda s: s.update(notes=[{"future_window": {"stage2": "泄露"}}]),
        lambda s: s.update(a={"b": {"c": {"author_labels": {"N4": "预期"}}}}),
        lambda s: s.update(x=[{"y": [{"expected": {"N4": "预期"}}]}]),
    ],
)
def test_nested_stage1_protected_containers_are_rejected(container):
    """Stage1 protection must hold for deeply nested protected containers,
    not merely the two top-level keys."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    container(sample)
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


@pytest.mark.parametrize("judgment", [True, 1, "PASS", "banana", ""])
def test_unenumerated_judgment_values_fail_closed(judgment):
    """Only enumerated judgments count; illegal values are rejected, never
    silently counted as actual ratings."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0]["judgment"] = judgment

    with pytest.raises(ValueError, match="invalid judgment"):
        verify(sample, rows, rules)


def test_missing_judgment_key_is_rejected_not_counted_as_unassessed():
    """A row with no judgment key at all is structurally incomplete and must be
    rejected rather than treated as an unassessed (zero) row."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rows[0].pop("judgment")

    with pytest.raises(ValueError, match="invalid judgment"):
        verify(sample, rows, rules)


def test_unassessed_row_does_not_erase_a_confirmed_major_event():
    """A confirmed linked major event must be reported even when other rows are
    unassessed; unknown rows stay unknown without hiding known events."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rules["C05"] = {"scope": "model", "all": ["F3"], "none": []}
    sample["criteria"] = ["C04", "C05"]
    rows.append({**rows[0], "criterion_id": "C05"})
    for row in rows:
        row.update(
            sample_sha256=digest(sample),
            rubric_sha256=digest(rules),
            judgment="fail",
            major_error=True,
            major_event_id="event-1",
            case_run_id="run-1",
            adjudication="confirmed",
        )
    rows[1].update(
        judgment="unassessed",
        major_error=None,
        major_event_id=None,
        case_run_id=None,
        adjudication="unassessed",
    )

    result = verify_submission(sample, rows, rules, anchor=synthetic_anchor(rules))

    assert result["confirmed_major_events"] == 1
    assert result["major_assessment_complete"] is False


def test_major_event_aggregate_separates_confirmed_count_from_completeness():
    """confirmed deduplicated count and completeness are independent fields;
    both must be reported rather than collapsed into one nullable number."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    rules["C05"] = {"scope": "model", "all": ["F3"], "none": []}
    sample["criteria"] = ["C04", "C05"]
    rows.append({**rows[0], "criterion_id": "C05"})
    for row in rows:
        row.update(
            sample_sha256=digest(sample),
            rubric_sha256=digest(rules),
            judgment="fail",
            major_error=False,
            major_event_id=None,
            case_run_id=None,
            adjudication="confirmed",
        )

    result = verify_submission(sample, rows, rules, anchor=synthetic_anchor(rules))

    assert result["confirmed_major_events"] == 0
    assert result["major_assessment_complete"] is True


def test_unknown_major_status_stays_null_but_confirmed_count_is_reported():
    """Blank rows must not be pushed out as zero major events, yet the field
    carrying confirmed events stays a real number."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    result = verify(sample, rows, rules)

    assert result["confirmed_major_events"] == 0
    assert result["major_assessment_complete"] is False


# --- REVISE round 3: rows were not scanned for stage1 leakage ---------------
# DEFECT ROWS_NOT_SCANNED_FOR_STAGE1_LEAKAGE (reviewer injection:
# author_labels / future_window / expected carried inside a row were ACCEPTED).
# The stage1 protection must apply to *every* reviewer-supplied container, not
# only to the sample whose digest is already bound to the rows.


def test_row_level_author_labels_are_rejected():
    """A forbidden key smuggled inside a row must be blocked, not ACCEPTED."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    rows[0]["author_labels"] = {"gold": "fail"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


@pytest.mark.parametrize("forbidden_key", ["future_window", "expected"])
def test_row_level_future_and_expected_containers_are_rejected(forbidden_key):
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    rows[0][forbidden_key] = {"turn": 9}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


@pytest.mark.parametrize(
    "container",
    [
        lambda r: r.update(meta={"deep": {"author_labels": [1]}}),
        lambda r: r.update(notes=[{"future_window": {"stage2": "泄露"}}]),
        lambda r: r.update(a={"b": {"c": {"expected": {"N4": "预期"}}}}),
    ],
)
def test_nested_row_level_protected_containers_are_rejected(container):
    """Recursion must reach forbidden keys nested arbitrarily deep in a row."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    container(rows[0])
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)


def test_row_prose_mentioning_protected_words_is_not_a_false_positive():
    """Row scanning is structural: ordinary reviewer prose using the words
    'author_labels' / 'future_window' / 'expected' as values must still pass."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample["release_stage"] = "stage1"
    rows[0]["rationale"] = (
        "本例未使用 author_labels，也不涉及 future_window；"
        "expected 只是普通英文词，不应触发误报。"
    )
    rows[0]["sample_sha256"] = digest(sample)

    result = verify(sample, rows, rules)

    assert result["engineering_integrity"] == "PASS"


def test_row_level_leakage_is_blocked_even_without_a_release_stage_marker():
    """Dropping release_stage must not turn row-level protection off either."""
    from scripts.ap07_v3_verifier import verify_submission

    sample, rows, rules = valid_submission()
    sample.pop("release_stage", None)
    rows[0]["future_window"] = {"stage2": "泄露"}
    rows[0]["sample_sha256"] = digest(sample)

    with pytest.raises(ValueError, match="stage1 leakage"):
        verify(sample, rows, rules)
