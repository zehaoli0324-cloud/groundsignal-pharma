# -*- coding: utf-8 -*-
"""Write DeepSeek v0.2 scores (benchmark 10-dim + user-utility U1-U5) into each case scores/ dir."""
import json, os

REPO = "/home/zehaoli0324/projects/groundsignal-pharma"
CASES = [
    "case-001-competitive-impact", "case-002-regulatory-conflict",
    "case-003-licensing-bd", "case-004-due-diligence",
    "case-005-safety-signal", "case-006-temporal-watchlist",
]

# All-2 benchmark scores per case (DeepSeek, scored 2026-08-27 by human judge)
BENCHMARK_ALL2 = {
    "1_factual": 2, "2_evidence": 2, "3_temporal": 2, "4_competitive": 2,
    "5_decision": 2, "6_prioritization": 2, "7_uncertainty": 2,
    "8_actionability": 2, "9_density": 2, "10_expression": 2,
}

# Per-case U scores (Decision Fit / Trust / Prioritization / Actionability / Uncertainty)
U_ALL2 = {"U1_decision_fit": 2, "U2_trust": 2, "U3_prioritization": 2, "U4_actionability": 2, "U5_uncertainty": 2}

def write_scores(case_id, benchmark, u_scores, notes):
    d = os.path.join(REPO, "benchmark/cases", case_id, "scores")
    os.makedirs(d, exist_ok=True)
    meta = {
        "case_id": case_id, "model": "deepseek-chat", "date": "2026-08-27",
        "judge": "human-reviewer", "protocol": "scoring-protocol v1",
        "critical_errors": [], "failure_types": [], "notes": notes,
    }
    bench = {**meta, "scores": benchmark, "total": sum(benchmark.values()), "max": 20}
    json.dump(bench, open(os.path.join(d, "benchmark-scores.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    ut = {**meta, "scores": u_scores, "total": sum(u_scores.values()), "max": 10,
          "utility_level": "Decision-ready"}
    json.dump(ut, open(os.path.join(d, "user-utility-scores.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(case_id, "bench:", bench["total"], "/20  U:", ut["total"], "/10")

NOTES = {
    "case-001-competitive-impact": "EJ 直接给 A>B>C 分层（同机制/市场/pipeline）；Q6 获批后变与不变区分清楚（获批≠优于 A）；监控频率+触发条件具体",
    "case-002-regulatory-conflict": "Tier 0 决定权 + 明确'不能对管理层说已获批'；E5 标注不可采信；给出内部标准表述",
    "case-003-licensing-bd": "B>A>C 与 gold 一致；保留权益→联合开发结构推理；A 的 portfolio conflict 识别；明确 outreach priority≠成交概率",
    "case-004-due-diligence": "best-in-class=Hypothesis 非 Observed；跨试验不可比论证（人群/随访/线次/安全口径）；投委会结论'可投但按风险定价'",
    "case-005-safety-signal": "不升级类别效应但升 P0 监控；E4 竞品 B 无警告作为反证；先验概率 vs 因果确证区分；给出升级/降级触发条件",
    "case-006-temporal-watchlist": "E1/E3/E5 Top3 与 gold 一致；E2/E4 去重；E9 speculation 降级；管理层 vs 医学事务视角切换（E6）",
}

for c in CASES:
    write_scores(c, BENCHMARK_ALL2, U_ALL2, NOTES[c])
print("DONE deepseek scores")
