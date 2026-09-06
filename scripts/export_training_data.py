#!/usr/bin/env python3
"""Export explicitly reviewed evaluation failures into SFT/preference candidates.

S5 v0.3.1 trust rules:
- benchmark identity is authenticated against an external trust-root policy;
- suite membership, manifest identity and source-case identity are policy-bound;
- a materialized payload is reconstructed from trusted source content before export;
- an embedded digest is only a consistency field, never the root of trust;
- ordinary non-benchmark sources require explicit policy allowlisting;
- missing/unknown authority fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUST_POLICY = REPO_ROOT / "medical/configs/s5-trust-root-v0.3.1.json"
ALLOWED_TRAINING_SPLITS = {"dev"}
BLOCKED_TRAINING_SPLITS = {"heldout", "regression"}
KNOWN_BENCHMARK_SPLITS = ALLOWED_TRAINING_SPLITS | BLOCKED_TRAINING_SPLITS
TRUSTED_MATERIALIZER_VERSIONS = {"s5-materializer-v0.2.1"}


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


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def canonical_materialized_sha256(case: Dict[str, Any]) -> str:
    payload = deepcopy(case)
    payload.pop("_training_export_context", None)
    provenance = payload.get("benchmark_provenance")
    if isinstance(provenance, dict):
        provenance.pop("materialized_payload_sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_repo_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PermissionError("S5 export blocked: authority path is missing")
    raw = Path(value)
    resolved = raw.resolve() if raw.is_absolute() else (REPO_ROOT / raw).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise PermissionError(f"S5 export blocked: path escapes repository: {value!r}") from exc
    return resolved


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise PermissionError(f"S5 export blocked: source outside repository: {path}") from exc


def load_trust_policy(policy: Dict[str, Any] | Path | None = None) -> Dict[str, Any]:
    if isinstance(policy, dict):
        out = policy
    else:
        path = Path(policy) if policy is not None else DEFAULT_TRUST_POLICY
        if not path.is_file():
            raise PermissionError(f"S5 export blocked: trust policy not found: {path}")
        out = read_json(path)
    if not str(out.get("policy_version") or "").startswith("s5-trust-root-v0.3.1"):
        raise PermissionError("S5 export blocked: unsupported or missing external trust-policy version")
    if not isinstance(out.get("benchmark_suites"), dict) or not isinstance(out.get("ordinary_training_sources"), dict):
        raise PermissionError("S5 export blocked: malformed external trust policy")
    return out


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


def _ordinary_source_context(file: Path, policy: Dict[str, Any]) -> Dict[str, Any]:
    rel = _repo_rel(file)
    entry = (policy.get("ordinary_training_sources") or {}).get(rel)
    if not isinstance(entry, dict):
        raise PermissionError(f"S5 export blocked: ordinary source is not externally allowlisted: {rel}")
    expected = str(entry.get("git_blob_sha1") or "")
    observed = git_blob_sha1(file)
    if not expected or observed != expected:
        raise PermissionError(f"S5 export blocked: ordinary source identity mismatch: {rel}")
    return {"kind": "ordinary_policy_allowlisted", "path": rel, "git_blob_sha1": observed}


def load_cases(path: Path, trust_policy: Dict[str, Any] | Path | None = None) -> Dict[str, Dict[str, Any]]:
    policy = load_trust_policy(trust_policy)
    cases: Dict[str, Dict[str, Any]] = {}
    for file in _iter_json_files(path):
        case = read_json(file)
        if not isinstance(case.get("benchmark_provenance"), dict):
            case = dict(case)
            case["_training_export_context"] = _ordinary_source_context(file, policy)
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
    return by_case_model.get((str(eval_row.get("case_id", "")), str(eval_row.get("model_id", ""))))


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


def _trusted_suite_authority(case: Dict[str, Any], provenance: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(case.get("case_id") or "")
    if provenance.get("stage") != "S5":
        raise PermissionError(f"Training export blocked for case {case_id}: unsupported provenance stage")
    suite_id = str(provenance.get("suite_id") or "")
    suite_entry = (policy.get("benchmark_suites") or {}).get(suite_id)
    if not isinstance(suite_entry, dict):
        raise PermissionError(f"Training export blocked for case {case_id}: suite {suite_id!r} is not in external trust policy")

    suite_path = _resolve_repo_path(suite_entry.get("suite_path"))
    if git_blob_sha1(suite_path) != str(suite_entry.get("suite_git_blob_sha1") or ""):
        raise PermissionError(f"Training export blocked for case {case_id}: trusted suite file identity mismatch")
    suite = read_json(suite_path)
    if str(suite.get("suite_id") or "") != suite_id:
        raise PermissionError(f"Training export blocked for case {case_id}: suite identity mismatch")

    family_id = str(provenance.get("family_id") or "")
    if family_id not in {str(x) for x in suite.get("family_ids") or []}:
        raise PermissionError(f"Training export blocked for case {case_id}: family is not a member of trusted suite")
    family_entry = (suite_entry.get("families") or {}).get(family_id)
    if not isinstance(family_entry, dict):
        raise PermissionError(f"Training export blocked for case {case_id}: family missing from external trust policy")

    family_root = _resolve_repo_path(suite_entry.get("family_root"))
    manifest_path = _resolve_repo_path(family_entry.get("manifest_path"))
    expected_manifest_path = (family_root / family_id / "manifest.json").resolve()
    if manifest_path != expected_manifest_path:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest path is not suite-authoritative")
    if git_blob_sha1(manifest_path) != str(family_entry.get("manifest_git_blob_sha1") or ""):
        raise PermissionError(f"Training export blocked for case {case_id}: trusted manifest identity mismatch")
    manifest = read_json(manifest_path)
    if str(manifest.get("family_id") or "") != family_id:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest family mismatch")

    case_entry = (family_entry.get("cases") or {}).get(case_id)
    if not isinstance(case_entry, dict):
        raise PermissionError(f"Training export blocked for case {case_id}: case absent from external trust policy")
    source_case_path = _resolve_repo_path(case_entry.get("source_case_path"))
    if git_blob_sha1(source_case_path) != str(case_entry.get("source_case_git_blob_sha1") or ""):
        raise PermissionError(f"Training export blocked for case {case_id}: trusted source-case identity mismatch")
    source_case = read_json(source_case_path)
    if str(source_case.get("case_id") or "") != case_id:
        raise PermissionError(f"Training export blocked for case {case_id}: source-case id mismatch")

    matching_refs = [r for r in manifest.get("cases") or [] if str(r.get("case_id") or "") == case_id]
    if len(matching_refs) != 1:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest case membership is ambiguous")
    ref = matching_refs[0]
    authoritative_split = str(case_entry.get("split") or "")
    authoritative_variant = str(case_entry.get("variant_type") or "")
    if authoritative_split not in KNOWN_BENCHMARK_SPLITS:
        raise PermissionError(f"Training export blocked for case {case_id}: unknown trusted split")
    if str(ref.get("split") or "") != authoritative_split or str(ref.get("variant_type") or "") != authoritative_variant:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest metadata diverges from external trust policy")
    ref_path = (manifest_path.parent / str(ref.get("path") or "")).resolve()
    if ref_path != source_case_path:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest source path diverges from external trust policy")

    return {
        "suite": suite,
        "suite_path": suite_path,
        "suite_entry": suite_entry,
        "family_id": family_id,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "ref": ref,
        "source_case": source_case,
        "source_case_path": source_case_path,
        "split": authoritative_split,
        "variant_type": authoritative_variant,
    }


def _expected_materialized_case(case: Dict[str, Any], provenance: Dict[str, Any], authority: Dict[str, Any]) -> Dict[str, Any]:
    suite = authority["suite"]
    split = authority["split"]
    allowed = {str(x) for x in suite.get("allowed_training_splits") or []}
    prohibited = {str(x) for x in suite.get("prohibited_training_splits") or []}
    if allowed - ALLOWED_TRAINING_SPLITS or not BLOCKED_TRAINING_SPLITS.issubset(prohibited):
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: trusted suite split policy is unsafe")

    materializer_version = str(provenance.get("materializer_version") or "")
    if materializer_version not in TRUSTED_MATERIALIZER_VERSIONS:
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: untrusted materializer version {materializer_version!r}")

    expected = deepcopy(authority["source_case"])
    expected["benchmark_provenance"] = {
        "stage": "S5",
        "suite_id": str(suite.get("suite_id")),
        "family_id": authority["family_id"],
        "split": split,
        "variant_type": authority["variant_type"],
        "evidence_class": suite.get("evidence_class"),
        "fresh_evidence": bool(suite.get("fresh_evidence", False)),
        "source_snapshot_commit": suite.get("source_snapshot_commit"),
        "source_manifest_path": _repo_rel(authority["manifest_path"]),
        "source_case_path": _repo_rel(authority["source_case_path"]),
        "source_manifest_sha256": sha256_file(authority["manifest_path"]),
        "source_case_sha256": sha256_file(authority["source_case_path"]),
        "materializer_version": materializer_version,
        "provenance_mode": "materialized_manifest_bound",
        "training_eligible": split in allowed and split not in prohibited,
    }
    expected["benchmark_provenance"]["materialized_payload_sha256"] = canonical_materialized_sha256(expected)
    return expected


def training_partition(case: Dict[str, Any], trust_policy: Dict[str, Any] | Path | None = None) -> tuple[str | None, bool | None, Dict[str, Any] | None]:
    policy = load_trust_policy(trust_policy)
    provenance = case.get("benchmark_provenance")
    if isinstance(provenance, dict):
        authority = _trusted_suite_authority(case, provenance, policy)
        expected = _expected_materialized_case(case, provenance, authority)
        observed = deepcopy(case)
        observed.pop("_training_export_context", None)
        if observed != expected:
            raise PermissionError(f"Training export blocked for case {case.get('case_id')}: payload/provenance diverges from external authority")
        split = authority["split"]
        eligible = bool(expected["benchmark_provenance"]["training_eligible"])
        return split, eligible, expected["benchmark_provenance"]

    context = case.get("_training_export_context")
    if isinstance(context, dict) and context.get("kind") == "ordinary_policy_allowlisted":
        path = _resolve_repo_path(context.get("path"))
        entry = (policy.get("ordinary_training_sources") or {}).get(_repo_rel(path))
        if not isinstance(entry, dict) or git_blob_sha1(path) != str(entry.get("git_blob_sha1") or ""):
            raise PermissionError(f"Training export blocked for case {case.get('case_id')}: ordinary-source authority no longer matches")
        return None, True, None

    if case.get("split") is not None:
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: partitioned case lacks external benchmark authority")
    raise PermissionError(f"Training export blocked for case {case.get('case_id')}: no external training-source authority")


def export_row(
    eval_row: Dict[str, Any],
    case: Dict[str, Any],
    run: Dict[str, Any] | None,
    trust_policy: Dict[str, Any] | Path | None = None,
) -> tuple[str, Dict[str, Any]] | None:
    candidate = eval_row.get("training_candidate") or {}
    if candidate.get("review_status") != "approved":
        return None

    split, eligible, provenance = training_partition(case, trust_policy)
    if split in BLOCKED_TRAINING_SPLITS or eligible is False:
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: split={split!r} is evaluation-only")
    if split is not None and split not in ALLOWED_TRAINING_SPLITS:
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: split={split!r} is not allowlisted")

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
    parser.add_argument("--trust-policy", type=Path, default=DEFAULT_TRUST_POLICY)
    args = parser.parse_args()

    policy = load_trust_policy(args.trust_policy)
    cases = load_cases(args.cases, policy)
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
        result = export_row(eval_row, cases[case_id], run, policy)
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
        "rule": "approved candidates only; export authority comes from external S5 trust policy",
        "trust_policy_version": policy.get("policy_version"),
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
