"""Prepare local source review; validate human drafts without case admission.

Only a text-free aggregate audit is suitable for publication. All packets,
workspaces, validation reports and reviewer conflicts remain local. A reviewer
ID is self-declared provenance, not proof of medical credentials or independence.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .candidate_facts import SCHEMA_VERSION as FACT_DRAFT_VERSION, build_fact_draft
from .candidate_privacy import SCANNER_VERSION, scan_text
from .candidate_review_ui import render_review_workspace
from .candidate_similarity import audit_candidate_similarity
from .extraction import VisibleFactExtractor
from .source_intake import COMMIT, FILES, audit_dialogues, verify_payload


SCHEMA_VERSION = "candidate-review/v0.1"
LOCAL_ROOT = Path(__file__).resolve().parents[2] / "medical/patient-eval/local"
RUBRICS = (
    ("clarification.relevant", "C1", "behavioral", False),
    ("questioning.unknown", "C2", "behavioral", False),
    ("correction.absorbed", "C3", "behavioral", False),
    ("risk.boundary", "C4", "clinical", True),
    ("explanation.repair", "C7", "behavioral", False),
    ("completion.summary", "C8", "behavioral", False),
)
_FLAGS = {"formal_approval": False, "clinical_gold": False, "dynamic_scenario_ready": False}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _new_local(path):
    path = Path(path)
    _require(path.resolve().is_relative_to(LOCAL_ROOT.resolve()), "output must be under ignored medical/patient-eval/local/")
    _require(not path.exists(), "output must be new; refusing overwrite")
    return path


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _immutable(packet):
    _require(isinstance(packet, dict) and isinstance(packet.get("items"), list), "review packet requires items")
    result = deepcopy(packet)
    result.pop("reviewer_id", None)
    result.pop("packet_sha256", None)
    for item in result["items"]:
        _require(isinstance(item, dict), "candidate item must be an object")
        item.pop("review", None)
    return result


def _digest(packet):
    return hashlib.sha256(_json(_immutable(packet)).encode("utf-8")).hexdigest()


def _blank_review(fact_draft):
    facts = []
    for fact in fact_draft["fact_candidates"]:
        review = deepcopy(fact["review"])
        review.pop("reviewer_id")
        review.update(fact_id=fact["candidate_id"], ask_patterns=[], disclosure_condition="")
        facts.append(review)
    return {
        "privacy": {"decision": "unreviewed", "checked_turn_ids": [], "reason": "", "additional_spans": []},
        "completeness": {"decision": "unreviewed", "reason": "", "evidence_turn_ids": []},
        "facts": facts,
        "rubrics": [{
            "criterion_id": criterion_id, "capability": capability,
            "kind": kind, "critical": critical, "required": True,
            "decision": "unreviewed", "applicability": "unreviewed",
            "description": "", "anchors": {"0": "", "1": "", "2": ""},
            "serious_error_definition": "", "opportunity": {"trigger": "", "deadline": ""},
            "reason": "",
        } for criterion_id, capability, kind, critical in RUBRICS],
    }


def build_review_packet(dialogues, candidate_ids, source_binding):
    """Pure preparation helper; prepare() additionally verifies pinned bytes.

    Tests may use synthetic data. This function itself does not authenticate a
    dataset merely because its caller supplies a source_binding dictionary.
    """
    _require(isinstance(dialogues, list) and isinstance(candidate_ids, list), "dialogues and candidate IDs must be lists")
    _require(isinstance(source_binding, dict), "source binding must be an object")
    lookup = {(type(d["dialogue"]).__name__, str(d["dialogue"])): d for d in dialogues}
    _require(len(lookup) == len(dialogues), "duplicate source dialogue IDs")
    identities = [(type(value).__name__, str(value)) for value in candidate_ids]
    _require(len(identities) == len(set(identities)) and all(key in lookup for key in identities), "unknown or duplicate candidate selection")
    items = []
    for index, identity in enumerate(identities):
        dialogue = lookup[identity]
        draft = build_fact_draft(dialogue)
        turns, findings = [], []
        for turn_index, original in enumerate(dialogue["information"]):
            turn_id = f"r{turn_index + 1:04d}"
            turns.append({"turn_id": turn_id, "source_turn_id": original["turn"],
                          "source_turn_index": turn_index, "role": original["role"], "content": original["sentence"]})
            for cue in scan_text(original["sentence"]):
                findings.append({"finding_id": f"P{len(findings) + 1:04d}", "turn_id": turn_id, **cue})
        items.append({"candidate_id": f"C{index + 1:04d}", "source_dialogue_id": dialogue["dialogue"],
                      "turns": turns, "privacy_findings": findings, "fact_draft": draft,
                      "review": _blank_review(draft)})
    packet = {"schema_version": SCHEMA_VERSION, "local_only": True, "source_binding": deepcopy(source_binding),
              "reviewer_id": "", "items": items, "privacy_scanner_version": SCANNER_VERSION,
              "similarity": audit_candidate_similarity(items), **_FLAGS,
              "interpretation": "Source and lexical annotations are proposals; historical doctor replies are not gold. "
                                "Human drafts do not establish clinical correctness, de-identification or case admission."}
    packet["packet_sha256"] = _digest(packet)
    return packet


def _public_audit(packet):
    facts, legacy, privacy = Counter(), Counter(), Counter()
    total_turns = 0
    for item in packet["items"]:
        facts.update(item["fact_draft"]["counters"])
        legacy.update(item["fact_draft"]["legacy_baseline"]["counters"])
        privacy.update(cue["kind"] for cue in item["privacy_findings"])
        total_turns += len(item["turns"])
    similarity = packet["similarity"]
    return {"schema_version": "candidate-preparation-audit/v0.1", "source": "ReMeDi-base",
            "upstream_commit": COMMIT, "candidate_count": len(packet["items"]), "turn_count": total_turns,
            "source_file_sha256": {filename: pin["sha256"] for filename, pin in FILES.items()},
            "selection_method": "first_50_unique_usable_dialogues_ordered_by_content_sha256",
            "algorithm_versions": {
                "preparation": SCHEMA_VERSION, "fact_draft": FACT_DRAFT_VERSION,
                "privacy_scanner": SCANNER_VERSION, "legacy_extractor": VisibleFactExtractor.version,
                "similarity": similarity["schema_version"],
            },
            "similarity_configuration": {key: similarity[key] for key in (
                "threshold", "threshold_status", "scope")},
            "fact_counters": dict(facts), "legacy_baseline_counters": dict(legacy),
            "privacy_cue_counts": dict(privacy),
            "similarity_counts": {key: similarity[key] for key in (
                "eligible_candidate_count", "possible_pair_count", "compared_pair_count",
                "skipped_pair_count", "exact_pair_count", "near_pair_count")},
            "human_reviewed_candidates": 0, "completed_dual_reviews": 0, **_FLAGS,
            "interpretation": "Deterministic first 50 candidates are not representative or independent held-out data. "
                              "Privacy cues need human review; zero cues are not clearance. Legacy unparsed clauses "
                              "are unsupported coverage, not measured error rate. No model evaluation was performed."}


def prepare(source_dir: Path, out: Path):
    out = _new_local(out)
    source_dir = Path(source_dir)
    _require(source_dir.resolve().is_relative_to(LOCAL_ROOT.resolve()), "source must be under ignored medical/patient-eval/local/")
    payloads = {}
    for filename, pin in FILES.items():
        payloads[filename] = (source_dir / filename).read_bytes()
        verify_payload(payloads[filename], pin)
    dialogues = json.loads(payloads["ReMeDi-base.json"])
    _, candidate_ids = audit_dialogues(dialogues, candidate_limit=50)
    manifest = _read(source_dir / "candidate-review-local.json")
    _require(manifest.get("source_commit") == COMMIT, "candidate manifest source commit mismatch")
    _require(_json(manifest.get("candidate_dialogue_ids")) == _json(candidate_ids), "candidate selection must match deterministic pinned-source recomputation")
    packet = build_review_packet(dialogues, candidate_ids, {
        "dataset": "ReMeDi-base", "commit": COMMIT, "files": deepcopy(FILES),
        "selection": "first_50_unique_usable_dialogues_ordered_by_content_sha256",
        "candidate_dialogue_ids": candidate_ids,
        "manifest_sha256": hashlib.sha256((source_dir / "candidate-review-local.json").read_bytes()).hexdigest(),
        "source_bytes_verified": True,
    })
    audit = _public_audit(packet)
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    (out / "original.json").write_text(_json(packet), encoding="utf-8")
    for reviewer in ("A", "B"):
        (out / f"reviewer-{reviewer}.json").write_text(_json(packet), encoding="utf-8")
        (out / f"reviewer-{reviewer}.html").write_text(render_review_workspace(packet), encoding="utf-8")
    (out / "public-audit.json").write_text(_json(audit), encoding="utf-8")
    return audit


def _enum(value, allowed, label):
    _require(isinstance(value, str) and value in allowed, label + " has invalid value")


def _optional_text(value, label):
    _require(value is None or isinstance(value, str), label + " must be text or null")


def _ids(value, turns, label):
    _require(isinstance(value, list) and all(isinstance(x, str) and x in turns for x in value), label + " references unknown turns")
    _require(len(value) == len(set(value)), label + " must not repeat turns")


def _spans(spans, turns, label, patient_only=False, source_index=None):
    _require(isinstance(spans, list), label + " must be a list")
    for span in spans:
        _require(isinstance(span, dict), label + " span must be an object")
        _require(set(span) <= {"turn_id", "start", "end", "text", "kind"}, label + " span has unknown fields")
        turn_id, start, end = span.get("turn_id"), span.get("start"), span.get("end")
        _require(isinstance(turn_id, str) and turn_id in turns, label + " references an unknown turn")
        turn = turns[turn_id]
        _require(type(start) is int and type(end) is int and 0 <= start < end <= len(turn["content"]), label + " requires original exclusive Unicode offsets")
        _require(isinstance(span.get("text"), str) and span["text"] == turn["content"][start:end], label + " text does not match original span")
        if "kind" in span:
            _require(_nonempty(span["kind"]), label + " kind must be nonempty")
        if patient_only:
            _require(turn["role"] == "patient", label + " must cite patient text")
        if source_index is not None:
            _require(turn["source_turn_index"] == source_index, label + " must cite the proposal's original turn")


def _actual(decision, reason, reviewer_id):
    if decision != "unreviewed":
        _require(_nonempty(reviewer_id), "decisions require a nonempty reviewer_id")
        _require(_nonempty(reason), "decisions require a nonempty reason")


def validate_review(original, review):
    """Check trusted source equality and review structure; allow missing drafts."""
    _require(isinstance(original, dict), "trusted original must be an object")
    _require(original.get("schema_version") == SCHEMA_VERSION, "unsupported trusted packet schema")
    _require(all(original.get(key) is False for key in _FLAGS), "source review cannot grant formal or clinical approval")
    _require(original.get("packet_sha256") == _digest(original), "trusted original packet digest mismatch")
    _require(_json(_immutable(original)) == _json(_immutable(review)), "immutable source packet differs from trusted original")
    _require(review.get("packet_sha256") == original["packet_sha256"], "review packet digest differs from trusted original")
    _require(set(review) == set(original), "review packet top-level fields changed")
    _require(isinstance(review.get("reviewer_id"), str), "reviewer_id must be text")
    reviewer_id = review["reviewer_id"]
    counts = Counter(dict.fromkeys(["candidates", "privacy_decided", "privacy_missing", "completeness_decided", "completeness_missing",
                                   "facts_decided", "facts_missing", "rubrics_decided", "rubrics_missing", "rubric_applicability_decided",
                                   "rubric_applicability_missing"], 0))
    for trusted, item in zip(original["items"], review["items"]):
        counts["candidates"] += 1
        _require(isinstance(item.get("review"), dict), "candidate review must be an object")
        human = item["review"]
        blank = _blank_review(trusted["fact_draft"])
        _require(set(human) == set(blank), "candidate review fields changed")
        turns = {turn["turn_id"]: turn for turn in trusted["turns"]}
        privacy = human["privacy"]
        _require(isinstance(privacy, dict) and set(privacy) == set(blank["privacy"]), "privacy fields changed")
        _enum(privacy["decision"], {"unreviewed", "reviewed_no_identifiers", "needs_redaction", "excluded"}, "privacy decision")
        _optional_text(privacy["reason"], "privacy reason")
        _ids(privacy["checked_turn_ids"], turns, "privacy checked_turn_ids")
        _spans(privacy["additional_spans"], turns, "privacy")
        _actual(privacy["decision"], privacy["reason"], reviewer_id)
        if privacy["decision"] in {"reviewed_no_identifiers", "needs_redaction"}:
            _require(set(privacy["checked_turn_ids"]) == set(turns), "privacy clearance/redaction requires checking every original turn")
        if privacy["decision"] == "reviewed_no_identifiers":
            _require(not privacy["additional_spans"], "no-identifiers decision conflicts with supplied identifier spans")
        if privacy["decision"] == "needs_redaction":
            _require(bool(privacy["additional_spans"]), "needs_redaction requires reviewer-confirmed identifier spans")
        complete = human["completeness"]
        _require(isinstance(complete, dict) and set(complete) == set(blank["completeness"]), "completeness fields changed")
        _enum(complete["decision"], {"unreviewed", "usable", "insufficient", "excluded"}, "completeness decision")
        _optional_text(complete["reason"], "completeness reason")
        _ids(complete["evidence_turn_ids"], turns, "completeness evidence")
        _actual(complete["decision"], complete["reason"], reviewer_id)
        if complete["decision"] != "unreviewed":
            _require(bool(complete["evidence_turn_ids"]), "completeness decision requires evidence")
        for section, entry in (("privacy", privacy), ("completeness", complete)):
            counts[section + ("_missing" if entry["decision"] == "unreviewed" else "_decided")] += 1
        facts = human["facts"]
        _require(isinstance(facts, list) and len(facts) == len(blank["facts"]), "fact rows must preserve original IDs/order")
        proposals = {fact["candidate_id"]: fact for fact in trusted["fact_draft"]["fact_candidates"]}
        for row, expected in zip(facts, blank["facts"]):
            _require(isinstance(row, dict) and set(row) == set(expected) and row.get("fact_id") == expected["fact_id"], "fact rows must preserve fields/IDs/order")
            _enum(row["decision"], {"unreviewed", "include", "exclude", "uncertain"}, "fact decision")
            _require(row["polarity"] is None or row["polarity"] in ("present", "absent", "unknown", "conflict"), "invalid fact polarity")
            _require(row["is_patient_assertion"] is None or type(row["is_patient_assertion"]) is bool, "is_patient_assertion must be bool or null")
            _require(row["disclosure_policy"] is None or row["disclosure_policy"] in ("initial", "on_question", "scheduled", "never"), "invalid disclosure policy")
            for field in ("subject", "time", "manual_groundsignal_slot", "correction_of_candidate_id", "reason", "disclosure_condition"):
                _optional_text(row[field], "fact " + field)
            _require(isinstance(row["ask_patterns"], list) and all(_nonempty(x) for x in row["ask_patterns"]), "ask_patterns must contain nonempty strings")
            proposal = proposals[row["fact_id"]]
            _spans(row["evidence_spans"], turns, "fact evidence", patient_only=True, source_index=proposal["source_turn_index"])
            _actual(row["decision"], row["reason"], reviewer_id)
            correction = row["correction_of_candidate_id"]
            if correction is not None:
                _require(correction in proposals and proposals[correction]["source_turn_index"] < proposal["source_turn_index"], "correction must reference a strictly earlier patient proposal")
            if row["disclosure_policy"] == "initial":
                _require(proposal["in_opening_prefix"], "future patient facts cannot enter initial disclosure")
            if row["decision"] == "include":
                _require(row["is_patient_assertion"] is True and row["polarity"] is not None, "included facts require explicit assertion and polarity review")
                _require(all(_nonempty(row[field]) for field in ("subject", "time", "manual_groundsignal_slot")), "included facts require subject/time/slot; explicit unknown is allowed")
                _require(bool(row["evidence_spans"]) and row["disclosure_policy"] is not None, "included facts require exact evidence and disclosure policy")
                if row["disclosure_policy"] == "on_question":
                    _require(bool(row["ask_patterns"]), "on_question disclosure requires explicit ask_patterns")
                if row["disclosure_policy"] == "scheduled":
                    _require(_nonempty(row["disclosure_condition"]), "scheduled disclosure requires a condition")
            counts["facts_missing" if row["decision"] == "unreviewed" else "facts_decided"] += 1
        rubrics = human["rubrics"]
        _require(isinstance(rubrics, list) and len(rubrics) == len(blank["rubrics"]), "rubric rows must preserve original IDs/order")
        for row, expected in zip(rubrics, blank["rubrics"]):
            _require(isinstance(row, dict) and set(row) == set(expected), "rubric fields changed")
            for field in ("criterion_id", "capability", "kind", "critical", "required"):
                _require(_json(row[field]) == _json(expected[field]), "rubric identity/static flags changed")
            _enum(row["decision"], {"unreviewed", "drafted", "excluded"}, "rubric decision")
            _enum(row["applicability"], {"unreviewed", "applicable", "not_applicable"}, "rubric applicability")
            for field in ("description", "serious_error_definition", "reason"):
                _optional_text(row[field], "rubric " + field)
            _require(isinstance(row["anchors"], dict) and set(row["anchors"]) == {"0", "1", "2"}, "rubric anchors require 0/1/2")
            _require(isinstance(row["opportunity"], dict) and set(row["opportunity"]) == {"trigger", "deadline"}, "rubric opportunity requires trigger/deadline")
            for value in [*row["anchors"].values(), *row["opportunity"].values()]:
                _optional_text(value, "rubric draft text")
            _actual(row["decision"], row["reason"], reviewer_id)
            _actual(row["applicability"], row["reason"], reviewer_id)
            if row["decision"] == "drafted":
                _require(row["applicability"] == "applicable", "drafted rubric requires applicable status")
                _require(all(_nonempty(value) for value in [row["description"], *row["anchors"].values(), *row["opportunity"].values()]), "drafted rubric requires description, all anchors and opportunity conditions")
                if row["critical"]:
                    _require(_nonempty(row["serious_error_definition"]), "critical rubric requires serious error definition")
            if row["decision"] == "excluded":
                _require(row["applicability"] == "not_applicable", "excluded rubric requires explicit not_applicable")
            counts["rubrics_missing" if row["decision"] == "unreviewed" else "rubrics_decided"] += 1
            counts["rubric_applicability_missing" if row["applicability"] == "unreviewed" else "rubric_applicability_decided"] += 1
    return {"schema_version": "candidate-review-validation/v0.1", "local_only": True,
            "packet_sha256": original["packet_sha256"], "reviewer_id": reviewer_id,
            "structurally_valid": True, "counts": dict(counts), **_FLAGS,
            "interpretation": "Valid draft structure does not establish correctness or reviewer credentials. "
                              "Missing fields remain missing; no model score or clinical approval is computed."}


def _comparison_fields(item):
    result = []
    review = item["review"]
    for section in ("privacy", "completeness"):
        result.append((section + ".decision", section, review[section]["decision"]))
    for fact in review["facts"]:
        for field in ("decision", "polarity", "is_patient_assertion", "subject", "time", "correction_of_candidate_id",
                      "manual_groundsignal_slot", "disclosure_policy"):
            value = fact[field]
            if field != "decision" and fact["decision"] == "unreviewed":
                value = None
            result.append(("facts." + field, fact["fact_id"], value))
    for rubric in review["rubrics"]:
        for field in ("decision", "applicability"):
            result.append(("rubrics." + field, rubric["criterion_id"], rubric[field]))
    return result


def _draft_content_fields(item):
    """Content equality aids adjudication; it is not semantic agreement."""
    review = item["review"]
    result = [("privacy.additional_spans", "privacy", review["privacy"]["additional_spans"],
               review["privacy"]["decision"] == "needs_redaction")]
    for fact in review["facts"]:
        included = fact["decision"] == "include"
        for field, applicable in (
            ("evidence_spans", included),
            ("ask_patterns", included and fact["disclosure_policy"] == "on_question"),
            ("disclosure_condition", included and fact["disclosure_policy"] == "scheduled"),
        ):
            result.append(("facts." + field, fact["fact_id"], fact[field], applicable))
    for rubric in review["rubrics"]:
        drafted = rubric["decision"] == "drafted"
        result.append(("rubrics.description", rubric["criterion_id"], rubric["description"], drafted))
        for anchor in ("0", "1", "2"):
            result.append(("rubrics.anchors." + anchor, rubric["criterion_id"], rubric["anchors"][anchor], drafted))
        for field in ("trigger", "deadline"):
            result.append(("rubrics.opportunity." + field, rubric["criterion_id"], rubric["opportunity"][field], drafted))
        result.append(("rubrics.serious_error_definition", rubric["criterion_id"],
                       rubric["serious_error_definition"], drafted and rubric["critical"]))
    return result


def _compare_draft_content(review_a, review_b):
    fields, differences = {}, []
    for item_a, item_b in zip(review_a["items"], review_b["items"]):
        for left, right in zip(_draft_content_fields(item_a), _draft_content_fields(item_b)):
            field, entry, a, eligible_a = left
            b, eligible_b = right[2:]
            stats = fields.setdefault(field, {
                "total_entries": 0, "jointly_applicable": 0, "not_jointly_applicable": 0,
                "paired_nonempty": 0, "missing_either": 0, "identical_content": 0, "different_content": 0,
            })
            stats["total_entries"] += 1
            if not eligible_a or not eligible_b:
                stats["not_jointly_applicable"] += 1
                continue
            stats["jointly_applicable"] += 1
            if not a or not b:
                stats["missing_either"] += 1
                continue
            stats["paired_nonempty"] += 1
            same = _json(a) == _json(b)
            stats["identical_content" if same else "different_content"] += 1
            if not same:
                differences.append({"candidate_id": item_a["candidate_id"], "entry_id": entry, "field": field,
                                    "review_a": deepcopy(a), "review_b": deepcopy(b),
                                    "classification": "canonical_content_difference_needs_adjudication"})
    for stats in fields.values():
        stats["identical_content_rate"] = (stats["identical_content"] / stats["paired_nonempty"]
                                           if stats["paired_nonempty"] else None)
    return {"fields": fields, "differences": differences,
            "interpretation": "Canonical content equality only, not semantic or clinical agreement. "
                              "Compare fact evidence only when both include; question/scheduled conditions only "
                              "when both use that disclosure policy; rubric text only when both drafted; "
                              "critical safety definitions only for critical rubrics; privacy spans only when "
                              "both need redaction. Nonapplicable and missing denominators are explicit."}


def compare_reviews(original, review_a, review_b):
    summaries = [validate_review(original, packet) for packet in (review_a, review_b)]
    identifiers = [packet["reviewer_id"].strip() for packet in (review_a, review_b)]
    _require(all(identifiers) and identifiers[0].casefold() != identifiers[1].casefold(), "comparison requires distinct nonempty reviewer IDs")
    fields, conflicts = {}, []
    for item_a, item_b in zip(review_a["items"], review_b["items"]):
        for left, right in zip(_comparison_fields(item_a), _comparison_fields(item_b)):
            field, entry, a = left
            b = right[2]
            stats = fields.setdefault(field, {"total": 0, "paired_decided": 0, "missing_either": 0, "agreements": 0, "conflicts": 0})
            stats["total"] += 1
            decided = all(value is not None and value != "" and value != "unreviewed" for value in (a, b))
            if not decided:
                stats["missing_either"] += 1
            else:
                stats["paired_decided"] += 1
                same = _json(a) == _json(b)
                stats["agreements" if same else "conflicts"] += 1
                if not same:
                    conflicts.append({"candidate_id": item_a["candidate_id"], "entry_id": entry, "field": field,
                                      "review_a": deepcopy(a), "review_b": deepcopy(b)})
    for stats in fields.values():
        stats["agreement_rate"] = stats["agreements"] / stats["paired_decided"] if stats["paired_decided"] else None
    return {"schema_version": "candidate-review-comparison/v0.1", "local_only": True,
            "packet_sha256": original["packet_sha256"], "reviewer_ids": identifiers,
            "fields": fields, "conflicts": conflicts,
            "draft_content_comparison": _compare_draft_content(review_a, review_b),
            "validation": summaries, **_FLAGS,
            "interpretation": "Exact annotation-decision agreement among paired decided fields, not clinical accuracy "
                              "or model scoring. Blank fields are excluded with explicit denominators; free-text differences "
                              "need adjudication. Reviewer identities and independence are self-declared."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--source-dir", type=Path, required=True)
    preparation.add_argument("--out", type=Path, required=True)
    validation = commands.add_parser("validate-review")
    validation.add_argument("--original", type=Path, required=True)
    validation.add_argument("--review", type=Path, required=True)
    validation.add_argument("--out", type=Path, required=True)
    comparison = commands.add_parser("compare-reviews")
    comparison.add_argument("--original", type=Path, required=True)
    comparison.add_argument("--review-a", type=Path, required=True)
    comparison.add_argument("--review-b", type=Path, required=True)
    comparison.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.source_dir, args.out)
        else:
            output = _new_local(args.out)
            original = _read(args.original)
            result = (validate_review(original, _read(args.review)) if args.command == "validate-review"
                      else compare_reviews(original, _read(args.review_a), _read(args.review_b)))
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            output.write_text(_json(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"candidate review failed: {exc}\n")
    # Never print local review decisions, source IDs, excerpts or reviewer IDs.
    print(_json({"command": args.command, "completed": True, **_FLAGS}))


if __name__ == "__main__":
    main()
