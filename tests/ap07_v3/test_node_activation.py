"""AP07 v3 N0-N5 node activation minimum slice (RED-first).

The Oracle activates a node only from facts *actually disclosed in the visible
prefix* up to the target turn. Hidden scenario facts may be used for
environment verification only — never to activate a node.

These tests pin the activation contract for scenario ``AP07-base`` only:

* a node fires only when its declared prerequisite facts are visible;
* an undisclosed fact must never activate its node;
* asked-but-not-understood is distinguishable from not-asked;
* nodes may be skipped and an action may run in parallel with further intake
  (補問), so activation is *not* a fixed sequence;
* unknown and untriggered are explicit states, not silent passes;
* N5 is an end-eligibility *state*, not a clinical score;
* activation grants no score: the module exposes no grading scale and stays
  separate from ``criteria.json`` C04/C05/C06/C10.

Everything here is offline: no model is contacted, no clinical score exists.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NODES = ROOT / "benchmark" / "ap07-oracle-v3" / "nodes.json"

# The frozen fact ids for scenario AP07-base, mirrored from the runner.
VISIBLE_ALL = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]


def load_nodes():
    import json

    return json.loads(NODES.read_text(encoding="utf-8"))


def prefix(*fact_ids, event_ids=(), turn_role="user"):
    """A minimal visible prefix that discloses ``fact_ids`` in order."""
    turns = []
    for index, fact_id in enumerate(fact_ids, start=1):
        turns.append(
            {
                "turn_id": "u" + str(index),
                "role": turn_role,
                "content": "已披露文本",
                "fact_ids": [fact_id],
                "event_id": None,
            }
        )
    for index, event_id in enumerate(event_ids, start=len(turns) + 1):
        turns.append(
            {
                "turn_id": "u" + str(index),
                "role": "user",
                "content": "事件文本",
                "fact_ids": [],
                "event_id": event_id,
            }
        )
    return turns


# --- module surface ---------------------------------------------------------


def test_node_activation_module_importable():
    import importlib.util

    assert importlib.util.find_spec("scripts.ap07_v3_oracle") is not None


def test_nodes_declaration_file_exists_and_declares_n0_to_n5():
    data = load_nodes()
    ids = [node["node_id"] for node in data["nodes"]]

    assert data["version"] == "ap07-oracle-v3"
    assert data["scenario_id"] == "AP07-base"
    # The declared spine N0..N5 is present, plus the named intake nodes the
    # activation tests reference.
    assert {"N0", "N1", "N2", "N3", "N4", "N5"} <= set(ids)
    assert {"N_symptoms", "N_support"} <= set(ids)


def test_node_declaration_binds_the_frozen_scenario_and_no_release_stage_bump():
    data = load_nodes()

    # stage discipline is inherited from the verifier contract, not re-declared.
    assert data["release_stage"] == "stage1"
    assert data["source_facts"] == VISIBLE_ALL


# --- activation is driven ONLY by the visible prefix ------------------------


def test_node_activates_only_when_its_facts_are_visible():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"))
    ids = {n["node_id"] for n in result["activated"]}

    assert "N3" in ids
    # N0 is the opening node: it fires on the visible patient turn, not on facts.
    assert "N0" in ids
    # N1 (identity) needs F1, which was never disclosed.
    assert "N1" not in ids


def test_undisclosed_fact_never_activates_its_node():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"))
    ids = {n["node_id"] for n in result["activated"]}

    # F7 (regional/support) was never disclosed, so its node must not fire.
    assert "N_support" not in ids
    assert all("F7" not in n["cited_fact_ids"] for n in result["activated"])


def test_hidden_facts_cannot_activate_a_node():
    """Hidden scenario facts are consulted for verification only, never for
    activation.

    The previous fixture put ``hidden_facts`` on a *wrapper* dict that was
    never passed to the oracle, so it could not fail even if the oracle began
    reading a turn-level hidden channel (reviewer ``INJ-Y``: 18 passed). This
    fixture puts the hidden fact id on a **turn** the oracle actually receives,
    in a channel that is explicitly *not* disclosure: ``fact_ids`` stays empty
    and the id appears only under ``hidden_facts``.

    ``fact_ids`` is the disclosure channel — an id there legitimately activates
    its node, which is why the companion positive control
    ``test_visible_fact_id_does_activate_its_node`` is required; without it this
    guard could pass vacuously.
    """
    from scripts.ap07_v3_oracle import activate_nodes

    turns = prefix("F3")
    turns.append(
        {
            "turn_id": "u90",
            "role": "user",
            "content": "（环境侧事实，患者未披露）",
            "fact_ids": [],  # NOT disclosed through the ordinary channel
            "hidden_facts": ["F7"],  # environment-only channel
            "event_id": None,
        }
    )
    result = activate_nodes(turns)
    activated = {n["node_id"] for n in result["activated"]}

    assert "N_support" not in activated
    assert all("F7" not in n["cited_fact_ids"] for n in result["activated"])


def test_visible_fact_id_does_activate_its_node():
    """Positive control for the hidden-fact guard above.

    The same fact id that must be *ignored* when it arrives through a hidden
    channel must *activate* its node when it is genuinely disclosed in the
    visible prefix. Without this control the guard could pass vacuously: a
    node that never activates at all would satisfy
    ``test_hidden_facts_cannot_activate_a_node``.
    """
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3", "F7"))
    activated = {n["node_id"] for n in result["activated"]}

    assert "N_support" in activated
    support = next(n for n in result["activated"] if n["node_id"] == "N_support")
    assert "F7" in support["cited_fact_ids"]


def test_each_activation_cites_evidence_location():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F1", "F2", "F3"))

    for node in result["activated"]:
        # N0 has no fact prerequisite; every other activation must cite a turn.
        if node["node_id"] == "N0":
            continue
        assert node["evidence"]["turn_id"]
        assert node["evidence"]["disclosure_log_index"] >= 0


# --- not-asked vs asked-but-not-understood ----------------------------------


def test_unknown_state_is_distinct_from_untriggered():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"))
    states = {entry["node_id"]: entry["state"] for entry in result["nodes"]}

    assert states["N3"] == "activated"
    # A node whose required fact was asked but answered "不清楚" is unknown;
    # one that was never touched stays untriggered. They must not collapse.
    assert set(states.values()) <= {"activated", "untriggered", "unknown", "eligible"}
    assert "untriggered" in states.values()


def test_asked_but_not_disclosed_marks_unknown_not_activated():
    from scripts.ap07_v3_oracle import activate_nodes

    turns = prefix("F3")
    turns.append(
        {
            "turn_id": "u9",
            "role": "user",
            "content": "这点我现在不清楚。",
            "fact_ids": ["F4"],
            "fact_status": {"F4": "unknown"},
            "event_id": None,
        }
    )
    result = activate_nodes(turns)
    states = {entry["node_id"]: entry["state"] for entry in result["nodes"]}

    assert states["N_symptoms"] == "unknown"
    assert "N_symptoms" not in {n["node_id"] for n in result["activated"]}


# --- skip / overlap / parallel intake ---------------------------------------


def test_nodes_may_be_skipped():
    """A prefix that discloses F3 but never F2 must still activate triage."""
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"))

    assert "N2" in {entry["node_id"] for entry in result["nodes"] if entry["state"] == "untriggered"}
    assert "N3" in {n["node_id"] for n in result["activated"]}


def test_activation_allows_parallel_intake_after_action_demand():
    """An action may already be warranted while intake continues in parallel."""
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"), allow_parallel_intake=True)

    assert result["action_indicated"] is True
    assert result["intake_may_continue"] is True


# --- N5 end eligibility is a state, not a score -----------------------------


def test_n5_is_end_eligibility_state_only():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F3"))
    n5 = next(entry for entry in result["nodes"] if entry["node_id"] == "N5")

    assert n5["kind"] == "end_eligibility"
    assert "score" not in n5
    assert n5["state"] in {"eligible", "untriggered"}


def test_activation_produces_no_score_or_clinical_verdict():
    from scripts.ap07_v3_oracle import activate_nodes

    result = activate_nodes(prefix("F1", "F2", "F3", "F4", "F5", "F6", "F7"))

    assert "score" not in result
    assert "clinical_status" not in result
    for node in result["activated"]:
        assert "score" not in node


def test_nodes_declaration_does_not_restate_the_rubric_scale():
    """Node activation must not smuggle a second grading scale."""
    data = load_nodes()

    assert "criteria" not in data
    assert "scoring" not in data
    for node in data["nodes"]:
        assert "score" not in node
        assert "points" not in node


# --- negative: keyword matching must not drive activation -------------------


def test_free_text_mention_without_fact_ids_does_not_activate():
    """Activation reads structured fact ids, not keywords in the prose.

    N0 (opening) legitimately fires on the visible turn; every fact-dependent
    node must stay cold because no fact id was disclosed.
    """
    from scripts.ap07_v3_oracle import activate_nodes

    turns = [
        {
            "turn_id": "u1",
            "role": "user",
            "content": "我肚子很疼",  # mentions pain, carries no fact ids
            "fact_ids": [],
            "event_id": None,
        }
    ]
    result = activate_nodes(turns)

    assert {n["node_id"] for n in result["activated"]} == {"N0"}


def test_unknown_scenario_is_rejected():
    from scripts.ap07_v3_oracle import activate_nodes

    with pytest.raises(ValueError, match="unknown scenario"):
        activate_nodes(prefix("F3"), scenario_id="AP07-not-a-scenario")


def test_node_declaration_carries_a_review_dispute_section():
    """Rule ambiguities stay visible instead of being silently resolved."""
    data = load_nodes()

    assert data["disputes"]
    for dispute in data["disputes"]:
        assert dispute["id"]
        assert dispute["status"] == "pending_confirmation"


def test_omitted_medication_warning_is_not_a_major_event_from_omission_alone():
    data = load_nodes()
    by_id = {d["id"]: d for d in data["disputes"]}

    entry = by_id["omitted_medication_warning_vs_active_substitution"]
    assert entry["major_event_eligible_from_omission_alone"] is False
    assert entry["hospital_supervised_analgesia_excluded"] is True
