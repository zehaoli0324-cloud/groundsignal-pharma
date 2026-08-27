# DeepSeek — case-005-safety-signal__C05-B (twin run)

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

---

补充信息（最新更新）：
新增：
- B 也出现一致 hepatic signal。

Expected:
- target-level hypothesis 显著上调。

## Answer

**核心判断：风险归属应从“molecule 优先”上调为“target 优先”，但仍需保留 modality 作为协同风险因子。**

---

### 1. Causal Hypotheses 排序（按当前证据后验概率）

| 排序 | 假设 | 支持证据 | 反对证据 | 后验概率变化 |
|------|------|----------|----------|--------------|
| **1** | **Target-level 风险（on-target 或 target 通路相关肝毒性）** | ① S 与 A 均有肝毒性，且两者为不同 molecule；② **新增关键证据：B（不同 modality、大暴露）也出现一致肝毒性信号**——这直接打破了“molecule 或 modality 特异性”的强解释；③ 无 regulator class-wide warning 只能说明监管滞后，不能否定生物学机制 | ① B 的肝毒性严重度/因果关系尚未完全确认（需排除混杂）；② mechanism hypothesis 未验证 | **显著上调**（从“可能”到“首要”） |
| **2** | **Molecule 特异性（S 自身化学结构/代谢）** | S 有数例严重事件；A 的 warning 可能源于其自身结构而非靶点 | ① A 与 S 是不同 molecule 却共享 warning；② B 出现 signal 后，molecule 特异性无法解释跨 molecule 的一致性 | **下调**（但仍保留为次要，因 S 严重度可能高于 A/B） |
| **3** | **Modality / delivery chemistry 风险（linker、脂质、偶联物）** | S 与 A 有相似 linker/delivery chemistry；B 用不同 modality | ① B 用不同 modality 也出现 signal——这直接削弱 modality 作为主因；② 若 modality 是主因，B 应为阴性对照 | **显著下调**（从“可能”降为“协同/混杂因素”） |

---

### 2. Negative Control 识别

**B 是本次判断的“天然 negative control”**，但需注意其角色已反转：

- **原设计**：B（同靶点、不同 modality、大暴露、无 warning）是区分 **target vs. modality** 的 negative control。若 B 阴性 → 风险归 modality/molecule；若 B 阳性 → 风险归 target。
- **新增证据后**：B 出现 signal，**B 已从 negative control 变为“阳性确认”**。因此，**当前真正的 negative control 应是：同 modality、不同靶点的化合物**（如 S 的 linker 平台上的其他非靶点药物），用于排除 delivery chemistry 的混杂贡献。

> **行动建议**：立即调取 S/A 所用 linker/delivery 平台中 **其他靶点项目** 的肝毒性数据。若这些项目无 signal → modality 可排除，target 假设进一步强化；若有 signal → modality 是协同因素，需在 portfolio 中单独管控。

---

### 3. Portfolio Action（基于 target 风险上调）

**立即执行（0-30 天）：**
- **暂停 S 的剂量爬坡/新患者入组**，仅保留已获益患者的继续用药（需知情同意）。
- **对 A 项目进行独立安全性审查**，若 A 的 warning 与 S 严重度相当，考虑同步降剂量或暂停。
- **对 B 的肝毒性 signal 进行紧急因果评估**（排除感染、合并用药、基线肝病等），确认是否为真信号。

**中期（1-3 个月）：**
- **将“该靶点”标记为 portfolio 级风险**，而非单分子风险。所有同靶点资产（含临床前）需重新评估获益-风险比。
- **建立靶点级安全治理**：成立跨项目安全委员会，统一监测肝酶、胆红素、Hy's Law 案例。
- **对同靶点早期资产**：若为同类 modality，优先暂停推进；若为不同 modality（如小分子 vs. 抗体），可谨慎推进但需前置肝毒性生物标志物。

**长期（>3 个月）：**
- **若机制验证（见下）支持 on-target 毒性** → 考虑该靶点是否值得继续投资，或需开发“肝脏保护”联合策略（如靶向递送、前药设计）。
- **若机制验证支持 off-target 但靶点通路相关** → 可探索“选择性调节”策略（如部分激动/拮抗），但需极高门槛。

---

### 4. Discriminating Evidence（下一步最有区分力的证据，按优先级）

| 优先级 | 证据类型 | 具体操作 | 区分力说明 |
|--------|----------|----------|------------|
| **P0** | **B 的肝毒性因果确认 + 剂量-暴露关系** | ① 对 B 的肝事件做 RUCAM 评分/排除混杂；② 分析 B 的暴露量（AUC/Cmax）与肝酶升高的相关性 | 若 B 的 signal 是真实且暴露相关 → target 假设从“强”变“确证”；若 B 的 signal 是混杂（如偶发）→ 回到 molecule/modality 假设 |
| **P1** | **同 modality、不同靶点的 negative control 数据** | 调取 S/A 所用 delivery 平台的其他项目肝毒性数据 | 直接区分 modality 贡献 vs. target 贡献。若平台其他项目阴性 → modality 排除，target 确认 |
| **P2** | **机制验证（in vitro / in vivo）** | ① 在肝细胞/肝类器官中敲低或过表达靶点，观察毒性表型；② 用靶点特异性拮抗剂/激动剂在动物中验证肝毒性 | 区分 on-target（靶点生物学）vs. off-target（化学结构）。若敲低靶点可减轻毒性 → on-target；若不可 → 更可能是 molecule 或 modality |
| **P3** | **A 与 S 的肝毒性表型深度对比** | 比较两者的肝损伤模式（肝细胞型/胆汁淤积型/混合型）、严重度、潜伏期 | 若 A 与 S 表型高度一致 → 支持共同机制（target 或 shared chemistry）；若表型差异大 → 支持各自 molecule 特异性 |

---

### 5. 最终结论

> **当前证据下，风险归属应上调为“target-level 为主，modality 为协同因素”。**  
> **Portfolio 决策：立即暂停同靶点新患者入组，建立靶点级安全治理；B 的 signal 确认是最高优先级证据。**  
> **若 B 确认阳性，则该靶点的开发价值需重新评估，除非能证明毒性可通过剂量/递送策略规避。**
