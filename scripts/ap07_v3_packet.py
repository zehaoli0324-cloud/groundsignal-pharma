"""AP07 v3 reviewer-packet freeze.

The offline runner deliberately records the simulator's hidden truth state
(``patient_snapshot``) on a session so local engineering artifacts can be
audited against the frozen scenario. That state must never reach a reviewer- or
model-visible packet.

This module is the single, explicit export path between the two:

* it validates the session against the real runner contract (fail closed — an
  invalid measurement yields no packet at all);
* it builds the packet from an **allowlist** of session fields, so a hidden key
  added to the runner later cannot ride along by default;
* it then re-runs the frozen stage1 leakage guard as a second, independent net.

Everything here is offline: no model is contacted, no clinical score is
computed, and the packet stays at release stage ``stage1``.
"""

from copy import deepcopy

from .ap07_v3_runner import AP07_VERSION, SYNTHETIC_TRAJECTORY_LABEL
from .ap07_v3_verifier import assert_no_stage1_leakage

PACKET_VERSION = "ap07-reviewer-packet/v1"

# The only release stage this module is allowed to emit. Stage2 schema and its
# leakage boundary are intentionally NOT implemented here.
RELEASE_STAGE = "stage1"

# Session fields copied into the packet. Everything else — including
# ``patient_snapshot`` — is dropped by construction.
PACKET_SESSION_FIELDS = (
    "session_id",
    "scenario_id",
    "family_id",
    "variant",
    "platform",
    "observability",
    "status",
)

TURN_FIELDS = ("turn_id", "role", "content")

PACKET_DISCLAIMER = (
    "离线工程评审包：由脚本化离线客户端驱动，不是真实被测模型输出，"
    "不构成任何模型能力成绩或临床评分。不含隐藏真值、作者标签或未来窗口。"
)


def build_reviewer_packet(session, *, patient_eval_contracts=None):
    """Build a reviewer-visible packet from an offline runner session.

    Hidden truth (``patient_snapshot``), author labels and future-window fields
    are stripped by construction via an allowlist. A session that already
    carries a stage1-forbidden key is refused rather than silently forwarded.
    """
    if patient_eval_contracts is None:
        from .patient_eval.contracts import validate_session
    else:  # pragma: no cover - injection point kept for symmetry with tests
        validate_session = patient_eval_contracts

    if session.get("status") == "measurement_invalid":
        raise ValueError("measurement_invalid: no reviewer packet may be built from an invalid measurement")

    # Independent, fail-closed net: refuse a session that smuggled a protected key
    # (e.g. author_labels) instead of quietly dropping the dialogue around it.
    assert_no_stage1_leakage(session)

    # The session contract is the trust boundary the runner already uses.
    validate_session(session)

    packet = {field: session[field] for field in PACKET_SESSION_FIELDS}
    packet.update(
        packet_version=PACKET_VERSION,
        benchmark_version=AP07_VERSION,
        release_stage=RELEASE_STAGE,
        trajectory_label=SYNTHETIC_TRAJECTORY_LABEL,
        model_calls=0,
        platform="offline_scripted",
        turns=[{key: turn[key] for key in TURN_FIELDS} for turn in session["turns"]],
        disclosure_log=deepcopy(session.get("disclosure_log", [])),
        packet_disclaimer=PACKET_DISCLAIMER,
    )
    # Belt and braces: the finished packet must itself clear the frozen guard.
    assert_no_stage1_leakage(packet)
    return packet


def export_reviewer_packet(path, session):
    """Write a reviewer packet to ``path`` and return the path.

    ``patient_snapshot`` is never serialized because the packet is built from
    the allowlisted structure above, not from the raw session.
    """
    import json
    from pathlib import Path

    payload = build_reviewer_packet(session)
    out = Path(path)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
