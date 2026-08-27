# Cross-Case Failure Taxonomy（v0.4）

> 六个 Case 跑完以后不按 Case 写孤立报告，而是聚合成模型画像。本表定义 failure cluster 及状态（截至 2026-08-27 v0.2 实测）。

## 10 个 Failure Cluster

| Cluster | 用户体验 | 可能根因 | 优化方向 | 实测状态 (v0.2) |
|---------|---------|---------|---------|:---:|
| STALE_KNOWLEDGE | 状态过时，失去信任 | 内部知识 freshness 不足 | retrieval / temporal truth / regression | ✅ 有真实案例（玛仕度肽，DeepSeek Track A） |
| SOURCE_HIERARCHY | 新闻压过监管事实 | evidence role 不清 | source-aware data / hard negatives | 未见（Track B 快照内） |
| OVERCLAIM | 看起来聪明但不可靠 | claim scope calibration 差 | preferred/rejected pairs | 未见（v0.1 误判已反转） |
| RELATION_SHORTCUT | shared target→竞品 | 结构推理 shortcut | graph-conditioned data | 未见（两模型均正确分层） |
| METRIC_SALIENCE_BIAS | 被漂亮数字误导 | 缺乏 experimental validity | counterexample / expert SFT | 未见（case-004 两模型均拒绝 62%>48%） |
| PRIORITIZATION_FAILURE | 信息很多但没结论 | coverage bias | Top-K preference | 未见（case-006 两模型均 Top3） |
| PASSIVE_ABSTENTION | 只会说"不知道" | uncertainty 无行动策略 | uncertain-but-actionable data | 未见（v0.1 abstention 测试 3/3 通过） |
| EXPRESSION_HIERARCHY | 正确但难用 | answer organization 差 | preference / response templates | 未见（两模型均 Decision-first） |
| AUDIENCE_MISMATCH | BD/VC/临床答案同质 | user conditioning 弱 | persona-conditioned data | 未见（case-006 医学事务视角切换正确） |
| FORECAST_OVERCONFIDENCE | 把可能写成必然 | uncertainty calibration 差 | calibration / negative examples | 未见（两模型均给 flip conditions） |

## 关键观察（诚实）

**v0.2（Track B，frozen-grounded）双模型 6 case 全部 Decision-ready，10 个 failure cluster 中 9 个未激活。**

原因：冻结快照 + 明确用户任务 = 前沿模型最容易答好的条件（"快照跟随"是共同强项）。

**唯一激活的 cluster：STALE_KNOWLEDGE**——来自 Track A（closed-book，玛仕度肽 bad case，DeepSeek 训练截止后新事实 stale）。

含义：failure taxonomy 的激活需要 Track A（无快照）与 Track C（live/冲突）条件。v0.4 框架就绪，但 failure 数据要靠下一轮 Track A 派生版产出。

## 已激活案例：STALE_KNOWLEDGE（玛仕度肽）

```yaml
failure_cluster: STALE_KNOWLEDGE
observed_behavior:
  - deepseek_v2_q4: "玛仕度肽 III 期、尚未获批"（2026-08-27 时点错误，实际 2025-06-27 已获批）
  - deepseek_v2_q4: "2024 年初提交 NDA"（实际 2025-01 受理）
user_experience: 状态过时导致用户基于错误前提决策；trust 流失
capability_gap_hypothesis: 训练截止后新事实（<1 年）的 freshness 不足；无 retrieval 补偿
intervention_candidates:
  - retrieval / temporal truth 注入（Track C Live-grounded）
  - 训练数据更新周期缩短
  - 要求模型对"监管状态"类问题显式标注 knowledge cutoff
success_metrics: Stale Claim Rate / Temporal Validity / Track A Freshness accuracy
regression_cases: case-002-regulatory-conflict（Track A 派生版）
```
