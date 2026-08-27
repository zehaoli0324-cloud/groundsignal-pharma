# GroundSignal Pharma — Decision Intelligence Benchmark v0.1（v0.2 cases 已落地）

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

## v0.2：6 个控制变量式 Case（已落地 2026-08-27）

> 来源：GroundSignal Decision Intelligence 6 Cases v0.2。每个 Case 同时产出产品资产（Intelligence Brief）与 Eval 资产（questions + gold + critical errors + anchors）。
> 这些 Case 是控制变量式 benchmark fixtures：Asset X / Company A 等证据快照用于冻结 gold，不代表当前真实世界事实。

| Case | 用户角色 | 核心区分能力 | Snapshot |
|------|---------|-------------|----------|
| case-001-competitive-impact | 药企战略/CI | 竞争层级（同机制 vs 市场 vs pipeline）+ 排序 | C01-T1 |
| case-002-regulatory-conflict | 监管情报/临床战略 | source hierarchy + 冲突消解 + abstention | C02-T1 |
| case-003-licensing-bd | 药企 BD | strategic fit + partner 排序（B>A>C）+ 不编造意图 | C03-T1 |
| case-004-due-diligence | VC/PE 投委会 | claim 拆解 + 跨试验不可比 + falsification | C04-T1 |
| case-005-safety-signal | 临床开发/安全 | 信号≠因果≠类别效应 + 风险优先级 | C05-T1 |
| case-006-temporal-watchlist | CI/管理层 | 12 事件压成 Top3 + 去重 + changed claim | C06-T1 |

### 仓库结构（每 case 独立目录）

```text
benchmark/cases/
  case-001-competitive-impact/
    case.md                 # 用户任务 + 冻结快照 + 理想 Brief + eval items + anchors
    gold-behavior.yaml      # pre-registered gold + critical errors + anchors
    eval-items.json         # 模型评测项（L1-L4）
    scores/                 # 盲评 score JSON（benchmark + user-utility 双份）
  case-002-regulatory-conflict/ ... case-006-temporal-watchlist/
  _archive/                 # v0.1 旧 case-001（git tag benchmark-v0.1 已存档）
```

### User Utility Rubric（U1-U5）

产品可用性视角（rubrics/user-utility-rubric.md）：Decision Fit / Trust / Prioritization / Actionability / Uncertainty。
5 维 × 0/1/2 + 总分解释（9-10 Decision-ready / 7-8 Analyst-useful / 5-6 Background-only / 0-4 Not useful）+ 任一 Critical User Error → Reject。
与 10 维 benchmark rubric 并行输出。

### 能力覆盖矩阵（12 能力 × 6 case）

| 能力 | C01 | C02 | C03 | C04 | C05 | C06 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Factual correctness | ●● | ●● | ● | ● | ● | ●● |
| Evidence grounding | ●● | ●●● | ●● | ●●● | ●●● | ●● |
| Temporal validity | ●● | ●●● | ● | ● | ● | ●●● |
| Relation reasoning | ●●● | ● | ●● | ● | ●● | ● |
| Source hierarchy | ● | ●●● | ● | ●● | ●● | ●● |
| Evidence sufficiency | ●● | ●● | ●● | ●●● | ●●● | ● |
| Abstention / uncertainty | ●● | ●●● | ●● | ●●● | ●●● | ●● |
| Prioritization | ●●● | ●● | ●●● | ●● | ●● | ●●● |
| Actionability | ●● | ●● | ●●● | ●●● | ●●● | ●●● |
| Change / impact propagation | ●● | ●● | ●● | ● | ●● | ●●● |
| Falsification / downside | ● | ●● | ●● | ●●● | ●●● | ● |
| User-specific answer quality | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● |

## v0.4：Model Diagnosis Benchmark（已落地 2026-08-27）

> 来源：GroundSignal Decision Intelligence Model Diagnosis v0.4（design-sources/ 有全文）。
> 直接映射岗位要求："凭借专业积累，从知识准确性、推理质量、表达水准等多维度对模型回答形成优劣判断，说明问题及原因，从个案归纳共性体验问题与优化方向。"

### 四大评估层（23 维，diagnostics/expert-diagnosis-rubric.md）

- A Knowledge Quality：A1 事实 / A2 Freshness / A3 Evidence Sufficiency / A4 Source Hierarchy / A5 Claim Scope
- B Reasoning Quality：B1 关系 / B2 因果结构 / B3 证据整合 / B4 反事实 / B5 优先级 / B6 不确定性 / B7 决策杠杆
- C Expression Quality：C1 Decision-first / C2 信息层级 / C3 措辞精度 / C4 密度 / C5 受众适配 / C6 校准的警示
- D User Utility：D1 决策契合 / D2 可辩护性 / D3 可行动性 / D4 非显然洞察 / D5 价值-风险不对称

### 关键纪律

- **Observed Failure ≠ Capability Gap**（失败可观察，能力缺口是假设，需多 case 支持）
- 三类回答对比：A Knowledge-rich Judgment-poor / B Insightful but Overclaimed / C Decision-ready
- 结果报告回答四件事：谁在哪些任务更好 / 为什么（bad case + 诊断）/ 用户感受到什么 / 怎么优化（data/SFT/prompt/retrieval/regression）

### 当前诊断产物

- diagnostics/model-capability-profile.md：双模型四层画像（唯一实测差异 = A2 Freshness，Track A）
- diagnostics/failure-taxonomy.md：10 个 failure cluster 状态（9 个待 Track A/C 激活，1 个已激活）
- diagnostics/optimization-cards/STALE_KNOWLEDGE.md：真实 Optimization Card（玛仕度肽 bad case）

## 与仓库的关系

- Evidence Graph（pharma/）→ Model Query → Model Response → Rubric Eval → Failure Type → Training Example → Regression
- GroundSignal LiveEval：以 continuously updated evidence graph 作为动态 truth source，对专业模型的事实新鲜度、证据引用、时间一致性、overclaim 做持续回归评测
