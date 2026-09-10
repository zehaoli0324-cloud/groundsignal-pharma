"""Local human-review console. Never admits or executes source-derived cases.

The browser exports candidate-review/v0.1 drafts; authoritative validation and
comparison remain in candidate_review. Console handoffs are unsigned proposals,
not credential checks, clinical approval, or runtime opportunity observations.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .candidate_review import _blank_review, _json, build_review_packet, validate_review

ASSETS = Path(__file__).resolve().parent / "clinical_console_assets"
FLAGS = {"formal_approval": False, "clinical_gold": False,
         "dynamic_scenario_ready": False, "s6_automatic_trust": "BLOCKED"}


def independent_packet(original: dict) -> dict:
    """Remove all prior review decisions without changing immutable evidence."""
    validate_review(original, original)
    packet = deepcopy(original)
    packet["reviewer_id"] = ""
    for item in packet["items"]:
        item["review"] = _blank_review(item["fact_draft"])
    validate_review(original, packet)
    return packet


def demo_packet() -> dict:
    # Entirely synthetic; no patient source, diagnosis, or treatment guidance.
    dialogues = [{"dialogue": "console-synthetic-1", "information": [
        {"turn": 1, "role": "patient", "sentence": "帮我整理记录，开始时间是昨天。", "actions": [
            {"text": "昨天", "range": [12, 13], "intent": "Inform", "slot": "time", "value1": "", "value2": ""}]},
        {"turn": 2, "role": "doctor", "sentence": "请核对记录的时间。", "actions": []},
        {"turn": 3, "role": "patient", "sentence": "更正，开始时间是前天。", "actions": [
            {"text": "前天", "range": [8, 9], "intent": "Inform", "slot": "time", "value1": "", "value2": ""}]},
    ]}]
    return build_review_packet(dialogues, ["console-synthetic-1"], {"synthetic": True})


def render_console(original: dict | None = None) -> str:
    packet = independent_packet(original) if original is not None else None
    payload = json.dumps({"packet": packet, "demo": demo_packet()}, ensure_ascii=False, allow_nan=False)
    for char, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                          ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(char, escaped)
    return (ASSETS.joinpath("index.html").read_text(encoding="utf-8")
            .replace("/* CONSOLE_CSS */", ASSETS.joinpath("console.css").read_text(encoding="utf-8"))
            .replace("/* CONSOLE_CORE */", ASSETS.joinpath("core.js").read_text(encoding="utf-8"))
            .replace("/* CONSOLE_APP */", ASSETS.joinpath("app.js").read_text(encoding="utf-8"))
            .replace("/* CONSOLE_CHOICES */", ASSETS.joinpath("choices.js").read_text(encoding="utf-8"))
            .replace("__CONSOLE_DATA__", payload))


def validate_handoff(original: dict, review: dict, handoff: dict) -> dict:
    """Validate an unsigned planning sidecar, without promoting trust."""
    result = validate_review(original, review)
    if handoff.get("schema_version") != "clinical-console-handoff/v0.1":
        raise ValueError("unsupported handoff schema")
    if (handoff.get("packet_sha256") != original["packet_sha256"]
            or handoff.get("reviewer_id") != review["reviewer_id"]
            or not review["reviewer_id"].strip()):
        raise ValueError("handoff source or reviewer mismatch")
    if any(handoff.get(key) != value or type(handoff.get(key)) is not type(value)
           for key, value in FLAGS.items()):
        raise ValueError("handoff cannot grant admission")
    if handoff.get("authority") != "self_declared_unsigned_not_approval":
        raise ValueError("handoff must remain unsigned and non-authoritative")
    if handoff.get("runtime_observations") != 0 or type(handoff.get("runtime_observations")) is not int:
        raise ValueError("planning cannot claim runtime observations")
    expected = {(item["candidate_id"], row["criterion_id"]) for item in original["items"]
                for row in item["review"]["rubrics"]}
    seen = set()
    for row in handoff.get("opportunity_plans", []):
        key = (row.get("candidate_id"), row.get("criterion_id"))
        if key not in expected or key in seen:
            raise ValueError("unknown or duplicate planning rule")
        seen.add(key)
        if row.get("status") not in {"unreviewed", "proposed", "not_applicable"}:
            raise ValueError("invalid planning status")
        if any(not isinstance(row.get(field), str) for field in ("trigger", "response", "deadline", "reason")):
            raise ValueError("planning fields must be text")
        if row["status"] == "proposed" and any(not row[field].strip() for field in ("trigger", "response", "deadline", "reason")):
            raise ValueError("proposed plan requires trigger, response, deadline, reason")
        if row["status"] == "not_applicable" and not row["reason"].strip():
            raise ValueError("inapplicable plan requires reason")
    if seen != expected:
        raise ValueError("handoff must preserve all planning rules")
    return {"schema_version": "clinical-console-handoff-validation/v0.1", "structurally_valid": True,
            "local_only": True, "candidate_counts": result["counts"], "plan_count": len(seen),
            "clinical_credentials_verified": False, "independence_verified": False, **FLAGS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render")
    render.add_argument("--original", type=Path)
    render.add_argument("--out", type=Path, required=True)
    check = sub.add_parser("validate-handoff")
    for field in ("original", "review", "handoff"):
        check.add_argument("--" + field, type=Path, required=True)
    choices = sub.add_parser("validate-choices")
    choices.add_argument("--original", type=Path, required=True)
    choices.add_argument("--answers", type=Path, required=True)
    choices.add_argument("--review-out", type=Path)
    comparison = sub.add_parser("compare-choices")
    for field in ("original", "answers-a", "answers-b"):
        comparison.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    if args.command == "render":
        original = json.loads(args.original.read_text(encoding="utf-8")) if args.original else None
        # Real source-containing HTML may only be generated in ignored local/.
        local_root = Path(__file__).resolve().parents[2] / "medical/patient-eval/local"
        if original and not args.out.resolve().is_relative_to(local_root.resolve()):
            raise ValueError("source-containing console must stay in ignored medical/patient-eval/local/")
        html = render_console(original)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(html)
        print("Console written; no case executed or admitted.")
    elif args.command == "validate-choices":
        from .clinical_console_choices import validate_choices
        result, review = validate_choices(json.loads(args.original.read_text(encoding="utf-8")),
                                          json.loads(args.answers.read_text(encoding="utf-8")))
        if args.review_out:
            local_root = Path(__file__).resolve().parents[2] / "medical/patient-eval/local"
            if not args.review_out.resolve().is_relative_to(local_root.resolve()):
                raise ValueError("source-containing review must stay in ignored medical/patient-eval/local/")
            args.review_out.parent.mkdir(parents=True, exist_ok=True)
            with args.review_out.open("x", encoding="utf-8") as stream:
                stream.write(_json(review))
        print(_json(result), end="")
    elif args.command == "compare-choices":
        from .clinical_console_choices import compare_choices
        result = compare_choices(*(json.loads(getattr(args, field).read_text(encoding="utf-8"))
                                   for field in ("original", "answers_a", "answers_b")))
        print(_json(result), end="")
    else:
        result = validate_handoff(*(json.loads(getattr(args, field).read_text(encoding="utf-8"))
                                    for field in ("original", "review", "handoff")))
        print(_json(result), end="")


if __name__ == "__main__":
    main()
