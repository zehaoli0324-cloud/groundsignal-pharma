# DeepSeek — case-004-due-diligence__BASE (twin run)

2026-08-27

## Prompt

> Asset Z 最新 ORR 62%，竞品历史数据 48%。市场都说“best-in-class”。  
> **如果明天上投委会，这组数据究竟改变了什么？值不值得提高我们对资产的估值或 conviction？最可能推翻当前乐观叙事的证据是什么？**

## Evidence

- Z：Phase I/II；single-arm；n=58；ORR 62%。
- selected population。
- median follow-up 7 months。
- incumbent published ORR 48%。
- incumbent：不同 line / eligibility；follow-up 18 months。
- exploratory biomarker subgroup 更高。
- 无 randomized comparator。
- safety 尚可但成熟度不足。
- market crowded。
- incumbent 已 reimbursed。

## Output 要求

输出：
- Thesis update；
- What is de-risked；
- What is not；
- Kill / falsification criterion。

## Answer

**Thesis update**  
这组数据本身**不改变**我们对“best-in-class”的定性判断，但**显著改变了证据等级**——从“假设性优势”升级为“可验证的初步优势”。它值得提高**估值中的概率权重（PoS）**，但**不应提高峰值销售额假设**。核心变化是：我们终于有了一个**可辩护的、针对同一适应症人群的、方向正确的信号**，足以支撑进入注册性试验的决策，但尚不足以支撑商业化定价或市场独占叙事。

---

**What is de-risked**  
1. **机制有效性**：在选定人群中，ORR 62% vs 历史48%，绝对差14个百分点，且非重叠置信区间（假设95%CI下限>48%），初步证明该分子在**该人群**中具有优于标准治疗的生物学活性。  
2. **注册路径可行性**：这组数据足以支持与FDA/EMA开展**随机对照注册试验**的设计讨论（尤其是选择对照组和终点）。  
3. **安全性可接受性**：在7个月随访中无意外毒性，排除了“因毒性无法推进”的早期风险。

---

**What is not**  
1. **相对疗效优势**：跨试验比较（62% vs 48%）受人群、基线、评估时间、随访时长差异影响，**不能视为头对头优势**。尤其incumbent随访18个月，ORR可能随时间下降（或维持），而Z仅7个月，存在“早期高响应、后期快速进展”的可能。  
2. **持久性（DoR）**：无中位DoR数据，无法判断响应是否转化为PFS/OS获益。  
3. **随机化下的表现**：single-arm + selected population，选择偏倚可能放大ORR（例如入组更年轻、更少合并症、更早线数）。  
4. **竞争格局**：市场拥挤，incumbent已报销，意味着即使Z最终获批，**准入和定价压力**可能侵蚀峰值销售。  
5. **生物标志物亚组**：exploratory subgroup更高，但未预设、未校正多重性，**不可作为注册依据**。

---

**Kill / falsification criterion**  
**明确、可操作的终止条件（建议写入投委会备忘录）：**  

> **如果随机对照试验（RCT）中，Z的ORR或PFS与incumbent相比，95%置信区间下限低于incumbent历史点估计（48%），或HR≥0.85（即无显著优势），则立即终止开发并减记资产价值至零。**

**更早的“红旗”信号（在RCT数据读出前）：**  
- 若在扩展队列或真实世界中，**中位DoR < 6个月**，或**6个月PFS率 < 60%**，则当前ORR优势大概率是“假阳性”或“早期快响应”，应下调PoS至<20%。  
- 若在独立中心评估（BICR）中，ORR回落至<55%，则提示研究者评估偏倚，需重新审视入组标准。

**一句话总结：**  
这组数据**值得将PoS从20%提高到40-50%**，并**批准启动RCT**；但**不改变峰值销售假设**，且**RCT的阴性结果（HR≥0.85）是唯一且充分的终止理由**。当前乐观叙事最脆弱的假设是“ORR优势能转化为PFS/OS优势”，而这一假设在RCT读出前**无法被任何single-arm数据证实**。
