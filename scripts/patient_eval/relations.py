"""Audit pressure declarations; never score answers or approve clinical facts.

Frozen v0.2 pairs are referenced without changing them. Separate fixed-prefix
developer examples exercise changed-fact and missing-information declarations.
Structural checks cannot establish the semantics of free text or clinical truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .contracts import nonempty, require, validate_turns


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RELATIONS = ROOT / "medical/patient-eval/calibration/v0.3/pressure-relations.json"
DEFAULT_SUITE = ROOT / "medical/patient-eval/pilot/v0.2/suite.json"
VERSION = "patient-pressure-relations/v0.3"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _diff(before, after, path=""):
    """Exact changed leaf paths, with collection insertion/removal kept atomic."""
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        changes = []
        for key in sorted(set(before) | set(after)):
            child = path + "/" + _escape(key)
            if key not in before or key not in after:
                changes.append(child)
            else:
                changes.extend(_diff(before[key], after[key], child))
        return changes
    if isinstance(before, list):
        if len(before) != len(after):
            return [path]
        return [p for i, (a, b) in enumerate(zip(before, after))
                for p in _diff(a, b, path + "/" + str(i))]
    return [] if before == after else [path]


def _get(value, pointer):
    require(isinstance(pointer, str) and pointer.startswith("/") and pointer != "/",
            "field paths must be non-root JSON pointers")
    try:
        for part in pointer[1:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        return value
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ValueError(f"unknown field path {pointer}") from error


def _inside(path, parent):
    return path == parent or path.startswith(parent + "/")


def _truth_paths(patient):
    paths = ["/facts/" + _escape(key) for key in patient["facts"]]
    paths.extend(f"/events/{i}/updates" for i, event in enumerate(patient.get("events", []))
                 if event.get("updates"))
    return paths


def _pair(relation, scenarios):
    ids = relation.get("source_scenario_ids")
    require(isinstance(ids, list) and bool(ids) and all(i in scenarios for i in ids),
            "unknown source scenario")
    sources = [scenarios[i] for i in ids]
    require(all(s["family_id"] == relation.get("family_id") for s in sources),
            "relation must retain the source family")
    criterion = relation.get("criterion_id")
    require(all(criterion in {c["id"] for c in s["criteria"]} for s in sources),
            "unknown criterion reference")
    if relation.get("pair_kind") == "frozen_pilot_variants":
        require(len(ids) == 2 and len(set(ids)) == 2 and "developer_pair" not in relation,
                "frozen pair requires two distinct source scenarios")
        require(sources[0]["criteria"] == sources[1]["criteria"] and
                sources[0]["protocol_id"] == sources[1]["protocol_id"],
                "paired criteria or protocol changed")
        return sources[0]["patient"], sources[1]["patient"]
    require(relation.get("pair_kind") == "developer_fixed_prefix" and len(ids) == 1,
            "unsupported pair kind")
    require(relation.get("eligible_for_pilot_comparison") is False,
            "developer pair cannot enter the frozen pilot comparison")
    pair = relation.get("developer_pair")
    require(isinstance(pair, dict) and set(pair) == {"baseline", "variant"},
            "developer pair must contain baseline and variant")
    for side in pair.values():
        require(isinstance(side, dict) and set(side) == {"facts", "visible_prefix"},
                "developer inputs require facts and visible_prefix only")
        validate_turns(side["visible_prefix"], completed=False)
        require(side["visible_prefix"][-1]["role"] == "user", "prefix must end in user")
        require(isinstance(side["facts"], dict) and bool(side["facts"]), "missing facts")
        for fact in side["facts"].values():
            require(isinstance(fact, dict) and set(fact) == {"value", "status"}, "invalid fact")
            require(fact["status"] in {"confirmed", "unknown"}, "invalid fact status")
            require((fact["value"] is None) == (fact["status"] == "unknown"),
                    "unknown fact must have null value; confirmed fact needs value")
    require(set(pair["baseline"]["facts"]) == set(pair["variant"]["facts"]),
            "developer pairs retain fact slots; mark removed information unknown")
    return pair["baseline"], pair["variant"]


def audit_relations(spec, suite):
    """Return a declaration audit or raise ValueError for a structural defect."""
    require(spec.get("schema_version") == VERSION, "unsupported relations schema")
    require(spec.get("scope") == "development_only" and spec.get("clinical_approval") is False,
            "relation materials cannot grant clinical or independent admission")
    require(spec.get("provenance") == "agent_authored_synthetic_development",
            "this entry point admits declared developer fixtures only")
    require(suite.get("schema_version") == "patient-pilot/v0.2", "unsupported source suite")
    require(spec.get("source_suite_sha256") == _digest(suite), "source suite fingerprint changed")
    sources = suite.get("scenarios", [])
    scenarios = {s["scenario_id"]: s for s in sources}
    require(len(scenarios) == len(sources), "duplicate source scenario")
    relations = spec.get("relations")
    require(isinstance(relations, list) and bool(relations), "empty relations")
    rows, seen = [], set()
    for relation in relations:
        rid = relation.get("relation_id")
        require(nonempty(rid) and rid not in seen, "missing or duplicate relation id")
        seen.add(rid)
        require(relation.get("review_status") == "unreviewed_development",
                "structural validation cannot approve a relation")
        kind = relation.get("relation")
        require(kind in {"invariant", "directional", "information_insufficient"}, "unknown relation")
        factor = relation.get("controlled_factor", {})
        require(nonempty(factor.get("id")) and nonempty(factor.get("description")),
                "one named controlled factor required")
        expected_type = {"invariant": "surface", "directional": "fact_update",
                         "information_insufficient": "information_removal"}[kind]
        require(factor.get("type") == expected_type, "factor type conflicts with relation")
        for field in ("expected_behavior", "positive_example", "negative_counterexample"):
            require(nonempty(relation.get(field)), f"missing {field}")
        require(relation["positive_example"] != relation["negative_counterexample"],
                "positive and negative examples must differ")
        require(nonempty(relation.get("reference_evidence")), "missing reference evidence")
        before, after = _pair(relation, scenarios)
        changed = _diff(before, after)
        declared = relation.get("changed_fields")
        require(isinstance(declared, list) and len(declared) == len(set(declared)) and
                set(declared) == set(changed) and bool(changed), "changed_fields do not match actual changes")
        permits = relation.get("permitted_changes")
        require(isinstance(permits, list) and len(permits) == len(changed), "invalid permitted changes")
        require(all(isinstance(p, dict) and set(p) == {"path", "factor_id"} and
                    p["factor_id"] == factor["id"] for p in permits), "undeclared additional factor")
        require({p["path"] for p in permits} == set(changed), "undeclared changed field")
        protected = relation.get("protected_facts")
        require(isinstance(protected, list) and bool(protected) and
                all(isinstance(p, str) for p in protected) and len(protected) == len(set(protected)),
                "protected facts must be unique paths")
        for path in protected:
            require(_get(before, path) == _get(after, path), f"protected fact changed: {path}")
        truth_paths = _truth_paths(before)
        changed_truth = [p for p in truth_paths if any(_inside(c, p) for c in changed)]
        for path in set(truth_paths) - set(changed_truth):
            require(any(_inside(path, protected_path) for protected_path in protected),
                    f"unchanged fact lacks protection: {path}")
        if kind == "invariant":
            require(not changed_truth, "false invariant: clinical fact state or update changed")
            # Only surface text is mutable, never triggers, budgets or fact answers.
            surfaces = {"/initial_user_message"} | {
                f"/events/{i}/content" for i, event in enumerate(before.get("events", []))
                if event.get("kind") == "pressure"}
            require(set(changed) <= surfaces, "invariant changed a non-surface field")
            require(len(changed) == 1, "invariant developer pair must change exactly one surface field")
        else:
            require(relation["pair_kind"] == "developer_fixed_prefix" and bool(changed_truth),
                    "fact-changing relations require separate developer examples")
            require(len(changed_truth) == 1, "change exactly one fact slot per developer example")
            path = changed_truth[0]
            old, new = _get(before, path), _get(after, path)
            if kind == "directional":
                require(old["status"] == new["status"] == "confirmed" and old["value"] != new["value"],
                        "directional example requires an explicit confirmed fact update")
            else:
                require(old["status"] == "confirmed" and new["status"] == "unknown" and new["value"] is None,
                        "insufficiency example must remove previously known information")
            prefixes = before["visible_prefix"], after["visible_prefix"]
            require(len(prefixes[0]) == len(prefixes[1]) and prefixes[0][:-1] == prefixes[1][:-1],
                    "developer pair must hold the earlier visible prefix fixed")
            allowed = {path + "/value", path + "/status",
                       f"/visible_prefix/{len(prefixes[0]) - 1}/content"}
            require(set(changed) <= allowed and any(c.startswith("/visible_prefix/") for c in changed),
                    "fact change must be paired with a last-user-message change only")
        rows.append({"relation_id": rid, "family_id": relation["family_id"], "relation": kind,
                     "pair_kind": relation["pair_kind"], "criterion_id": relation["criterion_id"],
                     "changed_fields": changed, "protected_fact_paths": len(protected),
                     "declaration_valid": True, "semantic_review": "unreviewed"})
    return {"schema_version": "patient-relation-audit/v0.3", "scope": "development_only",
            "spec_sha256": _digest(spec), "source_suite_sha256": _digest(suite),
            "relation_count": len(rows), "source_family_count": len({r["family_id"] for r in rows}),
            "relation_counts": dict(Counter(r["relation"] for r in rows)), "declarations": rows,
            "clinical_approval": False, "model_evaluation_performed": False,
            "interpretation": "Structural declaration audit only. Agent-authored synthetic development examples; "
            "not independent tests, semantic or clinical gold, model success rates, or admission evidence. "
            "Free-text factor isolation, fact consistency and expected behavior still require human review. "
            "Developer fixed-prefix examples are not frozen pilot variants; source families remain the grouping unit."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_RELATIONS)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--out", type=Path, required=True, help="new JSON audit file; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        audit = audit_relations(json.loads(args.spec.read_text(encoding="utf-8")),
                                json.loads(args.suite.read_text(encoding="utf-8")))
        with args.out.open("x", encoding="utf-8") as output:
            output.write(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"audit": str(args.out), "relations": audit["relation_count"],
                      "model_evaluation_performed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
