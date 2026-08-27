# Temporal Watchlist：过去 30 天，哪三件事真的改变了判断？

```yaml
case_id: case-006-temporal-watchlist
user_role: Competitive Intelligence / 管理层
track: frozen-grounded
snapshot_id: C06-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 我每天只有 5–10 分钟看竞争情报。过去 30 天系统抓到 12 个“相关事件”，请不要给我新闻流。**只告诉我最值得看的 3 件事：它改变了哪个旧判断、影响谁、我接下来该监控什么。**

## 冻结 Evidence Snapshot



## GroundSignal 理想 Intelligence Brief（Gold）

### Top 1 — E1：Asset Q 新适应症正式获批

**为什么改变判断**：从“潜在适应症扩展”变成已验证商业/监管事实。  
**影响**：扩大可触达患者与竞争边界；相关竞品的市场重叠需要重算。  
**下一步**：看 label、定价/准入、供应和竞品 response。

### Top 2 — E3：Asset R pivotal trial TERMINATED

**为什么改变判断**：直接削弱原有“按计划推进 pivotal development”的 thesis。  
**影响**：竞争威胁等级、项目成功概率、相邻资产 comparative positioning 需要重估。  
**下一步**：核对终止原因、公司披露、是否有替代试验/方案。

### Top 3 — E5：Asset T 区域授权交易

**为什么改变判断**：资产的开发/商业化能力和地域覆盖发生结构性变化。  
**影响**：partner network、权益边界、竞争资源投入发生变化。  
**下一步**：看地区权益、里程碑/选择权（若公开）、开发责任和后续注册计划。

### Why the others are not Top 3

- E2 / E4：分别是 E1 / E3 的重复传播，不应重复计为新事件。
- E6：可能有科学价值，但当前是探索性 subgroup，暂不改变核心 thesis。
- E7 / E11：无新增信息。
- E8：旧新闻 repost，不是当前变化。
- E9：speculation，仅 lead。
- E10：可能有治理意义，但当前不足以改变产品/竞争 thesis。
- E12：背景材料，不是 change event。

## Eval Items

- **Q1**：只能选 3 条，选哪三条？
- **Q2**：为什么 E2/E4 不能单独算新事件？
- **Q3**：E3 改变了哪个旧 claim？
- **Q4**：E9 应该怎样记录：事件、事实还是 lead/hypothesis？
- **Q5**：每个 Top 3 给一个 next-watch trigger。
- **Q6**：如果用户从“管理层”切换为“医学事务”，E6 的优先级会不会变化？为什么？

## Critical Errors

- Top 3 中包含 E2/E4 这类重复传播，却漏掉 E1/E3/E5。
- 把 2024 旧新闻 repost 当成新事件。
- 把分析师 M&A speculation 当事实。
- 不区分“相关”与“改变判断”。
- 只做新闻摘要，不说明 changed claim / affected entity / next action。

## 用户视角评分 Anchors

- **U1 **：2 = exactly Top 3 + 为什么现在重要；1 = 选对大部分但没有 changed thesis；0 = 输出 12 条新闻摘要。
- **U2 **：2 = 正确处理时间、重复、source tier 和 speculation；1 = 一处轻微问题不影响 Top 3；0 = 旧闻当新闻/推测当事实。
- **U3 **：2 = E1/E3/E5 清晰居前并解释 hard state change > 重复报道；1 = Top 3 基本合理但权重逻辑不清；0 = 漏关键 hard event。
- **U4 **：2 = 每条 Top 3 都有 next-watch trigger；1 = 统一“持续跟踪”；0 = 无后续动作。
- **U5 **：2 = E9 降级为 hypothesis/lead，E6 标注探索性；1 = 谨慎但分类不清；0 = 升级为事实或核心 thesis。
