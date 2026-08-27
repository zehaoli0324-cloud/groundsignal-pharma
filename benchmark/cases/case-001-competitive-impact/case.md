# Competitive Impact：新资产进入后，真正威胁谁？

```yaml
case_id: case-001-competitive-impact
user_role: 药企战略 / Competitive Intelligence
track: frozen-grounded
snapshot_id: C01-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 我们有一个进入 III 期、减重主要终点阳性的 GLP-1R/GIPR 双激动剂 Asset X。现在真正应该把谁列为高优先级竞争对象？是所有 GLP-1 产品，还是只有同机制资产？为什么？

用户不是要“竞品名单”，而是要：谁最值得监控；是什么层面的竞争；哪些关系只是机制邻近；哪些事件会让威胁等级升级。

## 冻结 Evidence Snapshot

- **E1 Asset X**：GLP-1R/GIPR 双激动剂；肥胖；Phase III；主要终点 vs placebo 阳性；尚未申报上市。
- **E2 Asset A**：GLP-1R/GIPR 双激动剂；肥胖；已获批上市。
- **E3 Asset B**：GLP-1R 单激动剂；肥胖；已获批上市。
- **E4 Asset C**：GLP-1R/GCGR 双激动剂；肥胖；Phase III。
- **E5**：snapshot 不包含任何 Asset X 与 A/B/C 的头对头数据。
- **E6**：snapshot 不包含定价、医保、供应、处方量信息。

## GroundSignal 理想 Intelligence Brief（Gold）

### Executive Judgment

**一级优先：Asset A。** 原因不是“都属于 GLP-1”，而是 **同适应症 + 同靶点组合 + 已商业化**，它既是最接近的机制 comparator，也是 Asset X 最直接的未来商业 benchmark。

**二级优先：Asset B。** 与 Asset X 在肥胖市场和 GLP-1R 上重叠，但机制不同，因此属于强市场竞争者，而非完全同机制对标。

**三级优先：Asset C。** 与 Asset X 都处于 Phase III、同属多受体激动策略，更适合作为 pipeline peer；其商业威胁取决于谁先申报/获批及临床差异。

### Why it matters

当前 Asset X 仍是 **pipeline competitor**，不应直接称为“已上市直接商业竞品”。真正改变威胁等级的下一事件是：NDA/BLA 申报、监管受理、批准、定价/准入和供应能力。

### What to watch next

1. Asset X 是否提交上市申请；
2. 是否出现与 A/B/C 的头对头或可比临床证据；
3. 安全性、停药率、耐受性；
4. 商业化变量：价格、医保、供应；
5. 新适应症/患者人群是否改变市场重叠。

### Uncertainty

- 不能从 placebo-controlled III 期阳性推断 Asset X 优于 A。
- 缺少定价/供应/医保时，不能判断实际市场份额威胁。
- “机制相似”不等于“商业竞争强度相同”。

## Eval Items

- **Q1 Fact**：Asset X 当前是什么开发状态？能否称“已上市竞品”？
- **Q2 Relation**：Asset X 与 Asset A 属于什么竞争关系？
- **Q3 Relation**：为什么 Asset B 是市场竞争者，但不是完全同机制 comparator？
- **Q4 Evidence Sufficiency**：能否说 Asset X 疗效优于 Asset A？
- **Q5 Decision**：请给出 A/B/C 的 watchlist 优先级并解释。
- **Q6 Temporal**：如果 Asset X 明天获批，哪些判断必须改变，哪些不变？

## Critical Errors

- Phase III 阳性 → “已获批/已上市”。
- shared target / shared indication → 无限定地判为完全直接竞争。
- 没有头对头数据却声称优于 Asset A。
- 用户问优先级，却只罗列 A/B/C。
- 编造 snapshot 中不存在的销售额/医保/价格。

## 用户视角评分 Anchors

- **U1 Decision Fit**：2 = 明确 A > B > C，并说明三者是不同层面的竞争；1 = 识别 A 最重要但排序不完整；0 = 只给竞品名单。
- **U2 Trust**：2 = 只使用 E1–E6，并明确“III 期≠上市”“无头对头≠优效”；1 = 事实正确但边界不完整；0 = 出现批准/优效 overclaim。
- **U3 Prioritization**：2 = 按机制、适应症、阶段/商业化状态综合排序；1 = 只看单一因素；0 = 等权罗列。
- **U4 Actionability**：2 = 给出申报/批准、头对头、安全、价格/供应等具体 triggers；1 = “持续关注临床和商业化”；0 = 无下一步。
- **U5 Uncertainty**：2 = 明确缺口及翻转条件；1 = 只说“信息有限”；0 = 把排序写成确定未来市场结果。
