"""A provenance-preserving baseline for *visible*, structured patient facts.

This module does not extract facts from language or infer a clinical diagnosis.
An upstream, separately evaluated extractor or a human supplies each observation.
Unknown is represented by ``status='unknown', value=None``; it is never treated
as a negative finding. Changing a fact (including resolving unknown) requires an
explicit reference to its current observation. Contradictions can instead be
retained as unresolved conflicts. These rules make lost corrections measurable.
"""

from copy import deepcopy
from typing import Any


class FactState:
    """Keep current observations, unresolved alternatives, and complete history.

    ``apply`` accepts ``{key, value, status, supersedes?}``. A repeated observation
    can omit ``supersedes``. A changed observation must either declare a conflict
    or explicitly supersede the current turn for that key. Referring to an older
    turn is rejected even if it exists, preventing stale concurrent updates.

    ``snapshot`` returns a detached ``{'facts': {key: record}}`` mapping. Each
    record contains ``value``, ``status``, ``turn_id``, ``history``, and, only while
    unresolved, ``alternatives``. History is the provenance; no hidden simulator
    state, guessed negatives, or implicit correction is introduced here.
    """

    _STATUSES = frozenset({"confirmed", "unknown", "conflict"})
    _FIELDS = frozenset({"key", "value", "status", "supersedes"})

    def __init__(self) -> None:
        self._facts: dict[str, dict[str, Any]] = {}

    def apply(self, update: dict, turn_id: str) -> None:
        """Atomically validate and append one visible observation.

        Invalid updates raise ``ValueError`` and leave the state untouched.
        A turn may update several different keys, but cannot update one key twice.
        """
        if not isinstance(update, dict):
            raise ValueError("update must be a dictionary")
        if set(update) - self._FIELDS:
            raise ValueError("update contains unsupported fields")
        if not {"key", "value", "status"} <= set(update):
            raise ValueError("update requires key, value, and status")
        key, value, status = update["key"], update["value"], update["status"]
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must be a nonempty string")
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise ValueError("turn_id must be a nonempty string")
        if not isinstance(status, str) or status not in self._STATUSES:
            raise ValueError("status must be confirmed, unknown, or conflict")
        if status == "unknown" and value is not None:
            raise ValueError("unknown must have value=None; it is not negative")
        if status != "unknown" and value is None:
            raise ValueError("a missing value must be explicitly unknown")

        current = self._facts.get(key)
        supersedes = update.get("supersedes")
        if "supersedes" in update:
            if not isinstance(supersedes, str) or not supersedes.strip():
                raise ValueError("supersedes must be a nonempty turn_id")
            if current is None or supersedes != current["turn_id"]:
                raise ValueError("supersedes must reference the current turn for this key")
        if current is not None:
            if any(event["turn_id"] == turn_id for event in current["history"]):
                raise ValueError("a key can have only one observation per turn")
            same = status == current["status"] and value == current["value"]
            if supersedes is None and not same and status != "conflict":
                raise ValueError("changed facts require supersedes or explicit conflict")

        observation = {"value": deepcopy(value), "status": status, "turn_id": turn_id}
        if supersedes is not None:
            observation["supersedes"] = supersedes
        history = deepcopy(current["history"]) if current is not None else []
        history.append(observation)
        record = {
            "value": deepcopy(value),
            "status": status,
            "turn_id": turn_id,
            "history": history,
        }
        if status == "conflict":
            # A superseding conflict starts a new unresolved set. An ordinary
            # conflict retains the previous possibilities without selecting one.
            alternatives: list[Any] = []
            if current is not None and supersedes is None:
                if current["status"] == "conflict":
                    alternatives = deepcopy(current["alternatives"])
                elif current["status"] == "confirmed":
                    alternatives = [deepcopy(current["value"])]
            if not any(value == candidate for candidate in alternatives):
                alternatives.append(deepcopy(value))
            record["alternatives"] = alternatives
        self._facts[key] = record

    def snapshot(self) -> dict:
        """Return an independent copy; callers cannot mutate stored provenance."""
        return {"facts": deepcopy(self._facts)}
