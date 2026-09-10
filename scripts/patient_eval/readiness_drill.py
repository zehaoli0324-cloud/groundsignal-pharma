"""Offline engineering drill; fixed synthetic data and local scripted responses only.

Runs the existing study implementation. Recovery here means a separately labelled
fresh replay; the production runner still has no resume support. No model score,
clinical approval, external request or personal-skill certification is produced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .study import run_dialogue, run_study, _write_json


def synthetic_suite():
    return {"scope": "development_only", "scenarios": [{
        "scenario_id": "readiness.onset-correction", "family_id": "readiness-synthetic",
        "variant": "explicit-correction", "protocol_id": "readiness-drill/v0.1",
        "source": "synthetic", "split": "development", "criteria": [],
        "patient": {
            "initial_user_message": "症状开始时间是昨天。", "initial_disclosed": ["onset"],
            "facts": {"onset": {"value": "昨天", "status": "confirmed",
                "answer": "症状开始时间是昨天。", "ask_patterns": ["开始时间"]}},
            "events": [{"id": "correct-onset", "kind": "correction", "after_disclosed": ["onset"],
                "min_assistant_turn": 1, "content": "更正，症状开始时间是今天。",
                "updates": [{"slot": "onset", "value": "今天", "status": "confirmed",
                             "answer": "症状开始时间是今天。"}]}],
            "max_assistant_turns": 3, "closing_message": "记录结束。",
        }}]}


class ScriptedClient:
    platform = "local/scripted-fixture"
    model = "scripted-fixture-not-a-model"

    def __init__(self, mode="normal", crash_after=None):
        self.mode, self.crash_after, self.calls = mode, crash_after, 0

    def public_config(self):
        return {"model": self.model, "platform": self.platform, "mode": self.mode,
                "crash_after": self.crash_after, "external_calls": False}

    def __call__(self, messages):
        self.calls += 1
        if self.crash_after is not None and self.calls > self.crash_after:
            raise KeyboardInterrupt("intentional local drill interruption")
        if self.mode == "timeout":
            raise TimeoutError("intentional local timeout")
        if self.mode == "invalid_adapter":
            return []
        return {"content": "" if self.mode == "empty" else "请继续补充记录。",
                "error": None, "attempts": [{"attempt": 1, "error": None, "elapsed_seconds": 0}],
                "usage": {}}


def _file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_drill(out):
    root = Path(out)
    root.mkdir(parents=True, exist_ok=False)
    suite = synthetic_suite()
    checks = []
    def check(name, passed, observed):
        checks.append({"check": name, "passed": bool(passed), "observed": observed})

    normal = ScriptedClient()
    manifest = run_study(suite, normal, root / "normal")
    check("normal_sessions_persisted", manifest["status"] == "completed" and manifest["completed_sessions"] == 2,
          {"persisted": manifest["completed_sessions"], "planned": manifest["planned_sessions"]})
    failure_statuses = {}
    for mode, expected in (("timeout", "target_error"), ("empty", "target_error"),
                           ("invalid_adapter", "measurement_invalid")):
        session = run_dialogue(suite["scenarios"][0], ScriptedClient(mode), "baseline")
        _write_json(root / (mode + ".json"), session)
        failure_statuses[mode] = session["status"]
        check(mode + "_classified", session["status"] == expected,
              {"status": session["status"], "termination": session["metadata"]["termination_reason"]})

    first_session = json.loads((root / "normal/session-0001.json").read_text())
    first_calls = sum(t["role"] == "assistant" for t in first_session["turns"])
    interrupted = ScriptedClient(crash_after=first_calls)
    stopped = False
    try:
        run_study(suite, interrupted, root / "interrupted")
    except KeyboardInterrupt:
        stopped = True
    interrupted_manifest = json.loads((root / "interrupted/manifest.json").read_text())
    original_hash = _file_digest(root / "interrupted/session-0001.json")
    check("interruption_preserves_checkpoint", stopped and interrupted_manifest["completed_sessions"] == 1
          and len(list((root / "interrupted").glob("session-*.json"))) == 1,
          {"persisted": interrupted_manifest["completed_sessions"], "planned": interrupted_manifest["planned_sessions"],
           "manifest_status": interrupted_manifest["status"]})
    for label, client in (("same_config", ScriptedClient(crash_after=first_calls)),
                          ("changed_config", ScriptedClient(mode="empty"))):
        rejected = False
        try:
            run_study(suite, client, root / "interrupted")
        except FileExistsError:
            rejected = True
        check(label + "_directory_reuse_rejected", rejected and client.calls == 0
              and _file_digest(root / "interrupted/session-0001.json") == original_hash,
              {"rejected": rejected, "new_client_calls": client.calls, "old_checkpoint_unchanged":
               _file_digest(root / "interrupted/session-0001.json") == original_hash})

    replay = run_study(suite, ScriptedClient(), root / "fresh-replay")
    check("new_directory_replay", replay["completed_sessions"] == 2
          and _file_digest(root / "interrupted/session-0001.json") == original_hash,
          {"persisted": replay["completed_sessions"], "recovery_kind": "fresh_replay_not_resume"})
    check("resume_limitation_explicit", manifest["resume_supported"] is False
          and interrupted_manifest["resume_supported"] is False, {"resume_supported": False})
    report = {"schema_version": "readiness-drill/v0.1", "source": "synthetic",
              "passed": all(c["passed"] for c in checks), "checks_passed": sum(c["passed"] for c in checks),
              "checks_total": len(checks), "checks": checks, "external_model_calls": 0,
              "real_source_sessions": 0, "clinical_gold": False, "clinical_approval": False,
              "dynamic_scenario_ready": False, "s6_automatic_trust": "BLOCKED",
              "model_quality_assessed": False, "human_handoff_verified": False,
              "resume_supported": False, "interrupted_checkpoint_sha256": original_hash,
              "failure_statuses": failure_statuses,
              "interpretation": "Local scripted engineering evidence only. Fresh replay repeats completed work; it is not resume or a model improvement result."}
    _write_json(root / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory; existing paths are rejected")
    args = parser.parse_args()
    result = run_drill(args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
