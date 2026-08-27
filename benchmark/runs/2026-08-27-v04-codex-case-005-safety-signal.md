# Codex (GPT-5-family) — case-005-safety-signal (v0.4 updated, visible-only)

2026-08-27

## Answer

当前最合理的归因是：**优先归到 S/A 共享的 linker / delivery chemistry，其次是 molecule-specific，暂不归为 target-wide 风险。**这里的“platform”应限定为共享化学模块，不能泛化到整个技术平台。

### Causal hypotheses 排序

1. **共享 linker / delivery chemistry 导致肝毒性——最高可能**
   - S 和 A 分子不同、靶点相同，但共享相似 linker/delivery chemistry，且均出现肝脏信号。
   - 可能机制包括肝脏富集、释放产物或反应性代谢物、转运体抑制、Kupffer cell 摄取等。
   - 目前证据支持“chemistry-family effect”，但尚不足以认定整个 platform 都有问题。

2. **S 的 molecule-specific toxicity——中等可能**
   - S 的 payload、代谢物、杂质、暴露峰值或 off-target 作用可能造成严重事件。
   - A 的 warning 可能是独立机制，现有信息尚不能证明两者完全同源。

3. **Target-mediated hepatotoxicity——较低但不能排除**
   - A 提供了一定支持，但 **B 是关键 negative control**：同靶点、较大暴露，却没有同类 warning。
   - 不过 B 使用不同 modality，因此只能削弱“普遍 target class effect”，不能排除依赖组织分布、靶点占有方式或效应机制的 target toxicity。
   - 没有监管机构 class-wide warning，也进一步降低了 target-wide 归因的优先级。

Spontaneous-report signal 可提高警觉，但受漏报、重复报告和适应症混杂影响，不能单独完成因果归因。

### Portfolio action

- **不要暂停整个 target portfolio。**
- 立即暂停或降速 S，以及采用相同/高度相似 linker-delivery chemistry 的项目：停止剂量递增和新增暴露，开展病例复核与加强肝功能监测。
- 对 B 和其他不同 modality、不同递送化学的同靶点资产，可以继续推进，但加入预设的 hepatic stopping rules 和强化监测。
- 将 A/S 共享化学模块列为暂时性 design liability；新项目优先采用替代 linker/delivery，并避免继续复制该模块。
- 在归因明确前，S 的资产价值和同化学家族资产应提高技术风险折扣；不应把这一折扣机械地施加于全部同靶点资产。

### 最有区分力的下一条证据

最有区分力的是一个**组件解耦的、暴露匹配的 head-to-head 实验**：

- 同一 target-binding molecule，比较问题 linker/delivery 与替代 chemistry；
- 同一 linker/delivery，比较 S/A 与不相关靶点或惰性 payload；
- 同时测定肝脏组织暴露、完整药物与游离产物、代谢物、胆汁酸/转运体效应及组织病理。

关键判读：

- **毒性随 linker/delivery 转移** → 强支持 chemistry/platform-module effect；
- **仅随 S 的主体分子或代谢物出现** → 支持 molecule-specific；
- **不同 chemistry 和 modality 下，只要达到相似靶点占有率均出现毒性** → 才会显著提升 target-mediated hypothesis。

若能获得临床数据，第二优先级是对 S、A、B 做统一定义下的**暴露校正 hepatic event 分析**，包括时间关系、去激发结果、合并用药和基础肝病。未经验证的 mechanism hypothesis 本身，区分力低于上述组件解耦证据。
