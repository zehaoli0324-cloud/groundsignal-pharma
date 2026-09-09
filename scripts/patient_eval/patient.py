"""Deterministic, question-dependent patient disclosure for development studies.

The simulator receives a patient specification, never a scenario's scoring
criteria, expected answers, model identity, or injected-fault labels. Its small
state machine discloses only explicitly requested facts and scheduled events.
Natural-language matching is a conservative *collection aid*, not a clinical
understanding model or a scoring rule. An operator can supply requested_slots
when reviewing an unfamiliar question; that decision belongs in the run trace.

Only ``content`` is patient speech. ``disclosed``, intent decisions, event IDs
and ``snapshot`` are operator-side records, never target messages.
"""

from __future__ import annotations

from copy import deepcopy
import math
from .patient_intent import (
    CLASSIFIER_VERSIONS, DEFAULT_CLASSIFIER_VERSION, classify_requested_slots,
)


_SPEC_FIELDS = frozenset({
    "initial_user_message", "initial_disclosed", "facts", "events",
    "max_assistant_turns", "closing_message",
})
_FACT_FIELDS = frozenset({"value", "status", "answer", "ask_patterns"})
_EVENT_FIELDS = frozenset({
    "id", "kind", "after_disclosed", "min_assistant_turn", "content", "updates",
})
_UPDATE_FIELDS = frozenset({"slot", "value", "status", "answer"})
_UNMATCHED = "我不确定你具体想问哪一项，能换个问法吗？"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _json_value(value: object) -> bool:
    """Accept actual JSON values, including finite numbers, without coercion."""
    if value is None or type(value) in {str, bool, int}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item) for key, item in value.items())
    return False


def _slot_list(value: object, facts: dict, label: str) -> None:
    _require(isinstance(value, list), f"{label} must be a list")
    _require(all(_nonempty(slot) for slot in value), f"{label} must contain slot IDs")
    _require(len(value) == len(set(value)), f"{label} contains duplicate slots")
    _require(set(value) <= set(facts), f"{label} references an unknown slot")


def _fact_value(value: object, status: object) -> None:
    _require(status in ("confirmed", "unknown"), "fact status must be confirmed or unknown")
    _require(_json_value(value), "fact value must be a finite JSON value")
    _require(status != "unknown" or value is None, "unknown must have value=None; it is not negative")
    _require(status != "confirmed" or value is not None, "a missing fact must be explicitly unknown")


def validate_patient_spec(spec: dict) -> None:
    """Reject malformed or mixed patient/scorer specifications at the boundary."""
    _require(isinstance(spec, dict), "patient specification must be an object")
    _require(set(spec) == _SPEC_FIELDS, "patient specification contains missing or unsupported fields")
    for field in ("initial_user_message", "closing_message"):
        _require(_nonempty(spec[field]), f"{field} must be nonempty")
    _require(type(spec["max_assistant_turns"]) is int and spec["max_assistant_turns"] >= 1,
             "max_assistant_turns must be a positive integer")
    facts = spec["facts"]
    _require(isinstance(facts, dict) and bool(facts), "facts must be a nonempty object")
    for slot, fact in facts.items():
        _require(_nonempty(slot), "fact slot ID must be nonempty")
        _require(isinstance(fact, dict) and set(fact) == _FACT_FIELDS,
                 "fact contains missing or unsupported fields")
        _fact_value(fact["value"], fact["status"])
        _require(_nonempty(fact["answer"]), "fact answer must be nonempty")
        patterns = fact["ask_patterns"]
        _require(isinstance(patterns, list) and bool(patterns)
                 and all(_nonempty(pattern) for pattern in patterns),
                 "ask_patterns must contain nonempty literal strings")
        _require(len(set(patterns)) == len(patterns), "duplicate ask_patterns")
    _slot_list(spec["initial_disclosed"], facts, "initial_disclosed")
    _require(isinstance(spec["events"], list), "events must be a list")
    ids = set()
    for event in spec["events"]:
        _require(isinstance(event, dict) and set(event) == _EVENT_FIELDS,
                 "event contains missing or unsupported fields")
        _require(_nonempty(event["id"]) and event["id"] not in ids, "invalid or duplicate event ID")
        ids.add(event["id"])
        _require(event["kind"] in ("correction", "pressure", "teach_back"), "unknown event kind")
        _slot_list(event["after_disclosed"], facts, "after_disclosed")
        _require(type(event["min_assistant_turn"]) is int and event["min_assistant_turn"] >= 1,
                 "min_assistant_turn must be a positive integer")
        _require(event["min_assistant_turn"] < spec["max_assistant_turns"],
                 "event cannot start at or after the final assistant turn")
        _require(_nonempty(event["content"]), "event content must be nonempty")
        _require(isinstance(event["updates"], list), "event updates must be a list")
        _require(bool(event["updates"]) == (event["kind"] == "correction"),
                 "only correction events have updates, and corrections need updates")
        updated = set()
        for update in event["updates"]:
            _require(isinstance(update, dict)
                     and {"slot", "value", "status"} <= set(update) <= _UPDATE_FIELDS,
                     "update contains missing or unsupported fields")
            slot = update["slot"]
            _require(_nonempty(slot) and slot in facts and slot not in updated,
                     "update references an unknown or duplicate slot")
            updated.add(slot)
            _fact_value(update["value"], update["status"])
            if "answer" in update:
                _require(_nonempty(update["answer"]), "updated answer must be nonempty")


class PatientSimulator:
    """A repeatable finite state machine with explicit disclosure provenance.

    Call opening() before respond(). Opening is idempotent. Each respond call
    represents one observed assistant turn. At max_assistant_turns the session
    ends *before* disclosing another fact/event, leaving the last visible turn
    as the target's answer. A terminal response has content=None; closing
    speech remains in the local log for an operator's collection worksheet.

    The next scheduled event has priority over answering new questions. It can
    fire only when its prerequisites were disclosed on earlier turns. A
    correction additionally requires every updated fact to have been disclosed.
    Missed prerequisites never trigger automatic disclosure. Events later in
    the list cannot jump over an untriggered earlier event.
    """

    def __init__(self, spec: dict, classifier_version: str = DEFAULT_CLASSIFIER_VERSION) -> None:
        validate_patient_spec(spec)
        _require(classifier_version in CLASSIFIER_VERSIONS, "unsupported patient classifier version")
        self._classifier_version = classifier_version
        self._spec = deepcopy(spec)
        self._facts = deepcopy(spec["facts"])
        self._opened = False
        self._disclosed: list[str] = []
        self._assistant_turn_count = 0
        self._next_event = 0
        self._event_log: list[dict] = []
        self._done = False
        self._stop_reason: str | None = None

    @property
    def classifier_version(self) -> str:
        """A session's rule version cannot be switched midway through replay."""
        return self._classifier_version

    def opening(self) -> dict:
        if not self._opened:
            self._opened = True
            self._disclosed.extend(self._spec["initial_disclosed"])
        return {
            "content": self._spec["initial_user_message"],
            "disclosed": list(self._spec["initial_disclosed"]),
            "event_ids": [],
            "done": False,
        }

    def _inferred_slots(self, text: str) -> list[str]:
        # Kept for callers inspecting the former private helper. Decisions are
        # produced and logged in respond(), without exposing them as speech.
        return classify_requested_slots(text, self._facts, self.classifier_version)["requested_slots"]

    def _response(self, content: str | None, classification: str,
                  disclosed: list[str] | None = None, event_ids: list[str] | None = None) -> dict:
        return {
            "content": content,
            "disclosed": list(disclosed or []),
            "event_ids": list(event_ids or []),
            "done": self._done,
            "stop_reason": self._stop_reason,
            "classification": classification,
            "classifier_version": self.classifier_version,
            # Like disclosed/event_ids, this is operator metadata. Only content
            # is patient speech and may enter the target conversation.
            "intent_decision": deepcopy(self._event_log[-1].get("intent_decision"))
            if self._event_log else None,
        }

    def _stop(self, reason: str, classification: str) -> dict:
        self._done = True
        self._stop_reason = reason
        self._event_log.append({
            "assistant_turn": self._assistant_turn_count,
            "kind": "stop",
            "classifier_version": self.classifier_version,
            "intent_decision": {"classifier_version": self.classifier_version,
                                "mode": "not_evaluated", "reason": reason},
            "reason": reason,
            "closing_message": self._spec["closing_message"],
            "not_reached_event_ids": [event["id"] for event in self._spec["events"][self._next_event:]],
        })
        return self._response(None, classification)

    def respond(self, assistant_text: str, requested_slots: list[str] | None = None,
                stop: bool = False) -> dict:
        _require(self._opened, "opening() must be called before respond()")
        _require(isinstance(assistant_text, str), "assistant_text must be a string")
        _require(type(stop) is bool, "stop must be a boolean")
        if requested_slots is not None:
            _slot_list(requested_slots, self._facts, "requested_slots")
        if self._done:
            return self._response(None, "stop")
        self._assistant_turn_count += 1
        if stop:
            return self._stop("target_stop", "stop")
        if self._assistant_turn_count >= self._spec["max_assistant_turns"]:
            return self._stop("turn_budget", "budget")

        events = self._spec["events"]
        if self._next_event < len(events):
            event = events[self._next_event]
            required = set(event["after_disclosed"]) | {update["slot"] for update in event["updates"]}
            if (self._assistant_turn_count >= event["min_assistant_turn"]
                    and required <= set(self._disclosed)):
                updated_slots = []
                for update in event["updates"]:
                    slot = update["slot"]
                    self._facts[slot]["value"] = deepcopy(update["value"])
                    self._facts[slot]["status"] = update["status"]
                    # If no short answer is supplied, repeat the authored
                    # correction on later questions, never the obsolete answer.
                    self._facts[slot]["answer"] = update.get("answer", event["content"])
                    updated_slots.append(slot)
                self._next_event += 1
                self._event_log.append({
                    "assistant_turn": self._assistant_turn_count,
                    "event_id": event["id"],
                    "kind": event["kind"],
                    "disclosed": list(updated_slots),
                    "classifier_version": self.classifier_version,
                    "intent_decision": {"classifier_version": self.classifier_version,
                                        "mode": "not_evaluated",
                                        "reason": "scheduled_event_preempted"},
                })
                return self._response(event["content"], "event", updated_slots, [event["id"]])

        if requested_slots is None:
            decision = classify_requested_slots(assistant_text, self._facts, self.classifier_version)
            decision["mode"] = "automatic"
        else:
            decision = {"classifier_version": self.classifier_version, "mode": "explicit_override",
                        "requested_slots": list(requested_slots), "clauses": [],
                        "reason": "operator_supplied_slots"}
        slots = decision["requested_slots"]
        if not slots:
            self._event_log.append({
                "assistant_turn": self._assistant_turn_count,
                "kind": "unmatched",
                "mapping": "explicit" if requested_slots is not None else self.classifier_version,
                "classifier_version": self.classifier_version,
                "intent_decision": deepcopy(decision),
            })
            return self._response(_UNMATCHED, "unmatched")
        for slot in slots:
            if slot not in self._disclosed:
                self._disclosed.append(slot)
        self._event_log.append({
            "assistant_turn": self._assistant_turn_count,
            "kind": "question",
            "disclosed": list(slots),
            "mapping": "explicit" if requested_slots is not None else self.classifier_version,
            "classifier_version": self.classifier_version,
            "intent_decision": deepcopy(decision),
        })
        return self._response("\n".join(self._facts[slot]["answer"] for slot in slots), "question", slots)

    def snapshot(self) -> dict:
        """Detached operator-only state; NEVER include this in target messages."""
        return deepcopy({
            "classifier_version": self.classifier_version,
            "opened": self._opened,
            "assistant_turn_count": self._assistant_turn_count,
            "disclosed": self._disclosed,
            "facts": self._facts,
            "fired_event_ids": [event["id"] for event in self._spec["events"][:self._next_event]],
            "not_reached_event_ids": [event["id"] for event in self._spec["events"][self._next_event:]],
            "event_log": self._event_log,
            "done": self._done,
            "stop_reason": self._stop_reason,
        })
