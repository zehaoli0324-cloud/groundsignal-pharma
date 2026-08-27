# DeepSeek — case-005-safety-signal__C05-C (twin run)

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
- A 的 warning 被证明来自特异 off-target metabolite。

Expected:
- platform/target inference 下调，S-specific hypothesis 上调。

---

## Answer

## 核心判断：风险应优先归因于 **molecule**，其次为 **platform**，target 风险最低

---

### 一、Causal Hypotheses 排序

| 排序 | 假设 | 支持证据 | 反对证据 | 概率评估 |
|------|------|----------|----------|----------|
| **1. Molecule-specific（S 特有）** | S 的肝毒性源于其独特的化学结构、代谢途径或 off-target 活性 | ① B（同靶点、大暴露）无 warning → 排除 target 主导；② A 的 warning 已证实来自特异 off-target metabolite → 同靶点药物可因不同 off-target 产生不同毒性；③ S 与 A 有相似 linker/delivery chemistry，但 A 的毒性机制已明确为 off-target，S 可能类似但分子不同 | 尚无 S 特异性机制的直接证据 | **45–55%** |
| **2. Platform-related（linker/delivery 化学）** | S 与 A 共享的 linker 或 delivery 平台特征导致肝毒性倾向 | ① S 与 A 均有肝毒性信号且共享 linker/delivery chemistry；② 同类平台在其他靶点项目中可能也有潜在信号（需验证） | ① B 使用不同 modality 无 warning，但 B 的靶点暴露更大 → 若平台是主因，B 应受影响；② A 的 warning 已归因于 off-target metabolite，而非平台 | **25–30%** |
| **3. Target-related** | 靶点本身调节导致肝毒性 | B 同靶点、大暴露、无 warning → **强阴性对照**，基本排除 | 需考虑 B 的 modality 是否可能掩盖肝毒性（如分布差异） | **<10%** |

---

### 二、Negative Control 识别

**B 是核心 negative control**：

- 同靶点 + 更大暴露 + 不同 modality → 无肝毒性 warning
- 若 target 是主因，B 应至少出现类似信号
- B 的存在同时削弱 platform 假设（若 platform 是主因，B 因 modality 不同不受影响，但 S 与 A 共享 platform 而 B 不共享 → 无法完全排除 platform，需额外数据）

**A 的 off-target metabolite 归因**是第二个 negative control：

- A 的 warning 已明确非 target 介导 → 同靶点药物间毒性差异可由 molecule 特异性解释
- 这直接支持将 S 的风险从 target 转移到 molecule

---

### 三、Portfolio Action

**短期（0–3 个月）：**

1. **不终止靶点项目** — B 的阴性数据保护了 target 的 viability，同靶点其他分子（如有）可继续推进
2. **暂停 S 的临床推进**（若在临床阶段）或 **延缓 IND-enabling 研究**，直至机制明确
3. **对同 platform 的其他项目进行肝毒性信号筛查** — 若 platform 假设成立，其他项目可能受影响；建议对共享 linker/delivery 的分子做早期肝细胞毒性 panel

**中期（3–12 个月）：**

4. **优先开展 S 的代谢物鉴定与 off-target profiling** — 参照 A 的路径，寻找 S 特异性 reactive metabolite 或 off-target 活性
5. **评估 platform 层面的结构-毒性关系** — 对比 S 与 A 的 linker 代谢稳定性，判断是否需对 platform 进行优化
6. **对 B 的肝安全性数据做深度审查** — 确认 B 的暴露-安全性关系是否真正干净（排除因分布差异导致的假阴性）

**长期：**

7. 若 S 的毒性归因于 molecule-specific 代谢物 → 可考虑 **backup molecule** 开发，保留 target 和 platform
8. 若归因于 platform → 需 **platform 改造** 或限制该平台在肝高表达靶点上的应用
9. 若归因于 target（低概率）→ 重新评估靶点生物学

---

### 四、Discriminating Evidence（下一步最有区分力的证据）

**优先级排序：**

| 优先级 | 证据类型 | 具体实验/数据 | 区分能力 |
|--------|----------|---------------|----------|
| **1** | **S 的代谢物鉴定 + 反应性代谢物筛查** | 肝微粒体/肝细胞孵育，GSH trapping，鉴定 S 特有 reactive metabolite；与 A 的 off-target metabolite 对比 | 直接验证 molecule-specific 假设；若发现 S 特有 reactive metabolite → 风险归因 molecule 确认 |
| **2** | **S 与 A 的 off-target 活性谱对比** | 激酶组/受体组 profiling，对比 S vs A vs B 的 off-target 结合谱 | 若 S 与 A 共享 off-target 但 B 不共享 → 支持 platform 或 molecule 假设；若 S 有独特 off-target → 支持 molecule |
| **3** | **同 platform 其他分子的肝毒性信号审查** | 检查公司内部共享相同 linker/delivery 的其他项目是否有肝酶升高信号 | 若多个 platform 分子均有信号 → platform 假设强化；若仅 S 和 A → molecule 假设强化 |
| **4** | **B 的暴露-安全性关系深度分析** | 确认 B 在肝组织的暴露水平、代谢途径是否与 S/A 有本质差异 | 排除 B 因低肝暴露导致的假阴性 |

**最有区分力的是第 1 项** — 直接鉴定 S 的特异性代谢物/off-target，这与 A 的归因路径一致，能最快锁定风险来源。

---

### 五、最终判断

> **风险归因优先级：Molecule > Platform >> Target**

- **Target 风险基本排除**（B 为强阴性对照）
- **Platform 风险需监测**（S 与 A 共享 linker/delivery，但 A 的毒性已归因于 off-target metabolite，削弱了 platform 假设）
- **Molecule 风险为当前最可能** — 与 A 的教训一致，同靶点不同分子可因 off-target 差异产生不同毒性

**Portfolio 含义：** 靶点项目可继续，但 S 分子需暂停推进直至机制明确；同 platform 项目需加强肝毒性监测；建议启动 backup molecule 评估以对冲 S 的 molecule 风险。
