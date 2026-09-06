#!/usr/bin/env python3
"""Export reviewed evaluation failures into SFT / preference candidates.

Important design rules:
- evaluation failures are not automatically training data;
- only explicitly approved candidates are exportable;
- S5 benchmark partitions are fail-closed: heldout/regression cases cannot be
  exported even when a candidate is approved;
- materialized benchmark provenance is propagated into every exported row.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

BLOCKED_TRAINING_SPLITS = {"heldout", "regression"}


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
    if case.get("benchmark_provenance"):
        return case
    parts = file.parts
    try:
        idx = parts.index("case-families")
    except ValueError:
        return case
    if len(parts) <= idx + 2:
        return case
    family_dir = Path(*parts[: idx + 2])
    manifest_path = family_dir / "manifest.json"
    if not manifest_path.is_file():
        return case
    manifest = read_json(manifest_path)
    case_id = str(case.get("case_id") or "")
    for ref in manifest.get("cases") or []:
        if str(ref.get("case_id") or "") != case_id:
            continue
        out = dict(case)
        split = str(ref.get("split") or "")
        out["benchmark_provenance"] = {
            "stage": "S5",
            "suite_id": "UNMATERIALIZED_SOURCE",
            "family_id": str(manifest.get("family_id") or family_dir.name),
            "split": split,
            "variant_type": ref.get("variant_type"),
            "evidence_class": "source_case_unmaterialized",
            "fresh_evidence": False,
            "source_snapshot_commit": None,
            "source_manifest_path": str(manifest_path),
            "source_case_path": str(file),
            "materializer_version": "manifest-resolver-compat-v0.1.1",
            "training_eligible": split not in BLOCKED_TRAINING_SPLITS,
        }
        return out
    raise ValueError(f"{file}: case_id {case_id!r} not found in sibling manifest")


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


def training_partition(case: Dict[str, Any]) -> tuple[str | None, bool | None, Dict[str, Any] | None]:
    provenance = case.get("benchmark_provenance")
    if isinstance(provenance, dict):
        split = provenance.get("split")
        eligible = provenance.get("training_eligible")
        return (str(split) if split is not None else None, bool(eligible) if eligible is not None else None, provenance)
    split = case.get("split")
    if split is not None:
        split = str(split)
        return split, split not in BLOCKED_TRAINING_SPLITS, None
    return None, None, None


def export_row(eval_row: Dict[str, Any], case: Dict[str, Any], run: Dict[str, Any] | None) -> tuple[str, Dict[str, Any]] | None:
    candidate = eval_row.get("training_candidate") or {}
    if candidate.get("review_status") != "approved":
        return None

    split, eligible, provenance = training_partition(case)
    if split in BLOCKED_TRAINING_SPLITS or eligible is False:
        raise PermissionError(
            f"Training export blocked for case {case.get('case_id')}: split={split!r} is evaluation-only"
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
        "rule": "approved candidates only; heldout/regression benchmark partitions are fail-closed",
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
