# -*- coding: utf-8 -*-
"""Write Codex v0.2 scores (benchmark 10-dim + user-utility U1-U5) into each case scores/ dir."""
import json, os

REPO = "/home/zehaoli0324/projects/groundsignal-pharma"
CASES = [
    "case-001-competitive-impact", "case-002-regulatory-conflict",
    "case-003-licensing-bd", "case-004-due-diligence",
    "case-005-safety-signal", "case-006-temporal-watchlist",
]
BENCHMARK_ALL2 = {
    "1_factual": 2, "2_evidence": 2, "3_temporal": 2, "4_competitive": 2,
    "5_decision": 2, "6_prioritization": 2, "7_uncertainty": 2,
    "8_actionability": 2, "9_density": 2, "10_expression": 2,
}
U_ALL2 = {"U1_decision_fit": 2, "U2_trust": 2, "U3_prioritization": 2, "U4_actionability": 2, "U5_uncertainty": 2}

NOTES = {
    "case-001-competitive-impact": "EJ 直接 A>B>C（同适应症同机制已上市/市场竞争/机制不同III期）；明确'不能仅监控同机制也不能无差别全列'；无头对头/价格/医保时不判断优效",
    "case-002-regulatory-conflict": "Tier 0 决定权 + under review 不能标已获批；媒体/聚合不能覆盖监管记录；事实与预期分离",
    "case-003-licensing-bd": "B>A>C 与 gold 一致；A 的 portfolio conflict（资源竞争/估值压价/交易搁置）识别；C 只有资金无战略需求",
    "case-004-due-diligence": "best-in-class=HYPOTHESIS 可信度偏低；62% vs 48% 跨试验不可比；投委会应给'期权价值+明确折价'而非 superiority 溢价",
    "case-005-safety-signal": "不认定因果/类别效应；Competitor B 大量暴露无警告=反证；升 High 优先级但触发条件驱动分阶段战略调整",
    "case-006-temporal-watchlist": "E1/E3/E5 Top3 与 gold 一致；E2/E4 去重；E9 未证实线索不占 Top3；E3 终止原因为主要不确定性",
}

for c in CASES:
    d = os.path.join(REPO, "benchmark/cases", c, "scores")
    os.makedirs(d, exist_ok=True)
    meta = {"case_id": c, "model": "codex-cli-0.149.1/gpt-5-family", "date": "2026-08-27",
            "judge": "human-reviewer", "protocol": "scoring-protocol v1",
            "critical_errors": [], "failure_types": [], "notes": NOTES[c]}
    bench = {**meta, "scores": BENCHMARK_ALL2, "total": 20, "max": 20}
    json.dump(bench, open(os.path.join(d, "benchmark-scores.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    ut = {**meta, "scores": U_ALL2, "total": 10, "max": 10, "utility_level": "Decision-ready"}
    json.dump(ut, open(os.path.join(d, "user-utility-scores.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(c, "20/20 U 10/10")
print("DONE codex scores")
