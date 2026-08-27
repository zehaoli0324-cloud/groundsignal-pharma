# Licensing / BD：最值得先找谁谈？

```yaml
case_id: case-003-licensing-bd
user_role: 药企 BD / Business Development
track: frozen-grounded
snapshot_id: C03-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 我们有一个 Phase II 的肿瘤 ADC Asset Y，准备做海外授权。请不要给我“全球大药企名单”，而是基于现有证据告诉我：**A、B、C 三家公司谁最值得先谈？为什么？**

## 冻结 Evidence Snapshot

### Asset Y
- Target T；ADC；实体瘤；Phase II。
- 已有早期疗效信号，但无随机对照确证性试验。
- 目标：海外开发 + 商业化授权，不希望失去全部全球权益。

### Company A
- 全球肿瘤商业化能力强；
- 已有 **同 Target T、同适应症、Phase III** 自研资产；
- 有 ADC 开发能力；
- 近年做过多笔大型外部授权。

### Company B
- 肿瘤商业化能力中上；
- **无同 Target T 资产**；
- 有互补的同适应症 franchise；
- 过去三年持续 in-license ADC；
- 有联合开发/区域权益交易记录。

### Company C
- 现金充足；
- 无成熟 ADC 平台；
- 同适应症布局弱；
- 只有一次相邻领域合作；
- 无证据显示近期积极寻求 Target T / ADC 资产。

## GroundSignal 理想 Intelligence Brief（Gold）

### Executive Judgment

**优先级：B > A > C。**

### Why B first

B 的优势是 **战略互补而非简单“大公司”**：无同 Target T 内部资产，内部 cannibalization / portfolio conflict 更低；有同适应症商业化能力；近期持续 in-license ADC；有区域权益/联合开发先例，更符合“保留部分权益”的交易偏好。

### Why A second

A 具备最强开发/商业化和交易能力，但其 Phase III 同靶点内部项目构成明显 **portfolio conflict**。不能说 A “不会合作”，但其合作动机和内部优先级需要重点尽调。

### Why C low priority

C 的问题不是“公司不够大”，而是 modality capability 弱、portfolio fit 弱、近期 licensing appetite 证据不足。

### What to validate before outreach

1. B 最近 ADC deal 的权益结构和付款结构；
2. A 的内部 Target T 项目是否覆盖同人群/同地区；
3. 三家的区域商业化能力；
4. Asset Y 是需要平台协同还是纯商业化 partner；
5. 是否存在内部竞争审查或优先权约束。

### Uncertainty

- “有历史交易”不等于“当前愿意买 Asset Y”；
- 公开信息不能证明任何一家有真实 deal intent；
- 当前推荐是 **outreach priority**，不是“成交概率”。

## Eval Items

- **Q1**：给 A/B/C 排序。
- **Q2**：为什么 B 的“没有同靶点资产”可能是优势？
- **Q3**：A 的强商业化能力为什么不能自动让它排第一？
- **Q4**：现有证据是否足以说 B “有意收购/授权 Asset Y”？
- **Q5**：第一次 outreach 前最应该补哪三类证据？
- **Q6**：如果 A 的 Phase III 项目终止，排序是否可能改变？为什么？

## Critical Errors

- “大药企/现金多”直接等于最佳 partner。
- 把历史 licensing 行为说成当前明确购买意愿。
- 忽略 A 的内部竞争资产。
- 完全不排序。
- 编造 deal term、内部战略或未给出的 BD 意图。

## 用户视角评分 Anchors

- **U1 **：2 = 明确 B > A > C 并给可执行理由；1 = 识别 B/A 但不敢排序；0 = 只输出公司画像。
- **U2 **：2 = 所有判断映射到 snapshot，并把行为证据与真实意向分开；1 = 有一两处推断未降级；0 = 捏造合作意图。
- **U3 **：2 = fit + conflict + licensing appetite + transaction structure 综合排序；1 = 只看一两个因素；0 = 无优先级。
- **U4 **：2 = 输出 diligence checklist；1 = “进一步调研 A/B/C”；0 = 无下一步。
- **U5 **：2 = 明确 outreach priority ≠ deal probability，并给翻转条件；1 = 泛化保留；0 = 写成确定成交判断。
