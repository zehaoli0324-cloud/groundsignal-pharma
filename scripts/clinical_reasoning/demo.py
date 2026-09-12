"""Run deterministic collection demonstrations, never model performance trials."""
import argparse
import json
from pathlib import Path
import sys

from .development import DevelopmentSession, validate_distractor_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("medical/patient-eval/clinical-reasoning-v1/cases"))
    args = parser.parse_args()
    cases = {name: json.loads((args.cases / (name + ".json")).read_text())
             for name in ("renal", "renal-distractor", "anemia")}
    output = {"mode": "scripted_engineering_demonstration", "model_calls": 0,
              "pair_check": validate_distractor_pair(cases["renal"], cases["renal-distractor"]),
              "sessions": []}
    for name in ("renal", "anemia"):
        case = cases[name]
        for fault in ("none", "drop_record_delivery"):
            env = DevelopmentSession(case, fault=fault)
            env.step({"action_id": "a1", "kind": "ask", "query": case["world"]["history"][0]["query"]})
            env.step({"action_id": "a2", "kind": "record", "query": case["world"]["records"][0]["query"]})
            # This is an author script closing a trace, not a model diagnosis.
            env.step({"action_id": "a3", "kind": "finish", "answer": "脚本取证演练结束，未生成临床判断。"})
            output["sessions"].append({"family": name, "fault": fault,
                                       "report": env.report(), "operator_trace": env.operator_trace()})
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
