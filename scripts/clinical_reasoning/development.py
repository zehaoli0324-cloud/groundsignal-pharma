"""Small, offline action environment; it does not grade clinical reasoning.

Only model_view() is target-visible. The world, evaluation notes, actual tool
returns and fault settings belong to the operator. Structured actions are an
engineering interface, not evidence of natural-language question understanding.
"""
from copy import deepcopy
from hashlib import sha256
import json


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _require(ok, code):
    if not ok:
        raise ValueError(code)


def validate_case(case):
    _require(isinstance(case, dict), "CASE_OBJECT_REQUIRED")
    _require(set(case) == {"schema_version", "case_id", "family_id", "scope",
                          "clinical_review", "opening", "world", "evaluation"},
             "CASE_FIELDS_INVALID")
    _require(case["schema_version"] == "clinical-reasoning-development/v0.1",
             "SCHEMA_UNSUPPORTED")
    _require(case["scope"] == "synthetic_development", "DEVELOPMENT_ONLY")
    _require(case["clinical_review"] == "pending", "EXPERT_APPROVAL_NOT_IMPLEMENTED")
    for key in ("case_id", "family_id"):
        _require(isinstance(case[key], str) and bool(case[key]), "IDENTITY_INVALID")
    opening = case["opening"]
    _require(isinstance(opening, dict) and set(opening) == {"task", "context_extra"},
             "OPENING_FIELDS_INVALID")
    _require(isinstance(opening["task"], str) and bool(opening["task"].strip()),
             "TASK_REQUIRED")
    _require(isinstance(opening["context_extra"], str), "CONTEXT_INVALID")
    _require(isinstance(case["evaluation"], dict), "EVALUATION_INVALID")
    world = case["world"]
    _require(isinstance(world, dict) and set(world) == {"history", "records"},
             "WORLD_FIELDS_INVALID")
    for kind, entries in world.items():
        _require(isinstance(entries, list), "WORLD_ENTRIES_INVALID")
        queries = set()
        for item in entries:
            _require(isinstance(item, dict) and set(item) == {"query", "content"},
                     "WORLD_ENTRY_FIELDS_INVALID")
            _require(all(isinstance(item[k], str) and bool(item[k].strip())
                         for k in ("query", "content")), "WORLD_ENTRY_INVALID")
            _require(item["query"] not in queries, "DUPLICATE_WORLD_QUERY")
            queries.add(item["query"])
    digest(case)  # Reject non-JSON values and non-finite numbers.
    return True


def _diff(a, b, path=""):
    if type(a) is not type(b):
        return [path or "/"]
    if isinstance(a, dict):
        paths = []
        for key in sorted(a.keys() | b.keys()):
            escaped = key.replace("~", "~0").replace("/", "~1")
            child = path + "/" + escaped
            paths.extend([child] if key not in a or key not in b
                         else _diff(a[key], b[key], child))
        return paths
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        return [p for i, (x, y) in enumerate(zip(a, b))
                for p in _diff(x, y, path + "/" + str(i))]
    return [] if a == b else [path]


def validate_distractor_pair(base, variant):
    """Narrow registered experiment: only initial irrelevant context changes.

    Exact content equality is a mechanical check, not clinical equivalence or
    proof that a chosen distractor really is irrelevant.
    """
    validate_case(base)
    validate_case(variant)
    _require(base["case_id"] != variant["case_id"], "DISTINCT_CASE_IDS_REQUIRED")
    differences = [p for p in _diff(base, variant) if p != "/case_id"]
    _require(differences == ["/opening/context_extra"], "UNCONTROLLED_PAIR_DIFFERENCE")
    return {"mechanical_pair_valid": True, "clinical_equivalence": "unassessed",
            "changed_paths": differences, "base_sha256": digest(base),
            "variant_sha256": digest(variant)}


class DevelopmentSession:
    """A stateful, bounded world with actual returned/delivered separation."""

    def __init__(self, case, *, fault="none", action_budget=8):
        validate_case(case)
        _require(fault in ("none", "drop_record_delivery"), "FAULT_UNSUPPORTED")
        _require(type(action_budget) is int and 1 <= action_budget <= 40,
                 "BUDGET_INVALID")
        self._case = deepcopy(case)
        self._fault = fault
        self._budget = action_budget
        self._messages = [{"role": "user", "content": case["opening"]["task"]
                           + ("\n" + case["opening"]["context_extra"]
                              if case["opening"]["context_extra"] else "")}]
        self._events = []
        self._seen = set()
        self._closed = False
        self._termination = None

    def model_view(self):
        # Strict projection: no scenario/family identifiers, future fact menu,
        # evaluation fields, mutation labels, or raw un-delivered responses.
        return deepcopy({"messages": self._messages,
                         "action_interface": {
                             "ask": "query: 所需病史主题（本版仅精确匹配结构化主题）",
                             "record": "query: 所需资料名称（本版仅精确匹配结构化主题）",
                             "finish": "answer: 当前判断和下一步",
                             "handoff": "answer: 转交理由和当前信息"}})

    def operator_trace(self):
        return deepcopy(self._events)

    def step(self, action):
        _require(not self._closed, "SESSION_CLOSED")
        _require(isinstance(action, dict), "ACTION_OBJECT_REQUIRED")
        kind = action.get("kind")
        _require(isinstance(kind, str) and kind in ("ask", "record", "finish", "handoff"),
                 "ACTION_KIND_INVALID")
        terminal = kind in ("finish", "handoff")
        fields = {"action_id", "kind", "answer" if terminal else "query"}
        _require(set(action) == fields, "ACTION_FIELDS_INVALID")
        _require(all(isinstance(action[k], str) and bool(action[k].strip()) for k in fields),
                 "ACTION_VALUE_INVALID")
        _require(action["action_id"] not in self._seen, "DUPLICATE_ACTION_ID")
        # All fallible validation and copy work precedes the state mutation.
        before = digest(self.model_view())
        if terminal:
            raw = delivered = None
            status = "finished" if kind == "finish" else "handed_off"
            reply = {"role": "assistant", "content": action["answer"]}
        else:
            collection = "history" if kind == "ask" else "records"
            match = next((x for x in self._case["world"][collection]
                          if x["query"] == action["query"]), None)
            raw = None if match is None else match["content"]
            dropped = kind == "record" and raw is not None and self._fault == "drop_record_delivery"
            status = "unsupported" if match is None else ("delivery_failed" if dropped else "delivered")
            delivered = None if dropped else raw
            reply = {"role": "user" if kind == "ask" else "tool", "content":
                     delivered if delivered is not None else
                     ("资料传递失败，未获得可用内容。" if dropped else "该主题本版未支持，不能据此判断阴性。")}
        event = {"index": len(self._events) + 1, "action": deepcopy(action),
                 "case_sha256": digest(self._case), "before_view_sha256": before,
                 "returned_content": raw, "delivered_content": delivered,
                 "delivery_status": status, "fault_applied": status == "delivery_failed"}
        messages = deepcopy(self._messages)
        if not terminal:
            messages.append({"role": "assistant", "content": json.dumps(
                {"kind": kind, "query": action["query"]}, ensure_ascii=False)})
        messages.append(reply)
        self._messages = messages
        self._events.append(event)
        self._seen.add(action["action_id"])
        self._closed = terminal or len(self._events) >= self._budget
        self._termination = status if terminal else ("action_budget" if self._closed else None)
        return self.model_view()

    def report(self):
        return {"scope": "synthetic_development", "case_sha256": digest(self._case),
                "actions": len(self._events), "closed": self._closed,
                "termination": self._termination,
                "model_calls": 0, "clinical_review": "pending",
                "quality": None, "outcome": "unassessed", "serious_error": None,
                "causal_status": "not_evaluated"}
