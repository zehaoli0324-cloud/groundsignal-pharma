# DeepSeek — case-005-safety-signal__BASE (twin run)

2026-08-27

## Prompt

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

**核心判断：当前证据最应优先归因于 molecule（分子本身），其次才是 platform（递送/连接子化学），target 归因目前证据最弱。**

---

## 1. Causal Hypotheses 排序（按当前证据支持度）

| 排序 | 假设 | 支持证据 | 反对证据 |
|------|------|----------|----------|
| **H1（首选）** | **Molecule-specific 毒性**（S 分子固有肝毒性，与靶点无关） | S 与 A 有相似 linker/delivery chemistry 但 A 也有 warning，说明**不是单纯 molecule 独有**；但 B 无 warning 且暴露更大，说明**不是 target 必然毒性**。S 与 A 共享的可能是分子结构特征（如疏水性、代谢物反应性） | S 与 A 的相似 chemistry 也可能指向 platform |
| **H2（次选）** | **Platform/delivery chemistry 相关**（linker 或递送系统导致肝蓄积/毒性） | S 与 A 共享 linker/delivery chemistry，且两者都有 warning；B 用不同 modality 无 warning——这组对比强烈支持 platform 假说 | 但 A 与 S 的 molecule 也可能共享某些非靶点结构特征；且无 regulator class-wide warning，说明 platform 风险未在更大范围显现 |
| **H3（最弱）** | **Target 相关**（靶点抑制本身导致肝毒性） | 无直接证据；mechanism hypothesis 未验证 | B 同靶点、更大暴露、无 warning，是**强阴性对照**，基本排除 target 作为主要归因 |

---

## 2. Negative Control（关键对照）

**B 是核心 negative control**：同靶点、更大暴露、不同 modality、无肝毒性 warning。

- 如果 B 在足够暴露下无信号，则 **target 归因基本被排除**。
- 如果 B 无信号而 S/A 有信号，则风险集中在 **S/A 共享的分子或 platform 特征**上。

**次要 negative control**：A 是“同靶点+同 platform 化学”的阳性对照，用于区分 molecule vs platform——但 A 与 S 的 molecule 差异可能不够大，需进一步结构比对。

---

## 3. Portfolio Action（基于当前判断）

**短期（0–3个月）：**
- **暂停 S 的临床推进**（如正在入组，暂停新患者入组；已入组患者加强肝功监测）。
- **不因 S 事件自动暂停同靶点其他资产**（B 可继续，因 B 是 negative control 且暴露更大无信号）。
- **对 A 进行风险重审**：若 A 在临床中，需评估其暴露-毒性关系，确认是否与 S 共享的 chemistry 相关。

**中期（3–12个月）：**
- **将 S 与 A 的分子结构、代谢物谱、体外肝细胞毒性数据做系统比对**，区分 molecule vs platform。
- **若 platform 假说成立**：对同 platform 的其他管线（即使不同靶点）进行肝毒性风险评估，考虑是否需要调整递送系统。
- **若 molecule 假说成立**：仅 S 受影响，A 可继续但需加强监测，B 完全不受影响。

**长期：**
- 若 target 假说被最终排除（B 数据充分），**保留靶点作为可开发方向**，但需选择更安全的 modality/molecule。
- 若 platform 假说成立，**考虑替换 linker/delivery chemistry** 作为下一代分子设计策略。

---

## 4. Discriminating Evidence（下一步最有区分力的证据）

**优先级排序：**

1. **S vs A 的分子结构/代谢物比对（最高区分力）**
   - 如果 S 与 A 共享某个独特的代谢物或反应性中间体（如谷胱甘肽加合物、活性代谢物），而 B 没有 → 支持 **molecule 假说**。
   - 如果 S 与 A 共享的是 linker 断裂产物或递送载体相关代谢物 → 支持 **platform 假说**。

2. **体外肝细胞毒性实验（区分 molecule vs platform）**
   - 用 S、A、B 的分子（在相同递送条件下）和 S/A 的 linker 单独测试：
     - 若 S 和 A 的分子（去掉 linker）均显示肝毒性，而 B 分子不显示 → molecule。
     - 若 S 和 A 的完整偶联物有毒，但游离分子无毒 → platform。

3. **B 的暴露-反应数据（排除 target）**
   - 确认 B 在临床/临床前达到的暴露量 ≥ S 的有效暴露量，且无肝毒性信号。若 B 暴露充分且无信号，target 假说可正式排除。

4. **S 的剂量-毒性关系（辅助）**
   - 若肝毒性呈剂量依赖性且与暴露相关，支持 molecule/pharmacology 相关；若为 idiosyncratic（非剂量依赖），更支持 molecule 特异反应。

---

## 总结

| 维度 | 判断 |
|------|------|
| 首要归因 | **Molecule-specific**（S 分子固有毒性） |
| 次要归因 | **Platform chemistry**（linker/delivery） |
| 排除归因 | **Target**（B 为强阴性对照） |
| Portfolio 行动 | 暂停 S；保留 B；重审 A；对同 platform 资产预警 |
| 下一步证据 | **S vs A 结构/代谢物比对 + 体外肝细胞毒性实验**（区分 molecule vs platform） |

**关键逻辑：** B 的存在是最大的信息优势——它告诉我们这不是靶点问题，因此我们不需要放弃整个靶点，只需在 molecule 和 platform 之间做精准切割。
