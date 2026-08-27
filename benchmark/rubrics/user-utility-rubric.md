# User Utility Rubric（用户视角评分 U1-U5）

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（U-scoring 部分落地）
> 这不是替代 10 维 benchmark rubric，而是其上的**产品可用性视角**。底层仍评 Factual / Evidence / Temporal / Reasoning / Uncertainty；User Utility Score 只问：

> **如果我是这个真实用户，我会不会把这份回答带进下一场会议并据此行动？**

## U1. Decision Fit — 有没有回答我真正要做的决定？

- **2**：直接回答核心决策，并明确推荐/判断/优先级。
- **1**：信息相关，但核心决策需要用户自己再推一步。
- **0**：主要是知识罗列、网页摘要或答非所问。

用户自问：**"看完第一屏，我知道该怎么判断了吗？"**

## U2. Trust / Defensibility — 我敢不敢把它带进会议？

- **2**：关键判断有可追溯证据；时间状态正确；事实/推断/假设分层清楚。
- **1**：大体可信，但关键一两处缺来源、时间或限定。
- **0**：核心事实错误、来源不匹配、把推测当事实，或存在 evidence fabrication。

用户自问：**"老板问'凭什么'，我能立即指出证据吗？"**

## U3. Prioritization — 有没有告诉我什么最重要？

- **2**：清楚排序 High / Medium / Low，能解释为什么 A > B > C。
- **1**：识别出重要项，但排序或取舍理由不够清楚。
- **0**：把所有相关信息等权罗列；用户仍不知道先看什么。

用户自问：**"如果我只有 10 分钟，我该先处理哪一件？"**

## U4. Actionability — 我下一步能做什么？

- **2**：给出具体下一步、触发条件、需补证据或应持续监控的变量。
- **1**：方向正确，但行动建议泛化，如"持续关注""进一步研究"。
- **0**：没有下一步；只停留在结论或背景。

用户自问：**"明天我能据此安排谁去做什么？"**

## U5. Uncertainty / Downside Awareness — 它知道自己不知道什么吗？

- **2**：明确哪些证据不足、什么会改变结论、有哪些竞争解释/风险。
- **1**：有保留表达，但未指出关键未知量或翻转条件。
- **0**：过度确定；把 HYPOTHESIS 写成 VERIFIED；证据不足仍强行结论。

用户自问：**"这份判断最可能在哪个地方错？系统自己有没有告诉我？"**

## 总分解释

| 分数 | 用户可用性 |
|------|-----------|
| **9–10** | Decision-ready：可直接进入会议/brief，仍保留人工责任 |
| **7–8** | Analyst-useful：明显节省工作，但需分析师复核关键点 |
| **5–6** | Background-only：适合背景研究，不足以支撑决策 |
| **0–4** | Not useful：信息噪声大或缺乏判断 |
| **任一 Critical Error** | **Reject**：无论总分多少都不可用于决策 |

## 通用 Critical User Errors

1. 核心事实或时间状态错误，且会改变用户决策。
2. 编造来源、试验、数字、批准状态或交易关系。
3. 用较弱来源覆盖明确的一手监管/注册事实。
4. 证据不足却把 HYPOTHESIS 升级为确定事实。
5. 用户要求优先级时完全不做取舍。
6. 漏掉 snapshot 中明确存在、且会改变决策的硬事件。
7. 在安全 Case 中把"信号"直接等同"因果/类别效应"。

## 评分流程

- U1-U5 每维 0/1/2 三档整数（与 benchmark rubric 一致）
- 任一 Critical User Error → Reject（不评分）
- 盲评 + 结构化 score JSON + 脚本生成报告（遵循 scoring-protocol v1）
- 与 10 维 benchmark rubric 并行输出：`scores/` 下分别存 `benchmark-scores.json` 与 `user-utility-scores.json`
