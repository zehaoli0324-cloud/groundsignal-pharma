"""Local-only ReMeDi annotation proposals, with a strict visible-prefix boundary.

This preparer does not establish medical facts. Source annotations and lexical
cues are review aids; reviewers must establish assertion, polarity, subject,
time, correction links and disclosure policy before any scenario adaptation.
The caller must bind this output to verified source bytes and keep it local.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from .extraction import VisibleFactExtractor


SCHEMA_VERSION = "candidate-fact-draft/v0.1"
_CUES = {
    "negation": r"没有|未曾|尚未|并非|不是|否认|不再|无",
    "uncertainty": r"不清楚|不知道|不确定|可能|也许|好像|似乎|记不清",
    "correction": r"更正|纠正|说错|记错|改口|不是.{0,12}而是",
    "person": r"妈妈|母亲|爸爸|父亲|孩子|儿子|女儿|丈夫|妻子|家人|本人|我",
    "time": r"今天|昨天|前天|刚才|之前|以后|去年|上周|本周|\d+\s*(?:年|月|天|小时|分钟)",
    "question": r"[?？]|是否|是不是|有没有|怎么办|为什么|能不能|吗",
}


def _identifier(value: object) -> bool:
    return type(value) is int or isinstance(value, str) and bool(value.strip())


def _cue_spans(sentence: str) -> list[dict]:
    cues = []
    for category, pattern in _CUES.items():
        for match in re.finditer(pattern, sentence):
            cues.append({
                "category": category, "start": match.start(), "end_exclusive": match.end(),
                "text": match.group(), "decision": "review_cue_only",
                "scope_resolved": False,
            })
    return sorted(cues, key=lambda cue: (cue["start"], cue["end_exclusive"], cue["category"]))


def _span_check(sentence: str, annotation: dict) -> dict:
    """Validate the pinned source's inclusive end offsets without searching.

    A matching entity elsewhere in the sentence never repairs an incorrect
    offset. Exact text alignment is evidence of alignment, not medical truth.
    """
    result = {"offset_convention": "zero_based_unicode_codepoints_inclusive_end",
              "status": "missing", "evidence_span": None}
    text, offsets = annotation.get("text"), annotation.get("range")
    if not isinstance(text, str) or not text or offsets is None:
        result["reason"] = "annotation_text_or_range_missing"
        return result
    if (not isinstance(offsets, list) or len(offsets) != 2
            or any(type(value) is not int for value in offsets)):
        result.update(status="mismatch", reason="malformed_range")
        return result
    start, end = offsets
    if not 0 <= start <= end < len(sentence):
        result.update(status="mismatch", reason="range_out_of_bounds")
    elif sentence[start:end + 1] != text:
        result.update(status="mismatch", reason="annotation_text_does_not_match_range")
    else:
        result.update(status="exact", reason="source_range_matches_patient_text",
                      evidence_span={"start": start, "end_exclusive": end + 1, "text": text})
    return result


def build_fact_draft(dialogue: dict) -> dict:
    """Return an unreviewed, detached draft using only actual patient text.

    ``information`` order remains authoritative even when source turn IDs are
    not contiguous. Doctor turns contribute role/identity to the order ledger,
    never medical propositions. Consecutive initial patient messages constitute
    the opening prefix; later turns cannot modify its baseline snapshot.
    """
    if not isinstance(dialogue, dict) or not _identifier(dialogue.get("dialogue")):
        raise ValueError("a source dialogue identifier is required")
    turns = dialogue.get("information")
    if not isinstance(turns, list) or not turns:
        raise ValueError("source information must be a nonempty turn list")
    seen = set()
    for turn in turns:
        if not isinstance(turn, dict) or not _identifier(turn.get("turn")):
            raise ValueError("every source turn requires an identifier")
        identity = (type(turn["turn"]).__name__, str(turn["turn"]))
        if identity in seen:
            raise ValueError("source turn identifiers must be unique")
        seen.add(identity)
        if turn.get("role") not in {"patient", "doctor"} or not isinstance(turn.get("sentence"), str):
            raise ValueError("source turns require a known role and original sentence")

    boundary = 0
    while boundary < len(turns) and turns[boundary]["role"] == "patient":
        boundary += 1
    counts = Counter(dict.fromkeys([
        "patient_turns", "patient_action_annotations", "malformed_actions",
        "actions_missing_or_nonlist_turns", "exact_spans", "mismatch_spans",
        "missing_spans", "opening_candidates", "later_candidates",
        "upstream_inquire_candidates", "lexical_review_cues", "empty_patient_turns",
    ], 0))
    extractor = VisibleFactExtractor()
    opening_snapshot = extractor.snapshot()
    patient_turns, candidates, snapshots = [], [], []
    for index, turn in enumerate(turns):
        if turn["role"] != "patient":
            continue
        counts["patient_turns"] += 1
        sentence, source_turn_id = turn["sentence"], turn["turn"]
        cues = _cue_spans(sentence)
        counts["lexical_review_cues"] += len(cues)
        patient_turns.append({
            "source_turn_id": source_turn_id, "source_turn_index": index,
            "original_text": sentence, "in_opening_prefix": index < boundary,
            "review_cues": cues,
        })
        baseline_turn_id = f"source-turn-index:{index}"
        if sentence.strip():
            snapshot = extractor.observe(baseline_turn_id, sentence)
        else:
            counts["empty_patient_turns"] += 1
            snapshot = extractor.snapshot()
        snapshots.append({
            "source_turn_id": source_turn_id, "source_turn_index": index,
            "baseline_turn_id": baseline_turn_id, "snapshot": snapshot,
        })
        if index < boundary:
            opening_snapshot = deepcopy(snapshot)
        actions = turn.get("actions")
        if not isinstance(actions, list):
            counts["actions_missing_or_nonlist_turns"] += 1
            continue
        for action_index, action in enumerate(actions):
            if not isinstance(action, dict):
                counts["malformed_actions"] += 1
                continue
            check = _span_check(sentence, action)
            if check["evidence_span"] is not None:
                check["evidence_span"].update(source_turn_id=source_turn_id, source_turn_index=index)
            counts["patient_action_annotations"] += 1
            counts[check["status"] + "_spans"] += 1
            counts["opening_candidates" if index < boundary else "later_candidates"] += 1
            counts["upstream_inquire_candidates"] += int(action.get("intent") == "Inquire")
            candidates.append({
                "candidate_id": f"turn-{index}-action-{action_index}",
                "source_turn_id": source_turn_id, "source_turn_index": index,
                "upstream_annotation": deepcopy(action),
                "provenance": {
                    "source_dataset": "ReMeDi-base", "source_role": "patient",
                    "source_action_index": action_index,
                    "annotation_status": "upstream_human_annotation_proposal_not_groundsignal_gold",
                },
                "span_check": check,
                "asserted_as_fact": False,
                "upstream_question_intent": action.get("intent") == "Inquire",
                "in_opening_prefix": index < boundary,
                "later_fact_candidate": index >= boundary,
                "review": {
                    "decision": "unreviewed", "is_patient_assertion": None,
                    "polarity": None, "subject": None, "time": None,
                    "correction_of_candidate_id": None,
                    "manual_groundsignal_slot": None, "disclosure_policy": None,
                    "reviewer_id": None, "evidence_spans": [], "reason": None,
                },
            })
    final_snapshot = extractor.snapshot()
    legacy_counts = {
        "observed_patient_turns": counts["patient_turns"] - counts["empty_patient_turns"],
        "current_fact_keys": len(final_snapshot["facts"]),
        "observation_events": sum(len(fact["history"]) for fact in final_snapshot["facts"].values()),
        "unparsed_clauses": len(final_snapshot["unparsed"]),
    }
    return {
        "schema_version": SCHEMA_VERSION, "local_only": True,
        "source_dialogue_id": dialogue["dialogue"],
        "source_turn_order": [
            {"source_turn_id": turn["turn"], "source_turn_index": index, "role": turn["role"]}
            for index, turn in enumerate(turns)
        ],
        "opening_boundary": {
            "source_turn_ids": [turn["turn"] for turn in turns[:boundary]],
            "patient_prefix_end_index_exclusive": boundary,
            "policy": "initial_consecutive_patient_turns_only_no_future_fact_promotion",
        },
        "patient_turns": patient_turns, "fact_candidates": candidates,
        "legacy_baseline": {
            "extractor_version": extractor.version,
            "opening_snapshot": opening_snapshot, "turn_snapshots": snapshots,
            "final_snapshot": final_snapshot, "counters": legacy_counts,
            "interpretation": "Narrow legacy rules on actual patient text only; outputs are development "
                              "baseline predictions, not approved facts. Unparsed counts indicate "
                              "unsupported coverage, not an independently measured error rate.",
        },
        "counters": dict(counts), "review_status": "unreviewed",
        "clinical_gold": False, "dynamic_scenario_ready": False,
        "runtime_export_allowed": False,
        "interpretation": "All actions, including questions, remain proposals. Exact spans verify only "
                          "alignment. Lexical cues do not resolve scope or assert medical facts. Missing "
                          "information is not a negative finding. All disclosure policies require review.",
    }
