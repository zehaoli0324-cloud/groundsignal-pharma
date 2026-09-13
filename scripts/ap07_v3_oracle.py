"""AP07 v3 Oracle node activation (N0-N5 minimum slice).

The Oracle answers one narrow question: *given only the facts actually
disclosed in the visible prefix up to the target turn, which nodes activate,
and where is the evidence?*

Design boundaries, all enforced by ``tests/ap07_v3/test_node_activation.py``:

* Activation reads structured ``fact_ids`` on user turns. Free text — including
  text that merely mentions a symptom — never activates a node, so keyword
  matching cannot become a clinical verdict.
* Hidden scenario facts are never consulted. They exist for environment
  verification only.
* Activation grants **no score**. This module exposes no grading scale, keeps
  the node states separate from ``criteria.json``'s C04/C05/C06/C10 and the
  medication criteria, and produces no ``clinical_status``.
* ``unknown`` (asked but not disclosed) and ``untriggered`` (never touched) are
  distinct states. Nodes may be skipped, and an action may be indicated while
  intake continues in parallel.

Everything here is offline: no model is contacted and no clinical judgment is
made.
"""

import json
from pathlib import Path

from .ap07_v3_runner import AP07_VERSION

NODES_FILENAME = "nodes.json"

# N0 (opening) has no fact prerequisite; it is active whenever the visible
# prefix contains at least one user turn (the patient's opening message).
OPENING_NODE = "N0"

ACTIVATED = "activated"
UNTRIGGERED = "untriggered"
UNKNOWN = "unknown"
ELIGIBLE = "eligible"

# States a node may report. Deliberately excludes any scored state.
ALLOWED_STATES = frozenset({ACTIVATED, UNTRIGGERED, UNKNOWN, ELIGIBLE})


def load_node_declaration(root=None):
    """Load the frozen N0-N5 declaration for AP07-base."""
    base = (
        Path(root)
        if root is not None
        else Path(__file__).resolve().parent.parent / "benchmark" / AP07_VERSION
    )
    return json.loads((Path(base) / NODES_FILENAME).read_text(encoding="utf-8"))


def _visible_facts(turns):
    """Collect disclosed fact ids, plus facts that were asked and left unknown.

    ``fact_status`` is the structured channel a simulator uses to record that a
    fact was raised but answered with "不清楚". It is kept strictly separate
    from disclosure.
    """
    visible = []
    unknown = []
    for turn in turns:
        if turn.get("role") != "user":
            continue
        status = turn.get("fact_status") or {}
        for fact_id in turn.get("fact_ids", []):
            if status.get(fact_id) in {"unknown", "unclear", None} and fact_id not in visible:
                if status.get(fact_id) in {"unknown", "unclear"}:
                    unknown.append(fact_id)
                    continue
            if fact_id not in visible:
                visible.append(fact_id)
    return visible, unknown


def _visible_events(turns):
    events = []
    for turn in turns:
        if turn.get("role") != "user":
            continue
        event_id = turn.get("event_id")
        if event_id and event_id not in events:
            events.append(event_id)
    return events


def activate_nodes(turns, *, scenario_id="AP07-base", allow_parallel_intake=False):
    """Activate N0-N5 for ``scenario_id`` from the visible prefix only.

    Returns a report of node states with cited evidence. No score, no clinical
    verdict, no hidden facts.
    """
    declaration = load_node_declaration()
    if scenario_id != declaration["scenario_id"]:
        raise ValueError(f"unknown scenario: {scenario_id!r}")

    visible, unknown = _visible_facts(turns)
    events = _visible_events(turns)
    visible_set = set(visible)

    activated = []
    nodes = []
    has_user_turn = any(turn.get("role") == "user" for turn in turns)
    for node in declaration["nodes"]:
        required = set(node.get("requires_facts", []))
        required_events = set(node.get("requires_events", []))
        missing_facts = required - visible_set
        missing_events = required_events - set(events)

        if node["node_id"] == OPENING_NODE and not has_user_turn:
            # No visible patient turn yet: nothing has happened.
            state = UNTRIGGERED
        elif not missing_facts and not missing_events:
            state = ELIGIBLE if node["node_id"] == "N5" else ACTIVATED
        elif required & set(unknown):
            state = UNKNOWN
        else:
            state = UNTRIGGERED

        entry = {
            "node_id": node["node_id"],
            "kind": node["kind"],
            "state": state,
            "cited_fact_ids": sorted(required & visible_set),
            "cited_event_ids": sorted(required_events & set(events)),
        }
        nodes.append(entry)
        if state == ACTIVATED:
            entry_evidence = _evidence_for(turns, required, required_events)
            entry["evidence"] = entry_evidence
            activated.append(entry)

    n5 = next(entry for entry in nodes if entry["node_id"] == "N5")
    n5["evidence"] = {"turn_id": turns[-1]["turn_id"] if turns else None, "disclosure_log_index": len(turns) - 1}

    action_node = declaration.get("action_indicated_node")
    return {
        "scenario_id": scenario_id,
        "version": declaration["version"],
        "release_stage": declaration["release_stage"],
        "nodes": nodes,
        "activated": activated,
        "action_indicated": action_node in {n["node_id"] for n in activated},
        "intake_may_continue": bool(allow_parallel_intake),
    }


def _evidence_for(turns, required_facts, required_events):
    """First visible turn that discloses a required fact/event."""
    for index, turn in enumerate(turns):
        if turn.get("role") != "user":
            continue
        if set(turn.get("fact_ids", [])) & required_facts:
            return {"turn_id": turn["turn_id"], "disclosure_log_index": index}
        if turn.get("event_id") in required_events:
            return {"turn_id": turn["turn_id"], "disclosure_log_index": index}
    return {"turn_id": None, "disclosure_log_index": -1}
