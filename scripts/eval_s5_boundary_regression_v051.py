#!/usr/bin/env python3
"""S5 v0.5.1 authority-composition repair exposed regression.

The v0.5 probes are permanently exposed. This evaluator preserves their immutable
first fresh FAIL and reuses those exact attack classes only as regression evidence.
It does not create or relabel fresh evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.5"
FIRST_OBSERVATION = ROOT / "medical/stage-evals/S5/fresh-first-observation-v0.5.json"
EXPECTED_FIRST_OBSERVATION_BLOB = "c300d301cb6bf23e5ec1cc0472666f44a1148e77"
DEFAULT_SCHEMA = ROOT / "medical/schemas/clinical-case.schema.json"

CARRIER_SUITE = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json"
CARRIER_ROOT = ROOT / "medical/stage-evals/S5/fresh-boundary-v0.4/families"
CARRIER_FAMILY = "S5FRESH-BOUNDARY-003"
CARRIER_HELDOUT = CARRIER_ROOT / CARRIER_FAMILY / "cases/S5FRESH-BND4-HO-001.json"
ORDINARY_SOURCE = ROOT / "medical/examples/clinical-medication-safety-001.json"
ORDINARY_COLLISION = EVAL_ROOT / "attack-sources/ordinary-caseid-collision.json"
ESCAPE_SUITE = EVAL_ROOT / "escape-authority/suite-escape-v0.5.json"
ESCAPE_ROOT = EVAL_ROOT / "escape-authority/families"

ORDINARY_CASE_ID = "clinical-medication-safety-001"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def approved_eval(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "training_candidate": {
            "review_status": "approved",
            "type": "sft",
            "ideal_response": "synthetic v0.5.1 exposed-regression response",
        },
    }


def export_probe(exporter: Any, case: dict[str, Any]) -> dict[str, Any]:
    try:
        result = exporter.export_row(approved_eval(str(case["case_id"])), case, None)
        return {"blocked": False, "exported": result is not None, "error_type": None}
    except PermissionError as exc:
        return {"blocked": True, "exported": False, "error_type": type(exc).__name__}
    except Exception as exc:
        return {
            "blocked": False,
            "exported": False,
            "error_type": type(exc).__name__,
            "unexpected_error": str(exc),
        }


def schema_exemption_aligned(schema: dict[str, Any]) -> bool:
    if "graph_eval" in set(schema.get("required") or []):
        return False
    for block in schema.get("allOf") or []:
        for alt in block.get("anyOf") or []:
            if "decision_contract_exemption" in set(alt.get("required") or []):
                return True
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    first = load_json(FIRST_OBSERVATION)
    preservation = {
        "expected_git_blob_sha": EXPECTED_FIRST_OBSERVATION_BLOB,
        "observed_git_blob_sha": git_blob_sha(FIRST_OBSERVATION),
        "historical_gate": first.get("fresh_structural_gate"),
        "historical_failures": first.get("hard_gate_failures"),
    }
    preservation["pass"] = bool(
        preservation["observed_git_blob_sha"] == EXPECTED_FIRST_OBSERVATION_BLOB
        and preservation["historical_gate"] == "FAIL"
        and preservation["historical_failures"] == ["S5-F16", "S5-F17", "S5-F18", "S5-F19"]
    )

    materializer = load_module(ROOT / "scripts/materialize_s5_cases.py", "s5_materializer_v051")
    exporter = load_module(ROOT / "scripts/export_training_data.py", "s5_exporter_v051")
    trust = load_module(ROOT / "scripts/s5_trust_policy.py", "s5_trust_v051")
    release_gate = load_module(ROOT / "scripts/s5_release_gate.py", "s5_release_v051")
    harness = load_module(ROOT / "scripts/model_harness.py", "s5_harness_v051")
    schema = load_json(args.schema)

    trust_root = exporter.trust_root_status()
    trust_root["pass"] = bool(trust_root.get("pass"))

    with tempfile.TemporaryDirectory(prefix="groundsignal-s5-v051-") as td_raw:
        td = Path(td_raw)
        carrier_out = td / "carrier"
        summary = materializer.materialize(CARRIER_SUITE, CARRIER_ROOT, carrier_out)
        paths = sorted(x for x in carrier_out.rglob("*.json") if x.name != "materialization-manifest.json")
        cases = [load_json(x) for x in paths]
        by_split: dict[str, dict[str, Any]] = {}
        split_counts: dict[str, int] = {}
        for case in cases:
            split = str((case.get("benchmark_provenance") or {}).get("split") or "")
            by_split.setdefault(split, case)
            split_counts[split] = split_counts.get(split, 0) + 1
        materialization = {
            "family_count": summary.get("family_count"),
            "case_count": summary.get("case_count"),
            "split_counts": dict(sorted(split_counts.items())),
            "training_eligible_count": summary.get("training_eligible_count"),
            "training_blocked_count": summary.get("training_blocked_count"),
        }
        materialization["pass"] = materialization == {
            "family_count": 1,
            "case_count": 5,
            "split_counts": {"dev": 3, "heldout": 1, "regression": 1},
            "training_eligible_count": 3,
            "training_blocked_count": 2,
        }

        bdev = export_probe(exporter, by_split["dev"])
        breg = export_probe(exporter, by_split["regression"])
        bho = export_probe(exporter, by_split["heldout"])
        baseline = {"dev": bdev, "regression": breg, "heldout": bho}
        baseline["pass"] = bool(bdev["exported"] and breg["blocked"] and bho["blocked"])

        ordinary_loaded = exporter.load_cases(ORDINARY_SOURCE)[ORDINARY_CASE_ID]
        ordinary_probe = export_probe(exporter, ordinary_loaded)
        ordinary_control = {**ordinary_probe, "pass": ordinary_probe["exported"]}

        mutated = copy.deepcopy(ordinary_loaded)
        mutated["interaction"]["prompt"] += " [ATTACKER_MUTATION_AFTER_ORDINARY_SOURCE_AUTHENTICATION]"
        f16_probe = export_probe(exporter, mutated)
        f16 = {
            "probe": "mutate allowlisted ordinary case after loader authentication",
            **f16_probe,
            "pass": f16_probe["blocked"],
        }

        forged = copy.deepcopy(load_json(CARRIER_HELDOUT))
        forged["_training_export_context"] = copy.deepcopy(ordinary_loaded["_training_export_context"])
        f17_probe = export_probe(exporter, forged)
        f17 = {
            "probe": "borrow authenticated ordinary-source context for raw heldout benchmark payload",
            "borrowed_context_path": forged["_training_export_context"].get("path"),
            **f17_probe,
            "pass": f17_probe["blocked"],
        }

        builder_rejected = False
        validator_rejected = False
        collision_policy = None
        try:
            collision_policy = trust.build_policy(
                [(CARRIER_SUITE, CARRIER_ROOT)],
                ordinary_sources=[ORDINARY_COLLISION],
                policy_version="s5-trust-root-v0.5-attack-collision",
            )
        except ValueError:
            builder_rejected = True
        # Independently exercise exporter's content validator even when the repaired builder rejects.
        if collision_policy is None:
            baseline_policy = trust.build_policy(
                [(CARRIER_SUITE, CARRIER_ROOT)],
                policy_version="s5-trust-root-v0.5-attack-collision",
            )
            collision_policy = copy.deepcopy(baseline_policy)
            collision_policy["ordinary_training_sources"] = {
                ORDINARY_COLLISION.relative_to(ROOT).as_posix(): {
                    "git_blob_sha1": git_blob_sha(ORDINARY_COLLISION)
                }
            }
        try:
            exporter._validate_policy_content(collision_policy, "s5-trust-root-v0.5-attack-collision")
        except PermissionError:
            validator_rejected = True
        f18 = {
            "probe": "byte-distinct ordinary source reuses a benchmark heldout case_id",
            "policy_builder_rejected": builder_rejected,
            "policy_content_validator_rejected": validator_rejected,
            "pass": builder_rejected and validator_rejected,
        }

        escape_builder_rejected = False
        escape_materializer_rejected = False
        try:
            trust.build_policy(
                [(ESCAPE_SUITE, ESCAPE_ROOT)],
                policy_version="s5-trust-root-v0.5-attack-family-escape",
            )
        except ValueError:
            escape_builder_rejected = True
        try:
            materializer.materialize(ESCAPE_SUITE, ESCAPE_ROOT, td / "escape")
        except (ValueError, FileNotFoundError, PermissionError):
            escape_materializer_rejected = True
        f19 = {
            "probe": "declared family manifest references case under non-member sibling family",
            "policy_builder_rejected": escape_builder_rejected,
            "materializer_rejected": escape_materializer_rejected,
            "pass": escape_builder_rejected and escape_materializer_rejected,
        }

        exemption = copy.deepcopy(by_split["dev"])
        exemption.pop("benchmark_provenance", None)
        exemption.pop("graph_eval", None)
        exemption["decision_contract_exemption"] = {
            "type": "NON_REASONING_CONTROL",
            "rationale": "v0.5.1 alignment control",
        }
        materializer_accepts = True
        try:
            materializer.validate_decision_contract(exemption)
        except ValueError:
            materializer_accepts = False
        decision_alignment = {
            "materializer_accepts_exemption": materializer_accepts,
            "schema_accepts_exemption_shape": schema_exemption_aligned(schema),
        }
        decision_alignment["pass"] = bool(
            decision_alignment["materializer_accepts_exemption"]
            and decision_alignment["schema_accepts_exemption_shape"]
        )

        sentinel = "S5_V051_GOLD_SENTINEL_DO_NOT_EXPOSE"
        prompt_case = copy.deepcopy(by_split["dev"])
        prompt_case["expected_behavior"]["must_include"].append(sentinel)
        prompt_case["graph_eval"]["expected_reasoning_path"].append(sentinel)
        prompt_case["safety"]["critical_errors"].append(sentinel)
        rendered = harness.build_user_prompt(prompt_case, "")
        prompt_leakage = {"sentinel_leaked": sentinel in rendered, "pass": sentinel not in rendered}

    gold = release_gate.evaluate(CARRIER_SUITE, CARRIER_ROOT)
    gold_containment = {
        "gold_approved_count": gold.get("gold_approved_count"),
        "pending_gold_count": gold.get("pending_gold_count"),
        "release_ready": gold.get("release_ready"),
        "decision": gold.get("decision"),
    }
    gold_containment["pass"] = bool(
        gold_containment["gold_approved_count"] == 0
        and gold_containment["pending_gold_count"] == 1
        and gold_containment["release_ready"] is False
        and gold_containment["decision"] == "BLOCKED_GOLD_REVIEW"
    )

    gates = {
        "historical_first_observation_preservation": preservation,
        "authenticated_trust_root": trust_root,
        "carrier_materialization": materialization,
        "baseline_partition_export_guard": baseline,
        "ordinary_source_allowlist_control": ordinary_control,
        "S5-F16": f16,
        "S5-F17": f17,
        "S5-F18": f18,
        "S5-F19": f19,
        "decision_contract_alignment": decision_alignment,
        "model_prompt_gold_leakage": prompt_leakage,
        "gold_release_containment": gold_containment,
    }
    failed = [name for name, gate in gates.items() if not gate.get("pass")]
    passed = not failed
    result = {
        "stage": "S5",
        "version": "v0.5.1",
        "eval_name": "authority-composition-repair-exposed-regression",
        "evidence_class": "development_exposed_regression",
        "fresh_evidence": False,
        "first_observation": False,
        "source_fresh_suite": "S5 v0.5 first observation; now exposed",
        **gates,
        "historical_failure_disposition": {
            "S5-F16": "REPAIRED_EXPOSED_REGRESSION" if f16["pass"] else "OPEN",
            "S5-F17": "REPAIRED_EXPOSED_REGRESSION" if f17["pass"] else "OPEN",
            "S5-F18": "REPAIRED_EXPOSED_REGRESSION" if f18["pass"] else "OPEN",
            "S5-F19": "REPAIRED_EXPOSED_REGRESSION" if f19["pass"] else "OPEN",
        },
        "failed_gates": failed,
        "regression_gate": "PASS" if passed else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "next_fresh_requirement": (
            "freeze v0.5.1, then author a genuinely new post-freeze authority-boundary suite; "
            "v0.5 is exposed forever"
        ),
        "notes": [
            "v0.5 is exposed regression evidence only; its fresh FAIL remains immutable.",
            "Ordinary-source export now reconstructs and exactly compares the authenticated source payload.",
            "case_id is reserved across benchmark and ordinary policy namespaces.",
            "Policy construction and materialization both enforce declared-family path containment.",
            "No expert approval, clinical validation, real-user evidence, or model-training gain is inferred.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
