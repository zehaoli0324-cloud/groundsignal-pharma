# S5 家族扩展蓝图：12 → 24 开发场景

> **文档性质**：扩展规划。**不含伪造病例内容。** 仅做覆盖缺口分析与家族结构规划。
> **创建日期**：2026-09-13
> **依据**：`medical/case-families/*/manifest.json` 实测统计、`medical/patient-eval/STAGE_DECOMPOSITION.md` 第 208 行、`S5_V0.1_EVAL_SPEC.md` 门槛定义
> **口径**：新家族的**医学内容必须由临床审核产生**，本文只给出结构、覆盖目标与验收门槛。

---

## 1. 目标与现状

| 项 | 现状 | 目标 | 缺口 |
|---|---|---|---|
| 开发病例族 | 12 | 24 | **12** |
| 病例总数 | 60（5/族） | 120 | **60** |
| 家族状态 | 12/12 `gold_review_needed` | 至少全部 `eval_ready` 或明确 `not_required` | — |

**结构契约**（`S5_V0.1_EVAL_SPEC.md` v0.1 release gates 第 2 条）：
每族 = **3 development + 1 regression + 1 held-out**，共 5 例。

**验证器现状**（实测）：
```
$ ~/venvs/m1env/bin/python scripts/validate_medical_case_families.py
families=12 cases=60
... 12 族全部 "OK?" ...
VALIDATION PASSED
```
> 注意：验证器输出前缀为 `OK?`（带问号），表示"结构校验通过"，**不等于**临床准入。

---

## 2. 现有 12 族的能力覆盖（实测统计）

### 2.1 task_type 分布

| task_type | 家族数 | 家族 |
|---|---|---|
| `medical_qa` | 4 | EVIDENCE-002/003、TRIAGE-001/003 |
| `clinical_reasoning` | 2 | CLINREASON-001/005 |
| `medication_safety` | 2 | MEDSAFE-001/002 |
| `report_interpretation` | 2 | REPORT-001/004 |
| `agent` | 1 | AGENT-001 |
| `multi_turn` | 1 | MULTITURN-001 |

### 2.2 覆盖薄弱的 task_type

| task_type | 现状 | 建议新增 |
|---|---|---|
| `agent` | 1 族 | **+2**（工具链是 S2/S6 的核心战场，仅 1 族不足） |
| `multi_turn` | 1 族 | **+2**（S6 多轮交互是主战场，仅 1 族不足） |
| `medication_safety` | 2 族 | +1 |
| `report_interpretation` | 2 族 | +1 |
| `clinical_reasoning` | 2 族 | +2 |
| `medical_qa` | 4 族 | 保持（已充足） |

### 2.3 失败假设覆盖（实测，Top 频次）

高频（≥3 族已覆盖）：`METRIC_SALIENCE_BIAS`(3)、`OVERCLAIM`(3)、`FAILURE_TO_CLARIFY`(3)、`PREMATURE_DIAGNOSIS`(3)、`FALSE_REASSURANCE`(3)

**仅 1 族覆盖的失败假设**（新家族应优先补）：
- 工具类：`NO_TOOL_BEFORE_HIGH_RISK_CLAIM`、`BAD_TOOL_SELECTION`、`BAD_QUERY`、`STALE_RETRIEVAL`、`TOOL_RESULT_IGNORED`、`OVERSEARCH`
- 时间类：`STALE_GUIDELINE`、`STATE_STALENESS`
- 安全类：`UNSAFE_RECOMMENDATION`、`UNSAFE_REASSURANCE`、`FAILURE_TO_ESCALATE`
- 交互类：`USER_PRESSURE_CAPITULATION`、`UNCERTAINTY_COLLAPSE`、`RECOMMENDATION_DROP`
- 来源类：`SOURCE_HIERARCHY`、`RELATION_SHORTCUT`

### 2.4 能力覆盖仅 1 族的项（实测 50 项能力中的薄弱项）

`tool_selection`、`query_formulation`、`source_hierarchy`、`temporal_retrieval`、`tool_result_utilization`、`stop_correctness`、`temporal_truth`、`guideline_versioning`、`state_tracking`、`multi_turn_clarification`、`recommendation_preservation`、`patient_communication`、`audience_adaptation` 等

> **观察**：Agent / 多轮 / 时间性 三类能力大量处于"仅 1 族覆盖"状态，与 `STAGE_DECOMPOSITION.md` 中 S2（来源路由）、S6（多轮）被列为重点的阶段定位不完全匹配。

---

## 3. 建议新增 12 族规划（结构层）

| # | 建议 family_id | task_type | 主攻能力 | 主攻失败假设 | 优先级依据 |
|---|---|---|---|---|---|
| N1 | `AGENT-002` | agent | `tool_result_utilization`、`stop_correctness` | `TOOL_RESULT_IGNORED`、`OVERSEARCH` | agent 仅 1 族，工具利用是 S6 核心 |
| N2 | `AGENT-003` | agent | `source_hierarchy`、`temporal_retrieval` | `STALE_RETRIEVAL`、`SOURCE_HIERARCHY` | S2 来源路由仅 1 族 |
| N3 | `MULTITURN-002` | multi_turn | `state_tracking`、`recommendation_preservation` | `STATE_STALENESS`、`RECOMMENDATION_DROP` | 多轮仅 1 族，状态维护是 S6.2 门槛 |
| N4 | `MULTITURN-003` | multi_turn | `multi_turn_clarification`、`uncertainty_preservation` | `USER_PRESSURE_CAPITULATION`、`UNCERTAINTY_COLLAPSE` | 抗压是 S7 关注点，仅 1 族 |
| N5 | `MEDSAFE-003` | medication_safety | `drug_interaction_reasoning`、`bleeding_safety` | `UNSAFE_RECOMMENDATION` | 用药安全可扩展，覆盖不足 |
| N6 | `MEDSAFE-004` | medication_safety | `medication_context`、`class_reasoning` | `MEDICATION_BLINDNESS`、`FALSE_REASSURANCE` | 同上 |
| N7 | `CLINREASON-002` | clinical_reasoning | `differential_reasoning`、`discriminative_test_selection` | `PREMATURE_CLOSURE`、`SINGLE_CAUSE_BIAS` | 鉴别诊断仅 1 族 |
| N8 | `CLINREASON-003` | clinical_reasoning | `causal_hypothesis_ranking`、`confound_awareness` | `CONFOUND_IGNORANCE`、`RELATION_SHORTCUT` | 因果/混杂仅 1 族 |
| N9 | `REPORT-002` | report_interpretation | `temporal_truth`、`guideline_versioning` | `STALE_GUIDELINE`、`FACT_UPGRADE` | 时间真值覆盖薄弱（S3/S4 重点） |
| N10 | `REPORT-003` | report_interpretation | `evidence_sufficiency`、`claim_scope_calibration` | `OVERCLAIM`、`CROSS_TRIAL_OVERCLAIM` | 证据充分性仅 2 族 |
| N11 | `EVIDENCE-004` | medical_qa | `threshold_reasoning`、`metric_salience_resistance` | `THRESHOLD_BLUR`、`METRIC_SALIENCE_BIAS` | 阈值推理是已知弱点 |
| N12 | `CLINREASON-006` | clinical_reasoning | `multi_feature_integration`、`uncertainty_calibration` | `PREMATURE_DIAGNOSIS`、`ANCHORING` | 多特征整合仅 1 族 |

> **本表为结构规划**。每个新家族的**具体病例、证据、图谱与 clinical gold 必须由临床审核产生**，不得由本蓝图直接生成。

---

## 4. 每族的验收门槛（`S5_V0.1_EVAL_SPEC.md` v0.1 gates）

新增家族必须逐条满足：

| # | Gate | 要求 | 阻断级别 |
|---|---|---|---|
| 1 | P0 materialization | 12（→24）族、60（→120）cases、5 例/族、rubric `medical-clinical-v0.2` | — |
| 2 | Family composition | 每族恰好 3 dev + 1 regression + 1 held-out | — |
| 3 | Held-out policy metadata | 每族声明非空 leakage rule + held-out variable(s) | — |
| 4 | Difficulty metadata | 每族 ≥4 target capabilities + ≥4 failure hypotheses | — |
| 5 | Split provenance binding | `family_id`/`split` 必须是**已材料化 case 的 schema 绑定属性**，不能只写在 manifest | **HARD GATE** |
| 6 | Training-export held-out guard | `split=heldout` 的 case 即使 training candidate 已批准，也必须被导出路径拒绝 | **HARD GATE** |
| 7 | Gold readiness | release-grade suite 需显式 `gold_approved`；`gold_review_needed` **不得静默升级** | **HARD GATE** |
| 8 | Decision-node contract | case schema 必须要求 `graph_eval`；graph contract 必须要求 `required_node_ids`/`required_edge_ids`/`expected_reasoning_path` | **HARD GATE** |
| 9 | Prompt gold-leakage probe | 只在 `expected_behavior`/`graph_eval`/`safety`/`scoring` 的 sentinel 不得出现在模型可见 prompt | — |

**Decision rule**（原文）：gate 5–8 任一失败 → 阻断 S5 release，且下游组件不得自动把 `heldout`/`regression` 标签当作 release-grade 分区。**平均百分比不能覆盖这些硬门。**

---

## 5. "扩展 ≠ 完成"：必须避免的三个陷阱

依据 `STAGE_DECOMPOSITION.md` S5 可测缺陷列：

1. **同家族被当多个独立样本**（S5.1）——通过"只增加文字长度"凑数不算扩展
2. **案例自证可信 / 已暴露测试重命名为全新**（S5.3）——新家族必须是**新建**的，不能把已暴露的改个名
3. **开发检查通过被误当研究放行**（S5.4）——结构合规 ≠ 临床准入

另据 `S5_INTEGRATION_STATUS.md`：**"本轮 12 合成场景仅开发，不冒充 24 开发场景或 72 研究家族已完成。"**

---

## 6. 工作量与依赖

| 步骤 | 依赖 | 可否现在做 |
|---|---|---|
| 结构层：12 个 manifest 骨架 | 无 | ✅ 可（但不含临床内容） |
| 证据层：每族 evidence.json + graph.json | 医学来源 | 🔴 需来源审核 |
| 病例层：每族 5 例 JSON | **临床设计** | 🔴 需临床人力 |
| 准入层：解除 `gold_review_needed` | **临床审核** | 🔴 需临床人力 |

**结论**：扩展 12→24 的**结构骨架可立即产出**，但**病例内容与准入全部依赖临床审核**——与 `BENCHMARK_GAP_MATRIX.md` 的关键路径判定一致。

---

## 7. 验证边界

- 本文为**规划文档**，未创建任何新家族、未写入任何病例内容、未改动现有 12 族。
- 覆盖统计来自实测（`validate_medical_case_families.py` 输出 + manifest 解析），非估算。
- 新增家族的 family_id 与能力映射为**建议**，需在实施前由作者确认。
- 未伪造任何 clinical gold、评分或准入状态。
