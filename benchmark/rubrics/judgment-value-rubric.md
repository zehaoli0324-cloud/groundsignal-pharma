# Judgment Value Score（J-score，0-14）

> v0.4 updated。A 层（Knowledge Gate）通过后才评 J-score。核心变化：不评"回答完整性"，评"专业判断质量 + 决策敏感性 + 非显然洞察"。

## 七个维度（0/1/2）

| ID | 维度 | 0 | 1 | 2 |
|----|------|---|---|---|
| J1 | Decision Compression | 资料堆砌 | 有结论但分散 | 1-3 个核心判断 |
| J2 | Non-obvious Insight | 复述事实 | 轻度综合 | 跨节点得出非显然洞察 |
| J3 | Structural Reasoning | 相关性 | 表层理由 | 结构机制 + 约束 |
| J4 | Second-order Impact | 事件本身 | 一阶影响 | 影响传播链 |
| J5 | Counterfactual Quality | 静态结论 | 泛化风险 | 明确翻转条件 |
| J6 | Decision Leverage | 无行动 | 泛化行动 | 最高信息价值/最高杠杆动作 |
| J7 | Value/Risk Asymmetry | 平均化比较 | 有排序 | 指出非对称价值 |

## 分级

| 分数 | 级别 |
|------|------|
| 13-14 | Executive-grade Intelligence |
| 10-12 | Strong Analyst Intelligence |
| 7-9 | Useful but conventional |
| 4-6 | Knowledge-rich, judgment-poor |
| 0-3 | Information retrieval only |

## Counterfactual Pair Metrics（twins 评分）

| 指标 | 定义 |
|------|------|
| Decision Sensitivity | 关键变量改变时，结论是否在正确方向变化（correct_direction_updates / expected_updates） |
| Invariance Discipline | 不相关变量变化时，是否保持不该变化的判断稳定 |
| Flip Calibration | 证据足以改变结论时敢改；证据不足时避免过度翻转 |
| Explanation Consistency | 结论变化是否与新增证据存在明确因果/结构解释 |
