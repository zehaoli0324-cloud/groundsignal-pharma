#!/usr/bin/env python3
"""Export explicitly reviewed evaluation failures into SFT/preference candidates.

S5 v0.6.1 trust rules:
- authenticated authority files are parsed from the exact byte snapshot that is hashed;
- policy registry remains the compile-time authenticated trust anchor;
- benchmark suite/family/manifest/source identities are externally policy-bound;
- ordinary sources are bound to backing file, exact loaded payload, canonical case_id and payload digest;
- benchmark/ordinary namespaces reject canonical-id and semantic-core lineage collisions;
- heldout/regression partitions remain evaluation-only and fail closed;
- caller-invented, substituted or off-repository authority is rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUST_POLICY = REPO_ROOT / "medical/configs/s5-trust-root-v0.4.1.json"
TRUST_POLICY_REGISTRY_PATH = REPO_ROOT / "medical/configs/s5-trust-policy-registry-v0.4.1.json"
TRUST_POLICY_REGISTRY_VERSION = "s5-trust-policy-registry-v0.4.1"
TRUST_POLICY_REGISTRY_GIT_BLOB_SHA1 = "b9637e31df679e49b36d49ea96177a8100fd5c2a"
ALLOWED_TRAINING_SPLITS = {"dev"}
BLOCKED_TRAINING_SPLITS = {"heldout", "regression"}
KNOWN_BENCHMARK_SPLITS = ALLOWED_TRAINING_SPLITS | BLOCKED_TRAINING_SPLITS
TRUSTED_MATERIALIZER_VERSIONS = {"s5-materializer-v0.2.1"}
SEMANTIC_CORE_FIELDS = (
    "task_type",
    "data_origin",
    "patient_context",
    "evidence_snapshot",
    "interaction",
    "expected_behavior",
    "graph_eval",
    "safety",
    "scoring",
)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _git_blob_sha1_bytes(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Compatibility helper. Security-sensitive reads use _json_snapshot instead."""
    return _git_blob_sha1_bytes(path.read_bytes())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_snapshot(path: Path) -> tuple[Dict[str, Any], str, str]:
    """Read once; hash and parse the same immutable in-memory byte snapshot."""
    data = path.read_bytes()
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermissionError(f"S5 export blocked: invalid authenticated JSON snapshot: {path}") from exc
    if not isinstance(obj, dict):
        raise PermissionError(f"S5 export blocked: authenticated JSON must be an object: {path}")
    return obj, _git_blob_sha1_bytes(data), hashlib.sha256(data).hexdigest()


def _authenticated_json(path: Path, expected_blob: str, label: str) -> tuple[Dict[str, Any], str]:
    obj, observed_blob, sha256 = _json_snapshot(path)
    if not expected_blob or observed_blob != expected_blob:
        raise PermissionError(f"S5 export blocked: {label} identity mismatch")
    return obj, sha256


def canonical_case_id(value: Any) -> str:
    text = str(value or "")
    return unicodedata.normalize("NFC", text)


def _require_canonical_case_id(value: Any, label: str) -> str:
    raw = str(value or "")
    if not raw:
        raise PermissionError(f"S5 export blocked: {label} lacks case_id")
    normalized = canonical_case_id(raw)
    if raw != normalized:
        raise PermissionError(f"S5 export blocked: {label} case_id is not Unicode NFC canonical")
    return normalized


def semantic_core_sha256(case: Dict[str, Any]) -> str:
    core = {key: deepcopy(case.get(key)) for key in SEMANTIC_CORE_FIELDS}
    encoded = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_materialized_sha256(case: Dict[str, Any]) -> str:
    payload = deepcopy(case)
    payload.pop("_training_export_context", None)
    provenance = payload.get("benchmark_provenance")
    if isinstance(provenance, dict):
        provenance.pop("materialized_payload_sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_case_sha256(case: Dict[str, Any]) -> str:
    payload = deepcopy(case)
    payload.pop("_training_export_context", None)
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


def _validate_policy_content(policy: Dict[str, Any], expected_policy_id: str) -> None:
    if str(policy.get("policy_version") or "") != expected_policy_id:
        raise PermissionError(f"S5 export blocked: policy version mismatch; expected {expected_policy_id!r}")
    suites = policy.get("benchmark_suites")
    ordinary = policy.get("ordinary_training_sources")
    if not isinstance(suites, dict) or not isinstance(ordinary, dict):
        raise PermissionError("S5 export blocked: malformed external trust policy")

    benchmark_case_ids: dict[str, str] = {}
    benchmark_blobs: dict[str, str] = {}
    benchmark_semantic_cores: dict[str, str] = {}

    for suite_id, suite_entry in suites.items():
        if not isinstance(suite_entry, dict):
            raise PermissionError(f"S5 export blocked: malformed suite entry {suite_id!r}")
        for field in ("suite_path", "suite_git_blob_sha1", "family_root"):
            if not str(suite_entry.get(field) or ""):
                raise PermissionError(f"S5 export blocked: suite {suite_id!r} missing {field}")
        suite_path = _resolve_repo_path(suite_entry["suite_path"])
        suite_obj, _ = _authenticated_json(
            suite_path, str(suite_entry["suite_git_blob_sha1"]), f"suite {suite_id!r}"
        )
        if str(suite_obj.get("suite_id") or "") != str(suite_id):
            raise PermissionError(f"S5 export blocked: suite identity mismatch for {suite_id!r}")
        family_root = _resolve_repo_path(suite_entry["family_root"])
        families = suite_entry.get("families")
        if not isinstance(families, dict) or not families:
            raise PermissionError(f"S5 export blocked: suite {suite_id!r} has no families")

        for family_id, family_entry in families.items():
            if not isinstance(family_entry, dict):
                raise PermissionError(f"S5 export blocked: malformed family {suite_id}/{family_id}")
            for field in ("manifest_path", "manifest_git_blob_sha1"):
                if not str(family_entry.get(field) or ""):
                    raise PermissionError(f"S5 export blocked: family {suite_id}/{family_id} missing {field}")
            manifest_path = _resolve_repo_path(family_entry["manifest_path"])
            expected_manifest_path = (family_root / str(family_id) / "manifest.json").resolve()
            if manifest_path != expected_manifest_path:
                raise PermissionError(f"S5 export blocked: manifest path is not family-authoritative: {family_id}")
            manifest, _ = _authenticated_json(
                manifest_path,
                str(family_entry["manifest_git_blob_sha1"]),
                f"manifest {suite_id}/{family_id}",
            )
            if str(manifest.get("family_id") or "") != str(family_id):
                raise PermissionError(f"S5 export blocked: manifest family mismatch: {family_id}")
            cases = family_entry.get("cases")
            if not isinstance(cases, dict) or not cases:
                raise PermissionError(f"S5 export blocked: family {suite_id}/{family_id} has no cases")

            for raw_case_id, case_entry in cases.items():
                case_id = _require_canonical_case_id(raw_case_id, f"benchmark {suite_id}/{family_id}")
                if case_id in benchmark_case_ids:
                    raise PermissionError(
                        f"S5 export blocked: duplicate benchmark case_id {case_id!r} across "
                        f"{benchmark_case_ids[case_id]} and {suite_id}/{family_id}"
                    )
                benchmark_case_ids[case_id] = f"{suite_id}/{family_id}"
                if not isinstance(case_entry, dict):
                    raise PermissionError(f"S5 export blocked: malformed case authority {case_id!r}")
                split = str(case_entry.get("split") or "")
                if split not in KNOWN_BENCHMARK_SPLITS:
                    raise PermissionError(f"S5 export blocked: unknown trusted split for {case_id!r}")
                for field in ("source_case_path", "source_case_git_blob_sha1", "variant_type"):
                    if not str(case_entry.get(field) or ""):
                        raise PermissionError(f"S5 export blocked: case {case_id!r} missing {field}")
                source_path = _resolve_repo_path(case_entry["source_case_path"])
                try:
                    source_path.relative_to(manifest_path.parent.resolve())
                except ValueError as exc:
                    raise PermissionError(f"S5 export blocked: source case escapes declared family: {case_id}") from exc
                source_obj, _ = _authenticated_json(
                    source_path,
                    str(case_entry["source_case_git_blob_sha1"]),
                    f"source case {case_id!r}",
                )
                source_id = _require_canonical_case_id(source_obj.get("case_id"), f"source case {case_id!r}")
                if source_id != case_id:
                    raise PermissionError(f"S5 export blocked: source-case id mismatch for {case_id!r}")
                blob = str(case_entry["source_case_git_blob_sha1"])
                prior = benchmark_blobs.get(blob)
                if prior and prior != case_id:
                    raise PermissionError(
                        f"S5 export blocked: benchmark blob identity reused by {prior!r} and {case_id!r}"
                    )
                benchmark_blobs[blob] = case_id
                core = semantic_core_sha256(source_obj)
                benchmark_semantic_cores.setdefault(core, case_id)

    ordinary_case_ids: dict[str, str] = {}
    for rel, entry in ordinary.items():
        if not isinstance(entry, dict):
            raise PermissionError(f"S5 export blocked: malformed ordinary source entry {rel!r}")
        blob = str(entry.get("git_blob_sha1") or "")
        if not blob:
            raise PermissionError(f"S5 export blocked: ordinary source {rel!r} lacks blob identity")
        path = _resolve_repo_path(rel)
        if _repo_rel(path) != rel or not path.is_file():
            raise PermissionError(f"S5 export blocked: ordinary source path mismatch: {rel}")
        source, _ = _authenticated_json(path, blob, f"ordinary source {rel!r}")
        if blob in benchmark_blobs:
            raise PermissionError(
                f"S5 export blocked: ordinary source {rel!r} is byte-identical to benchmark case "
                f"{benchmark_blobs[blob]!r}"
            )
        case_id = _require_canonical_case_id(source.get("case_id"), f"ordinary source {rel!r}")
        if case_id in benchmark_case_ids:
            raise PermissionError(
                f"S5 export blocked: ordinary source {rel!r} reuses benchmark case_id {case_id!r}"
            )
        if case_id in ordinary_case_ids:
            raise PermissionError(
                f"S5 export blocked: ordinary case_id {case_id!r} reused by "
                f"{ordinary_case_ids[case_id]!r} and {rel!r}"
            )
        core = semantic_core_sha256(source)
        if core in benchmark_semantic_cores:
            raise PermissionError(
                f"S5 export blocked: ordinary source {rel!r} shares benchmark semantic core with "
                f"{benchmark_semantic_cores[core]!r}"
            )
        ordinary_case_ids[case_id] = rel


def _registered_policy_catalog() -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    if not TRUST_POLICY_REGISTRY_PATH.is_file():
        raise PermissionError("S5 export blocked: authenticated trust-policy registry is missing")
    registry, _ = _authenticated_json(
        TRUST_POLICY_REGISTRY_PATH,
        TRUST_POLICY_REGISTRY_GIT_BLOB_SHA1,
        "trust-policy registry",
    )
    if str(registry.get("registry_version") or "") != TRUST_POLICY_REGISTRY_VERSION:
        raise PermissionError("S5 export blocked: unsupported trust-policy registry version")
    entries = registry.get("policies")
    default_id = str(registry.get("default_policy_id") or "")
    if not isinstance(entries, dict) or not entries or default_id not in entries:
        raise PermissionError("S5 export blocked: malformed trust-policy registry")

    catalog: Dict[str, Dict[str, Any]] = {}
    seen_paths: set[str] = set()
    for policy_id, entry in entries.items():
        if not isinstance(entry, dict):
            raise PermissionError(f"S5 export blocked: malformed registry entry {policy_id!r}")
        path = _resolve_repo_path(entry.get("path"))
        rel = _repo_rel(path)
        if rel != str(entry.get("path") or ""):
            raise PermissionError(f"S5 export blocked: non-canonical policy path for {policy_id!r}")
        if rel in seen_paths:
            raise PermissionError("S5 export blocked: trust registry reuses a policy path")
        seen_paths.add(rel)
        expected_blob = str(entry.get("git_blob_sha1") or "")
        if not expected_blob or not path.is_file():
            raise PermissionError(f"S5 export blocked: registered policy identity missing for {policy_id!r}")
        policy_obj, _ = _authenticated_json(path, expected_blob, f"registered policy {policy_id!r}")
        _validate_policy_content(policy_obj, str(policy_id))
        catalog[str(policy_id)] = {
            "path": path,
            "path_rel": rel,
            "git_blob_sha1": expected_blob,
            "policy": policy_obj,
        }
    return registry, catalog


def trust_root_status() -> Dict[str, Any]:
    registry, catalog = _registered_policy_catalog()
    default_id = str(registry["default_policy_id"])
    default = catalog[default_id]
    return {
        "registry_version": registry["registry_version"],
        "registry_path": _repo_rel(TRUST_POLICY_REGISTRY_PATH),
        "registry_git_blob_sha1": TRUST_POLICY_REGISTRY_GIT_BLOB_SHA1,
        "default_policy_id": default_id,
        "default_policy_path": default["path_rel"],
        "default_policy_git_blob_sha1": default["git_blob_sha1"],
        "registered_policy_count": len(catalog),
        "pass": True,
    }


def load_trust_policy(policy: Dict[str, Any] | Path | None = None) -> Dict[str, Any]:
    registry, catalog = _registered_policy_catalog()
    if policy is None:
        return deepcopy(catalog[str(registry["default_policy_id"])]["policy"])
    if isinstance(policy, dict):
        for entry in catalog.values():
            if policy == entry["policy"]:
                return deepcopy(entry["policy"])
        raise PermissionError("S5 export blocked: caller-supplied policy object is not an authenticated registry policy")
    path = _resolve_repo_path(str(Path(policy)))
    for entry in catalog.values():
        if path == entry["path"]:
            return deepcopy(entry["policy"])
    raise PermissionError(f"S5 export blocked: policy path is not registered as a trust root: {_repo_rel(path)}")


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if not path.is_dir():
        raise FileNotFoundError(path)
    for file in sorted(path.rglob("*.json")):
        if file.name != "materialization-manifest.json":
            yield file


def _ordinary_source_context(
    file: Path,
    policy: Dict[str, Any],
    source: Dict[str, Any] | None = None,
    observed_blob: str | None = None,
) -> Dict[str, Any]:
    rel = _repo_rel(file)
    entry = (policy.get("ordinary_training_sources") or {}).get(rel)
    if not isinstance(entry, dict):
        raise PermissionError(f"S5 export blocked: ordinary source is not externally allowlisted: {rel}")
    expected = str(entry.get("git_blob_sha1") or "")
    if source is None or observed_blob is None:
        source, observed_blob, _ = _json_snapshot(file)
    if not expected or observed_blob != expected:
        raise PermissionError(f"S5 export blocked: ordinary source identity mismatch: {rel}")
    case_id = _require_canonical_case_id(source.get("case_id"), f"ordinary source {rel!r}")
    return {
        "kind": "ordinary_policy_allowlisted",
        "path": rel,
        "git_blob_sha1": observed_blob,
        "case_id": case_id,
        "payload_sha256": canonical_case_sha256(source),
    }


def load_cases(path: Path, trust_policy: Dict[str, Any] | Path | None = None) -> Dict[str, Dict[str, Any]]:
    policy = load_trust_policy(trust_policy)
    cases: Dict[str, Dict[str, Any]] = {}
    for file in _iter_json_files(path):
        case, observed_blob, _ = _json_snapshot(file)
        if not isinstance(case.get("benchmark_provenance"), dict):
            case = dict(case)
            case["_training_export_context"] = _ordinary_source_context(
                file, policy, source=case, observed_blob=observed_blob
            )
        case_id = _require_canonical_case_id(case.get("case_id"), f"loaded case {file}")
        if case_id in cases:
            raise ValueError(f"Duplicate case_id while loading export input: {case_id}")
        cases[case_id] = case
    return cases


def run_index(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[Tuple[str, str], Dict[str, Any]]]:
    by_run: Dict[str, Dict[str, Any]] = {}
    by_case_model: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if row.get("run_id"):
            by_run[str(row["run_id"])] = row
        if row.get("case_id") and row.get("model_id"):
            by_case_model[(str(row["case_id"]), str(row["model_id"]))] = row
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
    case_id = _require_canonical_case_id(case.get("case_id"), "materialized benchmark case")
    if provenance.get("stage") != "S5":
        raise PermissionError(f"Training export blocked for case {case_id}: unsupported provenance stage")
    suite_id = str(provenance.get("suite_id") or "")
    suite_entry = (policy.get("benchmark_suites") or {}).get(suite_id)
    if not isinstance(suite_entry, dict):
        raise PermissionError(f"Training export blocked for case {case_id}: suite {suite_id!r} is not in external trust policy")
    suite_path = _resolve_repo_path(suite_entry.get("suite_path"))
    suite, _ = _authenticated_json(
        suite_path, str(suite_entry.get("suite_git_blob_sha1") or ""), f"trusted suite {suite_id!r}"
    )
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
    manifest, manifest_sha256 = _authenticated_json(
        manifest_path,
        str(family_entry.get("manifest_git_blob_sha1") or ""),
        f"trusted manifest {family_id!r}",
    )
    if str(manifest.get("family_id") or "") != family_id:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest family mismatch")

    case_entry = (family_entry.get("cases") or {}).get(case_id)
    if not isinstance(case_entry, dict):
        raise PermissionError(f"Training export blocked for case {case_id}: case absent from external trust policy")
    source_case_path = _resolve_repo_path(case_entry.get("source_case_path"))
    declared_family_dir = manifest_path.parent.resolve()
    try:
        source_case_path.relative_to(declared_family_dir)
    except ValueError as exc:
        raise PermissionError(f"Training export blocked for case {case_id}: source case escapes declared family") from exc
    source_case, source_case_sha256 = _authenticated_json(
        source_case_path,
        str(case_entry.get("source_case_git_blob_sha1") or ""),
        f"trusted source case {case_id!r}",
    )
    source_id = _require_canonical_case_id(source_case.get("case_id"), f"source case {case_id!r}")
    if source_id != case_id:
        raise PermissionError(f"Training export blocked for case {case_id}: source-case id mismatch")

    refs = [r for r in manifest.get("cases") or [] if str(r.get("case_id") or "") == case_id]
    if len(refs) != 1:
        raise PermissionError(f"Training export blocked for case {case_id}: manifest case membership is ambiguous")
    ref = refs[0]
    split = str(case_entry.get("split") or "")
    variant = str(case_entry.get("variant_type") or "")
    if split not in KNOWN_BENCHMARK_SPLITS:
        raise PermissionError(f"Training export blocked for case {case_id}: unknown trusted split")
    if str(ref.get("split") or "") != split or str(ref.get("variant_type") or "") != variant:
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
        "manifest_sha256": manifest_sha256,
        "ref": ref,
        "source_case": source_case,
        "source_case_path": source_case_path,
        "source_case_sha256": source_case_sha256,
        "split": split,
        "variant_type": variant,
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
        raise PermissionError(
            f"Training export blocked for case {case.get('case_id')}: untrusted materializer version {materializer_version!r}"
        )
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
        "source_manifest_sha256": authority["manifest_sha256"],
        "source_case_sha256": authority["source_case_sha256"],
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
            raise PermissionError(
                f"Training export blocked for case {case.get('case_id')}: payload/provenance diverges from external authority"
            )
        split = authority["split"]
        return split, bool(expected["benchmark_provenance"]["training_eligible"]), expected["benchmark_provenance"]

    context = case.get("_training_export_context")
    if isinstance(context, dict) and context.get("kind") == "ordinary_policy_allowlisted":
        path = _resolve_repo_path(context.get("path"))
        rel = _repo_rel(path)
        entry = (policy.get("ordinary_training_sources") or {}).get(rel)
        expected_blob = str((entry or {}).get("git_blob_sha1") or "")
        if not isinstance(entry, dict) or not expected_blob:
            raise PermissionError(f"Training export blocked for case {case.get('case_id')}: ordinary-source authority missing")
        source, _ = _authenticated_json(path, expected_blob, f"ordinary source {rel!r}")
        source_case_id = _require_canonical_case_id(source.get("case_id"), f"ordinary source {rel!r}")
        observed = deepcopy(case)
        observed.pop("_training_export_context", None)
        expected_payload_sha = canonical_case_sha256(source)
        if (
            str(context.get("path") or "") != rel
            or str(context.get("git_blob_sha1") or "") != expected_blob
            or str(context.get("case_id") or "") != source_case_id
            or str(context.get("payload_sha256") or "") != expected_payload_sha
            or _require_canonical_case_id(case.get("case_id"), "ordinary export case") != source_case_id
            or observed != source
        ):
            raise PermissionError(
                f"Training export blocked for case {case.get('case_id')}: ordinary payload/context diverges from exact source authority"
            )
        return None, True, None

    if case.get("split") is not None:
        raise PermissionError(f"Training export blocked for case {case.get('case_id')}: partitioned case lacks external benchmark authority")
    raise PermissionError(f"Training export blocked for case {case.get('case_id')}: no external training-source authority")


def export_row(eval_row: Dict[str, Any], case: Dict[str, Any], run: Dict[str, Any] | None, trust_policy: Dict[str, Any] | Path | None = None) -> tuple[str, Dict[str, Any]] | None:
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
        result = export_row(eval_row, cases[case_id], find_run(eval_row, by_run, by_case_model), policy)
        if result is None:
            skipped += 1
            continue
        kind, row = result
        (sft_rows if kind == "sft" else pref_rows).append(row)

    write_jsonl(args.out_dir / "sft.jsonl", sft_rows)
    write_jsonl(args.out_dir / "preference.jsonl", pref_rows)
    status = trust_root_status()
    manifest = {
        "sft_count": len(sft_rows),
        "preference_count": len(pref_rows),
        "skipped_not_approved_or_none": skipped,
        "rule": "approved candidates only; export authority comes from authenticated S5 trust-policy registry",
        "trust_policy_version": policy.get("policy_version"),
        "trust_policy_registry_version": status.get("registry_version"),
        "trust_policy_registry_git_blob_sha1": status.get("registry_git_blob_sha1"),
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
