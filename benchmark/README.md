# GroundSignal Pharma — Decision Intelligence Benchmark v0.1

> **给定真实世界医药证据，系统能不能帮助专业用户做出一个更好的判断？**

不是医学考试。不考"替尔泊肽的靶点是什么"（低价值），而是考：

> 一家 GLP-1 创新药公司准备寻找海外合作伙伴，基于现有管线、靶点、适应症、临床阶段和竞争格局，最应该优先比较哪些竞品？为什么？

## 核心原则

1. **用户任务是母体，Eval 是子集。** 同一案例同时服务：产品验证 + 模型评测 + 求职作品集。
2. **证据分层不可混。** OBSERVED（事实）/ DERIVED（结构化推断）/ HYPOTHESIS（待验证假设）严格区分。
3. **同一问题，不同证据状态，不同正确答案。**（LiveEval 的动态 truth：Phase II 注册 → III 期阳性 → NDA → FDA 获批，答案逐级变化）
4. **同一信息，不同用户，不同理想答案。**（科研看 endpoint/局限，BD 看资产价值/合作方，VC 看价值拐点/拥挤度，战略看 watchlist 威胁等级）
5. **不确定就要说不知道（Abstention）。** 证据不足时，正确答案是"证据不足"，而不是编一个。

## 用户 → 任务 → 问题 → 失败 → 指标

| 用户 | 真实任务 | GroundSignal 应输出 | 不可接受错误 | 核心指标 |
|------|---------|---------------------|-------------|---------|
| 药企 BD | 找合作/授权机会 | 候选公司、资产重叠、机制互补、历史交易 | 虚构合作关系；猜测当事实 | Precision、Evidence Coverage、Actionability |
| 药企战略/CI | 判断竞争格局 | shared target/indication/modality/stage + 竞争层级 | shared target = direct competitor | Relation Precision、False Positive |
| 临床开发 | 评估邻近管线 | Trial、phase、endpoint、population、status | 把注册状态当疗效证据 | Temporal Accuracy、Evidence Sufficiency |
| 医疗 VC/PE | 赛道拥挤度判断 | target/indication landscape、阶段分布、交易活跃度 | 只数公司不分析资产差异 | Coverage、Decision Usefulness |
| 医疗 VC/PE | 投前尽调 | claim → evidence → contradiction → confidence | 照抄公司宣传材料 | Claim Precision、Contradiction Recall |
| 行业研究 | 解释行业事件 | Event → first-order impact → affected assets | 时间相关性当因果 | Impact Precision |
| 管理层 | Watchlist | Top-N prioritized alerts + why it matters | 所有新闻都推送 | Precision@K、User Useful Rate |

## Case 结构（模板）

每个 case 包含：

```yaml
case_id:           # 如 case-001-glp1-competition
user_role:         # BD / CI / VC / IR / Clinical Dev
scenario:          # 用户任务背景（真实世界情境）
evidence_snapshot: # T1/T2/T3/T4 证据状态（LiveEval 用）
questions:         # 5-8 个模型问题，分层：
                   #   L1 事实题（Fact / Temporal Grounding）
                   #   L2 关系题（Relation Reasoning）
                   #   L3 证据充分性（Evidence Sufficiency / Overclaim）
                   #   L4 产品题（Task Usefulness / Decision Relevance）
gold:              # 正确答案 + 证据依据（NCT/批准日期/来源）
unacceptable:      # 不可接受错误（哪些答案直接判负）
```

## 四层派生（同一个 case 拆 4 层）

1. **事实题**：这个资产目前处于什么临床阶段？→ Fact / Temporal Grounding
2. **关系题**：它和司美格鲁肽构成直接竞争吗？→ Relation Reasoning（不能只看"都做肥胖"）
3. **证据充分性**：当前公开信息足以说它优于替尔泊肽吗？→ Evidence Sufficiency + Overclaim（III 期阳性 ≠ superiority）
4. **产品题**：如果你是竞争情报负责人，它值得进高优先级 watchlist 吗？→ Task Usefulness

## 同一题 × 不同证据状态（LiveEval 核心）

Case 固定："Drug X 是否已证明对肥胖有效？"

| 快照 | 证据状态 | 正确答案 |
|------|---------|---------|
| T1 | 仅 Phase II 注册 | **证据不足** |
| T2 | Phase III topline positive | 可以说"III 期达到主要终点"，不能说"已批准" |
| T3 | NDA accepted | 仍不能说 "FDA approved" |
| T4 | FDA approval | 这时才可以说"已获批" |

这一个案例同时测试：factuality / evidence sufficiency / uncertainty / temporal reasoning / overclaim / source hierarchy。

## BD Answer Rubric（10 维）

见 `rubrics/bd-answer-rubric.md`。

## 规模

v0.1 目标：3 类用户 × 4 case = 12 case，每 case 5-8 个问题 + 1 个完整决策任务 → 60-100 evaluation items。
每个 case 同时产生：产品案例 / 模型考题 / Judge calibration sample / 训练数据（Bad vs Preferred）。

## 与仓库的关系

- Evidence Graph（pharma/）→ Model Query → Model Response → Rubric Eval → Failure Type → Training Example → Regression
- GroundSignal LiveEval：以 continuously updated evidence graph 作为动态 truth source，对专业模型的事实新鲜度、证据引用、时间一致性、overclaim 做持续回归评测
