"""Organize existing private scoring drafts; never infer executable mappings.

The input is a frozen v0.4 draft and its public audit. Text is copied into a
private worksheet; only fixed fields and counts enter the public summary.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from .contracts import require
from .dynamic_case_drafts import _ADMISSION, _sha, _validate_private_case, _public_case_row
from .candidate_review import LOCAL_ROOT
from .import_batch import write_new_json


def prepare_worklist(private, audit):
    require(private.get("schema_version") == "dynamic-case-draft/v0.4", "unsupported private draft")
    require(audit.get("schema_version") == "dynamic-case-draft-audit/v0.1", "unsupported audit")
    require(private.get("admission") == audit.get("admission") == _ADMISSION,
            "admission state changed")
    require(private.get("local_only") is True and private.get("scope") == "development_only",
            "private draft scope changed")
    require(_sha(private) == audit.get("private_bundle_sha256"), "private draft digest mismatch")
    cases = private.get("cases")
    require(isinstance(cases, list) and bool(cases), "empty private draft")
    require([_public_case_row(c) for c in cases] == audit.get("cases"), "case audit mismatch")
    rows, counts, seen = [], [], set()
    for case in cases:
        _validate_private_case(case)
        require(re.fullmatch(r"C[0-9]{4}", case["candidate_id"]) is not None
                and case["case_id"] == "DEV04-" + case["candidate_id"], "invalid public case ID")
        require(case["case_id"] not in seen, "duplicate case ID")
        seen.add(case["case_id"])
        require(case.get("admission") == _ADMISSION and case["clinical_runnable"] == "BLOCKED",
                "case admission changed")
        drafted = [r for r in case["scoring_drafts"] if r["decision"] == "drafted"]
        require(len({r["criterion_id"] for r in drafted}) == len(drafted), "duplicate criterion ID")
        for rule in drafted:
            require(rule["structured_opportunity"] == {"trigger_turn": None, "response_turn": None,
                    "deadline": None, "mapping_status": "UNRESOLVED"}, "existing mapping must not be reset")
            require(set(rule["anchors"]) == {"0", "1", "2"}, "missing score anchors")
            rows.append({
                "case_id": case["case_id"], "candidate_id": case["candidate_id"],
                "criterion_id": rule["criterion_id"], "capability": rule["capability"],
                "existing_rule_draft": deepcopy(rule),
                "available_fact_ids": [f["fact_id"] for f in case["facts"]],
                "available_event_ids": [e["event_id"] for e in case["disclosure_events"]],
                "mapping_proposal": {"trigger_event_ids": [], "evidence_fact_ids": [],
                    "target_response_policy": None, "deadline_policy": None,
                    "not_applicable_condition": None, "not_reached_condition": None},
                "runtime_turn_mapping": {"trigger_turn_id": None, "response_turn_id": None},
                "review_status": "UNREVIEWED", "mapping_status": "UNRESOLVED",
                "clinical_adjudication_required": bool(rule["critical"] or rule["kind"] == "clinical"),
                "reviewer_decision": None, "reviewer_reason": None,
                "runtime_evaluated": False,
            })
        counts.append({"candidate_id": case["candidate_id"], "case_id": case["case_id"],
                       "prepared_draft_rows": len(drafted), "mapped_opportunities": 0})
    worksheet = {"schema_version": "patient-scoring-worklist/v0.1", "local_only": True,
                 "input_draft_sha256": _sha(private), "admission": deepcopy(_ADMISSION),
                 "interpretation": "已有草稿整理，不是新评分结论。原始来源话轮不等于未来运行话轮。",
                 "rows": rows}
    summary = {"schema_version": "patient-scoring-worklist-summary/v0.1",
               "input_draft_sha256": _sha(private), "admission": deepcopy(_ADMISSION),
               "cases": counts, "case_count": len(cases), "prepared_draft_rows": len(rows),
               "mapped_opportunities": 0, "independently_reviewed": 0, "runtime_evaluated": 0,
               "clinical_adjudication_required": sum(r["clinical_adjudication_required"] for r in rows),
               "patient_text_included": False,
               "interpretation": "草稿整理完成数与映射完成数分开统计；所有临床和运行状态保持待验收。"}
    return worksheet, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-drafts", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        out = Path(args.out)
        require(out.resolve().is_relative_to(LOCAL_ROOT.resolve()), "worksheet must stay under ignored local/")
        require(not out.exists(), "refusing to overwrite existing worksheet")
        private = json.loads(Path(args.private_drafts).read_text(encoding="utf-8"))
        audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
        worksheet, summary = prepare_worklist(private, audit)
        write_new_json(out, worksheet)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(2, f"scoring worklist failed: {error}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
