# DeepSeek — case-005-safety-signal (v0.4 updated, visible-only)

2026-08-27

## Prompt

你是医药行业分析师。请直接回答用户的问题。

> Asset S 出现严重肝毒性。A 是同靶点，也有类似 warning；B 同靶点但没有。  
> **我们现在最应该把风险归到 molecule、platform 还是 target？这个判断会怎样影响 portfolio 决策？下一步哪条证据最有区分力？**

## Evidence

- S：数例严重 hepatic event。
- A：同 target；不同 molecule；有 hepatic warning。
- B：同 target；较大暴露；无同类 warning。
- S 与 A 有相似 linker / delivery chemistry。
- B 使用不同 modality。
- spontaneous report 有 signal。
- mechanism hypothesis 未验证。
- 无 regulator class-wide warning。

## Output 要求

必须：
- 排序至少 2 个 causal hypotheses；
- 指出 negative control；
- 给 portfolio action；
- 给 discriminating evidence。

## Answer

**核心判断：当前证据最应优先归因于 molecule（分子本身），其次才是 platform（递送/连接子化学），target 风险目前证据最弱。**  
理由：S 与 A 共享相似 linker/delivery chemistry，且都有肝毒性信号，而 B（同靶点、不同 modality、更大暴露）无信号——这直接削弱了 target 归因，同时强烈指向 molecule 或 platform 层面的共同毒性机制。

---

### 1. Causal Hypotheses 排序（按当前证据支持度）

| 排序 | 假设 | 支持证据 | 反对证据 |
|------|------|----------|----------|
| **H1（首选）** | **Molecule 固有毒性**（S 的特定化学结构/代谢物导致肝损伤） | S 有严重事件；A 有 warning 但 B 无；S 与 A 的分子骨架可能共享某些毒性药效团（如反应性代谢物、共价结合倾向） | 尚无直接机制数据；A 与 S 并非同一分子，需确认共享结构片段 |
| **H2（次选）** | **Platform 毒性**（linker/delivery 化学，如脂质纳米颗粒、连接子释放特性） | S 与 A 使用相似 linker/delivery；B 使用不同 modality 且无信号 | 若为 platform 毒性，B 若用不同 modality 则无法排除 target 效应；需确认 A 与 S 的 platform 相似度是否高于其与 B 的差异 |
| **H3（最弱）** | **Target 介导毒性**（靶点生物学本身导致肝损伤） | 无 class-wide warning；B 大暴露无信号 | B 是强 negative control，直接否定 target 为充分原因；除非 B 的 modality 改变了靶点组织分布或下游信号，否则 target 假设不成立 |

---

### 2. Negative Control 明确指定

**B 是当前最关键的 negative control。**  
- B 同靶点、更大暴露、无肝毒性信号 → 排除 target 作为独立充分原因。  
- 但 B 的 modality 不同，因此 B 只能排除 target 假设，**不能区分 molecule vs platform**。  
- 若要进一步区分 molecule vs platform，需要寻找一个 **同 platform、不同 molecule、同靶点** 的对照（如 A 的另一个类似物），或 **同 molecule、不同 platform** 的对照（如 S 的裸抗体/游离小分子形式）。

---

### 3. Portfolio Action（基于当前判断）

**立即行动：**  
- **暂停 S 的进一步剂量递增或扩展队列**，除非有明确的获益-风险依据（如肿瘤适应症、无替代疗法）。  
- **对 A 进行肝毒性信号的主动监测**（即使 A 已有 warning，需评估其发生率/严重度是否与 S 一致，以支持 molecule vs platform 归因）。  
- **不因 target 假设而放弃同靶点其他 modality 项目**（如 B 或 B 类项目），因为 target 风险证据不足。

**中期决策（基于证据更新）：**  
- 若证据指向 **molecule**：保留 platform 上其他分子，淘汰 S 的分子系列。  
- 若证据指向 **platform**：暂停该 platform 的所有项目（包括 A），转向 B 类 modality 或替代 linker。  
- 若证据指向 **target**（罕见但需排除）：则整个靶点组合需重新评估，但当前概率低。

---

### 4. Discriminating Evidence（最有区分力的下一步）

**优先级排序：**

1. **S 与 A 的分子结构/代谢物对比分析**（最高区分力）  
   - 检查 S 和 A 是否共享相同的反应性代谢物、共价蛋白结合位点、或肝细胞毒性结构片段。  
   - 若共享 → 支持 molecule 假设；若不共享 → 支持 platform 假设。  
   - 方法：体外肝细胞毒性、代谢物鉴定（LC-MS/MS）、共价结合实验。

2. **S 的“裸分子”或“无 linker”形式测试**（区分 molecule vs platform）  
   - 若 S 的游离药物（不含 linker/delivery）在肝细胞中仍显示毒性 → molecule 固有毒性。  
   - 若游离药物无毒，而完整 conjugate 有毒 → platform 毒性。  
   - 这是最直接的因果分离实验。

3. **B 的暴露-毒性关系再确认**（排除 target 假设的残余风险）  
   - 确认 B 在肝组织中的暴露水平确实高于或等于 S（若 B 肝暴露低，则 target 假设不能完全排除）。  
   - 若 B 肝暴露高且无毒性 → target 假设基本关闭。

4. **A 的剂量-毒性关系**（辅助）  
   - 若 A 的肝毒性呈剂量依赖性且与 S 的严重度模式一致 → 支持 molecule 或 platform 共享机制；若 A 的 warning 是罕见/轻度，而 S 严重 → 更支持 molecule 特异性。

---

**总结一句话：** 当前证据最支持 molecule 归因，B 是排除 target 的关键对照；下一步最有区分力的证据是 **S 与 A 的分子结构/代谢物对比** 以及 **S 的裸分子毒性测试**，这将直接决定是淘汰分子系列还是整个 platform。

## Usage

{"prompt_tokens": 192, "completion_tokens": 1184, "total_tokens": 1376, "prompt_tokens_details": {"cached_tokens": 0}, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 192}
