# DeepSeek — case-004-due-diligence

2026-08-27

## Prompt

你是医药行业竞争情报分析师。你的回答将直接给一位真实专业用户（药企 BD / 战略 / 竞争情报 / VC 投委会 / 临床开发）看，用于会议和决策。

回答要求（用户视角评分标准）：
1. Decision Fit：先直接回答用户的核心决策，给明确判断/推荐/优先级，不要只罗列信息
2. Trust：每个关键判断有证据支撑；事实/推断/假设分层（OBSERVED / DERIVED / HYPOTHESIS）
3. Prioritization：明确 High / Medium / Low 排序并解释为什么
4. Actionability：给出具体下一步、触发条件、需补证据、应监控的变量
5. Uncertainty：明确哪些证据不足、什么会改变结论、有哪些风险/竞争解释

只使用提供的 Evidence Snapshot，不要编造快照中不存在的来源、数字、试验、批准状态或交易关系。证据不足时明确说"证据不足"。不要联网搜索。

输出格式：先给一段 Executive Judgment（3-5 句核心判断），然后逐题回答 Q1...Q6。

> 公司路演材料称 Asset Z 是 “best-in-class”，并说早期临床 ORR 高于已上市竞品。如果我明天要上投委会，这个 claim 到底能信到什么程度？最关键的反证和缺口是什么？

## 冻结 Evidence Snapshot

- **E1 Company deck**：Asset Z “best-in-class”；Phase I/II single-arm；n=58；ORR 62%。
- **E2 Trial design**：主要为经过筛选的人群；随访中位时间 7 个月；无随机 comparator。
- **E3 Incumbent published trial**：ORR 48%，但患者线次、既往治疗、入组标准与 Asset Z 不同；随访 18 个月。
- **E4 Safety**：Asset Z Grade ≥3 AE 发生，但 snapshot 不提供与 incumbent 完全可比的安全口径。
- **E5 Regulatory**：Asset Z 尚未获批。
- **E6 Biomarker subgroup**：探索性 subgroup 显示较高响应，但样本小、非预设 confirmatory endpoint。
- **E7**：无 head-to-head trial。

## 问题

Q1. **Q1**：哪些 claim 是 OBSERVED，哪些只是 HYPOTHESIS？
Q2. **Q2**：62% vs 48% 能否支持 superiority？为什么？
Q3. **Q3**：什么证据最可能推翻 “best-in-class” thesis？
Q4. **Q4**：如果你是投委会成员，你会怎样写一段 3 句结论？
Q5. **Q5**：下一轮数据里最值得优先看哪三项？
Q6. **Q6**：如果 biomarker subgroup 在更大队列复现，哪些判断会升级，哪些仍不能升级？

请先给 Executive Judgment，再逐题回答。

## Answer

# Executive Judgment

Asset Z 的 “best-in-class” 主张目前**证据等级为 Hypothesis，而非 Observed**。62% vs 48% 的跨试验比较在方法学上**不能支持 superiority**，因为两组人群、随访时长、线次和入组标准均不可比，且无 head-to-head 数据。最关键的反证缺口是：**① 无随机对照；② 随访仅 7 个月 vs 18 个月，ORR 可能随时间衰减；③ 安全性口径不可比，若 Grade ≥3 AE 显著高于 incumbent，则 “best-in-class” 在风险-获益维度不成立。** 投委会结论应写为：**“有信号，无证据；可投但须按风险定价，估值不得包含 superiority 溢价。”**

---

## Q1：哪些 claim 是 OBSERVED，哪些只是 HYPOTHESIS？

**OBSERVED（直接观察到的数据）：**
- Asset Z 在 Phase I/II single-arm 试验中，n=58，ORR = 62%（E1）
- 随访中位时间 7 个月（E2）
- 人群经过筛选（E2）
- 探索性 biomarker subgroup 显示较高响应（E6，但样本小、非预设）
- Asset Z 尚未获批（E5）
- 无 head-to-head trial（E7）

**HYPOTHESIS（推断/主张，无直接证据）：**
- “Best-in-class” —— 这是**结论性主张**，需要同时满足疗效、安全性、耐受性、给药便利性等多维度全面优于所有已上市/在研竞品。目前仅有一个单臂早期数据，**远不足以支撑**。
- “ORR 高于已上市竞品” —— 这是**跨试验比较的推断**，不是直接观察。62% 与 48% 来自不同试验、不同人群，不能视为直接对比结果。

**DERIVED（可推导但需注明前提）：**
- 若 biomarker subgroup 的响应率显著高于整体（E6），可推导 “该生物标志物可能富集响应人群”，但这是**探索性发现**，需独立验证。

---

## Q2：62% vs 48% 能否支持 superiority？为什么？

**不能。** 理由如下：

1. **人群不可比（E3）**：两试验的患者线次、既往治疗史、入组标准不同。若 Asset Z 入组的是更早期、更少治疗的患者，62% 可能只是人群差异的反映，而非药物更优。
2. **随访时间差异（E2 vs E3）**：Asset Z 随访仅 7 个月，incumbent 随访 18 个月。ORR 是短期终点，但**响应持续时间（DoR）未知**——若 Asset Z 的响应在 12 个月时大量消退，则 62% 的 “含金量” 远低于 incumbent 的 48%（后者已证明持续 18 个月）。
3. **无随机化（E2, E7）**：单臂试验无法排除选择偏倚。筛选人群（E2）可能富集了更可能响应的患者。
4. **无置信区间**：n=58 的 ORR 62%，95% CI 约为 48%-74%。Incumbent 的 48% 若 CI 为 40%-56%，两者 CI 可能重叠——**统计上无法排除两者真实疗效相同甚至 Asset Z 更差**。
5. **安全性未纳入比较（E4）**：若 Grade ≥3 AE 发生率显著更高，“best-in-class” 在净获益维度不成立。

**结论：62% vs 48% 只能作为 “信号”，不能作为 superiority 的证据。**

---

## Q3：什么证据最可能推翻 “best-in-class” thesis？

按推翻力度排序：

| 优先级 | 证据类型 | 推翻机制 |
|--------|----------|----------|
| **High** | 随机对照试验（RCT）结果：Asset Z 的 PFS/ORR 不优于 incumbent，或毒性更高 | 直接比较，最有力 |
| **High** | 随访延长后 DoR 显著缩短（如中位 DoR < 6 个月） | 即使 ORR 高，若响应不持久，临床价值大打折扣 |
| **High** | 安全性数据：Grade ≥3 AE 率显著高于 incumbent，或出现未预期的严重毒性（如治疗相关死亡） | 风险-获益失衡 |
| **Medium** | Biomarker subgroup 在更大队列中无法复现 | 若 “best-in-class” 仅存在于 biomarker 阳性亚群，则适应症范围收窄，价值下降 |
| **Medium** | 竞品（含在研）公布更优数据（如 ORR > 70% 且随访更长） | 相对位置下降 |
| **Low** | 监管拒绝或要求额外试验 | 延迟但不一定推翻疗效主张 |

**最关键的单一反证**：**一项设计良好的 RCT 显示 Asset Z 在 PFS 或 OS 上不优于 incumbent，或毒性不可接受。** 这是投委会最应关注的数据。

---

## Q4：如果你是投委会成员，你会怎样写一段 3 句结论？

> **“Asset Z 的早期数据提供了有意义的疗效信号（ORR 62%，单臂，n=58），但当前证据不足以支持 ‘best-in-class’ 主张——跨试验比较不可比，随访仅 7 个月，安全性口径缺失。建议按 ‘有前景的早期资产’ 定价，估值中剔除 superiority 溢价，并将投资决策与以下里程碑挂钩：随机对照数据、DoR 成熟度、安全性完整披露。若下一轮数据中 PFS/DoR 显著优于历史对照且毒性可控，可上调估值；否则维持谨慎。”**

---

## Q5：下一轮数据里最值得优先看哪三项？

**优先级排序：**

1. **【High】随机对照试验（或至少匹配调整后的间接比较）的 PFS / DoR 数据** —— 这是唯一能回答 “是否真的更好” 的证据。若 PFS HR < 0.7 且 DoR 中位数 ≥ 12 个月，superiority 主张开始有支撑。
2. **【High】完整安全性数据（按相同 CTCAE 口径，与 incumbent 对齐）** —— 特别是 Grade ≥3 AE 率、停药率、治疗相关死亡。若 Grade ≥3 AE 率 > 1.5× incumbent，则 “best-in-class” 在净获益维度不成立。
3. **【Medium】Biomarker subgroup 的独立验证（更大样本、预设分析）** —— 若复现且效应量大（如 biomarker+ 人群 ORR > 75%），可支持精准适应症定位，但**不能**升级为整体 “best-in-class”。

**监控变量**：随访时间点（12 个月、18 个月）的 DoR 生存曲线形态；若曲线陡降，则早期 ORR 的临床意义有限。

---

## Q6：如果 biomarker subgroup 在更大队列复现，哪些判断会升级，哪些仍不能升级？

**会升级：**
- **Asset Z 在 biomarker 阳性人群中的定位**：从 “探索性信号” 升级为 “有证据的精准治疗候选”。若复现且效应量大，可支持在 biomarker+ 人群中开展注册性试验。
- **投资价值评估**：若 biomarker+ 人群占目标患者群体的比例可观（如 > 30%），且响应率显著高于 incumbent 在该人群中的数据，则可给予**条件性溢价**（但需以伴随诊断开发为前提）。

**仍不能升级：**
- **整体 “best-in-class” 主张**：biomarker subgroup 复现只说明 “在特定人群中可能更优”，不能推广到全体患者。除非 biomarker+ 人群覆盖 > 80% 的目标患者，否则整体 superiority 仍无证据。
- **安全性结论**：biomarker 复现不解决安全性问题。若毒性高，即使在 biomarker+ 人群中，风险-获益仍需单独评估。
- **长期获益（OS）**：ORR 和 PFS 的改善不一定转化为 OS 获益。仍需长期随访数据。

**关键区分**：biomarker 复现升级的是 **“精准定位”** 的判断，不升级 **“广谱 best-in-class”** 的判断。投委会应明确：**Asset Z 的价值主张可能从 “广谱最佳” 收缩为 “特定人群最佳”**，这影响市场空间估算和估值倍数。

## Usage

{"prompt_tokens": 628, "completion_tokens": 1866, "total_tokens": 2494, "prompt_tokens_details": {"cached_tokens": 0}, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 628}
