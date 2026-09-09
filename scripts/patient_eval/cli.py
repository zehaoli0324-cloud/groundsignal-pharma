"""Command-line entry points; all generated patient text stays at --out."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import run_api
from .contracts import load_suite, require, validate_session
from .diagnosis import diagnose
from .importers import import_blackbox
from .reporting import paired_family_comparison, render_report
from .retrieval import rank_evidence
from .runner import replay_control, run_fixture
from .scoring import aggregate_scores, score_session


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "medical/patient-eval/development/scenarios.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evaluate_sessions(suite, sessions, controls=None):
    scenarios = {scenario["scenario_id"]: scenario for scenario in suite["scenarios"]}
    controls = controls or {}
    require(isinstance(controls, dict), "controls must map baseline session IDs to control lists")
    require(set(controls) <= {session.get("session_id") for session in sessions}, "controls reference unknown baseline sessions")
    scores, diagnoses, normalized_sessions = [], [], []
    ids = set()
    for session in sessions:
        validate_session(session)
        require(session["session_id"] not in ids, "duplicate session_id")
        ids.add(session["session_id"])
        require(session["scenario_id"] in scenarios, "unknown scenario_id")
        scenario = scenarios[session["scenario_id"]]
        if session["observability"] == "black_box":
            session = import_blackbox(session)
        normalized_sessions.append(session)
        metadata = session.get("metadata", {})
        require(metadata.get("session_protocol_id") == scenario["protocol_id"], "session protocol mismatch")
        lane = metadata.get("comparison_lane")
        require(lane in {"fixed_prefix", "free_dialogue"}, "unknown comparison lane")
        if lane == "fixed_prefix":
            expected = [{"role": t["role"], "content": t["content"]} for t in scenario["prefix"]]
            observed = [{"role": t["role"], "content": t["content"]} for t in session["turns"][:len(expected)]]
            require(expected == observed, "fixed-prefix mismatch: do not compare different visible inputs")
            expected_length = len(expected) + (1 if session["status"] == "completed" else 0)
            require(len(session["turns"]) == expected_length,
                    "fixed-prefix replay must contain exactly one target answer (or no answer on failure)")
        else:
            require(session["turns"][0]["content"] == scenario["prefix"][0]["content"],
                    "free dialogue must start from the specified patient question")
        score = score_session(session, scenario)
        scores.append(score)
        session_controls = controls.get(session["session_id"], [])
        require(isinstance(session_controls, list), "session controls must be a list")
        for control in session_controls:
            require(isinstance(control, dict) and isinstance(control.get("controlled_session"), dict),
                    "control requires a complete controlled_session")
            controlled = control["controlled_session"]
            validate_session(controlled)
            if controlled["observability"] == "black_box":
                control["controlled_session"] = import_blackbox(controlled)
        diagnoses.append(diagnose(session, score, session_controls))
    return {"title": "GroundSignal 患者多轮评测报告", "scope": "development_only",
            "sessions": normalized_sessions, "scores": scores, "diagnoses": diagnoses, "controls": controls,
            "aggregate": aggregate_scores(scores)}


def save_bundle(out, bundle):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "sessions.json", bundle["sessions"])
    write_json(out / "results.json", bundle)
    (out / "report.html").write_text(render_report(bundle), encoding="utf-8")
    print(json.dumps({"report": str(out / "report.html"), "aggregate": bundle["aggregate"]},
                     ensure_ascii=False, indent=2))


def demo(suite, out):
    sessions, scores, diagnoses, rows, retrieval_probes = [], [], [], [], []
    for scenario in suite["scenarios"]:
        fault = run_fixture(scenario, drop_correction=True)
        restored = run_fixture(scenario)
        fault_score = score_session(fault, scenario)
        restored_score = score_session(restored, scenario)
        sessions.extend([fault, restored])
        scores.extend([fault_score, restored_score])
        diagnoses.extend([diagnose(fault, fault_score, replay_control(scenario, fault, restored)),
                          diagnose(restored, restored_score)])
        for session, score in ((fault, fault_score), (restored, restored_score)):
            state_results = [r for r in score["criterion_results"] if r["criterion_id"] == "state.latest"]
            require(len(state_results) == 1, "demo requires state.latest criterion")
            rows.append({"family_id": scenario["family_id"], "scenario_id": scenario["scenario_id"],
                         "variant": scenario["variant"], "platform": session["metadata"]["arm"], "repeat_id": 0,
                         "score": float(state_results[0]["outcome"] == "pass"), "comparison_lane": "fixed_prefix",
                         "protocol_id": scenario["protocol_id"]})
        request = scenario["retrieval"]
        ranked = rank_evidence(request["query"], request["passages"], top_k=1,
                               as_of=request["as_of"], population=request["population"])
        expected = next(c["expected"] for c in scenario["criteria"] if c.get("check") == "selected_evidence")
        retrieval_probes.append({"scenario_id": scenario["scenario_id"], "expected": expected,
                                 "insertion_order_top1": request["passages"][0]["id"],
                                 "bm25_filtered_top1": ranked[0]["id"] if ranked else None})
    comparison = paired_family_comparison(rows, "fault", "restored")
    comparison.update(metric="synthetic_state_record_accuracy", clinical_effect=False,
                      interpretation="只验证故意丢失纠正事件的可检出与恢复；确定性合成结果不能估计真实患者效果。")
    bundle = {"title": "GroundSignal 患者多轮评测 · 合成机制验证", "scope": "development_only",
              "sessions": sessions, "scores": scores, "diagnoses": diagnoses,
              "aggregate": aggregate_scores(scores), "comparison": comparison,
              "retrieval_probes": retrieval_probes,
              "implemented_modules": ["C3:mechanical_state", "C5:mechanical_retrieval"],
              "clinical_assessment": "pending_human_review", "formal_admission": "not_implemented"}
    save_bundle(out, bundle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Patient evaluation development tooling")
    commands = parser.add_subparsers(dest="command", required=True)
    demo_parser = commands.add_parser("demo", help="offline synthetic intervention/replay")
    api_parser = commands.add_parser("run-api", help="explicit network call for one response per fixed prefix")
    eval_parser = commands.add_parser("evaluate", help="score imported observations and render evidence report")
    for child in (demo_parser, api_parser, eval_parser):
        child.add_argument("--suite", default=str(DEFAULT_SUITE))
        child.add_argument("--out", required=True)
    for name in ("base-url", "model", "key-env"):
        api_parser.add_argument("--" + name, required=True)
    api_parser.add_argument("--timeout", type=float, default=30)
    api_parser.add_argument("--retries", type=int, default=1)
    eval_parser.add_argument("--sessions", required=True)
    eval_parser.add_argument("--controls", help="optional JSON mapping baseline session IDs to recorded controls")
    importer = commands.add_parser("import", help="validate operator-collected black-box records")
    importer.add_argument("--input", required=True)
    importer.add_argument("--out", required=True)
    compare = commands.add_parser("compare", help="family-paired comparison of predeclared scalar metrics")
    compare.add_argument("--rows", required=True)
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            records = read_json(args.input)
            records = records if isinstance(records, list) else [records]
            normalized = [import_blackbox(record) for record in records]
            for session in normalized:
                validate_session(session)
            write_json(args.out, normalized)
            print(f"Validated {len(normalized)} black-box sessions: {args.out}")
            return
        if args.command == "compare":
            result = paired_family_comparison(read_json(args.rows), args.baseline, args.candidate)
            write_json(args.out, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        suite = load_suite(args.suite)
        if args.command == "demo":
            demo(suite, args.out)
            return
        if args.command == "run-api":
            sessions = []
            # Checkpoint each paid result; an interruption does not erase completed calls.
            for scenario in suite["scenarios"]:
                sessions.append(run_api(scenario, base_url=args.base_url, model=args.model, key_env=args.key_env,
                                        timeout=args.timeout, retries=args.retries))
                write_json(Path(args.out) / "sessions.json", sessions)
        else:
            sessions = read_json(args.sessions)
            require(isinstance(sessions, list) and bool(sessions), "sessions must be a nonempty list")
        controls = read_json(args.controls) if args.command == "evaluate" and args.controls else None
        save_bundle(args.out, evaluate_sessions(suite, sessions, controls))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"patient-eval: {exc}\n")
