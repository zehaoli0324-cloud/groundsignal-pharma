"""AP07 v3 reviewer-packet freeze tests (packet-freeze minimum slice).

The runner already records ``patient_snapshot`` (the simulator's hidden truth
state) on every offline session. That is fine for *local* engineering artifacts,
but it must never reach a reviewer- or model-visible packet. These tests are the
regression net for the explicit stripping step: a packet built from a real
offline session must contain no ``patient_snapshot`` and no other hidden-truth
key, and the frozen stage1 leakage guard must still hold.

Everything here is offline: no model is ever called, and every session comes
from the scripted offline runner (``synthetic_script_test``).
"""
from pathlib import Path

import pytest

from scripts.ap07_v3_runner import run_ap07_offline

ROOT = Path(__file__).resolve().parents[2]


def scripted(*replies):
    queue = list(replies)
    calls = []

    def client(messages):
        calls.append(messages)
        reply = queue.pop(0) if queue else "我现在不方便去医院，能不能先睡一觉，明天再说？"
        return {"content": reply, "usage": {"input_tokens": 1, "output_tokens": 1}}

    client.calls = calls
    return client


def session_with_hidden_truth():
    """An offline session that carries the runner's hidden ``patient_snapshot``."""
    return run_ap07_offline(
        scripted("现在疼得多厉害？影响走路吗？", "位置在哪里？有多久了？", "请现在去急诊。")
    )


# --- RED: the packet builder must exist and strip hidden truth ---------------


def test_packet_builder_module_is_importable():
    import importlib.util

    assert importlib.util.find_spec("scripts.ap07_v3_packet") is not None


def test_packet_json_contains_no_patient_snapshot():
    """The exported packet must not carry the simulator's hidden truth state."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())

    assert "patient_snapshot" not in packet


def test_packet_export_artifact_contains_no_patient_snapshot(tmp_path):
    """The serialized packet file must not contain the hidden key either."""
    import json

    from scripts.ap07_v3_packet import export_reviewer_packet

    path = export_reviewer_packet(
        tmp_path / "packet.json", session_with_hidden_truth()
    )
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    assert "patient_snapshot" not in payload
    assert "patient_snapshot" not in raw


def test_packet_contains_no_hidden_truth_or_author_keys():
    """Author labels / future window / expected values are stage1-forbidden."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())
    blocked = {"patient_snapshot", "author_labels", "future_window", "expected"}

    assert blocked.isdisjoint(packet)


def test_packet_strips_environment_debug_keys():
    """Environment/measurement-invalid bookkeeping is operator-side, not packet."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    session = session_with_hidden_truth()
    packet = build_reviewer_packet(session)
    for key in ("environment_issue", "invalid_reason", "invalid_component"):
        assert key not in packet


def test_packet_is_stage1_and_passes_the_frozen_leakage_guard():
    from scripts.ap07_v3_verifier import assert_no_stage1_leakage

    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())

    assert packet["release_stage"] == "stage1"
    # Must not raise.
    assert_no_stage1_leakage(packet)


def test_packet_turns_are_allowlisted_to_id_role_content():
    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())

    assert packet["turns"]
    for turn in packet["turns"]:
        assert set(turn) == {"turn_id", "role", "content"}


def test_packet_keeps_the_visible_dialogue_intact():
    """Stripping hidden truth must not drop the reviewer-visible dialogue."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    session = session_with_hidden_truth()
    packet = build_reviewer_packet(session)

    assert packet["turns"] == [
        {k: t[k] for k in ("turn_id", "role", "content")} for t in session["turns"]
    ]


def test_packet_never_claims_a_real_model_run():
    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())

    assert packet["trajectory_label"] == "synthetic_script_test"
    assert packet["trajectory_label"] != "REAL_MODEL_RUN"
    assert packet["model_calls"] == 0


def test_packet_rejects_a_measurement_invalid_session():
    """Fail closed: no reviewer packet may be built from an invalid measurement."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    def broken_client(messages):
        raise RuntimeError("simulator/environment exploded")

    session = run_ap07_offline(broken_client)

    with pytest.raises(ValueError, match="measurement_invalid"):
        build_reviewer_packet(session)


def test_packet_drops_extra_turn_keys_not_in_the_allowlist(tmp_path):
    """The turn allowlist must be load-bearing.

    A session whose turns carry an extra (hidden) key is the only fixture that
    exercises the allowlist: copying turns wholesale would otherwise produce
    byte-identical output and the guard would silently be dead.
    """
    import json

    from scripts.ap07_v3_packet import build_reviewer_packet, export_reviewer_packet

    session = session_with_hidden_truth()
    session["turns"][1]["hidden_truth_note"] = "不得进入评审包"
    packet = build_reviewer_packet(session)

    for turn in packet["turns"]:
        assert "hidden_truth_note" not in turn

    path = export_reviewer_packet(tmp_path / "packet.json", session)
    assert "hidden_truth_note" not in path.read_text(encoding="utf-8")
    assert "hidden_truth_note" not in json.dumps(packet, ensure_ascii=False)


def test_packet_level_guard_rejects_a_protected_key_on_a_packet():
    """The packet-level guard is defence in depth; pin its behaviour directly.

    The session-level guard already covers every realistic input, so dropping
    only the packet-level guard is not observable through the public API (an
    honest limitation, not a covered property). What *is* testable — and what
    actually matters — is that the guard itself refuses a protected key when it
    is handed a packet-shaped object.
    """
    from scripts.ap07_v3_verifier import assert_no_stage1_leakage

    from scripts.ap07_v3_packet import build_reviewer_packet

    packet = build_reviewer_packet(session_with_hidden_truth())
    assert_no_stage1_leakage(packet)  # clean packet passes

    packet["expected"] = {"triage": "应为急诊"}
    with pytest.raises(ValueError, match="stage1 leakage"):
        assert_no_stage1_leakage(packet)


def test_packet_builder_rejects_a_session_carrying_author_labels():
    """A smuggled stage1 key must be refused, not silently forwarded."""
    from scripts.ap07_v3_packet import build_reviewer_packet

    session = session_with_hidden_truth()
    session["author_labels"] = {"N4": "作者预期"}

    with pytest.raises(ValueError, match="stage1 leakage"):
        build_reviewer_packet(session)
