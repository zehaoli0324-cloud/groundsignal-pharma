"""Version-bound, offline import of recorded development conversations.

This validates records, not clinical admission or collection authenticity.
Source-derived dynamic v0.4 drafts are not an accepted suite format.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .contracts import load_suite, require, validate_scenario, validate_session
from .importers import import_blackbox


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def scenario_digest(scenario):
    """Canonical scenario digest, including protocol and criteria, not just ID."""
    return digest_bytes(json.dumps(scenario, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8"))


def write_new_json(path, value):
    """Publish a complete file with exclusive creation, including racing writers."""
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # atomic no-replace; temp and destination share a filesystem
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validate_batch(records, suite, suite_sha256):
    """Validate the whole batch before saving; never fill missing version claims."""
    require(isinstance(records, list) and bool(records), "records must be a nonempty list")
    require(isinstance(suite, dict) and suite.get("schema_version") == "patient-eval/v0.1"
            and suite.get("scope") == "development_only", "unsupported development suite")
    require(isinstance(suite_sha256, str) and len(suite_sha256) == 64
            and all(c in "0123456789abcdef" for c in suite_sha256), "invalid suite digest")
    require(isinstance(suite.get("scenarios"), list) and bool(suite["scenarios"]), "empty suite")
    scenarios = {}
    for scenario in suite["scenarios"]:
        validate_scenario(scenario)
        require(scenario["scenario_id"] not in scenarios, "duplicate scenario_id in suite")
        scenarios[scenario["scenario_id"]] = scenario
    sessions, ids = [], set()
    for record in records:
        session = import_blackbox(record)
        validate_session(session)
        require(session["session_id"] not in ids, "duplicate session_id in batch")
        ids.add(session["session_id"])
        require(session["scenario_id"] in scenarios, "unknown scenario_id")
        scenario = scenarios[session["scenario_id"]]
        meta = session["metadata"]
        require(meta.get("suite_sha256") == suite_sha256, "missing or mismatched suite_sha256")
        require(meta.get("scenario_sha256") == scenario_digest(scenario),
                "missing or mismatched scenario_sha256")
        for field in ("family_id", "variant"):
            require(session[field] == scenario[field], "scenario identity mismatch: " + field)
        require(meta["question_source"] == scenario["source"], "question source mismatch")
        require(meta["session_protocol_id"] == scenario["protocol_id"], "protocol mismatch")
        prefix = [{"role": t["role"], "content": t["content"]} for t in scenario["prefix"]]
        turns = [{"role": t["role"], "content": t["content"]} for t in session["turns"]]
        if meta["comparison_lane"] == "fixed_prefix":
            require(turns[:len(prefix)] == prefix, "fixed-prefix content or order mismatch")
            require(len(turns) == len(prefix) + (session["status"] == "completed"),
                    "fixed-prefix must have one target answer or none on failure")
        else:
            require(turns[0] == prefix[0], "free-dialogue opening mismatch")
        criteria = {c["id"] for c in scenario["criteria"]}
        require(all(o["criterion_id"] in criteria for o in session["observations"]),
                "observation references unknown criterion")
        # Missing reviews stay missing; an import never creates a pass or score.
        meta["import_binding_version"] = "patient-import-binding/v0.1"
        meta["import_binding_is_admission"] = False
        sessions.append(session)
    return sessions


def import_file(input_path, suite_path, out):
    require(not Path(out).exists(), "refusing to overwrite existing import")
    raw = Path(input_path).read_bytes()
    suite_raw = Path(suite_path).read_bytes()
    suite = load_suite(suite_path)
    require(Path(suite_path).read_bytes() == suite_raw, "suite changed during load")
    records = json.loads(raw)
    sessions = validate_batch(records, suite, digest_bytes(suite_raw))
    for session in sessions:
        session["metadata"]["import_source_file_sha256"] = digest_bytes(raw)
    write_new_json(out, sessions)
    statuses = Counter(s["status"] for s in sessions)
    return {"schema_version": "patient-import-summary/v0.1", "sessions": len(sessions),
            "unique_cases": len({s["scenario_id"] for s in sessions}),
            "statuses": dict(sorted(statuses.items())),
            "sessions_without_observations": sum(not s["observations"] for s in sessions),
            "clinical_approval": False, "network_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = import_file(args.input, args.suite, args.out)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f"bound import failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
