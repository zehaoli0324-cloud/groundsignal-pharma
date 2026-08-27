# Expert Diagnosis Rubric — 四大评估层（v0.4）

> 来源：GroundSignal Decision Intelligence Model Diagnosis v0.4
> 用途：对模型回答形成"知识准确性 / 推理质量 / 表达水准 / 用户价值"的清晰优劣判断，说明问题及原因，归纳共性并给出优化方向。

## A. Knowledge Quality（知识质量）

| ID | 维度 | 判断问题 |
|----|------|---------|
| A1 | Factual Correctness | 事实是否正确 |
| A2 | Temporal Freshness | 是否使用当前有效状态，而非 stale knowledge |
| A3 | Evidence Sufficiency | 证据能否真正支持 claim（≠ 有来源就算正确） |
| A4 | Source Hierarchy | 是否知道监管记录/注册记录/公司公告/媒体分别能支持什么 |
| A5 | Claim Scope | 是否把"Phase III 阳性 / NDA accepted / safety signal"升级成更强结论 |

## B. Reasoning Quality（推理质量）

| ID | 维度 | 判断问题 |
|----|------|---------|
| B1 | Relation Reasoning | 能否区分 shared target / mechanistic neighbor / pipeline / commercial competitor |
| B2 | Causal / Structural Reasoning | 是否解释"为什么"，而非相关性拼接 |
| B3 | Evidence Integration | 多条证据冲突/互补时能否合理综合 |
| B4 | Counterfactual Reasoning | 关键变量变化时结论是否随之正确更新 |
| B5 | Prioritization | 能否把几十条信息压缩成 1-3 个真正重要判断 |
| B6 | Uncertainty / Abstention | 证据不足时是否知道不能继续升级结论 |
| B7 | Decision Leverage | 能否指出"下一条最值得获取的信息"或"最高杠杆行动" |

## C. Expression Quality（表达水准）

| ID | 维度 | 判断问题 |
|----|------|---------|
| C1 | Decision-first | 是否先给结论再给依据，而非先堆背景 |
| C2 | Information Hierarchy | 关键信息是否前置，次要证据是否降级 |
| C3 | Precision of Language | 是否用"支持/提示/不能证明/已验证/假设"等精确措辞 |
| C4 | Information Density | 是否高信息密度，而非重复、空泛、过长 |
| C5 | Audience Fit | 对 BD / VC / CI / 临床开发是否用不同理想答案结构 |
| C6 | Calibrated Caveats | 不确定性是否放在影响决策的位置，而非结尾"仅供参考" |

## D. User Utility（用户价值）

| ID | 维度 | 判断问题 |
|----|------|---------|
| D1 | Decision Fit | 是否真正解决用户决策 |
| D2 | Defensibility | 用户能否带进会议并回答"凭什么" |
| D3 | Actionability | 是否能安排下一步动作 |
| D4 | Non-obvious Insight | 是否给出知识网络综合后才能得到的判断 |
| D5 | Value / Risk Asymmetry | 是否指出谁比表面更危险、更有价值、更值得下注 |

## 评分

- 每维 0/1/2 三档整数（与 scoring-protocol v1 一致）
- 四层输出：`knowledge / reasoning / expression / user_utility` 各给总分
- 关键纪律：**Observed Failure ≠ Capability Gap**——失败可观察，能力缺口是假设，需多 case 支持

## 三类典型回答（对比基准）

| 类型 | 特征 | 标签 |
|------|------|------|
| A. Knowledge-rich, Judgment-poor | 事实基本正确，但只罗列资料 | JUDGMENT_POOR |
| B. Insightful but Overclaimed | 有判断有高见，但超出证据边界 | OVERCLAIM / FORECAST_OVERCONFIDENCE |
| C. Decision-ready | 事实/推理/表达/用户价值均好 | — |
