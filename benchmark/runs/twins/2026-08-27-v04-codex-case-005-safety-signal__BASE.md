# Codex — case-005-safety-signal__BASE (twin run)

2026-08-27

## Answer

当前最合理的归因排序是：**platform/shared chemistry > molecule-specific > target-mediated**。但现阶段只能算工作假设，不宜宣布为 class effect。

1. **Platform / shared linker-delivery chemistry（首位）**  
   S 与 A 分子不同，却共享相似 linker/delivery chemistry，并都出现肝毒性，提示共同的肝脏暴露、代谢产物或细胞摄取机制。

2. **Molecule-specific toxicity（次位）**  
   S 的严重事件仍可能来自其独特结构、杂质、代谢物、剂量或暴露峰值；A 的 warning 未必与 S 属于同一机制。

3. **Target-mediated toxicity（目前较低）**  
   B 是关键 **negative control**：同 target、暴露更大，却没有同类 warning；同时监管机构也没有 class-wide warning。  
   不过 B 使用不同 modality，因此若其肝组织暴露、细胞内 target engagement 或患者人群不同，这个 negative control 并不完美，不能完全排除 target 风险。

### Portfolio action

- **S：暂停升级暴露和新增大规模投入**，在明确机制前采用肝功能强化监测、严格停药规则，并评估风险是否存在可接受的治疗窗。
- **共享 S/A chemistry 的项目：整体进入风险闸门**。冻结同类 linker/delivery 的新候选推进，优先做去风险化和替代 chemistry；不要只淘汰 S 后继续复制同一平台。
- **B 及不同 modality 的同靶点项目：继续推进，但设验证性监测**。目前证据不足以放弃整个 target。
- Portfolio 层面暂时应把风险计入 **platform concentration risk**，而不是直接关闭 target；同时保留 molecule-specific escape route。

### 最有区分力的下一条证据

最有价值的是一套**跨分子的肝脏暴露—损伤机制对照实验**：在可比 target engagement 下，比较 S、A、B 的肝细胞/肝组织暴露、代谢物、蛋白加合物及线粒体或胆汁酸转运损伤。

判读逻辑：

- S、A 阳性而 B 阴性，且毒性随共同 linker/delivery 暴露变化 → **platform/chemistry**；
- 仅 S 阳性 → **molecule-specific**；
- 三者在匹配肝内 target engagement 后均出现相同损伤 → **target-mediated**。

若能新增化合物，最强的实验设计是“正交矩阵”：**同 target、不同 chemistry**，以及**不同 target、相同 platform chemistry**。它能直接解除目前 target 与 shared chemistry 之间的混杂。spontaneous-report signal 可支持警戒，但因缺乏暴露分母和混杂控制，不能单独完成因果归因。
