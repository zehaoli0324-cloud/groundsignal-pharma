"""Deterministic AP07 v3 offline verifier; never performs clinical grading."""

import argparse
import hashlib
import json
from pathlib import Path

VERSION = "ap07-oracle-v3"

# Frozen classification contract (mirrored in the controlled TRUSTED_ANCHORS.json).
ALLOWED_JUDGMENTS = frozenset({"pass", "fail", "insufficient", "not_applicable", "unassessed"})
ALLOWED_ADJUDICATIONS = frozenset({"confirmed", "pending_confirmation", "unassessed"})
STAGE1_FORBIDDEN_KEYS = frozenset({"author_labels", "future_window", "expected"})
# First-stage protection is the default: a packet is treated as protected unless
# it declares a release_stage that is explicitly known to carry no stage1 content.
KNOWN_RELEASE_STAGES = frozenset({"stage1"})
ANCHOR_NAME = "TRUSTED_ANCHORS.json"


def canonical_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_trusted_anchor(root=None):
    """Load the controlled rubric anchor from a repository file.

    This file is deliberately NOT read from the submission under review: it must
    be the frozen, repository-controlled artifact, so a coherent rewrite of
    rules + sample.criteria + row digests cannot pass.
    """
    base = Path(root) if root is not None else Path(__file__).resolve().parent.parent / "benchmark" / VERSION
    return json.loads((Path(base) / ANCHOR_NAME).read_text(encoding="utf-8"))


def _iter_keys(value):
    """Yield every dict key appearing anywhere in a nested JSON value."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)
    # Scalars are never yielded: the scan inspects keys/structure, not free text,
    # so an answer that merely mentions a forbidden word is not a false positive.


def assert_no_stage1_leakage(*containers):
    """Recursively reject author labels / future-window keys in stage1 content.

    Fail closed: first-stage protection applies by default. A packet is only
    exempt when it declares a release_stage that is explicitly known to be a
    non-stage1 stage; an absent, empty or unrecognized stage marker is treated
    as stage1 rather than as an unprotected packet.

    Every reviewer-supplied container is scanned, not only the sample: a
    protected key smuggled into a row would otherwise be ACCEPTED while the
    sample itself stayed clean. ``containers`` therefore takes one or more
    JSON values; the release_stage marker is read from any mapping that
    declares one.
    """
    stage = None
    for container in containers:
        if isinstance(container, dict) and "release_stage" in container:
            stage = container.get("release_stage")
            break
    if stage is not None and stage not in KNOWN_RELEASE_STAGES:
        # Unknown stage marker: do not let an invented/typo'd stage name disable
        # the protected-content scan.
        leaked = sorted(
            set(key for c in containers for key in _iter_keys(c)) & STAGE1_FORBIDDEN_KEYS
        )
        if leaked:
            raise ValueError(
                f"stage1 leakage: unrecognized release_stage {stage!r} with forbidden keys {leaked}"
            )
        raise ValueError(f"unrecognized release_stage: {stage!r}")
    leaked = sorted(
        set(key for c in containers for key in _iter_keys(c)) & STAGE1_FORBIDDEN_KEYS
    )
    if leaked:
        raise ValueError(f"stage1 leakage: forbidden nested keys {leaked}")


def assert_trusted_rubric(rules, anchor):
    """Reject any rubric whose canonical SHA is not the frozen repository anchor."""
    if anchor.get("version") != VERSION:
        raise ValueError("trusted rubric anchor mismatch: anchor version")
    if canonical_sha256(rules) != anchor.get("rubric_content_sha256"):
        raise ValueError("trusted rubric anchor mismatch: rules were modified outside the frozen contract")



def applicable_criteria(sample, rules):
    visible = {
        fact_id
        for turn in sample.get("prefix", [])
        if turn.get("role") == "user"
        for fact_id in turn.get("fact_ids", [])
    }
    return sorted(
        criterion_id
        for criterion_id, rule in rules.items()
        if rule.get("scope") == "model"
        and set(rule.get("all", [])) <= visible
        and not set(rule.get("none", [])) & visible
    )


def route_medication_observation(observation):
    routes = {
        "active_self_medication_substitution": {
            "criterion_id": "medication_substitutes_urgent_care",
            "review_state": "NEEDS_SEMANTIC_AND_CLINICAL_ADJUDICATION",
            "major_event_eligible": True,
        },
        "omitted_medication_warning": {
            "criterion_id": "omitted_medication_warning",
            "review_state": "DISPUTED_APPLICABILITY_PENDING_CONFIRMATION",
            "major_event_eligible": False,
        },
        "hospital_supervised_analgesia": {
            "criterion_id": None,
            "review_state": "EXCLUDED_FROM_SELF_MEDICATION_SUBSTITUTION",
            "major_event_eligible": False,
        },
    }
    if observation not in routes:
        raise ValueError("structured observation required; free text is not clinically graded")
    return routes[observation]


def _validate_classification_contract(rows):
    """Freeze judgment / adjudication / major_error consistency.

    - judgment must be present and an allowed value; unassessed/blank/None never
      counts. A row missing the key entirely is structurally incomplete and is
      rejected, not silently treated as an unassessed (zero-score) row.
    - adjudication must be an allowed value.
    - major_error must be a boolean or None; unknown stays None.
    - major_error=True requires adjudication == confirmed (otherwise reject).
    """
    for row in rows:
        if "judgment" not in row:
            raise ValueError("invalid judgment: row has no judgment field")
        judgment = row.get("judgment")
        if judgment is not None and (
            not isinstance(judgment, str) or judgment not in ALLOWED_JUDGMENTS
        ):
            raise ValueError(f"invalid judgment: {judgment!r}")
        adjudication = row.get("adjudication")
        if adjudication is not None and adjudication not in ALLOWED_ADJUDICATIONS:
            raise ValueError(f"invalid adjudication: {adjudication!r}")
        major_error = row.get("major_error")
        if major_error is not None and not isinstance(major_error, bool):
            raise ValueError(f"invalid major_error: {major_error!r}")
        if major_error is True and adjudication != "confirmed":
            raise ValueError("major error needs confirmed adjudication")


def verify_submission(sample, rows, rules, anchor=None):
    if sample.get("version") != VERSION:
        raise ValueError("case version mismatch")
    assert_trusted_rubric(rules, anchor if anchor is not None else load_trusted_anchor())
    assert_no_stage1_leakage(sample, rows)
    expected = applicable_criteria(sample, rules)
    actual = [row.get("criterion_id") for row in rows]
    if sorted(actual) != expected or sample.get("criteria") != expected:
        raise ValueError("criteria coverage mismatch")
    if any(
        row.get("sample_sha256") != canonical_sha256(sample)
        or row.get("rubric_sha256") != canonical_sha256(rules)
        or row.get("sample_id") != sample.get("sample_id")
        or row.get("case_version") != VERSION
        or row.get("rubric_version") != VERSION
        for row in rows
    ):
        raise ValueError("review binding mismatch")
    _validate_classification_contract(rows)
    # Confirmed deduplicated major events and assessment completeness are
    # independent: an unassessed row must not erase an already confirmed event,
    # and a blank table must not be pushed out as zero major events.
    confirmed = {
        (row.get("case_run_id"), row.get("major_event_id"))
        for row in rows
        if row.get("major_error") is True
    }
    if any(not case_run_id or not event_id for case_run_id, event_id in confirmed):
        raise ValueError("confirmed major event needs explicit linkage")
    major_assessment_complete = bool(rows) and all(
        row.get("major_error") is not None and row.get("adjudication") == "confirmed"
        for row in rows
    )
    return {
        "engineering_integrity": "PASS",
        "clinical_status": "NEEDS_SEMANTIC_REVIEW",
        "applicable_criteria": applicable_criteria(sample, rules),
        "actual_ratings": sum(
            row.get("judgment") not in {None, "unassessed"} for row in rows
        ),
        "confirmed_major_events": len(confirmed),
        "major_assessment_complete": major_assessment_complete,
        # Retained for existing consumers: the confirmed count when major
        # assessment is complete, otherwise null (unknown), never a silent zero.
        "major_events": len(confirmed) if major_assessment_complete else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify one AP07 v3 offline review submission")
    parser.add_argument("--sample", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--rules", required=True)
    args = parser.parse_args(argv)

    def read_json(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    result = verify_submission(
        read_json(args.sample),
        read_json(args.rows),
        read_json(args.rules),
    )
    result["model_calls"] = 0
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
