"""Pinned ReMeDi-base intake; source material, never clinical gold or held-out data.

Raw conversations and candidate identifiers stay under the ignored local/ tree.
Only aggregate audit.json is suitable for publication. No model is called.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import urllib.request


COMMIT = "f94bb9abfba48f467669d2454771bbe263cc4ae5"
BASE = f"https://raw.githubusercontent.com/yanguojun123/Medical-Dialogue/{COMMIT}/"
MAX_BYTES = 32 * 1024 * 1024
FILES = {
    "ReMeDi-base.json": {
        "path": "data/ReMeDi-base.json", "bytes": 16596996,
        "git_blob": "fa444d7e10841c0485223db6b51d0c36e335619f",
        "sha256": "b27b6b1222255cc87cbc6cc0fb6ce7de98e0b6341f5ea61892bb92f247383458",
    },
    "MIT-license.txt": {
        "path": "MIT-license.txt", "bytes": 1066,
        "git_blob": "3d5238e789df847576ba47726d05faa082b79e52",
        "sha256": "8effa9b9543b2d7fd40b799051202b5eeb2966004baba2be40e7a0a378fe60e4",
    },
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def verify_payload(data: bytes, expected: dict) -> None:
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if (len(data) != expected["bytes"] or blob != expected["git_blob"]
            or hashlib.sha256(data).hexdigest() != expected["sha256"]):
        raise ValueError("source integrity mismatch: expected pinned bytes, Git blob and SHA-256")


def _read_bounded(stream) -> bytes:
    data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("source exceeds 32 MiB limit")
    return data


def _payload(filename: str, local: Path | None) -> bytes:
    if local is not None:
        with local.open("rb") as stream:
            data = _read_bounded(stream)
    else:
        with urllib.request.urlopen(BASE + FILES[filename]["path"], timeout=30) as stream:
            data = _read_bounded(stream)
    verify_payload(data, FILES[filename])
    return data


def _identifier(value: object) -> bool:
    return type(value) is int or isinstance(value, str) and bool(value.strip())


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def audit_dialogues(data: object, candidate_limit: int = 50) -> tuple[dict, list]:
    """Inspect actual source keys without rewriting turn order or clinical labels.

    Returns (public aggregate, local candidate identifiers). This public helper
    accepts synthetic fixtures; intake() additionally enforces the source pin.
    """
    if not isinstance(data, list) or not data:
        raise ValueError("expected a nonempty dialogue list")
    if type(candidate_limit) is not int or not 0 <= candidate_limit <= 50:
        raise ValueError("candidate_limit must be an integer from 0 to 50")
    counts = Counter(dict.fromkeys([
        "dialogues", "turns", "malformed_dialogues", "malformed_turns",
        "empty_dialogues", "empty_sentences", "invalid_roles", "missing_dialogue_ids",
        "missing_turn_ids", "duplicate_dialogue_ids", "duplicate_turn_ids",
        "adjacent_same_role_pairs", "dialogues_with_adjacent_same_role",
        "actions_present_turns", "actions_nonempty_turns", "actions_empty_turns",
        "actions_missing_or_nonlist_turns", "action_entries", "nondict_action_entries",
        "message_nonempty_turns", "exact_normalized_duplicate_dialogues",
        "schema_usable_unique_dialogues",
    ], 0))
    roles, starts, ends, dialogue_ids, signatures = Counter(), Counter(), Counter(), set(), set()
    candidates = []
    for dialogue in data:
        counts["dialogues"] += 1
        if not isinstance(dialogue, dict):
            counts["malformed_dialogues"] += 1
            continue
        identifier = dialogue.get("dialogue")
        valid_id = _identifier(identifier)
        if not valid_id:
            counts["missing_dialogue_ids"] += 1
        id_key = (type(identifier).__name__, str(identifier)) if valid_id else None
        duplicate_id = id_key in dialogue_ids if valid_id else False
        counts["duplicate_dialogue_ids"] += int(duplicate_id)
        if valid_id:
            dialogue_ids.add(id_key)
        turns = dialogue.get("information")
        if not isinstance(turns, list):
            counts["malformed_dialogues"] += 1
            continue
        if not turns:
            counts["empty_dialogues"] += 1
        usable = valid_id and not duplicate_id and bool(turns)
        turn_ids, sequence, previous_role, repeated_role = set(), [], None, False
        for turn in turns:
            counts["turns"] += 1
            if not isinstance(turn, dict):
                counts["malformed_turns"] += 1
                usable, previous_role = False, None
                continue
            role, sentence, turn_id = turn.get("role"), turn.get("sentence"), turn.get("turn")
            known_role = role if role in ("doctor", "patient") else "invalid"
            roles[known_role] += 1
            counts["invalid_roles"] += int(known_role == "invalid")
            text = _normalized(sentence) if isinstance(sentence, str) else ""
            counts["empty_sentences"] += int(not text)
            has_id = _identifier(turn_id)
            key = (type(turn_id).__name__, str(turn_id)) if has_id else None
            duplicate = key in turn_ids if has_id else False
            counts["missing_turn_ids"] += int(not has_id)
            counts["duplicate_turn_ids"] += int(duplicate)
            if has_id:
                turn_ids.add(key)
            usable = usable and known_role != "invalid" and bool(text) and has_id and not duplicate
            if previous_role == known_role and known_role != "invalid":
                counts["adjacent_same_role_pairs"] += 1
                repeated_role = True
            previous_role = known_role
            sequence.append((known_role, text))
            actions = turn.get("actions")
            if isinstance(actions, list):
                counts["actions_present_turns"] += 1
                counts["actions_nonempty_turns"] += int(bool(actions))
                counts["actions_empty_turns"] += int(not actions)
                counts["action_entries"] += len(actions)
                counts["nondict_action_entries"] += sum(not isinstance(a, dict) for a in actions)
            else:
                counts["actions_missing_or_nonlist_turns"] += 1
            counts["message_nonempty_turns"] += int(isinstance(turn.get("message"), str)
                                                    and bool(turn["message"].strip()))
        counts["dialogues_with_adjacent_same_role"] += int(repeated_role)
        if sequence:
            starts[sequence[0][0]] += 1
            ends[sequence[-1][0]] += 1
        if usable:
            signature = hashlib.sha256(_json(sequence).encode()).hexdigest()
            if signature in signatures:
                counts["exact_normalized_duplicate_dialogues"] += 1
            else:
                signatures.add(signature)
                candidates.append((signature, identifier))
    counts["schema_usable_unique_dialogues"] = len(candidates)
    audit = {
        "counts": dict(counts), "role_counts": dict(roles),
        "first_role_counts": dict(starts), "last_role_counts": dict(ends),
        "candidate_selection_count": min(candidate_limit, len(candidates)),
        "duplicate_definition": "usable dialogues; role + NFKC and whitespace-normalized sentence sequence",
        "annotation_scope": "actions presence and container structure only; clinical correctness unreviewed",
        "sequence_policy": "original bytes and turn order preserved; repeated roles are descriptive, not invalid",
        "candidate_selection": "first 50 or fewer unique usable dialogues ordered by content SHA-256",
    }
    return audit, [identifier for _, identifier in sorted(candidates)[:candidate_limit]]


def intake(out: Path, input_path: Path | None = None, license_path: Path | None = None) -> dict:
    if out.exists():
        raise ValueError("output must be a new directory")
    local_root = Path(__file__).resolve().parents[2] / "medical/patient-eval/local"
    if not out.resolve().is_relative_to(local_root.resolve()):
        raise ValueError("output must be inside ignored medical/patient-eval/local/")
    raw = _payload("ReMeDi-base.json", input_path)
    license_bytes = _payload("MIT-license.txt", license_path)
    aggregate, candidates = audit_dialogues(json.loads(raw))
    audit = {
        "schema_version": "medical-source-audit/v0.1", "source": "ReMeDi-base",
        "upstream_commit": COMMIT, "files": FILES, "license": "MIT",
        "public_exposed": True, "source_material_only": True,
        "clinical_gold": False, "dynamic_scenario_ready": False,
        "independent_held_out": False, "deidentification_verified": False,
        "clinical_label_correctness_verified": False, **aggregate,
    }
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    (out / "ReMeDi-base.json").write_bytes(raw)
    (out / "MIT-license.txt").write_bytes(license_bytes)
    (out / "audit.json").write_text(_json(audit), encoding="utf-8")
    (out / "candidate-review-local.json").write_text(_json({
        "local_only": True, "source_commit": COMMIT, "candidate_dialogue_ids": candidates,
        "review_status": "unreviewed", "selection_is_representative": False,
        "required_review": ["privacy", "medical validity", "scenario feasibility", "rubric authorship"],
    }), encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new directory under medical/patient-eval/local/")
    parser.add_argument("--input", type=Path, help="optional exact pinned source file")
    parser.add_argument("--license-input", type=Path, help="optional exact pinned MIT license file")
    args = parser.parse_args()
    try:
        audit = intake(args.out, args.input, args.license_input)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"intake failed: {exc}\n")
    print(_json(audit))


if __name__ == "__main__":
    main()
