"""Run with ``python -m scripts.patient_eval.pilot_cli --help``."""

import argparse
import json
from pathlib import Path

from .agreement import rater_agreement
from .cli import read_json, save_bundle
from .contracts import require
from .pilot import (DEFAULT_PILOT, advance_collection, apply_review, compare_intervention, load_pilot_suite, make_review_packet,
                    new_collection, score_pilot, write_new_json)


class ProtocolFixtureClient:
    """A visible-history-only question checklist, not a medical model.

    It deliberately has no scenario argument and cannot read private facts or
    expected outcomes. This demonstrates simulator branching and plumbing.
    """
    model = "protocol-fixture-v0.2"
    platform = "development/protocol-fixture"

    def public_config(self):
        return {"model": self.model, "transport": "offline_fixture", "clinical_model": False}

    def __call__(self, messages):
        index = sum(message["role"] == "assistant" for message in messages)
        prompts = [
            "请问这是谁的情况、咨询对象是谁？什么症状、药名、报告项目或具体说法需要核对？",
            "请问症状开始时间、服药时间、报告日期、上次咨询日期、截图转发日期分别是什么？是否发热？",
            "请问药名和成分是否清楚？报告项目名、原文发布日期、期间是否变化、信息来源是什么？",
            "请问观察记录、随访内容、两个家人的情况、是否服药和原文内容分别是什么？",
            "请用自己的话复述你对这些信息的理解；未知信息不能当成确定结论。",
            "我会保留已经说明的不确定性和更正，不据这些片段给出诊断或用药保证。你还有什么需要核对？",
        ]
        return {"content": prompts[min(index, len(prompts) - 1)], "error": None,
                "attempts": [{"attempt": 1, "elapsed_seconds": 0.0, "error": None}], "usage": {}}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dynamic patient pilot v0.2; development only")
    commands = parser.add_subparsers(dest="command", required=True)
    names = ("validate", "demo", "study", "score", "compare", "review-packet", "apply-review", "collect-start", "collect-reply")
    children = {name: commands.add_parser(name) for name in names}
    for name, child in children.items():
        child.add_argument("--suite", default=str(DEFAULT_PILOT))
        if name != "validate":
            child.add_argument("--out", required=True)
    for name in ("demo", "study", "review-packet", "compare"):
        children[name].add_argument("--seed", type=int, default=7)
    for name in ("demo", "study"):
        children[name].add_argument("--repeats", type=int, default=1)
    for name in ("score", "compare", "review-packet", "apply-review"):
        children[name].add_argument("--sessions", required=True)
    children["apply-review"].add_argument("--packet", required=True)
    children["apply-review"].add_argument("--operator-key", required=True)
    children["compare"].add_argument("--criterion", required=True)
    real = children["study"]
    for name in ("base-url", "model", "key-env"):
        real.add_argument("--" + name, required=True)
    real.add_argument("--max-tokens", type=int, default=800)
    real.add_argument("--timeout", type=float, default=30)
    real.add_argument("--retries", type=int, default=1)
    start = children["collect-start"]
    for name in ("scenario", "metadata", "platform", "session-id"):
        start.add_argument("--" + name, required=True)
    reply = children["collect-reply"]
    reply.add_argument("--journal", required=True)
    reply.add_argument("--response-file")
    reply.add_argument("--finish", action="store_true")
    reply.add_argument("--target-error", action="store_true")
    submitted = reply.add_mutually_exclusive_group()
    submitted.add_argument("--patient-submitted", dest="patient_submitted", action="store_const", const=True, default=None)
    submitted.add_argument("--input-not-submitted", dest="patient_submitted", action="store_const", const=False)
    reply.add_argument("--requested-slots", help="operator-corrected comma-separated question slot IDs")
    reply.add_argument("--classification-note", help="required evidence note for manual question classification")
    agreement = commands.add_parser("agreement")
    for name in ("ratings", "reviewer-a", "reviewer-b", "out"):
        agreement.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "agreement":
            result = rater_agreement(read_json(args.ratings), args.reviewer_a, args.reviewer_b)
            write_new_json(args.out, result)
        else:
            suite = load_pilot_suite(args.suite)
            by_id = {s["scenario_id"]: s for s in suite["scenarios"]}
            if args.command == "validate":
                result = {"scope": suite["scope"], "scenarios": len(by_id),
                          "families": len({s["family_id"] for s in suite["scenarios"]})}
            elif args.command in {"demo", "study"}:
                from .study import run_study
                from .transport import ChatClient
                client = ProtocolFixtureClient() if args.command == "demo" else ChatClient(
                    args.base_url, args.model, args.key_env, timeout=args.timeout,
                    retries=args.retries, max_tokens=args.max_tokens)
                run_study(suite, client, args.out, repeats=args.repeats, seed=args.seed)
                sessions = read_json(Path(args.out) / "sessions.json")
                bundle = score_pilot(suite, sessions)
                save_bundle(Path(args.out) / "evaluation", bundle)
                result = {"out": args.out, "sessions": len(sessions), "clinical_review": "pending",
                          "real_model_called": args.command == "study"}
            elif args.command == "score":
                require(not Path(args.out).exists(), "report output already exists")
                bundle = score_pilot(suite, read_json(args.sessions))
                save_bundle(args.out, bundle)
                result = {"out": args.out, "sessions": len(bundle["sessions"])}
            elif args.command == "compare":
                result = compare_intervention(suite, read_json(args.sessions), args.criterion, seed=args.seed)
                write_new_json(args.out, result)
            elif args.command == "review-packet":
                result = make_review_packet(suite, read_json(args.sessions), args.out, seed=args.seed)
            elif args.command == "apply-review":
                sessions = apply_review(suite, read_json(args.sessions), read_json(args.packet), read_json(args.operator_key))
                write_new_json(args.out, sessions)
                result = {"out": args.out, "sessions": len(sessions), "clinical_truth": "human_adjudicated_only"}
            elif args.command == "collect-start":
                require(args.scenario in by_id, "unknown scenario")
                journal = new_collection(by_id[args.scenario], read_json(args.metadata), args.platform, args.session_id)
                write_new_json(args.out, journal)
                result = {"journal": args.out, "next_patient_message": journal["next_patient_message"]}
            else:
                journal = read_json(args.journal)
                require(journal["session"]["scenario_id"] in by_id, "unknown journal scenario")
                require(bool(args.response_file) != args.target_error,
                        "provide exactly one of --response-file or --target-error")
                content = Path(args.response_file).read_text(encoding="utf-8") if args.response_file else ""
                updated = advance_collection(by_id[journal["session"]["scenario_id"]], journal, content,
                                             finish=args.finish, target_error=args.target_error,
                                             requested_slots=args.requested_slots.split(",") if args.requested_slots is not None else None,
                                             classification_note=args.classification_note, patient_submitted=args.patient_submitted)
                write_new_json(args.out, updated)
                result = {"journal": args.out, "done": updated["done"], "next_patient_message": updated["next_patient_message"]}
                if updated["done"]:
                    session_path = str(Path(args.out).with_suffix(".sessions.json"))
                    write_new_json(session_path, [updated["session"]])
                    result["sessions_file"] = session_path
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"patient-pilot: {error}\n")


if __name__ == "__main__":
    main()
