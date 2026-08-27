# BD Answer Rubric（优秀回答标准 · 10 维）

> 回答"对"和回答"好用"是两件事。本 rubric 定义 BD/投资/行业研究场景下什么是专业答案。

| # | 维度 | 要评估的问题 | 判断 |
|---|------|-------------|------|
| 1 | Factual correctness | 事实正确吗？ | 获批日期/阶段/数字是否有误 |
| 2 | Evidence grounding | 每个核心判断有证据吗？ | 关键 claim 是否带来源（NCT/批准日期/URL） |
| 3 | Temporal validity | 是否使用最新状态？ | 是否用了过时信息（stale knowledge） |
| 4 | Competitive reasoning | 是否真正理解竞争关系？ | 是否区分 shared target vs direct competitor |
| 5 | Decision relevance | 是否回答用户真正关心的问题？ | 是否答非所问（BD 问合作机会却答机制） |
| 6 | Prioritization | 是否区分重要和不重要？ | 是否把次要信息放在关键判断之前 |
| 7 | Uncertainty | 不确定内容是否降级表达？ | 是否把 HYPOTHESIS 说成 VERIFIED |
| 8 | Actionability | 用户下一步知道查什么/做什么吗？ | 是否给出可执行的下一步 |
| 9 | Information density | 是否高信息密度而非堆新闻？ | 是否罗列新闻而不是提炼判断 |
| 10 | Expression quality | 是否像专业分析而非网页摘要？ | 语言是否结构化、有判断、不空洞 |

## 评分

- 每维 0-2 分（0=不可接受，1=部分，2=达标）
- 1/4/7 维任一得 0 分 → 该答案整体判负（不可接受错误）
- 输出格式：分维分数 + 一句话理由 + 失败类型标签

## 失败类型标签（Failure Taxonomy）

| 标签 | 含义 |
|------|------|
| OVERCLAIM | 证据不足时过度声称（III 期阳性 → "已获批"） |
| STALE_KNOWLEDGE | 用过时状态（还在说 recruiting，实际已 completed） |
| SOURCE_HIERARCHY_VIOLATION | 优先相信错误来源（Tier 3 新闻压过 FDA 记录） |
| RELATION_OVERSIMPLIFY | 关系推理简化（shared target → 直接竞品） |
| TEMPORAL_CONFUSION | 时间错乱（把 2022 年的批准说成现在） |
| EVIDENCE_FABRICATION | 编造来源/数字/试验（最严重） |
| ABSTENTION_FAILURE | 证据不足时拒绝说"不知道" |
| DECISION_IRRELEVANCE | 答非所问（不解决用户任务） |
