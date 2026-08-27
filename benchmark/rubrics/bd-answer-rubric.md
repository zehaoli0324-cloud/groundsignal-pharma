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

## 评分（冻结：三档整数，禁止 0.5 分）

- 每维 **0 / 1 / 2 三档整数**（禁止 0.5、1.5 等中间值）
  - **2 = 达标**：完全满足该维定义，且有明确证据支持
  - **1 = 部分**：部分满足，或满足但缺少关键限定/边界说明
  - **0 = 不可接受**：不满足，或出现该维的 Critical Error
- 1/4/7 维任一得 0 分 → 该答案整体判负（不可接受错误）
- 判分必须对照 case 里的 **gold + 判分 anchors**，禁止凭印象打分
- 盲评：评分时隐藏模型名，按 case_id + response_id 打分
- 输出：结构化 JSON（见 scoring-protocol.md），报告由脚本生成，禁止手写最终报告

## 判分 anchors 示例（Competitive reasoning，维 4）

- 2 = 明确区分 market competitor / mechanistic direct comparator / development-stage asymmetry（如"同适应症但机制不同、阶段不对等，所以是部分竞争而非完全对等"）
- 1 = 开头断言 direct competitor，但随后给出机制/阶段限定（如"是直接竞争，但靶点不同"——有区分但断言先行）
- 0 = shared indication/target 直接等同于完全竞争（如"都做肥胖，所以直接竞争"，无任何限定）

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
