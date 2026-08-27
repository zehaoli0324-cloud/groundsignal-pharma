# Eval v1 — 存进去的对不对？（医药版）

## 方法

从 pharma/ 图谱的关系行分层抽样（覆盖 GLP-1 / PD-1 / CAR-T / CXO 板块），按采集期多源验证逐条核对 gold：
- ClinicalTrials.gov 试验状态 = 一手（VERIFIED）
- FDA/NMPA 批准日期 = 一手（VERIFIED）
- 多源报道（Reuters/FiercePharma/公司官网） = SUPPORTED
- 单一自媒体 = INFERRED

## 指标

- Relation Precision / Evidence Precision / Entity Resolution / Temporal Validity / Abstention

## 当前证据打标结果（evidence-audit.py，2026-08-27）

| 库 | VERIFIED | SUPPORTED | INFERRED | UNKNOWN | NA |
|----|----------|-----------|----------|---------|-----|
| pharma/ | 36 | 11 | 0 | 0 | 4 |
| demo/ | 4 | 26 | 0 | 0 | 1 |

UNKNOWN 清零；SUPPORTED 集中在公司官网与行业媒体来源（合规，但 precision 抽样仍待跑 50 条 gold set）。

## 已知短板（诚实）

- 关系行来源引用：核心关系已带（来源: URL），聚合行需补
- 时间信息：部分事件只有年份，需补到日期
- 弱证据混入：授权交易金额为报道口径，未逐条验证
