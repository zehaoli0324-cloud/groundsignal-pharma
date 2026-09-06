#!/usr/bin/env python3
"""Export reviewed evaluation failures into SFT / preference candidates.

Important design rules:
- evaluation failures are not automatically training data;
- only explicitly approved candidates are exportable;
- S5 benchmark partitions are authenticated against the authoritative family manifest;
- missing/unknown benchmark split identity is fail-closed;
- materialized S5 payloads must pass digest verification before export;
- ordinary unpartitioned non-benchmark files are allowed only when loaded through
  this module's trusted file-loader path, never by case-local self-assertion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TRAINING_SPLITS = {"dev"}
BLOCKED_TRAINING_SPLITS = {"heldout", "regression"}
KNOWN_BENCHMARK_SPLITS = ALLOWED_TRAINING_SPLITS | BLOCKED_TRAINING_SPLITS
_TRUSTED_UNPARTITIONED_SOURCE = object()


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_materialized_sha256(case: Dict[str, Any]) -> str:
    payload = deepcopy(case)
    payload.pop("_training_export_context", None)
    provenance = payload.get("benchmark_provenance")
    if isinstance(provenance, dict):
        provenance.pop("materialized_payload_sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_repo_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PermissionError("S5 export blocked: provenance source path is missing")
    raw = Path(value)
    resolved = raw.resolve() if raw.is_absolute() else (REPO_ROOT / raw).resolve()
    root = REPO_ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"S5 export blocked: provenance path escapes repository: {value!r}") from exc
    return resolved


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if not path.is_dir():
        raise FileNotFoundError(path)
    for file in sorted(path.rglob("*.json")):
        if file.name == "materialization-manifest.json":
            continue
        yield file


def _attach_family_manifest_provenance(file: Path, case: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve legacy raw case files under case-families to their manifest split."""
    incoming = dict(case)
    incoming.pop("_training_export_context", None)
    if incoming.get("benchmark_provenance"):
        return incoming

    resolved_file = file.resolve()
    parts = resolved_file.parts
    try:
        idx = parts.index("case-families")
    except ValueError:
        incoming["_training_export_context"] = _TRUSTED_UNPARTITIONED_SOURCE
        return incoming
    if len(parts) <= idx + 2:
        raise PermissionError(f"{file}: ambiguous case-families path")

    family_dir = Path(*parts[: idx + 2])
    manifest_path = family_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PermissionError(f"{file}: S5-family-like source has no sibling manifest")
    manifest = read_json(manifest_path)
    case_id = str(incoming.get("case_id") or "")
    for ref in manifest.get("cases") or []:
        if str(ref.get("case_id") or "") != case_id:
            continue
        split = str(ref.get("split") or "")
        if split not in KNOWN_BENCHMARK_SPLITS:
            raise PermissionError(f"{file}: unsupported manifest split {split!r}")
        try:
            manifest_rel = manifest_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
            case_rel = resolved_file.relative_to(REPO_ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise PermissionError(f"{file}: S5 raw case must live inside repository") from exc
        incoming["benchmark_provenance"] = {
            "stage": "S5",
            "suite_id": "UNMATERIALIZED_SOURCE",
            "family_id": str(manifest.get("family_id") or family_dir.name),
            "split": split,
            "variant_type": ref.get("variant_type"),
            "evidence_class": "source_case_unmaterialized",
            "fresh_evidence": False,
            "source_snapshot_commit": None,
            "source_manifest_path": manifest_rel,
            "source_case_path": case_rel,
            "source_manifest_sha256": sha256_file(manifest_path),
            "source_case_sha256": sha256_file(resolved_file),
            "materializer_version": "manifest-resolver-compat-v0.2.1",
            "provenance_mode": "source_manifest_resolved",
            "training_eligible": split in ALLOWED_TRAINING_SPLITS,
        }
        return incoming
    raise PermissionError(f"{file}: case_id {case_id!r} not found in sibling manifest")


def load_cases(path: Path) -> Dict[str, Dict[str, Any]]:
    cases: Dict[str, Dict[str, Any]] = {}
    for file in _iter_json_files(path):
        case = _attach_family_manifest_provenance(file, read_json(file))
        case_id = str(case.get("case_id", ""))
        if not case_id:
            raise ValueError(f"Case file missing case_id: {file}")
        if case_id in cases:
            raise ValueError(f"Duplicate case_id while loading export input: {case_id}")
        cases[case_id] = case
    return cases


def run_index(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[Tuple[str, str], Dict[str, Any]]]:
    by_run: Dict[str, Dict[str, Any]] = {}
    by_case_model: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        run_id = row.get("run_id")
        if run_id:
            by_run[str(run_id)] = row
        case_id = row.get("case_id")
        model_id = row.get("model_id")
        if case_id and model_id:
            by_case_model[(str(case_id), str(model_id))] = row
    return by_run, by_case_model


def find_run(eval_row: Dict[str, Any], by_run: Dict[str, Dict[str, Any]], by_case_model: Dict[Tuple[str, str], Dict[str, Any]]) -> Dict[str, Any] | None:
    rid = eval_row.get("run_id") or eval_row.get("response_id")
    if rid and str(rid) in by_run:
        return by_run[str(rid)]
    key = (str(eval_row.get("case_id", "")), str(eval_row.get("model_id", "")))
    return by_case_model.get(key)


def case_context(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_context": case.get("patient_context", {}),
        "evidence_snapshot": case.get("evidence_snapshot", {}),
        "prior_turns": case.get("interaction", {}).get("prior_turns", []),
    }


def failure_list(eval_row: Dict[str, Any]) -> List[str]:
    failures = eval_row.get("failure_types") or eval_row.get("failure_clusters") or []
    if isinstance(failures, str):
        failures = [failures]
    return [str(x) for x in failures]


def _authoritative_manifest_ref(case: Dict[str, Any], provenance: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    if provenance.get("stage") != "S5":
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: unsupported benchmark provenance stage")
    case_id = str(case.get("case_id") or "")
    family_id = str(provenance.get("family_id") or "")
    manifest_path = _resolve_repo_path(provenance.get("source_manifest_path"))
    source_case_path = _resolve_repo_path(provenance.get("source_case_path"))
    if not manifest_path.is_file() or not source_case_path.is_file():
        raise PermissionError(f"Training export blocked for case {case_id}: authoritative provenance source missing")

    expected_manifest_sha = str(provenance.get("source_manifest_sha256") or "")
    expected_source_sha = str(provenance.get("source_case_sha256") or "")
    if not expected_manifest_sha or sha256_file(manifest_path) != expected_manifest_sha:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest digest mismatch")
    if not expected_source_sha or sha256_file(source_case_path) != expected_source_sha:
        raise PermissionError(f"Training export blocked for case {case_id}: source-case digest mismatch")

    manifest = read_json(manifest_path)
    if str(manifest.get("family_id") or "") != family_id:
        raise PermissionError(f"Training export blocked for case {case_id}: family authority mismatch")
    for ref in manifest.get("cases") or []:
        if str(ref.get("case_id") or "") == case_id:
            authoritative_split = str(ref.get("split") or "")
            if authoritative_split not in KNOWN_BENCHMARK_SPLITS:
                raise PermissionError(f"Training export blocked for case {case_id}: unknown authoritative split {authoritative_split!r}")
            authoritative_case_path = (manifest_path.parent / str(ref.get("path") or "")).resolve()
            if authoritative_case_path != source_case_path:
                raise PermissionError(f"Training export blocked for case {case_id}: source-case path is not manifest-authoritative")
            return authoritative_split, ref
    raise PermissionError(f"Training export blocked for case {case_id}: absent from authoritative manifest")


def _verify_payload_integrity(case: Dict[str, Any], provenance: Dict[str, Any]) -> None:
    case_id = str(case.get("case_id") or "")
    mode = str(provenance.get("provenance_mode") or "")
    if mode == "materialized_manifest_bound":
        expected = str(provenance.get("materialized_payload_sha256") or "")
        if not expected:
            raise PermissionError(f"Training export blocked for case {case_id}: materialized payload digest missing")
        observed = canonical_materialized_sha256(case)
        if observed != expected:
            raise PermissionError(f"Training export blocked for case {case_id}: materialized payload digest mismatch")
        return
    if mode == "source_manifest_resolved":
        source_case_path = _resolve_repo_path(provenance.get("source_case_path"))
        source_case = read_json(source_case_path)
        current = deepcopy(case)
        current.pop("benchmark_provenance", None)
        current.pop("_training_export_context", None)
        if current != source_case:
            raise PermissionError(f"Training export blocked for case {case_id}: raw source payload diverged after authority resolution")
        return
    raise PermissionError(f"Training export blocked for case {case_id}: unknown provenance mode {mode!r}")


def training_partition(case: Dict[str, Any]) -> tuple[str | None, bool | None, Dict[str, Any] | None]:
    provenance = case.get("benchmark_provenance")
    if isinstance(provenance, dict):
        local_split = provenance.get("split")
        if not isinstance(local_split, str) or local_split not in KNOWN_BENCHMARK_SPLITS:
            raise PermissionError(f"Training export blocked for case {case.get('case_id')}: missing/unknown benchmark split {local_split!r}")
        authoritative_split, _ = _authoritative_manifest_ref(case, provenance)
        if local_split != authoritative_split:
            raise PermissionError(
                f"Training export blocked for case {case.get('case_id')}: local split={local_split!r} disagrees with manifest={authoritative_split!r}"
            )
        eligible = provenance.get("training_eligible")
        expected_eligible = authoritative_split in ALLOWED_TRAINING_SPLITS
        if not isinstance(eligible, bool) or eligible is not expected_eligible:
            raise PermissionError(
                f"Training export blocked for case {case.get('case_id')}: training_eligible={eligible!r} disagrees with authoritative split"
            )
        _verify_payload_integrity(case, provenance)
        return authoritative_split, eligible, provenance

    if case.get("split") is not None:
        raise PermissionError(
            f"Training export blocked for case {case.get('case_id')}: partitioned case lacks authenticated benchmark provenance"
        )
    if case.get("_training_export_context") is _TRUSTED_UNPARTITIONED_SOURCE:
        return None, True, None
    raise PermissionError(
        f"Training export blocked for case {case.get('case_id')}: unpartitioned direct case has no trusted loader context"
    )


def export_row(eval_row: Dict[str, Any], case: Dict[str, Any], run: Dict[str, Any] | None) -> tuple[str, Dict[str, Any]] | None:
    candidate = eval_row.get("training_candidate") or {}
    if candidate.get("review_status") != "approved":
        return None

    split, eligible, provenance = training_partition(case)
    if split in BLOCKED_TRAINING_SPLITS or eligible is False:
        raise PermissionError(
            f"Training export blocked for case {case.get('case_id')}: split={split!r} is evaluation-only"
        )
    if split is not None and split not in ALLOWED_TRAINING_SPLITS:
        raise PermissionError(
            f"Training export blocked for case {case.get('case_id')}: split={split!r} is not allowlisted"
        )

    kind = candidate.get("type")
    ideal = candidate.get("ideal_response") or candidate.get("chosen")
    if not ideal:
        raise ValueError(f"Approved training candidate missing ideal_response/chosen for case {case['case_id']}")

    base = {
        "source_case_id": case["case_id"],
        "source_run_id": (run or {}).get("run_id"),
        "source_family_id": (provenance or {}).get("family_id"),
        "source_suite_id": (provenance or {}).get("suite_id"),
        "source_split": split,
        "failure_type": candidate.get("failure_type") or (failure_list(eval_row)[0] if failure_list(eval_row) else None),
        "rubric_version": eval_row.get("rubric_version") or eval_row.get("version", {}).get("rubric"),
        "reviewed_by": candidate.get("reviewed_by"),
        "review_status": "approved",
    }

    instruction = case.get("interaction", {}).get("prompt", "")
    context = case_context(case)

    if kind == "sft":
        return "sft", {"instruction": instruction, "context": context, "ideal_response": ideal, **base}
    if kind == "preference":
        rejected = candidate.get("rejected") or (run or {}).get("response")
        if not rejected:
            raise ValueError(f"Preference candidate missing rejected response for case {case['case_id']}")
        return "preference", {"prompt": instruction, "context": context, "chosen": ideal, "rejected": rejected, **base}
    if kind in {None, "none"}:
        return None
    raise ValueError(f"Unknown training_candidate.type={kind!r} for case {case['case_id']}")


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export approved GroundSignal training-data candidates")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--runs", required=True, type=Path, help="Model harness run JSONL")
    parser.add_argument("--eval", required=True, type=Path, help="Evaluations with training_candidate blocks")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    runs = read_jsonl(args.runs)
    eval_rows = read_jsonl(args.eval)
    by_run, by_case_model = run_index(runs)

    sft_rows: List[Dict[str, Any]] = []
    pref_rows: List[Dict[str, Any]] = []
    skipped = 0

    for eval_row in eval_rows:
        case_id = str(eval_row.get("case_id", ""))
        if case_id not in cases:
            raise KeyError(f"Evaluation references unknown case_id: {case_id}")
        run = find_run(eval_row, by_run, by_case_model)
        result = export_row(eval_row, cases[case_id], run)
        if result is None:
            skipped += 1
            continue
        kind, row = result
        if kind == "sft":
            sft_rows.append(row)
        elif kind == "preference":
            pref_rows.append(row)

    write_jsonl(args.out_dir / "sft.jsonl", sft_rows)
    write_jsonl(args.out_dir / "preference.jsonl", pref_rows)
    manifest = {
        "sft_count": len(sft_rows),
        "preference_count": len(pref_rows),
        "skipped_not_approved_or_none": skipped,
        "rule": "approved candidates only; S5 partition authority and materialized payload integrity are fail-closed",
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
