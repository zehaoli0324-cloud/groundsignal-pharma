#!/usr/bin/env python3
"""Run GroundSignal dynamic patient scripts without external dependencies.

CLI examples:
  python pilot_runner.py --suite dynamic_patient_scripts_3_public.json --list
  python pilot_runner.py --suite dynamic_patient_scripts_3_public.json --case GS-DYN-001
  python pilot_runner.py --suite dynamic_patient_scripts_3_public.json --case GS-DYN-001 \
      --input-json sample_model_messages.json --output-jsonl run.jsonl

The runner simulates only the patient-side disclosure contract. It does not
call a model, assign clinical scores, or establish a clinical gold standard.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


class PatientScript:
    def __init__(self, case: dict[str, Any], run_id: str):
        self.case = deepcopy(case)
        self.run_id = run_id
        self.model_turn = 0
        self.disclosed: set[str] = set()
        self.fact_disclosed_at: dict[str, int] = {}
        self.events_emitted: set[str] = set()
        self.closed = False
        self.stop_reason: str | None = None
        self.records: list[dict[str, Any]] = []
        self._append_record(
            speaker="simulated_patient",
            content=self.case["opening"],
            record_type="opening",
            disclosed_fact_ids=[],
            triggered_rule_ids=["opening"],
        )

    def _append_record(
        self,
        *,
        speaker: str,
        content: str,
        record_type: str,
        disclosed_fact_ids: list[str] | None = None,
        triggered_rule_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "schema_version": "groundsignal-dynamic-run-record/v0.1",
            "run_id": self.run_id,
            "script_id": self.case["script_id"],
            "case_reference_id": self.case.get("case_reference_id", self.case["script_id"]),
            "family_id": self.case.get("family_id", self.case["script_id"]),
            "model_turn": self.model_turn,
            "speaker": speaker,
            "record_type": record_type,
            "content": content,
            "disclosed_fact_ids": disclosed_fact_ids or [],
            "triggered_rule_ids": triggered_rule_ids or [],
            "timestamp_utc": _now(),
            "state": self.state_snapshot(),
            "metadata": metadata or {},
        }
        self.records.append(record)
        return record

    def _pending_correction(self) -> bool:
        for event in self.case.get("scheduled_events", []):
            if event["event_id"] in self.events_emitted:
                continue
            is_correction = bool(event.get("correction_of") or event.get("correction_of_source_fact_id"))
            if not is_correction:
                continue
            if event["trigger_type"] == "after_model_turn":
                return True
            if event["trigger_type"] == "after_fact_disclosed" and event["trigger_fact_id"] in self.fact_disclosed_at:
                return True
        return False

    def state_snapshot(self) -> dict[str, Any]:
        all_facts = [fact["fact_id"] for fact in self.case.get("facts", [])]
        return {
            "model_turn": self.model_turn,
            "closed": self.closed,
            "stop_reason": self.stop_reason,
            "disclosed_fact_ids": sorted(self.disclosed),
            "hidden_fact_ids": [fact_id for fact_id in all_facts if fact_id not in self.disclosed],
            "events_emitted": sorted(self.events_emitted),
            "pending_correction": self._pending_correction(),
        }

    def _append_record(self, *, speaker: str, content: str, record_type: str,
                       disclosed_fact_ids: list[str] | None = None,
                       triggered_rule_ids: list[str] | None = None,
                       metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "schema_version": "groundsignal-dynamic-run-record/v0.1",
            "run_id": self.run_id,
            "script_id": self.case["script_id"],
            "case_reference_id": self.case.get("case_reference_id", self.case["script_id"]),
            "family_id": self.case.get("family_id", self.case["script_id"]),
            "model_turn": self.model_turn,
            "speaker": speaker,
            "record_type": record_type,
            "content": content,
            "disclosed_fact_ids": disclosed_fact_ids or [],
            "triggered_rule_ids": triggered_rule_ids or [],
            "timestamp_utc": _now(),
            "state": self.state_snapshot(),
            "metadata": metadata or {},
        }
        self.records.append(record)
        return record

    def opening(self) -> str:
        return self.case["opening"]

    def _event_due(self, event: dict[str, Any]) -> bool:
        if event["event_id"] in self.events_emitted:
            return False
        if event["trigger_type"] == "after_model_turn":
            return self.model_turn >= int(event["after_model_turn"])
        if event["trigger_type"] == "after_fact_disclosed":
            fact_id = event["trigger_fact_id"]
            return fact_id in self.fact_disclosed_at and self.model_turn >= self.fact_disclosed_at[fact_id] + int(event.get("delay_model_turns", 0))
        raise ValueError(f"Unsupported trigger_type: {event['trigger_type']}")

    def _due_events(self) -> list[dict[str, Any]]:
        events = [event for event in self.case.get("scheduled_events", []) if self._event_due(event)]
        return sorted(events, key=lambda event: (-int(event.get("priority", 0)), event["event_id"]))

    def _is_explicit_stop(self, text: str) -> bool:
        return text.strip() in set(self.case["stop_policy"]["explicit_stop_commands"])

    def _looks_like_conclusion(self, text: str) -> bool:
        policy = self.case["stop_policy"]
        has_question = any(marker in text for marker in policy["question_markers"])
        has_conclusion = any(marker in text for marker in policy["conclusion_markers"])
        return (not has_question) and has_conclusion

    def _close(self, reason: str) -> str:
        self.closed = True
        self.stop_reason = reason
        message = self.case["stop_policy"]["closing_patient_message"]
        self._append_record(speaker="simulated_patient", content=message, record_type="closing", triggered_rule_ids=[f"stop:{reason}"])
        return message

    def respond(self, model_text: str) -> str:
        if self.closed:
            raise RuntimeError(f"Run already closed: {self.stop_reason}")
        if self._is_explicit_stop(model_text):
            self._append_record(speaker="model", content=model_text, record_type="model_input", metadata={"explicit_stop": True})
            return self._close("explicit_stop")
        self.model_turn += 1
        self._append_record(speaker="model", content=model_text, record_type="model_input")
        policy = self.case["stop_policy"]
        if self.model_turn >= int(policy["minimum_model_turns_before_conclusion_stop"]) and self._looks_like_conclusion(model_text) and not (policy.get("do_not_stop_with_pending_correction", True) and self._pending_correction()):
            return self._close("model_conclusion")
        output_parts: list[str] = []
        triggered: list[str] = []
        disclosed_now: list[str] = []
        for event in self._due_events():
            output_parts.append(event["message"])
            self.events_emitted.add(event["event_id"])
            triggered.append(event["event_id"])
        budget = int(self.case.get("max_disclosures_per_turn", 1))
        for fact in self.case.get("facts", []):
            if len(disclosed_now) >= budget:
                break
            fact_id = fact["fact_id"]
            if fact_id in self.disclosed:
                continue
            if fact.get("exclude_patterns") and _matches(fact["exclude_patterns"], model_text):
                continue
            if _matches(fact["patterns"], model_text):
                output_parts.append(fact["response"])
                self.disclosed.add(fact_id)
                self.fact_disclosed_at[fact_id] = self.model_turn
                disclosed_now.append(fact_id)
                triggered.append(f"fact:{fact_id}")
        for unknown in self.case.get("unknown_responses", []):
            if len(disclosed_now) >= budget:
                break
            if _matches(unknown["patterns"], model_text):
                if unknown["response"] not in output_parts:
                    output_parts.append(unknown["response"])
                disclosed_now.append(unknown["unknown_id"])
                triggered.append(f"unknown:{unknown['unknown_id']}")
        if not output_parts:
            output_parts.append(self.case["fallback_response"])
            triggered.append("fallback_unknown")
        response = " ".join(part.strip() for part in output_parts if part.strip())
        self._append_record(speaker="simulated_patient", content=response, record_type="patient_response", disclosed_fact_ids=disclosed_now, triggered_rule_ids=triggered)
        if self.model_turn >= int(self.case["stop_policy"]["maximum_model_turns"]):
            self.closed = True
            self.stop_reason = "maximum_model_turns"
        return response

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def load_suite(path: Path) -> dict[str, Any]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if suite.get("schema_version") != "groundsignal-dynamic-patient-suite/v0.1":
        raise ValueError("Unsupported dynamic suite schema")
    return suite


def find_case(suite: dict[str, Any], script_id: str) -> dict[str, Any]:
    matches = [case for case in suite["cases"] if case["script_id"] == script_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or duplicate script_id: {script_id}")
    return matches[0]


def read_messages(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("input-json must be a JSON list")
    messages: list[str] = []
    for row in payload:
        if isinstance(row, str):
            messages.append(row)
        elif isinstance(row, dict) and isinstance(row.get("content"), str):
            messages.append(row["content"])
        else:
            raise ValueError("Each input-json row must be a string or object with string content")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--case", dest="script_id")
    parser.add_argument("--run-id", default=f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--print-state", action="store_true")
    args = parser.parse_args()
    suite = load_suite(args.suite)
    if args.list:
        for case in suite["cases"]:
            print(f"{case['script_id']}\t{case['case_reference_id']}\t{case['title']}")
        return 0
    if not args.script_id:
        parser.error("--case is required unless --list is used")
    patient = PatientScript(find_case(suite, args.script_id), args.run_id)
    print(f"PATIENT> {patient.opening()}")
    if args.input_json:
        for message in read_messages(args.input_json):
            if patient.closed:
                break
            print(f"MODEL> {message}")
            print(f"PATIENT> {patient.respond(message)}")
    else:
        while not patient.closed:
            try:
                message = input("MODEL> ")
            except EOFError:
                break
            if message.strip() == "/state":
                print(json.dumps(patient.state_snapshot(), ensure_ascii=False, indent=2))
                continue
            print(f"PATIENT> {patient.respond(message)}")
    if args.output_jsonl:
        patient.write_jsonl(args.output_jsonl)
    if args.print_state:
        print(json.dumps(patient.state_snapshot(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
