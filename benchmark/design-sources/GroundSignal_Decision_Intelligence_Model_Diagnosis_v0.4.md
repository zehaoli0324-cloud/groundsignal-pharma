# GroundSignal Pharma — Decision Intelligence + Model Diagnosis Benchmark v0.4

> 目标：不仅评估模型“答对没有”，还要利用专业领域积累，判断**知识准确性、推理质量、表达水准、用户价值**的优劣，解释问题与原因，并从单个案例归纳出共性体验问题和模型优化方向。

---

# 1. 与岗位要求的直接映射

岗位要求：

> 能凭借自身专业积累，从知识准确性、推理质量、表达水准等多个维度对模型回答形成清晰的优劣判断，说明问题所在及原因，并从个案中归纳出共性的体验问题与优化方向。

GroundSignal Benchmark 对应为四层：

```text
专业用户任务
    ↓
Decision Intelligence Case
    ↓
模型回答
    ↓
Expert Evaluation
    ├─ Knowledge Quality
    ├─ Reasoning Quality
    ├─ Expression Quality
    └─ User Utility
    ↓
Observed Failure
    ↓
Capability Gap Hypothesis
    ↓
Cross-case Failure Cluster
    ↓
Optimization Intervention
    ↓
Regression Set
```

---

# 2. 四大评估层

## A. Knowledge Quality（知识质量）

### A1 Factual Correctness
事实是否正确。

### A2 Temporal Freshness
是否使用当前有效状态，而非 stale knowledge。

### A3 Evidence Sufficiency
证据能否真正支持 claim，而不是“有来源就算正确”。

### A4 Source Hierarchy
是否知道监管记录、注册记录、公司公告、媒体分别能支持什么。

### A5 Claim Scope
是否把“Phase III 阳性”“NDA accepted”“安全 signal”等信息升级成更强结论。

---

## B. Reasoning Quality（推理质量）

### B1 Relation Reasoning
能否区分 shared target / mechanistic neighbor / pipeline competitor / commercial competitor。

### B2 Causal / Structural Reasoning
是否解释“为什么”，而不是只做相关性拼接。

### B3 Evidence Integration
多条证据冲突或互补时，能否形成合理综合。

### B4 Counterfactual Reasoning
关键变量变化时，结论是否随之正确更新。

### B5 Prioritization
能否把几十条相关信息压缩成 1–3 个真正重要判断。

### B6 Uncertainty / Abstention
证据不足时是否知道不能继续升级结论。

### B7 Decision Leverage
能否指出“下一条最值得获取的信息”或“最高杠杆行动”。

---

## C. Expression Quality（表达水准）

表达不是“文笔好不好”，而是专业答案是否适合真实用户。

### C1 Decision-first
是否先给结论，再给依据，而不是先堆背景。

### C2 Information Hierarchy
关键信息是否前置，次要证据是否降级。

### C3 Precision of Language
是否使用“支持 / 提示 / 不能证明 / 已验证 / 假设”等精确措辞。

### C4 Information Density
是否高信息密度，而非重复、空泛、过长。

### C5 Audience Fit
对 BD / VC / CI / 临床开发是否使用不同的理想答案结构。

### C6 Calibrated Caveats
不确定性是否放在真正影响决策的位置，而不是结尾加一句“仅供参考”。

---

## D. User Utility（用户价值）

### D1 Decision Fit
回答是否真正解决用户决策。

### D2 Defensibility
用户能否把答案带进会议，并回答“凭什么”。

### D3 Actionability
是否能安排下一步动作。

### D4 Non-obvious Insight
是否给出知识网络综合后才能得到的判断。

### D5 Value / Risk Asymmetry
是否指出谁比表面更危险、更有价值、更值得下注。

---

# 3. 关键升级：每个 Case 不只要 Gold，还要 Expert Diagnosis

每个 Case 固定增加以下结构：

```yaml
expert_evaluation:
  answer_quality:
    knowledge:
    reasoning:
    expression:
    user_utility:

  observed_failures:
    - failure_id:
      behavior:
      severity:
      user_impact:

  capability_gap_hypotheses:
    - hypothesis:
      supporting_cases:
      confidence:

  optimization_candidates:
    - intervention:
      target_failure:
      expected_effect:
      regression_case:
```

关键纪律：

> **Observed Failure ≠ Capability Gap。**

例如：

Observed Failure：
> 模型把“shared target”直接写成“最直接商业竞品”。

Capability Gap Hypothesis：
> 模型可能缺少“竞争关系需要结合适应症、阶段、商业化状态”的结构化判断能力。

不能从一个 case 直接宣布：
> “模型缺乏竞争分析能力”。

---

# 4. 每个 Case 增加“回答优劣对比”

不只给模型打分，还要展示为什么 A 比 B 好。

建议每个 Case 至少保留三类回答：

## Response A — Knowledge-rich, Judgment-poor
事实基本正确，但只是罗列资料。

## Response B — Insightful but Overclaimed
有判断、有高见，但超出证据边界。

## Response C — Decision-ready
事实、推理、表达、用户价值均较好。

这种设计能最直接展示专家判断：

> “C 为什么最好？”
> “A 为什么虽然没错但不好用？”
> “B 为什么看起来聪明但实际上风险最大？”

---

# 5. 六个 Case 的新增诊断目标

## Case 01 — Competitive Structure Shift

### 主要区分
- Knowledge：产品状态是否正确；
- Reasoning：competition ≠ similarity；
- Expression：能否先回答“谁最脆弱”；
- User：能否给出 watch priority。

### 典型回答差异

**A：**
> A 和 X 靶点最相似，因此 A 是最大竞品；B 次之；C 再次。

问题：
- 事实可能没错；
- 但把机制相似度直接当战略威胁；
- 缺少商业脆弱性、供应、支付、转换成本。

标签：
`RELATION_OVERSIMPLIFY / JUDGMENT_POOR`

**B：**
> B 才最危险，因为它的单 GLP-1 产品一定会被下一代双激动剂淘汰。

问题：
- 有非显然判断；
- 但“一定淘汰”属于 unsupported forecast；
- 高见建立在过度确定上。

标签：
`OVERCLAIM / FORECAST_OVERCONFIDENCE`

**C：**
> A 是最直接 clinical comparator，但 B 可能是战略上更脆弱的 incumbent；这一判断取决于 X 的疗效差异、价格、支付覆盖和供应能力。

为什么最好：
- 关系层次清楚；
- 证据边界清楚；
- 给出 flip conditions。

### 优化方向
若多个 Case 都出现“A 型回答”：
> 优化重点不是补更多事实，而是加入**关系层级 + 决策排序 preference data**。

---

## Case 02 — Regulatory Strategic Inflection

### 主要区分
- Knowledge：NDA accepted ≠ approval；
- Reasoning：风险构成如何变化；
- Expression：能否把“状态字段”转为“战略拐点”；
- User：下一步监控什么。

### 典型 failure

**事实正确但低价值：**
> NDA 已受理，目前尚未获批。

这是正确答案，但不够好。

用户真正需要：
> 临床失败风险下降，但监管执行/launch/支付/供应风险权重上升。

标签：
`FACTUALLY_CORRECT_BUT_DECISION_IRRELEVANT`

### 优化方向
如果模型经常只回答状态：
- preference data：奖励 “state → changed risk → next watch”；
- system/prompt：要求回答 “what changed / why it matters”；
- benchmark regression：固定 Regulatory Inflection cases。

---

## Case 03 — Licensing / BD

### 主要区分
- Knowledge：portfolio / deal history；
- Reasoning：marginal strategic value；
- Expression：能否直接给 partner ranking；
- User：能否支持 outreach。

### 典型 failure

**A 型：品牌偏见**
> Company A 最大、能力最强，所以最值得合作。

根因假设：
> 模型用“公司规模/知名度”shortcut 替代 strategic fit。

用户影响：
> BD 团队把时间花在低动机、高冲突对象上。

优化：
- hard negative：最强公司 ≠ 最优 partner；
- preference pairs：strategic need > company size；
- regression：internal-conflict variants。

---

## Case 04 — Investment Thesis

### 主要区分
- Knowledge：trial design / endpoints；
- Reasoning：clinical de-risking ≠ commercial de-risking；
- Expression：是否形成 IC-ready thesis；
- User：是否说明 kill criterion。

### 典型 failure

**高分数据崇拜**
> ORR 62% 高于 48%，说明 Asset Z 更有竞争力。

问题：
- 忽略 cross-trial comparability；
- 忽略 DOR / PFS / reimbursement / switching；
- 把“漂亮数据”直接转换成“高商业价值”。

共性体验问题：
`METRIC_SALIENCE_BIAS`

优化：
- counterexample data；
- 要求模型显式拆 “clinical / regulatory / commercial risk”；
- preference data 奖励 kill criteria。

---

## Case 05 — Safety Attribution

### 主要区分
- Knowledge：AE / warning / regulator；
- Reasoning：molecule vs platform vs target；
- Expression：风险层级是否清楚；
- User：portfolio 要做什么。

### 典型 failure

**过度安全化：**
> 同靶点两个资产出现肝毒性，因此是 class effect。

**过度保守：**
> 因果未证明，因此暂时无法得出任何结论。

两者都不好。

优秀答案：
> 不能确认 class effect，但现有 pattern 足以把 platform/target hypothesis 升级为 P0 验证任务。

共性能力：
> **decision under uncertainty**，而不只是 abstention。

优化：
- 训练“uncertain but actionable”答案；
- safety hypothesis discrimination data；
- negative-control examples。

---

## Case 06 — Temporal Watchlist

### 主要区分
- Knowledge：事件准确性；
- Reasoning：event → thesis update；
- Expression：能否一屏讲清 Top 3；
- User：是否减少信息负担。

### 典型 failure

**News summarizer behavior**
> 把 12 个 event 都总结一遍。

事实可能全部正确，但用户体验很差。

Failure：
`INFORMATION_OVERLOAD / PRIORITIZATION_FAILURE`

根因假设：
> 模型倾向 coverage maximization，而不是 decision compression。

优化：
- preference data：Top-K over exhaustive coverage；
- reward “changed thesis”；
- regression metric：Precision@K + User Useful Rate。

---

# 6. Cross-Case Failure Taxonomy（必须新增）

六个 Case 跑完以后，不按 Case 写六篇孤立报告，而是聚合成模型画像。

建议至少统计：

| Failure Cluster | 用户体验 | 可能根因 | 优化方向 |
|---|---|---|---|
| STALE_KNOWLEDGE | 状态过时，失去信任 | 内部知识 freshness 不足 | retrieval / temporal truth / regression |
| SOURCE_HIERARCHY | 新闻压过监管事实 | evidence role 不清 | source-aware data / hard negatives |
| OVERCLAIM | 看起来聪明但不可靠 | claim scope calibration 差 | preferred/rejected pairs |
| RELATION_SHORTCUT | shared target→竞品 | 结构推理 shortcut | graph-conditioned data |
| METRIC_SALIENCE_BIAS | 被漂亮数字误导 | 缺乏 experimental validity | counterexample / expert SFT |
| PRIORITIZATION_FAILURE | 信息很多但没结论 | coverage bias | Top-K preference |
| PASSIVE_ABSTENTION | 只会说“不知道” | uncertainty 无行动策略 | uncertain-but-actionable data |
| EXPRESSION_HIERARCHY | 正确但难用 | answer organization 差 | preference / response templates |
| AUDIENCE_MISMATCH | BD/VC/临床答案同质 | user conditioning 弱 | persona-conditioned data |
| FORECAST_OVERCONFIDENCE | 把可能写成必然 | uncertainty calibration 差 | calibration / negative examples |

---

# 7. Optimization Card（从个案到优化）

每个共性 failure 最终形成一个 Optimization Card：

```yaml
failure_cluster: PRIORITIZATION_FAILURE

observed_behavior:
  - case_01: 罗列全部竞品，没有排序
  - case_06: 总结 12 条事件，没有 Top 3

user_experience:
  - information overload
  - decision time not reduced

capability_gap_hypothesis:
  - model optimizes coverage over decision compression

intervention_candidates:
  - preference data: ranked concise answer > exhaustive list
  - prompt policy: executive judgment first
  - synthetic hard cases requiring Top-K
  - user-role conditioned answer template

success_metrics:
  - Precision@K
  - User Utility Score
  - Decision Compression score
  - regression pass rate

regression_cases:
  - C01
  - C06
```

---

# 8. 结果报告不再只写“哪个模型得分高”

最终报告必须回答四件事：

## 1. 哪个模型在哪些用户任务上更好？
不是总榜，而是 capability profile。

## 2. 为什么？
给出具体 bad case 和 expert diagnosis。

## 3. 用户会感受到什么差异？
例如：
- “模型 A 更像数据库”
- “模型 B 判断积极但容易越过证据边界”
- “模型 C 更适合 CI，但在 safety 上过度 abstain”

## 4. 应该怎样优化？
分别给：
- data intervention
- SFT / preference intervention
- prompt / product intervention
- retrieval / tool intervention
- regression set

---

# 9. 最终要证明的不是“我会做 Benchmark”

GroundSignal + Benchmark 最终应该证明：

> 我能利用生命科学/临床医药专业积累，定义什么是事实正确、什么是证据充分、什么是合理推理、什么是专业表达；能指出模型回答为什么好或不好；能把多个 bad case 聚类为稳定的模型体验问题，并把这些问题转化为数据、训练、Prompt、工具和回归评测的具体优化方案。

这才完整对应：

**专业领域专家 → 模型判断 → failure taxonomy → capability gap → optimization → regression。**
