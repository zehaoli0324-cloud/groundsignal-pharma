# Due Diligence：所谓 “Best-in-Class” 到底有多少证据？

```yaml
case_id: case-004-due-diligence
user_role: 医疗 VC / PE / 投资委员会
track: frozen-grounded
snapshot_id: C04-T1
```

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2（落地脚本生成）

## 用户真实任务

> 公司路演材料称 Asset Z 是 “best-in-class”，并说早期临床 ORR 高于已上市竞品。如果我明天要上投委会，这个 claim 到底能信到什么程度？最关键的反证和缺口是什么？

## 冻结 Evidence Snapshot

- **E1 Company deck**：Asset Z “best-in-class”；Phase I/II single-arm；n=58；ORR 62%。
- **E2 Trial design**：主要为经过筛选的人群；随访中位时间 7 个月；无随机 comparator。
- **E3 Incumbent published trial**：ORR 48%，但患者线次、既往治疗、入组标准与 Asset Z 不同；随访 18 个月。
- **E4 Safety**：Asset Z Grade ≥3 AE 发生，但 snapshot 不提供与 incumbent 完全可比的安全口径。
- **E5 Regulatory**：Asset Z 尚未获批。
- **E6 Biomarker subgroup**：探索性 subgroup 显示较高响应，但样本小、非预设 confirmatory endpoint。
- **E7**：无 head-to-head trial。

## GroundSignal 理想 Intelligence Brief（Gold）

### Executive Judgment

**“Promising activity” 有证据；“best-in-class / superiority” 当前没有被证明。**

### Claim Decomposition

可以支持：Asset Z 在该 Phase I/II 人群中观察到较高 ORR，存在值得继续跟踪的疗效信号。

不能支持：ORR 62% > 48% 就证明优于 incumbent；证明更持久、更安全；证明 broader population 中仍成立；“best-in-class” 作为已验证事实。

### Why the cross-trial comparison is weak

两组在 line of therapy、eligibility、follow-up、sample size、safety reporting、biomarker enrichment 均不完全可比。因此 62% vs 48% 是 **hypothesis-generating**，不是 superiority proof。

### Investment-relevant downside

如果后续出现更成熟随访后 ORR/DOR 回落、随机试验差异消失、安全负担上升、biomarker subgroup 无法复现，则当前 “best-in-class” thesis 会显著弱化。

### What would increase conviction

1. 随访成熟后的 DOR/PFS；
2. 更大样本、预设 subgroup；
3. randomized / head-to-head；
4. 可比安全数据；
5. 监管互动和后续 pivotal trial design。

## Eval Items

- **Q1**：哪些 claim 是 OBSERVED，哪些只是 HYPOTHESIS？
- **Q2**：62% vs 48% 能否支持 superiority？为什么？
- **Q3**：什么证据最可能推翻 “best-in-class” thesis？
- **Q4**：如果你是投委会成员，你会怎样写一段 3 句结论？
- **Q5**：下一轮数据里最值得优先看哪三项？
- **Q6**：如果 biomarker subgroup 在更大队列复现，哪些判断会升级，哪些仍不能升级？

## Critical Errors

- 直接复述公司 “best-in-class” 作为事实。
- 用不可比 cross-trial ORR 证明 superiority。
- 忽略 follow-up / population / design 差异。
- 将探索性 subgroup 当确证性 biomarker。
- 只讲 upside，不指出任何能推翻 thesis 的证据。

## 用户视角评分 Anchors

- **U1 **：2 = 明确告诉 IC“可以相信到哪、不能相信到哪”；1 = 只说证据有限；0 = 变成论文摘要/公司介绍。
- **U2 **：2 = claim 拆成 observed / unsupported / hypothesis，并解释跨试验不可比；1 = 谨慎但拆解不完整；0 = 把公司材料当 gold。
- **U3 **：2 = DOR/PFS、randomized evidence、安全性列为关键验证点；1 = 数据点很多但无排序；0 = 无重点。
- **U4 **：2 = 输出可直接进入 diligence request list 的问题；1 = “看更多临床数据”；0 = 无下一步。
- **U5 **：2 = 明确 thesis flip conditions / downside scenarios；1 = 风险提示泛化；0 = 过度乐观或过度否定。
