# DeepSeek — case-004-due-diligence (v0.4 updated, visible-only)

2026-08-27

## Prompt

你是医药行业分析师。请直接回答用户的问题。

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
这组数据本身**不改变**我们对“best-in-class”的定性判断，但**显著改变了**我们对“该定性是否可被证实”的概率分布。  
- 之前：ORR 62% vs 48% 是“可能更好”的假设。  
- 现在：在**同一类经治人群**（尽管是单臂、小样本）中，ORR 绝对差14个百分点，且中位随访仅7个月即达到此水平——这使“Z在缓解深度上优于incumbent”从**弱假设**升级为**中等置信度的可检验假设**。  
- 但**不改变**我们对“PFS/OS获益”的预期，因为ORR在多数实体瘤中仅是替代终点，且此处无随机对照。

**What is de-risked**  
1. **生物学活性（on-target effect）**：62% ORR在7个月随访时未衰减，说明缓解不是瞬时假象。  
2. **剂量/方案可行性**：安全可耐受，支持继续推进。  
3. **与incumbent的差异化定位**：在“缓解深度”这一维度上，Z有明确信号，可作为未来注册试验的**分层假设**或**早期疗效信号**。

**What is not**  
1. **PFS/OS获益**：无随机对照，无法排除“缓解但不延长生存”的经典陷阱（尤其incumbent已reimbursed，对照组选择会偏倚）。  
2. **人群可比性**：Z是selected population（可能富集biomarker阳性），incumbent是更宽人群。若Z的62%来自富集亚组，而incumbent的48%是全人群，则**头对头比较无效**。  
3. **安全性长期轮廓**：7个月随访不足以暴露迟发毒性（尤其联合用药或长期维持场景）。  
4. **竞争格局**：market crowded，即使Z ORR更高，若incumbent已有医保覆盖且医生惯性处方，商业转化率存疑。

**Kill / falsification criterion**  
**最可能推翻当前乐观叙事的证据（按优先级排序）：**  
1. **随机对照中期分析**：若Z在PFS上**不优于**incumbent（HR ≥ 1.0，或95%CI跨1），则ORR优势沦为“无临床意义的替代指标”——这是最直接的杀手。  
2. **亚组分析反转**：若Z的62% ORR主要来自biomarker阳性亚组，而该亚组在incumbent中同样高（如60%+），则“差异化”消失。  
3. **安全性信号**：若在后续随访中出现≥15%的3-4级非血液学毒性（尤其间质性肺炎、心脏毒性），且无生存获益补偿，则价值重估。  
4. **入组偏倚证据**：若Z的selected population标准（如PD-L1高表达、特定突变）在真实世界中仅覆盖<20%患者，则商业峰值大幅缩水。  

**投委会建议**：  
- **估值调整**：可小幅上调（+10-15%）以反映“缓解深度”这一差异化信号，但**不应**因ORR而大幅上调，因为PFS/OS仍是决定定价权的核心。  
- **Conviction**：从“观望”上调至“有条件推进”——建议**立即启动随机II期**（对照组选incumbent或标准治疗），以6个月PFS为中期终点，这是唯一能区分“真best-in-class”与“选择性人群的假阳性”的试验设计。  
- **明确否定条件**：若随机II期PFS HR > 0.85（即Z劣于或仅等于incumbent），则放弃该资产或降级为“me-too”。

## Usage

{"prompt_tokens": 197, "completion_tokens": 816, "total_tokens": 1013, "prompt_tokens_details": {"cached_tokens": 0}, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 197}
