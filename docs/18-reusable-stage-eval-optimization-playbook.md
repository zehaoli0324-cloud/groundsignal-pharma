# 可复用的分 Stage 评估与优化方法

> 适用范围：大模型、Agent、RAG、AI4S、医疗 AI、数据/评测平台等多阶段系统。  
> 来源：从 GroundSignal Medical 的 S1–S10 实践中抽象，不依赖医疗领域本身。

## 1. 术语表

- **Stage（阶段）**：一个有明确输入、输出、责任和失败边界的系统环节。
- **Stage Contract（阶段契约）**：规定该 Stage 的输入/输出 schema、必须保持的不变量、允许失败方式和下游可依赖的保证。
- **Observability（可观测性）**：系统能否记录足够信息，让错误被定位到具体 Stage，而不是只看到最终答案错了。
- **Held-out（留出集）**：不用于当前实现调参的数据。
- **Fresh held-out（全新留出集）**：实现先冻结，再创建的新 evaluator/案例/攻击；第一次结果永久保存。
- **Exposed regression（已暴露回归）**：已经被实现方见过的失败集，只用于防止旧问题复发。
- **Hard gate（硬门禁）**：不可由平均分抵消的失败条件，如安全错误、数据泄漏、权威链破坏、held-out 污染。
- **Failure taxonomy（失败分类体系）**：把 bad case 从“这个例子错了”提升为稳定的错误类型/能力缺口。
- **Capability definition（能力定义）**：描述系统应该具备的可验证能力，而不是描述某个具体测试样例。
- **Vertical slice（纵向切片）**：跨多个 Stage 的小型端到端评估，用于检查局部 PASS 能否组合成系统 PASS。

## 2. 方法一：按“错误能否局部归因”拆 Stage，而不是按代码目录拆

Stage 的目标不是让架构图更漂亮，而是让最终 bad case 可以回答：**是哪一个决策节点错了？**

一个合格 Stage 至少要定义：

```text
输入是什么
→ 做什么决策
→ 输出什么结构
→ 哪些不变量必须成立
→ 有哪些高风险失败
→ 下游允许依赖什么
→ 用什么指标和 hard gate 验证
```

如果一个错误出现后只能说“整个 Agent 不行”，说明 Stage 划分仍然过粗；如果一个 Stage 只有格式转换、没有独立决策，也可能拆得过细。

## 3. 方法二：Observability-first——先让错误可测，再优化算法

优先级应是：

```text
可观测
→ 可归因
→ 可复现
→ 可评估
→ 才能可靠优化
```

每个 Stage 应输出结构化 trace，包括输入身份、版本、关键中间决策、置信度/abstention、来源、输出身份和下游引用。没有 trace 的端到端平均分很难指导修复。

## 4. 方法三：Stage Contract + 不变量，比“多加测试题”更重要

对每个 Stage 写一份 machine-checkable contract：

- input schema / output schema；
- version / source identity；
- invariants（不变量）；
- failure modes；
- hard gates；
- promotion criteria（晋级条件）。

优化优先改 contract、状态机、身份模型、数据结构或算法，使一整类错误变得不可表达/不可通过，而不是为单个案例添加 if/else。

## 5. 方法四：把“能力分数”和“信任门禁”分开

推荐每个 Stage 同时维护两组指标。

**能力指标**回答“做得多好”：accuracy、F1、recall、ranking quality、calibration、latency 等。

**信任门禁**回答“能不能被下游使用”：critical false support、held-out leakage、unsafe action、source identity mismatch、gold not approved 等。

规则：平均分不能抵消 hard gate。例如 99% accuracy + 1 个高风险 false-support，仍可判 release blocked。

## 6. 方法五：Freeze → Fresh → Immutable First Observation

这是最关键的泛化证据纪律。

```text
实现完成
→ freeze commit + 关键 blob
→ 之后才写新的 fresh suite
→ 首次运行
→ 原始结果永久保存
```

如果首次 FAIL：保留 FAIL，不能修完后把同一 suite 改叫 fresh PASS。修复后的同一 suite 自动降级为 exposed regression。

这可以区分：

```text
“会不会做这道已经见过的题”
vs
“修复是否泛化到新的未知 failure family”
```

## 7. 方法六：每次 FAIL 必须从 bad case 提炼为 capability gap

标准链条：

```text
Bad case
→ observation（发生了什么）
→ root cause（为什么发生）
→ failure taxonomy（属于哪类错误）
→ capability definition（系统应具备什么能力）
→ generic repair（通用修复）
→ exposed regression
→ 新 fresh family
```

禁止直接从 bad case 跳到 patch。否则非常容易形成测试集过拟合。

## 8. 方法七：Fresh suite 应测“新组合关系”，不只是换实体名

真正有价值的新 fresh family 应改变至少一个结构性维度，例如：

- 单点错误 → 多条件组合；
- 静态内容 → 时间/状态变化；
- 精确重复 → 近似/变换/血缘复用；
- 单 Stage → 跨 Stage 组合；
- 正常输入 → adversarial（对抗）输入；
- 常规路径 → authority / identity / provenance（权威、身份、来源）边界；
- 单次检查 → check/use 一致性；
- 明确证据 → 冲突、缺失、低质量或噪声证据。

只替换疾病名、公司名、药名或 prompt 表述通常不构成真正 fresh 能力证据。

## 9. 方法八：Regression Firewall——历史失败全部保留，但分证据等级

推荐至少保留四层测试：

```text
L0 syntax / schema / fixture
L1 development regression
L2 historical exposed failure regression
L3 post-freeze independent fresh
```

历史 exposed case 应永久保留在 CI，防止能力回退；但报告中必须与 fresh 指标分栏，不能混成一个总分。

## 10. 方法九：局部 PASS 后必须跑 cross-stage vertical slice

Stage eval 解决“哪里错”，vertical slice 解决“局部正确能否组合”。

例如：

```text
S2 retrieval 正确
+ S3 verification 正确
≠ S2→S3 一定正确
```

边界字段丢失、版本错位、置信度被覆盖、source role 传错等问题，只会在联合评估中出现。

建议每完成 2–3 个 Stage，就增加一条小型 vertical slice，而不是等 S10 再做第一次端到端测试。

## 11. 方法十：Gold / Human / Clinical Gate 与结构性 Gate 正交

自动 evaluator 能证明结构、逻辑、身份、统计或行为边界，却不能自动产生专家批准。

因此使用并行证据轴：

```text
structural gate
model-behavior gate
human/Judge calibration gate
domain expert gold gate
real-user gate
production/clinical gate
```

某一轴 PASS 不应被翻译为其他轴 PASS。

## 12. 方法十一：Promotion 不是 PASS/FAIL 二元值，而是成熟度阶梯

推荐通用成熟度：

```text
SCaffold
→ Development PASS
→ Exposed Regression PASS
→ Independent Fresh Evidence
→ Repeated Fresh Evidence
→ Cross-stage Evidence
→ Real-source / Human-calibrated Evidence
→ Bounded Release
→ Production Validation
```

报告必须写清“当前在哪一级”和“缺什么证据升级”，避免用模糊的“系统已经验证”描述。

## 13. 方法十二：优化顺序按风险传播，而不是按容易程度

优先修复会污染下游的上游 Stage。例如 source routing 错误会污染 evidence verification；benchmark partition 泄漏会污染训练和最终 regression。因此应该建立 dependency-aware release order（依赖感知放行顺序）。

通用判断：

```text
如果 Stage A 的错误会让 Stage B 的评估数据或标签失真
→ A 必须先被 bounded release
→ B 的结果在此之前只能算 scaffold/development evidence
```

## 14. 标准 Stage Eval Package

以后新项目建议每个 Stage 固定交付以下目录结构：

```text
stage-evals/SX/
  protocol-vX.json
  suite-vX.json
  raw-first-observation-vX.json
  failures-vX.json
  REPORT.md
scripts/
  eval_sX_*.py
.github/workflows/
  sX-*.yml
docs/
  stage-status.md
```

其中 `protocol` 至少包含 target freeze、scope、metrics、hard gates、freshness declaration；`failures` 至少包含 observation、root cause、severity、capability gap；raw first observation 不做手工润色。

## 15. 标准迭代周期

推荐把每轮工作固定为：

```text
Define Stage Contract
→ Build development eval
→ Fix obvious bugs
→ Freeze implementation
→ Author fresh suite
→ First observation
→ Preserve raw evidence
→ Taxonomy + root cause
→ Generic repair
→ Exposed regression
→ Cross-stage regression
→ Re-freeze
```

当 fresh 连续只发现同一类表面变体时，说明应该停止继续加 case，转而重新检查 Stage contract 或系统抽象；当多个不同 failure family 的 fresh suite 均稳定通过，再讨论 bounded release。

## 16. 可直接复用的 Stage Card 模板

```yaml
stage_id: SX
name: <stage name>
owner: <primary owner>
inputs:
  - <typed input>
outputs:
  - <typed output>
upstream_dependencies:
  - <stage>
downstream_consumers:
  - <stage>
invariants:
  - <must always hold>
capability_metrics:
  - <metric + threshold>
hard_gates:
  - <zero-tolerance condition>
observability:
  - <required trace/log>
evidence_level: <scaffold/dev/exposed/fresh/...>
release_status: <blocked/conditional/bounded>
next_proof:
  - <what new evidence is required>
```

## 17. GroundSignal 中已经验证这套方法有效的地方

S4 的第一次 independent fresh 18/20 FAIL，修复后旧 fresh 只作为 exposed regression，同时另外创建新 fresh 20/20；这证明“修旧题”和“新泛化”被成功分开。

S5 从 F4–F23 连续五轮 fresh 发现新的 provenance、trust-root、policy-root、authority-composition、lineage/TOCTOU 边界；每一轮旧 failure family 修复后仍能被下一轮新的攻击组合继续击穿。这说明该方法能持续暴露系统抽象中的新缺口，而不是让分数因为测试集被看见而虚高。

## 18. 与本仓库其他文档的关系

- `docs/17-evaluation-methods-and-optimization-ledger.md`：GroundSignal 当前事实与结果总账。
- 本文：跨项目可复用的方法论，不绑定当前实现版本。
- `docs/19-algorithm-collaboration-handoff-guide.md`：如何把 Stage eval 与算法开发团队解耦并协作。
