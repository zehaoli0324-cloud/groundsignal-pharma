# Regulatory Conflict：多源冲突时，到底相信谁？

```yaml
case_id: case-002-regulatory-conflict
user_role: 监管情报 / 临床战略 / Competitive Intelligence
track: frozen-grounded
snapshot_id: C02-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 公司公告说“上市申请已受理，预计近期上市”；ClinicalTrials.gov 显示关键试验已完成；行业媒体标题写“即将获批”，另一篇二手稿甚至写成“已经获批”。我现在到底应该把这个资产标成什么状态？能不能对内部管理层说“已获批”？

## 冻结 Evidence Snapshot

- **E1 Regulator database / Tier 0**：上市申请已受理，状态 = under review；无 approval decision。
- **E2 ClinicalTrials.gov / Tier 0**：关键 Phase III trial = COMPLETED。
- **E3 Company press release / Tier 2**：公司称“申请已获受理，期待尽快惠及患者”。
- **E4 Industry media / Tier 3**：标题“重磅产品即将获批”。
- **E5 Aggregator / Tier 4**：摘要写“产品已获批上市”，未给监管链接。
- **E6**：snapshot 截止时点未发现 regulator approval record。

## GroundSignal 理想 Intelligence Brief（Gold）

### Executive Judgment

**当前唯一可写入生产系统的监管状态是：上市申请已受理 / 审评中，尚无证据证明已获批。**

### Evidence Resolution

- E1 决定“当前监管状态”；
- E2 只能证明关键试验已完成，**不能证明批准**；
- E3 支持“公司已提交并获受理”，但“期待上市”属于 forward-looking statement；
- E4 是预测性媒体表述；
- E5 与 Tier 0 监管记录冲突，应标记为 **unsupported / stale / erroneous lead**，不能覆盖 E1。

### Recommended Internal Wording

> “截至 snapshot time，监管机构已受理该资产上市申请，当前处于审评阶段；尚未检索到正式批准记录。”

### What to watch next

- regulator approval decision / label；
- CRL / additional information request；
- approval date；
- approved indication 与公司申请适应症是否一致。

### Uncertainty

“预计近期上市”不能被转写成“高概率一定获批”；系统可以表达时间预期，但必须与事实状态分离。

## Eval Items

- **Q1**：当前监管状态是什么？
- **Q2**：哪一条证据拥有最高决定权？为什么？
- **Q3**：ClinicalTrials.gov 的 COMPLETED 能支持哪些 claim，不能支持哪些 claim？
- **Q4**：如何处理 E5“已获批”的冲突？
- **Q5**：给管理层一句可直接使用的表述。
- **Q6**：什么新证据出现后 gold 才能从 “under review” 更新为 “approved”？

## Critical Errors

- 把 trial completed 当作 approval。
- 用媒体/聚合站覆盖监管数据库。
- 把“预计/期待”转写成事实。
- 在没有批准记录时写“已获批”。
- 把所有来源简单投票，忽略 source hierarchy。

## 用户视角评分 Anchors

- **U1 **：2 = 第一行明确“受理/审评中，未获批”；1 = 结论正确但绕；0 = 状态错误/无法判断。
- **U2 **：2 = 明确每个来源能/不能支持什么；1 = 只说“监管更权威”；0 = 来源层级错误。
- **U3 **：2 = regulator decision 是唯一 P0 watch trigger；1 = 有重点但不够明确；0 = 所有来源等权。
- **U4 **：2 = 给出内部标准表述 + 下一监控字段；1 = “继续关注审批”；0 = 无行动输出。
- **U5 **：2 = 区分事实状态与时间预期；1 = 有保留但未拆开；0 = 把预期升级为事实。
