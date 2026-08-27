# GroundSignal Pharma — Decision Intelligence + Model Diagnosis Benchmark v0.4
## Blind Decision Tasks · Counterfactual Twins · Hidden Expert Rubric

> 版本目标：不仅评估模型“答对没有”，还要利用专业领域积累，判断知识准确性、推理质量、表达水准和用户价值；进一步解释 failure 原因、归纳跨 Case 的共性体验问题，并形成可执行优化方向。
>
> **本版相较旧 v0.4 的关键修订：**
> 1. 不再用 Q1/Q2/Q3 逐步提示模型完成推理；
> 2. 模型只看到真实用户问题 + 原始/半结构化 Evidence Bundle；
> 3. Gold behavior、关键 trade-off、shortcut、flip condition 全部隐藏；
> 4. 每个 Case 增加 Counterfactual Twin，测试判断是否随关键变量正确变化；
> 5. 评估重点从“回答完整性”升级为“专业判断质量 + 决策敏感性 + 非显然洞察”。

---

# 1. Benchmark 的核心问题

GroundSignal 不应该只测：

> 模型能否从给定证据中复述正确事实？

而应该测：

> **模型能否像专业领域分析师一样，从复杂证据网络中主动识别真正影响决策的变量，形成有边界、有优先级、有反事实敏感性的高价值判断？**

因此：

```text
Raw / Semi-structured Evidence
        ↓
Model independently extracts relevant structure
        ↓
Decision Intelligence
        ↓
Expert Diagnosis
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
Regression
```

---

# 2. 三个 Track

## Track A — Closed-book
不给 GroundSignal evidence。

测：
- model internal knowledge；
- freshness；
- uncertainty；
- hallucination / overclaim。

## Track B — Frozen-grounded
给固定 evidence snapshot，但**不替模型总结答案特征**。

测：
- evidence extraction；
- relation reasoning；
- source role；
- professional judgment；
- decision synthesis。

## Track C — Live-grounded
GroundSignal 实时检索 / knowledge graph / temporal state 注入。

测：
- truth infrastructure；
- temporal validity；
- model + retrieval 整体能力；
- GroundSignal 自身 stale / evidence mismatch。

---

# 3. Visible / Hidden 严格分离

## 3.1 模型可见内容

每个 Case 只允许包含：

```yaml
user_role:
decision_context:
user_question:
evidence_bundle:
output_constraints:
```

其中 `evidence_bundle` 尽量接近用户真实会面对的材料：
- regulator record；
- trial registry；
- company disclosure；
- pipeline table；
- licensing announcement；
- safety report；
- historical thesis；
- event feed。

禁止在可见 prompt 中出现：
- “为什么 A 不能排第一？”
- “为什么 B 没同靶点资产是优势？”
- “注意 shared target ≠ competitor”
- “请识别 source hierarchy”
- “请讨论 negative control”
- “请给出 flip condition”

这些内容都属于 evaluator，不属于题目。

---

## 3.2 Hidden Evaluator

```yaml
hidden_evaluator:
  core_decision:
  must_notice:
  acceptable_conclusions:
  critical_tradeoffs:
  forbidden_shortcuts:
  critical_errors:
  flip_conditions:
  counterfactual_expectation:
  expert_rationale:
```

---

# 4. 四层 Expert Diagnosis

## A. Knowledge Quality

### A1 Factual Correctness
核心事实是否正确。

### A2 Temporal Freshness
是否使用当前有效状态。

### A3 Evidence Sufficiency
claim 与 evidence 是否匹配。

### A4 Source Hierarchy
是否理解监管/注册/公司/媒体各自证据角色。

### A5 Claim Scope
是否把 Phase III 阳性、NDA accepted、安全 signal 等升级成更强结论。

---

## B. Reasoning Quality

### B1 Relation Reasoning
是否区分结构邻近、机制邻近、市场竞争和商业竞争。

### B2 Structural / Causal Reasoning
是否解释“为什么”，而非只做相关性拼接。

### B3 Evidence Integration
是否主动整合多源证据，而不是逐条摘要。

### B4 Counterfactual Sensitivity
关键变量改变后，判断是否正确更新。

### B5 Prioritization
是否把大量信息压缩成 1–3 个关键判断。

### B6 Uncertainty / Abstention
证据不足时是否正确降级。

### B7 Decision Leverage
是否能识别下一条最有信息价值的证据或最高杠杆行动。

---

## C. Expression Quality

### C1 Decision-first
先给判断，再给依据。

### C2 Information Hierarchy
核心结论、依据、风险、下一步层次清楚。

### C3 Precision of Language
使用“支持 / 提示 / 不能证明 / 假设 / 已验证”等精确语言。

### C4 Information Density
不堆背景，不重复。

### C5 Audience Fit
BD / VC / CI / 临床 / 管理层答案结构不同。

### C6 Calibrated Caveats
不确定性服务于决策，而非机械 disclaimer。

---

## D. User Utility

### D1 Decision Fit
是否直接解决用户要做的决定。

### D2 Defensibility
用户能否带进会议并回答“凭什么”。

### D3 Actionability
是否能转成下一步工作。

### D4 Non-obvious Insight
是否形成需要跨节点/跨证据综合才能得到的洞察。

### D5 Value / Risk Asymmetry
是否识别表面不明显的受益者、受损者、机会或脆弱点。

---

# 5. Judgment Value Score（0–14）

只有 A 层 Gate 通过后才评。

| 维度 | 0 | 1 | 2 |
|---|---|---|---|
| J1 Decision Compression | 资料堆砌 | 有结论但分散 | 1–3 个核心判断 |
| J2 Non-obvious Insight | 复述事实 | 轻度综合 | 跨节点得出非显然洞察 |
| J3 Structural Reasoning | 相关性 | 表层理由 | 结构机制 + 约束 |
| J4 Second-order Impact | 事件本身 | 一阶影响 | 影响传播链 |
| J5 Counterfactual Quality | 静态结论 | 泛化风险 | 明确翻转条件 |
| J6 Decision Leverage | 无行动 | 泛化行动 | 最高信息价值/最高杠杆动作 |
| J7 Value/Risk Asymmetry | 平均化比较 | 有排序 | 指出非对称价值 |

- 13–14：Executive-grade Intelligence
- 10–12：Strong Analyst Intelligence
- 7–9：Useful but conventional
- 4–6：Knowledge-rich, judgment-poor
- 0–3：Information retrieval only

---

# 6. Case 01 — Competitive Structure Shift

```yaml
case_id: C01
track: B
user_role: Pharma Strategy / Competitive Intelligence
primary_capabilities:
  - strategic_vulnerability
  - commercial_vs_mechanistic_competition
  - second_order_impact
  - counterfactual_sensitivity
```

## Visible Task

### User question

> 我们在评估一个新的减重 Asset X。不要给我竞品清单。  
> 我想知道：**如果 X 成功上市，谁的竞争地位最可能被重新定价？谁表面上最像竞品，但实际未必最脆弱？请给出你最重要的判断、依据，以及最值得优先补的一条信息。**

### Evidence Bundle

- Asset X：GLP-1R/GIPR，Phase III；肥胖；主要终点阳性；尚未申报上市。
- Asset A：GLP-1R/GIPR；肥胖；已上市。
- Asset B：GLP-1R 单激动剂；肥胖；已上市；品牌和支付覆盖强。
- Asset C：GLP-1R/GCGR；肥胖；Phase III。
- Company A：供应能力强，支付覆盖成熟。
- Company B：商业渠道强，但核心减重产品机制相对单一。
- Company C：pipeline 较新，商业化资源较弱。
- 无 X 对 A/B/C 的 head-to-head。
- X 的价格、医保、供应未公开。

### Output Constraint

最多 500 字：
1. Executive Judgment
2. Why
3. What could change your view
4. Highest-value next evidence

## Hidden Evaluator

### Must notice
- mechanism similarity ≠ strategic vulnerability；
- A 是最直接 clinical comparator，但商业护城河较强；
- B 可能比表面更脆弱；
- price / payer / supply 是关键 flip variables。

### Forbidden shortcuts
- shared target → biggest threat；
- “双激动剂一定淘汰单激动剂”；
- 没头对头却声称优效。

### Counterfactual Twin C01-B
唯一改变：
- X 获批后价格低 30%；
- payer coverage 与 B 接近；
- supply 充足。

Expected:
- B 的战略脆弱性应明显上调。

### Counterfactual Twin C01-C
唯一改变：
- X 疗效优秀，但供应严重受限、coverage 差。

Expected:
- 商业冲击判断应明显下调；
- clinical competitiveness 与 commercial threat 分离。

---

# 7. Case 02 — Regulatory Inflection

```yaml
case_id: C02
track: B
user_role: Strategy / BD / Regulatory Intelligence
primary_capabilities:
  - state_transition_reasoning
  - risk_decomposition
  - source_role
  - strategic_inflection
```

## Visible Task

### User question

> Asset R 的 NDA 已受理。管理层问我：“这条信息除了‘还没获批’之外，到底改变了什么？”  
> 请告诉我：**我们的风险判断、竞争监控和商业准备应该怎样变化？**

### Evidence Bundle

- Regulator：NDA accepted / under review。
- Pivotal Phase III：completed。
- 公司近 3 个月开始扩产。
- 新增 commercial / market access 招聘。
- 无 regulator approval record。
- Competitor A 已上市。
- Competitor B Phase III。
- price / reimbursement unknown。

### Output Constraint
最多 500 字，必须：
- 明确“什么改变了”；
- 明确“什么没有改变”；
- 指出下一条最高价值 evidence。

## Hidden Evaluator

### Must notice
- clinical execution risk 下降；
- regulatory / launch / payer / supply risk 权重上升；
- expansion/hiring 是行为一致性证据，不是 approval evidence；
- intelligence 应从 clinical readout 转向 label / approval / launch readiness。

### Forbidden shortcut
- NDA accepted = high probability approval；
- expansion/hiring = approval proof。

### Twin C02-B
新增：
- review 延期 6 个月。

Expected:
- time-to-market / launch assumptions 下调；
- 但不等于 efficacy thesis 被推翻。

### Twin C02-C
新增：
- 获批，但 label 明显窄于申请范围。

Expected:
- regulatory success 与 commercial upside 分离。

---

# 8. Case 03 — Licensing / BD

```yaml
case_id: C03
track: B
user_role: BD Lead
primary_capabilities:
  - marginal_strategic_value
  - internal_conflict
  - bargaining_asymmetry
  - partner_prioritization
```

## Visible Task

### User question

> Asset Y 要做 ex-China licensing。我们只能先和两家公司进入实质沟通。  
> **A、B、C 你选哪两家？哪一家看起来最强但其实最可能浪费我们的时间？为什么？你最想在 outreach 前补哪一条信息？**

### Evidence Bundle

#### Asset Y
- Target T ADC，Phase II。
- 希望保留中国权益。
- 需要海外 pivotal development + commercialization。

#### Company A
- 全球肿瘤商业化能力极强。
- 自研同 Target T Phase III。
- ADC 经验强。
- 多笔大型 licensing。
- 交易谈判能力强。

#### Company B
- 无 Target T 内部资产。
- 有同适应症 franchise。
- 过去 3 年持续 in-license ADC。
- 有 ex-China / co-development precedent。
- 商业化能力中上。

#### Company C
- 现金多。
- oncology footprint 较弱。
- 无成熟 ADC 平台。
- licensing appetite 不明确。

### Output Constraint
必须给：
- Top 2；
- “最容易浪费时间”的对象；
- 1 个最高价值 diligence question。

## Hidden Evaluator

### Must notice
- partner quality ≠ company size；
- B 的 marginal strategic value 可能最高；
- A 有 internal conflict + bargaining asymmetry；
- historical licensing appetite ≠ current intent。

### Shortcut probes
- brand/size salience；
- cash = partner quality；
- deal history = current intent。

### Twin C03-B
唯一改变：
- A 的同 Target T Phase III 项目因 futility terminated。

Expected:
- A 排名应明显上升。

### Twin C03-C
唯一改变：
- B 刚刚 in-license 另一同 Target T ADC。

Expected:
- B strategic gap 减少，优先级应下降。

---

# 9. Case 04 — Investment Thesis

```yaml
case_id: C04
track: B
user_role: Healthcare VC / PE / IC
primary_capabilities:
  - evidence_sufficiency
  - cross_trial_validity
  - clinical_vs_commercial_derisking
  - falsification
```

## Visible Task

### User question

> Asset Z 最新 ORR 62%，竞品历史数据 48%。市场都说“best-in-class”。  
> **如果明天上投委会，这组数据究竟改变了什么？值不值得提高我们对资产的估值或 conviction？最可能推翻当前乐观叙事的证据是什么？**

### Evidence Bundle

- Z：Phase I/II；single-arm；n=58；ORR 62%。
- selected population。
- median follow-up 7 months。
- incumbent published ORR 48%。
- incumbent：不同 line / eligibility；follow-up 18 months。
- exploratory biomarker subgroup 更高。
- 无 randomized comparator。
- safety 尚可但成熟度不足。
- market crowded。
- incumbent 已 reimbursed。

### Output Constraint
输出：
- Thesis update；
- What is de-risked；
- What is not；
- Kill / falsification criterion。

## Hidden Evaluator

### Must notice
- clinical de-risking ≠ commercial de-risking；
- cross-trial ORR 不可直接证明 superiority；
- crowded market 中 switching / DOR / PFS / safety / access 重要；
- kill criterion 比“继续观察”更有价值。

### Twin C04-B
唯一改变：
- ORR 58%，但 DOR 显著更长且成熟。

Expected:
- 可能比单纯 62% ORR 更有价值。

### Twin C04-C
唯一改变：
- biomarker subgroup 在独立较大 cohort 复现。

Expected:
- differentiated positioning 上调；
- 但仍不能自动叫 best-in-class。

---

# 10. Case 05 — Safety Attribution

```yaml
case_id: C05
track: B
user_role: Clinical Development / Safety / Portfolio Strategy
primary_capabilities:
  - causal_structure
  - negative_control
  - hypothesis_discrimination
  - uncertain_but_actionable
```

## Visible Task

### User question

> Asset S 出现严重肝毒性。A 是同靶点，也有类似 warning；B 同靶点但没有。  
> **我们现在最应该把风险归到 molecule、platform 还是 target？这个判断会怎样影响 portfolio 决策？下一步哪条证据最有区分力？**

### Evidence Bundle

- S：数例严重 hepatic event。
- A：同 target；不同 molecule；有 hepatic warning。
- B：同 target；较大暴露；无同类 warning。
- S 与 A 有相似 linker / delivery chemistry。
- B 使用不同 modality。
- spontaneous report 有 signal。
- mechanism hypothesis 未验证。
- 无 regulator class-wide warning。

### Output Constraint
必须：
- 排序至少 2 个 causal hypotheses；
- 指出 negative control；
- 给 portfolio action；
- 给 discriminating evidence。

## Hidden Evaluator

### Must notice
- B 是关键 negative control；
- 当前更支持 platform/modality hypothesis，而非直接 target-wide class effect；
- “不能确认”不等于“不行动”。

### Forbidden shortcuts
- two same-target events = class effect；
- no confirmed causality = do nothing。

### Twin C05-B
新增：
- B 也出现一致 hepatic signal。

Expected:
- target-level hypothesis 显著上调。

### Twin C05-C
新增：
- A 的 warning 被证明来自特异 off-target metabolite。

Expected:
- platform/target inference 下调，S-specific hypothesis 上调。

---

# 11. Case 06 — Temporal Watchlist / Belief Updating

```yaml
case_id: C06
track: B
user_role: CEO / Strategy / Competitive Intelligence
primary_capabilities:
  - change_of_belief
  - deduplication
  - second_order_propagation
  - decision_compression
```

## Visible Task

### User question

> 过去 30 天我们抓到 12 条相关信息。我不需要新闻摘要。  
> **只告诉我：哪三个我们原来相信的判断已经失效或必须重估？哪一个变化对未来 6–12 个月最重要？**

### Existing Theses
- T1：Asset Q 仍是潜在扩适应症竞争者。
- T2：Asset R pivotal development 按计划推进。
- T3：Asset T 缺少海外商业化 partner。
- T4：Company K 独立运营。
- T5：赛道竞争强度稳定。

### Event Bundle
- E1：Regulator 正式批准 Asset Q 新适应症。
- E2：公司新闻稿重复 E1。
- E3：Asset R pivotal trial = TERMINATED。
- E4：行业媒体重复 E3。
- E5：Company M / N 签 Asset T 区域授权。
- E6：探索性 subgroup 更新。
- E7：旧产能计划重申。
- E8：2024 旧批准新闻 repost。
- E9：分析师猜测 Company K 可能被收购。
- E10：新 CFO。
- E11：重申年度指引。
- E12：综述。

### Output Constraint
最多 400 字：
- 3 个 thesis update；
- Top 1 strategic change；
- 1 个二阶影响；
- 1 个 weak signal。

## Hidden Evaluator

### Must notice
- T1/T2/T3 失效或需重估；
- E2/E4 是重复传播；
- E9 只能保留 lead；
- watchlist 单位应是 belief update，不是 event count。

### Twin C06-B
新增：
- E3 终止原因是非 efficacy 的 sponsor portfolio reprioritization。

Expected:
- R 的 development path 受损，但不能直接推断 efficacy failure。

### Twin C06-C
新增：
- E5 licensing 仅为很小区域、无开发权。

Expected:
- T3 更新幅度比原版小。

---

# 12. Counterfactual Pair Metrics

除了普通 rubric，新增：

## 12.1 Decision Sensitivity
关键变量改变时，结论是否在正确方向变化。

```text
DS = correct_direction_updates / expected_updates
```

## 12.2 Invariance Discipline
不相关变量变化时，模型是否保持不该变化的判断稳定。

## 12.3 Flip Calibration
当 evidence 足以改变结论时是否敢改；
当 evidence 不足时是否避免过度翻转。

## 12.4 Explanation Consistency
结论变化是否与新增证据存在明确因果/结构解释。

---

# 13. Cross-case Failure Taxonomy

| Failure Cluster | 表现 | 用户体验 | 可能根因 | 优化 |
|---|---|---|---|---|
| STALE_KNOWLEDGE | 状态过时 | 信任崩溃 | freshness | retrieval / temporal data |
| SOURCE_HIERARCHY | 弱源压过强源 | 事实失真 | evidence-role 弱 | source-aware data |
| OVERCLAIM | 高见越界 | 看似聪明但危险 | calibration | preference negatives |
| RELATION_SHORTCUT | 相似=竞争 | 战略排序错 | shortcut | graph-conditioned data |
| BRAND_SALIENCE | 大公司=好 partner | BD 资源浪费 | salience bias | hard negatives |
| METRIC_SALIENCE | 高数字=高价值 | 投资判断偏差 | experimental validity | counterexamples |
| PASSIVE_ABSTENTION | 只说不知道 | 无法行动 | uncertainty policy | uncertain-but-actionable |
| PRIORITIZATION_FAILURE | 全部都讲 | 信息过载 | coverage bias | Top-K preference |
| COUNTERFACTUAL_RIGIDITY | 条件变了结论不变 | 模板化 | shallow reasoning | paired twins |
| OVER-SENSITIVITY | 小变量导致大翻转 | 不稳定 | poor calibration | invariance regression |
| AUDIENCE_MISMATCH | 所有人同一种答案 | 难用 | user conditioning 弱 | persona-conditioned data |
| EXPRESSION_HIERARCHY | 正确但没有重点 | 会议不可用 | organization | preference / templates |

---

# 14. Expert Diagnosis Output

每个模型回答都必须生成：

```yaml
case_id:
response_id:

quality:
  knowledge:
  reasoning:
  expression:
  user_utility:
  judgment_value:

observed_failures:
  - behavior:
    evidence:
    severity:
    user_impact:

capability_gap_hypotheses:
  - hypothesis:
    confidence:
    supporting_cases:

counterfactual_behavior:
  expected_change:
  observed_change:
  sensitivity_score:

optimization_candidates:
  - type: data | SFT | preference | prompt | retrieval | tool
    intervention:
    target_failure:

regression:
  cases:
```

---

# 15. Optimization Card

示例：

```yaml
failure_cluster: BRAND_SALIENCE

observed:
  - C03-A: model ranks A first because "largest pharma"
  - C03-B: A internal asset terminates, ranking barely changes

user_impact:
  - BD effort allocated to strategically conflicted partner
  - bargaining asymmetry underestimated

capability_gap_hypothesis:
  - model substitutes company strength for marginal strategic fit

interventions:
  - hard negative pairs: strongest company != best partner
  - preference data rewarding strategic need / internal conflict reasoning
  - counterfactual twins on portfolio conflict
  - explicit graph features for competing internal assets

success_metrics:
  - C03 Decision Sensitivity
  - partner-ranking accuracy
  - expert preference win rate
```

---

# 16. 最终报告不做简单总榜

报告必须回答：

1. **哪个模型在哪类专业任务上更好？**
2. **具体好在哪里、差在哪里？**
3. **用户实际会感受到什么差异？**
4. **哪些 failure 是单例，哪些已形成跨 Case pattern？**
5. **最可能的 capability gap 是什么？**
6. **应该用什么数据/训练/产品/检索手段优化？**
7. **优化后用哪些 counterfactual regression 验证？**

不允许只写：

> Model A 92，Model B 89。

---

# 17. Benchmark 是否“有效”的判据

Benchmark 自己也要过 Validity Gate：

## V1 Observability
题目是否提供足够证据支持专业判断。

## V2 Non-leading
题目是否没有提前泄露 gold 的推理骨架。

## V3 Shortcut Resistance
是否存在真实但错误的显著 shortcut。

## V4 Frontier Discrimination
至少一部分题应能区分：
- Knowledge-rich / Judgment-poor；
- Insightful but Overclaimed；
- Decision-ready。

## V5 Counterfactual Sensitivity
关键变量变化时，gold 应发生可解释变化。

## V6 User Relevance
真实专业用户是否认为这个决策值得花时间。

## V7 Gold Robustness
专家对核心判断/可接受答案是否有足够一致性。

---

# 18. 当前版本的核心定位

GroundSignal Benchmark 不再是：

> “把医药知识整理好，然后问模型几个问题。”

而是：

> **构造真实专业用户的高价值决策环境，让模型在不被提示推理路径的情况下独立完成 evidence extraction → structural reasoning → judgment → prioritization → action；再由领域专家判断回答的知识、推理、表达和用户价值，并把失败归纳为可优化的模型能力问题。**

最终要证明的能力链是：

```text
专业积累
→ 定义高价值用户问题
→ 定义优秀答案
→ 设计非 leading 的专业评测
→ 识别模型真实 failure
→ 解释 failure 原因
→ 聚类共性体验问题
→ 设计优化数据 / preference / prompt / retrieval
→ counterfactual regression
```

这才完整对应专业领域模型数据策略 / Eval / Data Product 岗位。
