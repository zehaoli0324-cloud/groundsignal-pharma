"""Auditable finite Chinese question rules; never a clinical language model.

Only slot IDs and their authored ask_patterns are read. Values, patient answers,
scoring criteria and target identity cannot affect classification. Quotes and
negated/deferred/third-party requests are excluded before disclosure matching.
The retained legacy implementation supports honest replay of older journals.
"""
from __future__ import annotations

import re
import unicodedata

LEGACY_CLASSIFIER_VERSION = "literal-v0.2"
DEFAULT_CLASSIFIER_VERSION = "conservative-zh-v0.3"
CLASSIFIER_VERSIONS = (LEGACY_CLASSIFIER_VERSION, DEFAULT_CLASSIFIER_VERSION)
_LEGACY_QUESTION = re.compile(r"[?？]|请问|是否|多久|什么|哪|告诉|能否|多少|几|有没有|有无|可否|能不能|吗(?:呀|呢)?$")
_LEGACY_CLAUSES = re.compile(r"[^，,。；;！!\n?？]+[?？]?")
_CLAUSES = re.compile(r"[^，,。；;！!\n?？]+[?？]?")
_DIRECT = re.compile(r"[?？]|请问|是否|多久|什么|哪|能否|多少|几|有没有|有无|可否|能不能|吗(?:呀|呢)?$|请(?:提供|补充|描述|说明|确认)|告诉我|说一下|说说|补充一下")
_NEGATED_REQUEST = re.compile(
    r"(?:不要|不用|不必|无需|不需要|暂不|先不|不再|别)(?:现在|暂时|再|急着|立即|直接|在这里|在本轮|向我)?(?:回复|回答|告诉|提供|补充|说明|询问|问|说|核实|确认)"
    r"|不是(?:在)?问|(?:不|无需|不用|不必)需要(?:你)?(?:回答|回复|说明)"
)
_THIRD_PARTY = re.compile(r"(?:告诉|转告|问|向)(?:一下)?(?:医生|医师|护士|家属|同事|朋友)|(?:给|向)(?:医生|医师|护士|家属)(?:说明|提供|补充|回答)")
_REPORTED = re.compile(r"^(?:医生|医师|护士|家属|患者|病人|他|她|病历|网页|书上|示例)(?:之前|刚才|曾经)?(?:问|说|写|提到)|(?:示例|例句|只是转述)")
_DECLARATIVE = re.compile(r"^(?:再|进一步)?(?:决定|判断|评估)(?:是否|有无)|^(?:我|我们)(?:会|将|已经|正在|先|已)(?:记录|告诉|核实|解释|考虑|整理)|^(?:我|目前|现在)?(?:还)?(?:不知道|不清楚|尚不清楚)|(?:以后|下次|到时).*(?:问|讨论|回答)|(?:这个问题|这些问题).*(?:以后|下次)|(?:需要|应该|是否要|能否)(?:被)?记录")
_CONFIRMATION = re.compile(r"[，,]\s*(?=(?:对吗|是吗|对不对|是不是这样)[?？]?(?:$|[。；;]))")
_QUOTE_PAIRS = {"“": "”", "「": "」", "『": "』", '"': '"'}
_ALIASES = {
    # Duration and onset are treated as one authored slot in the pilot schema.
    # This does not infer onset dates or convert a duration into a clinical fact.
    "onset": [r"持续(?:了)?(?:几天|几周|多长时间|多少天|多久)",
              r"(?:症状|不舒服|状况)出现到现在(?:有)?(?:多少天|多久)"],
}


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


def _mask_quotes(text: str) -> tuple[str, list[dict]]:
    chars = list(text)
    spans = []
    stack = []
    start = None
    for index, char in enumerate(text):
        if stack and char == stack[-1]:
            stack.pop()
            if not stack:
                spans.append({"start": start, "end": index + 1, "text": text[start:index + 1]})
                chars[start:index + 1] = " " * (index + 1 - start)
                # A closed quotation ends reported scope; following direct
                # speech is evaluated independently even without punctuation.
                chars[index] = ";"
                start = None
        elif char in _QUOTE_PAIRS:
            if not stack:
                start = index
            stack.append(_QUOTE_PAIRS[char])
    # An unclosed quotation is uncertain; conservatively suppress its remainder.
    if stack:
        spans.append({"start": start, "end": len(text), "text": text[start:]})
        chars[start:] = " " * (len(text) - start)
    return "".join(chars), spans


def _matches(clause: str, facts: dict) -> list[dict]:
    matches = []
    for slot, fact in facts.items():
        for pattern in fact["ask_patterns"]:
            literal = _normalized(pattern)
            for found in re.finditer(re.escape(literal), clause):
                matches.append({"slot": slot, "pattern": pattern, "kind": "authored_literal",
                                "start": found.start(), "end": found.end()})
        for pattern in _ALIASES.get(slot, []):
            for found in re.finditer(pattern, clause):
                matches.append({"slot": slot, "pattern": pattern, "kind": "bounded_alias",
                                "start": found.start(), "end": found.end()})
    # A specific phrase (e.g. 原文日期) must not also license another slot's
    # nested generic phrase (日期). Exact-span collisions are ambiguous instead.
    matches = [match for match in matches if not any(
        other["slot"] != match["slot"] and other["start"] <= match["start"]
        and other["end"] >= match["end"]
        and (other["end"] - other["start"] > match["end"] - match["start"])
        for other in matches)]
    ambiguous = {(m["start"], m["end"]) for m in matches if any(
        o["slot"] != m["slot"] and (o["start"], o["end"]) == (m["start"], m["end"])
        for o in matches)}
    return [dict(match, ambiguous=(match["start"], match["end"]) in ambiguous) for match in matches]


def classify_requested_slots(text: str, facts: dict, version: str = DEFAULT_CLASSIFIER_VERSION) -> dict:
    """Return operator-only decisions; a lack of mapping is not itself an error.

    `facts` uses the patient spec structure, but only ask_patterns are inspected.
    `version` is strict: missing journal versions must be resolved by the caller
    to LEGACY_CLASSIFIER_VERSION, never silently replayed under current rules.
    """
    if version not in CLASSIFIER_VERSIONS:
        raise ValueError(f"unsupported patient classifier version: {version}")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    normalized = _normalized(text)
    evidence = []
    requested = set()
    if version == LEGACY_CLASSIFIER_VERSION:
        for clause in _LEGACY_CLAUSES.findall(normalized):
            clause = clause.strip()
            slots = [slot for slot, fact in facts.items() if any(
                _normalized(pattern) in clause for pattern in fact["ask_patterns"])]
            selected = slots if _LEGACY_QUESTION.search(clause) else []
            requested.update(selected)
            evidence.append({"text": clause, "matched_slots": slots,
                             "requested_slots": selected,
                             "reason": "legacy_question_match" if selected else "legacy_unmatched"})
        return {"classifier_version": version, "requested_slots": [s for s in facts if s in requested],
                "clauses": evidence, "suppressed_quotes": []}

    masked, quotes = _mask_quotes(normalized)
    masked = _CONFIRMATION.sub(" ", masked)
    # Explicit contrasts have independent scopes, even without punctuation.
    masked = re.sub(r"但是|但|而是|不过|只回答", ",", masked)
    for clause in _CLAUSES.findall(masked):
        clause = clause.strip()
        if not clause:
            continue
        matches = _matches(clause, facts)
        slots = [slot for slot in facts if any(m["slot"] == slot and not m["ambiguous"] for m in matches)]
        if _NEGATED_REQUEST.search(clause):
            reason = "negated_request"
        elif _THIRD_PARTY.search(clause):
            reason = "third_party_instruction"
        elif _REPORTED.search(clause):
            reason = "reported_or_example"
        elif _DECLARATIVE.search(clause):
            reason = "deferred_or_declarative"
        elif not _DIRECT.search(clause):
            reason = "no_direct_request"
        elif not slots:
            reason = "unsupported_or_ambiguous_slot"
        else:
            reason = "direct_supported_request"
        selected = slots if reason == "direct_supported_request" else []
        # A standalone cancellation such as '不必现在回复我' retracts the
        # immediately preceding question. '以上问题' explicitly scopes all.
        if reason == "negated_request" and not matches and re.search(r"回答|回复", clause):
            affected = evidence if re.search(r"以上|上述|这些|所有", clause) else evidence[-1:]
            for prior in affected:
                prior["requested_slots"] = []
                prior["reason"] = "cancelled_by_following_clause"
        evidence.append({"text": clause, "matched_slots": slots, "requested_slots": selected,
                         "reason": reason, "matched_patterns": matches})
    for decision in evidence:
        requested.update(decision["requested_slots"])
    return {"classifier_version": version, "requested_slots": [slot for slot in facts if slot in requested],
            "clauses": evidence, "suppressed_quotes": quotes}
