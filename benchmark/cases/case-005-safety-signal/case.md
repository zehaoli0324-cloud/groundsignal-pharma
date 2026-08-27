# Safety Signal：这是“风险信号”还是“类别效应”？

```yaml
case_id: case-005-safety-signal
user_role: 临床开发 / 药物安全 / Portfolio Strategy
track: frozen-grounded
snapshot_id: C05-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 我们的 Asset S 最近出现一个严重肝毒性安全信号；同靶点竞品 A 有类似标签警告，但竞品 B 没有。这是不是已经说明“靶点级类别效应”？我们是否应该立刻下调整个项目的战略优先级？

本 Case 只做**产品/研发情报层面的风险判断**，不提供个体患者诊疗或用药建议。

## 冻结 Evidence Snapshot

- **E1 Asset S trial**：出现数例严重 hepatic adverse events；事件数少，但临床严重性高。
- **E2**：当前没有完整暴露人年 / 对照背景发生率，因果关系未建立。
- **E3 Competitor A**：同靶点、不同分子；标签含 hepatic warning。
- **E4 Competitor B**：同靶点；已积累较多暴露；当前无同类 boxed warning。
- **E5 Pharmacovigilance**：自发报告中有 disproportionality signal，但存在 reporting bias，不能估计 incidence。
- **E6 Mechanism**：存在 plausible mechanistic hypothesis，但尚无直接验证。
- **E7**：无监管机构声明“该靶点存在 class-wide hepatic toxicity”。

## GroundSignal 理想 Intelligence Brief（Gold）

### Executive Judgment

**这是一个需要升级监控和复核优先级的高严重度 safety signal，但现有证据不足以定性为已证实因果，更不足以直接升级为“靶点级类别效应”。**

### What is observed

Asset S 出现严重 hepatic events；Competitor A 存在相关 warning；自发报告系统出现 signal。

### What is not established

Asset S 与事件的确定因果；incidence；靶点级 class effect；项目必须终止。

### Why this still matters

“尚未证明因果”不等于“可以忽略”。严重度高 + 相邻资产出现类似风险，足以把该问题升级为 **P0 evidence review / monitoring topic**。

### Recommended portfolio action

- 提高 safety diligence 优先级；
- 系统性核对暴露量、时间关系、再挑战/去挑战、合并用药、基础疾病等混杂；
- 比较 A/B 的分子机制、剂量暴露和标签；
- 关注 regulator communication / protocol amendment / hold；
- 在证据升级前，把 cross-asset class inference 保持为 **HYPOTHESIS**。

### Uncertainty / flip conditions

若出现 regulator 明确 class warning、多个独立同靶点资产出现一致模式、exposure-adjusted 风险稳定升高、机制证据支持，则 class-effect confidence 应上调。

## Eval Items

- **Q1**：当前能否说 Asset S “导致” hepatic injury？
- **Q2**：能否说这是 target-level class effect？
- **Q3**：为什么 Competitor A 的 warning 是重要信号，但不是充分证明？
- **Q4**：在“因果未证实”的情况下，为什么仍应提升风险优先级？
- **Q5**：最值得补哪四类证据？
- **Q6**：什么新证据出现后可以把 HYPOTHESIS 上调？

## Critical Errors

- AE report = causality。
- 一个资产/一个竞品信号 = 类别效应。
- 因为“未证明因果”就建议忽略严重信号。
- 将自发报告频数解释为发生率。
- 给出个体患者用药/剂量建议。

## 用户视角评分 Anchors

- **U1 **：2 = 明确 risk posture：“不定性为 class effect，但升为高优先级复核”；1 = 只说“需要更多数据”；0 = 过度恐慌或过度安慰。
- **U2 **：2 = 区分 signal / causality / incidence / class effect；1 = 有概念混用；0 = 信号直接写成因果。
- **U3 **：2 = 严重度、跨资产一致性、监管信号列为 P0；1 = 知道重要但无层级；0 = 忽略或等同一般 AE。
- **U4 **：2 = 输出 evidence-review checklist 与 watch triggers；1 = “加强安全监测”；0 = 无下一步。
- **U5 **：2 = 明确当前 confidence + 升级/降级条件；1 = 只说“尚不确定”；0 = 过度确定。
