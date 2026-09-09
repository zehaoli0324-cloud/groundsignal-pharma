"""Conservative Chinese rules for facts stated in *visible user text*.

This is a deliberately small, independently testable extraction baseline. It
does not accept scenario annotations, guess answers to an assistant's question,
or interpret arbitrary Chinese as a medical fact. Unknown, negative and
conflicting findings remain distinct. Unparsed clauses remain available for
audit and the target always keeps its complete original conversation.
"""

from __future__ import annotations

import re
from copy import deepcopy

from .state import FactState


_TIME_KEYS = {
    "症状开始时间": "symptom_onset",
    "服药时间": "medication_time",
    "报告日期": "report_date",
    "上次咨询日期": "last_consultation_date",
    "截图转发日期": "screenshot_forward_date",
    "原文发布日期": "original_publication_date",
}
_UNKNOWN_KEYS = {
    "是否发热": "fever",
    "发热情况": "fever",
    "是否服药": "medication_taken",
    "药名": "medication_name",
    "报告项目名": "report_item",
    "期间是否变化": "interval_change",
    **_TIME_KEYS,
}
_SUBJECTS = {"妈妈": "mother", "母亲": "mother", "爸爸": "father", "父亲": "father"}
_CORRECTION = re.compile(r"^(?:更正(?:一下)?|刚才说错了?|我刚才说错了?|纠正一下|改口)[：:，,\s]*")


class VisibleFactExtractor:
    """``observe(turn_id, text)`` must only be called for actual user turns.

    Supported declarative formats are intentionally explicit, e.g. ``没有发热``
    or ``更正，服药时间是昨天晚上``. A bare conflicting declaration records a
    conflict. An explicit correction or resolving an earlier unknown references
    the preceding observation. No assistant text is accepted by the runner.
    """

    version = "visible-chinese-rules/v0.2"

    def __init__(self) -> None:
        self._state = FactState()
        self._unparsed: list[dict] = []
        self._seen_turns: set[str] = set()

    @staticmethod
    def _parse(clause: str) -> tuple[str, object, str] | None:
        subject = ""
        for chinese, normalized in _SUBJECTS.items():
            if clause.startswith(chinese):
                subject = normalized + "."
                clause = clause[len(chinese):]
                break
        for label, key in _UNKNOWN_KEYS.items():
            if clause in {label + "不清楚", label + "不知道", label + "尚不清楚"}:
                return subject + key, None, "unknown"
        if clause in {"没有发热", "没有发烧", "不发热", "不发烧"}:
            return subject + "fever", False, "confirmed"
        if clause in {"有发热", "有发烧", "发热", "发烧"}:
            return subject + "fever", True, "confirmed"
        if clause in {"没有服药", "尚未服药", "还没有服药"}:
            return subject + "medication_taken", False, "confirmed"
        if clause in {"已经服药", "已服药", "有服药"}:
            return subject + "medication_taken", True, "confirmed"
        for label, key in _TIME_KEYS.items():
            match = re.fullmatch(re.escape(label) + r"(?:是|为|：|:)\s*(.{1,40})", clause)
            if match:
                value = match.group(1).strip()
                if any(term in value for term in ("不清楚", "不知道", "可能", "也许", "不是", "没有")):
                    return None  # No certainty upgrade from a hedged/negated value.
                return subject + key, value, "confirmed"
        match = re.fullmatch(r"(?:我)?(?:是)?(?:替|帮)(妈妈|母亲|爸爸|父亲)问的?", clause)
        if match and not subject:
            return "patient_subject", _SUBJECTS[match.group(1)], "confirmed"
        return None

    def observe(self, turn_id: str, text: str) -> dict:
        if not isinstance(turn_id, str) or not turn_id.strip() or turn_id in self._seen_turns:
            raise ValueError("a unique nonempty user turn_id is required")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("visible user text is required")
        self._seen_turns.add(turn_id)
        correction = False
        parsed_updates: dict[str, tuple[object, str, bool, str]] = {}
        ambiguous_keys: set[str] = set()
        clauses = []
        for sentence in re.findall(r"[^。！？!?；;\n]+[。！？!?；;\n]?", text):
            sentence_clauses = re.split(r"[，,]+", sentence.rstrip("。！!；;\n"))
            # Detect question scope BEFORE splitting commas: "时间是昨天，对吗"
            # asks for confirmation of the first clause. Explicit supported
            # unknown declarations ("是否发热不清楚") are not questions merely
            # because their field label contains "是否".
            question_scope = []
            for part in sentence_clauses:
                parsed_part = self._parse(part.strip())
                if parsed_part is None or parsed_part[2] != "unknown":
                    question_scope.append(part)
            obvious_question = re.search(r"吗|么|呢|是否|是不是|对不对", "，".join(question_scope))
            if "?" in sentence or "？" in sentence or obvious_question:
                self._unparsed.append({"turn_id": turn_id, "text": sentence.strip(), "reason": "question_not_declaration"})
                continue
            clauses.extend(sentence_clauses)
        for raw in clauses:
            clause = raw.strip()
            if not clause:
                continue
            while _CORRECTION.match(clause):
                correction = True
                clause = _CORRECTION.sub("", clause, count=1).strip()
            if not clause:
                continue
            parsed = self._parse(clause)
            if parsed is None:
                self._unparsed.append({"turn_id": turn_id, "text": raw.strip(), "reason": "outside_supported_rules"})
                continue
            key, value, status = parsed
            if key in parsed_updates and parsed_updates[key][:2] != (value, status):
                # Within-turn conflicts need a separate parser. Do not quietly
                # select the last string or create two same-turn state events.
                ambiguous_keys.add(key)
            parsed_updates[key] = (value, status, correction, raw.strip())
        for key, (value, status, is_correction, raw) in parsed_updates.items():
            if key in ambiguous_keys:
                self._unparsed.append({"turn_id": turn_id, "text": text, "reason": "within_turn_conflict", "key": key})
                continue
            update = {"key": key, "value": value, "status": status}
            current = self._state.snapshot()["facts"].get(key)
            if current and (current["value"] != value or current["status"] != status):
                if is_correction or current["status"] == "unknown":
                    update["supersedes"] = current["turn_id"]
                elif status == "unknown":
                    # Retraction to uncertainty requires an explicit correction;
                    # otherwise preserve the previous fact and flag the clause.
                    self._unparsed.append({"turn_id": turn_id, "text": raw, "reason": "uncertain_retraction_requires_correction"})
                    continue
                else:
                    update["status"] = "conflict"
            self._state.apply(update, turn_id)
        return self.snapshot()

    def snapshot(self) -> dict:
        return {**self._state.snapshot(), "unparsed": deepcopy(self._unparsed), "extractor_version": self.version}
