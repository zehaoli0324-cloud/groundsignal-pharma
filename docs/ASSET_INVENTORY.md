# GroundSignal Pharma 资产盘点报告

> **文档性质**：工程资产盘点，非临床验证、非发布声明。
> **盘点日期**：2026-09-13
> **盘点基准**：`863db9b`（"Publish deidentified patient-evaluation pilot v0.1 (#18)"，2026-09-10）
> **核实方式**：实地读取文件、运行测试、复算 SHA。每条结论标注来源路径。
> **口径声明**：状态列以文件自述（文件内 `status`/`review`/`VERSION` 字段）为准，**未逐条人工确认**。凡文件自述含"needed"/"pending"/"BLOCKED"的，一律照实记录为未完成。

---

## 0. 一句话现状

平台工程已建设到 **S5 v0.9.1 canonical freeze**（十阶段中的第五阶段），S2–S5 有可运行代码与真实测试；但**十二个病例族全部为 `gold_review_needed`，无一条临床金标准，零真实模型调用**。工程成熟度远高于科研成熟度。

---

## 1. 仓库结构总览

```
groundsignal-pharma/
├── medical/patient-eval/      ← 患者评测主力子系统（S1–S10 十阶段）
├── medical/case-families/     ← 12 个病例族（全部 gold_review_needed）
├── medical/stage-evals/       ← 各阶段 eval 记录（仅 S2/S3/S4/S5 有内容）
├── medical/truth-layer/       ← S3 时间真值产物
├── medical/evaluation/        ← 评分契约（rubric）
├── medical/schemas/           ← 数据契约 schema
├── benchmark/                 ← 决策智能 benchmark（v0.1–v0.4）+ rubrics
├── scripts/                   ← 158 个 .py（S2–S5 全链路 + patient_eval 包）
├── tests/patient_eval/        ← 18 文件 / 217 测试
├── docs/taskbooks/            ← 任务书（master v1.2 / multiturn v1.1 / lit-addendum v1.3）
├── docs/handoffs/             ← 交接文档
├── posttrain/                 ← 训练数据 schema（SFT/preference/judge-label/trajectory）
└── patient_bench/             ← 早期提案（本地未跟踪；开发已迁至 integration 仓库）
```

**注意**：`patient_bench/` 在本地为未跟踪目录。其 `docs/PROPOSAL.md` 第 132 行明确说明该扩展的开发已迁移到 `~/projects/groundsignal-patient-integration`，原目录保留历史。

---

## 2. 四类核心资产盘点

### 2.1 Rubric（判据契约）

| 文件 | 版本 ID | 用途 | 状态 |
|---|---|---|---|
| `medical/evaluation/rubrics/medical-clinical-v0.2.md` | `medical-clinical-v0.2` | 核心医疗评测契约。9 维度组，0/1/2 三档，critical_error 覆盖均分 | 自述"frozen for P0 12-family/60-case build" |
| `medical/patient-eval/pilot/v0.2/suite.json` | `patient-pilot-rubric/v0.2` | 患者试评评分规则（**current**） | 已冻结 |
| `medical/patient-eval/REVIEW_V0.3.md` | `patient-review/v0.3` | 评审**存储**版本（≠ 评分规则版本） | 已冻结 |
| `medical/patient-eval/development/manual-transcript.example.json` | `development-mechanical-v0.1` | 机械检查规则 | 已冻结 |
| `benchmark/rubrics/judgment-value-rubric.md` | J1–J7 | 决策判断价值评分（决策智能 benchmark） | 已冻结 |
| `benchmark/rubrics/user-utility-rubric.md` | U1–U5 | 用户效用评分 | 已冻结 |
| `benchmark/rubrics/bd-answer-rubric.md` | — | BD 回答评分 | 已冻结 |
| `benchmark/diagnostics/expert-diagnosis-rubric.md` | — | 专家诊断 rubric | 已冻结 |
| `patient_bench/cases/demo-abdominal.json` | `patient-consultation-0.1.0-draft` | 患者咨询 rubric（7 维度 + 3 critical_errors） | **draft** |

**关键区分**（`REVIEW_V0.3.md` 第 140 行）：临床评分规则版本 = `patient-pilot-rubric/v0.2`；评审存储版本 = `patient-review/v0.3`。两者作用不同，**不能混用**。

**medical-clinical-v0.2 的九个维度组**：
1. 核心最终答案（8 项：事实正确性/证据充分性/时态有效性/临床推理/不确定性校准/任务有用性/沟通/安全性）
2. 知识图谱 grounding（必需节点召回/必需边召回/无支撑边率/证据链接精度/路径有效性/时态图准确性）
3. 检索 RAG（Evidence Recall@K / Critical Passage Recall@K / Precision@K / 当前版本召回 / 来源层级 / 矛盾取代召回）
4. Agent 轨迹（9 项）
5. 多轮（关键槽收集/状态跟踪/纠错传播/信念更新/抗压/澄清→作答过渡）
6. 病例族一致性（边界一致性/反事实敏感性/干扰不变性/弃权保持/留出泛化）
7. 关键医疗安全门（预注册全局类）
8. 人/评委协议
9. 状态边界（冻结契约 ≠ 已获临床复核）

---

### 2.2 Oracle / Truth（真值层）

**truth-ledger（事实状态账本）—— 已建成**

| 项 | 内容 |
|---|---|
| 实现 | `scripts/s4_truth_ledger_v01.py` → `scripts/s4_truth_ledger_v011.py` |
| 版本 | `S4-truth-ledger-v0.1.1`（`s4_truth_ledger_v011.py` 第 13 行） |
| 定义 | 事实版本、冲突、替换、溯源、回滚的更新层（`medical/stage-evals/S4/S4_V0.1_FRESH_FAIL_REPORT.md` 第 13 行） |
| 评测结果 | 首次独立 fresh 18/20 FAIL → 修复后旧 fresh 回归 20/20 + 新 independent fresh 20/20 |
| CI | `.github/workflows/s4-v01-truth-ledger-dev.yml`（跑评估器 + `diff -u` 校验可复现性） |
| 产物 | `medical/truth-layer/`、`medical/stage-evals/S4/s4-truth-ledger-dev-v0.1.json`、`s4-truth-ledger-fresh-heldout-v0.1.json` |

**Oracle（临床参考/可接受处置集合）—— 仅有提案级**

- 主力 `medical/patient-eval/` 子系统**无显式 oracle 概念**，临床真值以 rubric + 判据 + 人工判定承载（`medical/patient-eval/README.md` 第 37 行）。
- 显式 oracle 仅存在于 `patient_bench/`：`cases/demo-abdominal.json` 第 33–44 行一个 `oracle` 对象，`status: "DRAFT_REQUIRES_CLINICAL_REVIEW"`。
- 相关策略文件：`groundsignal-patient-integration/benchmark/patient-consultation-v1/oracle-policy.json`。
- **全仓库无独立 `*oracle*` 文件名**（按文件名检索返回 0）。

**金标准状态**（客观字段，非判断）：
- `gold_approved=false` —— 案例没有获得专家确认的标准答案资格（`S5_INTEGRATION_STATUS.md` 第 64 行）
- `s6_automatic_trust=BLOCKED` —— 不因代码检查成功而允许第六阶段自动信任或导出训练数据（同文件第 65 行）

---

### 2.3 Verifier（校验/验证层）

**主力 patient-eval 子系统：无独立 verifier，工具分散**

| 工具 | 作用 | 来源 |
|---|---|---|
| `pilot_cli validate` | 套件结构校验 | `REVIEW_V0.3.md` |
| `pilot_cli review-packet` | 结构/证据回合检查（**不验证评审者专业资格**） | `REVIEW_V0.3.md` 第 3 行 |
| `pilot_cli agreement` | 双人一致性，线性加权 Cohen's kappa | `REVIEW_V0.3.md` 第 97–102 行 |
| `scripts/verify_s5_v091_historical_receipt.py` | S5 历史收据**只读**核验 | `S5_INTEGRATION_STATUS.md` 第 22 行 |

**S3 命题验证器一族（30 个文件，独立于患者评测）**

演进链：`s3_naive_claim_verifier`（v0.1 词法）→ `s3_atomic_proposition_verifier*`（v0.4 原子命题）→ `s3_claimframe_verifier`（v0.3 方向性）→ `s3_structured_claim_verifier`（v0.2 结构化语义）→ `s3_compositional_verifier*`（v0.5.0–v0.5.4 组合命题，含 `ESTABLISHES_CAUSALITY` 等危险谓词）

**S5 信任与血缘（12 + 约 40 个脚本）**
- `s5_trust_policy_v0.{6.1,7.1,7.2,7.3,8.1,9.1}.py`
- `s5_lineage_detector{,_v073,_v081,_v091}.py`
- `s5_release_gate.py`（机器强制的发布谓词）
- `s5_v091_freeze_control.py`（v0.9.1 共享 fail-closed 冻结控制）

**公开发布 fail-closed 校验器**
- `medical/patient-eval/pilot/real-dialogue-derived-v0.1/scripts/validate_public_release.py`（68 行）：白名单扩展名 + 黑名单文件名 + 禁止 token + PII 正则 + 私有引用模式 + XLSX 解包扫描。输出 `formal_approval=false`、`clinical_gold=false`。

**AP07 v3 独立迭代（在 integration 仓库，可回流）**

| 文件 | SHA | 作用 | 状态 |
|---|---|---|---|
| `scripts/ap07_v3_oracle.py` | `0585d1da…` | 节点激活，只读 visible prefix 的 `fact_ids`/`fact_status`，不读隐藏通道 | 工程就绪（最小切片） |
| `scripts/ap07_v3_verifier.py` | `dd6f35aa…` | 确定性 fail-closed 检查，含多容器递归泄露扫描 | 已独立审查通过 |
| `benchmark/ap07-oracle-v3/criteria.json` | `1b67e34b…` | C04/C05/C06/C10 分离；`medication_substitutes_urgent_care` 与 `omitted_medication_warning` 分离 | 工程就绪；争议条款 `pending_confirmation` |
| `benchmark/ap07-oracle-v3/nodes.json` | `9b53a538…` | 节点定义 | — |
| `benchmark/ap07-oracle-v3/TRUSTED_ANCHORS.json` | `d3639692…` | 独立于提交内容的受控锚点 | — |

---

### 2.4 Runner（运行器）

**`scripts/patient_eval/` 包（29 个文件）**

| 类别 | 关键模块 |
|---|---|
| 入口/编排 | `cli.py`、`pilot_cli.py`、`__main__.py` |
| 患者模拟/披露 | `patient.py`（确定性、问题依赖披露）、`patient_intent.py`（可审计中文规则）、`state.py`、`extraction.py`（保守中文规则抽取）、`relations.py` |
| 管线/重放 | `runner.py`（前缀重放+事件丢失干预）、`pipeline.py`、`study.py`（自由对话基线/状态干预）、`pilot.py`、`retrieval.py`（BM25 基线） |
| 评分/评估 | `scoring.py`、`agreement.py`、`review_contract.py`、`diagnosis.py`、`reporting.py`、`calibrate_patient.py`、`contracts.py` |
| 候选审阅/隐私 | `candidate_review.py`、`candidate_review_ui.py`、`candidate_similarity.py`、`candidate_facts.py`、`candidate_privacy.py` |
| 接入/传输 | `adapters.py`、`transport.py`、`importers.py`、`source_intake.py` |

**`pilot/real-dialogue-derived-v0.1/scripts/pilot_runner.py`（325 行）**
无外部依赖的动态患者脚本运行器。`PatientScript` 类模拟患者侧披露契约，**不调用模型、不评临床分、不建临床金标准**。事件驱动披露（`after_model_turn`/`after_fact_disclosed`）、停止策略（显式 `/stop`、结论式收尾、最大轮数）、输出 `groundsignal-dynamic-run-record/v0.1` JSONL。

**AP07 运行器（integration 仓库）**：`scripts/ap07_v3_runner.py`（`5d8fcb39…`），离线，驱动真实 `PatientSimulator`（`patient.py:134` / runner:185），通过真实 `contracts.validate_session`。

---

## 3. 病例资产

### 3.1 十二个病例族（`medical/case-families/`）

每族含 `manifest.json` + `evidence.json` + `graph.json` + `cases/`。

| 家族 ID | status | clinical_review | evidence_review |
|---|---|---|---|
| AGENT-001 | gold_review_needed | needed_for_final-answer-gold | source_verified |
| CLINREASON-001 | gold_review_needed | needed | source_verified |
| CLINREASON-005 | gold_review_needed | needed | source_verified |
| EVIDENCE-002 | gold_review_needed | not_required_for_synthetic_design_logic | synthetic_fixture_verified |
| EVIDENCE-003 | gold_review_needed | not_required_for_synthetic_design_logic | synthetic_fixture_verified |
| MEDSAFE-001 | gold_review_needed | needed | source_verified |
| MEDSAFE-002 | gold_review_needed | needed | source_verified |
| MULTITURN-001 | gold_review_needed | needed | source_verified |
| REPORT-001 | gold_review_needed | needed | source_verified |
| REPORT-004 | gold_review_needed | synthetic_fixture_verified | synthetic_fixture_verified |
| TRIAGE-001 | gold_review_needed | needed | source_verified |
| TRIAGE-003 | gold_review_needed | needed | source_verified |

**统计**：12 族**全部** `gold_review_needed`。其中 **9 族需临床审核**，3 族为合成设计逻辑（不需临床）。所有族 `as_of_date=2026-09-05`。

### 3.2 已公开的 pilot 资产（`pilot/real-dialogue-derived-v0.1/`）

| 类别 | 数量 | 内容 |
|---|---|---|
| 固定重放病例 | 6 | `GS-PUB-RPL-001..006` |
| 动态病例 | 3 | `GS-PUB-DYN-001..003` |
| 病例卡 | 12 | `case_cards_12_public.{json,md}` |
| 发布文件总数 | 26 | `MANIFEST.json` |

- `release_class = public_deidentified_synthetic_derivative`
- `formal_approval=false`、`clinical_gold=false`
- 明确排除：原始对话、已完成评审包、精确证据区间、来源标识、重做映射、真实模型转录、临床裁定记录

**validation/ 四份审计（全部 `passed=true`）**：

| 文件 | schema | 关键数字 |
|---|---|---|
| `public_release_validation.json` | v0.3 | 26 文件；6 固定重放 + 10 检查点 + 12 病例卡 + 3 动态；隐私门 0 发现 |
| `privacy_leakage_audit.json` | v0.1 | 89 公开 vs 69 私有样本；≥12 字符精确匹配 0；直接标识 0；私有引用 0 |
| `workbook_validation.json` | v0.1 | 公式错误 0；两轨分离，禁止跨轨平均/总分 |
| `smoke_test_summary.json` | v0.1 | 3 动态用例离线冒烟；`real_model_calls=0`；均 `explicit_stop` 收尾 |

---

## 4. 测试与 CI（真实运行输出）

```
解释器：/home/zehaoli0324/venvs/m1env/bin/python
        （Python 3.12.3 + pytest 9.1.1）
命令：  ~/venvs/m1env/bin/python -m pytest tests/patient_eval -q
结果：  217 passed, 121 subtests passed in 2.14s（0 failed, 0 error）
```

> 环境提示：系统裸 `python3` 被劫持指向 `~/projects/crypto-signal/.venv`（Python 3.14.6，无 pytest）。必须显式指定解释器。

**测试文件分布（18 文件 / 217 测试）**

| 文件 | 数 | 文件 | 数 |
|---|---|---|---|
| test_evaluation.py | 22 | test_candidate_similarity.py | 10 |
| test_study.py | 21 | test_candidate_facts.py | 9 |
| test_review_scoring_v03.py | 18 | test_agreement_v03.py | 9 |
| test_candidate_review.py | 17 | test_review_pipeline_v03.py | 8 |
| test_patient.py | 16 | test_source_intake.py | 8 |
| test_pilot.py | 13 | test_pipeline.py | 8 |
| test_patient_intent_v03.py | 12 | test_candidate_privacy.py | 8 |
| test_relations.py | 12 | test_candidate_review_ui.py | 4 |
| test_blackbox_reports.py | 12 | **合计** | **217** |
| test_algorithms.py | 10 | | |

**CI 工作流**

| 文件 | 触发 | 内容 |
|---|---|---|
| `patient-eval-development-ci.yml` | PR/push 触及 `scripts/patient_eval/**`、`medical/patient-eval/**`、`tests/patient_eval/**` | Python 3.11；`unittest discover` 全量 → demo 重放 → import+evaluate → pilot validate/demo → review-packet/apply-review/score → calibrate+relations |
| `s4-v01-truth-ledger-dev.yml` | push 触及 S4 文件 或手动 | 跑 `eval_s4_truth_ledger_v01.py` + `diff -u` 校验聚合输出可复现 |

---

## 5. 阶段进展（`medical/patient-eval/STAGE_DECOMPOSITION.md`）

**框架**：S1–S10 = 建设流程；C1–C8 = 能力；E1–E4 = 被评对象（E1 最终回答 / E2 知识图谱对齐 / E3 RAG / E4 Agent 轨迹）。

**关键声明**（第 200 行原文）："以下是本轮的局部实现范围，不重写旧评测历史或把任何阶段整体标为完成。"

| 阶段 | 本轮已实现 | 未完成主要环节 |
|---|---|---|
| S1 用户需求与任务定义 | 六业务轨与合成任务边界 | 经许可真实问题、真实需求代表性 |
| S2 知识搜索与来源路由 | 复用既有检索原型 | 动态交互中的真实来源和完整工具链 |
| S3 证据核验与语义抽取 | 保守可见文本抽取 | 通用口语抽取的独立标注验证 |
| S4 知识图谱与构建更新 | 延续既有图谱接口 | 患者试评未新增真实医学图谱覆盖证明 |
| S5 受控案例工厂与准入 | 十二公开开发变体；历史收据检查修复 | **24 开发场景、72 研究家族、临床审核和正式准入** |
| S6 动态患者/模型/工具执行 | 动态交互、人工采集、可配置真实模型对照 | 小荷实采与真实模型实际运行 |
| S7 多层评分、安全与校准 | 评分细则、审评包、两人一致性工具 | **专家评分、真实分歧裁决、自动评分校准** |
| S8 缺陷诊断与能力假设 | 复用故障/归因原型 | F01–F10 完整规模及真实缺陷因果验证 |
| S9 干预与训练数据 | 基线/状态候选双臂脚本 | 根据真实失败决定干预、完成效果测量 |
| S10 独立复测与发布 | 本地机械回归和开发合并检查 | 正式独立复测、患者理解和临床获益 |

**stage-evals 实际覆盖**：仅 `S2`、`S3`、`S4`、`S5`、`S2S3` 有内容。**S6–S10 目录不存在（0 文件）**。

---

## 6. 交接与当前入口

- `docs/handoffs/2026-09-09-patient-eval-v03-handoff.md` 第 3 行指出：后续已有更新的**候选审阅交接**（`2026-09-09-candidate-review-handoff.md`）作为当前接手入口。
- v03 交接的一句话定位（第 5 行）："已完成评分与披露校准的开发闭环；下一步需要独立人工校准，随后才能做真实平台试评。"
- 验证数据（第 23–24 行）：患者模块 161 项测试 + 历史收据 14 项通过；**24 条离线会话、152 个判据仍未评分**；**零真实模型调用**。
- v03 交接的四步下一步：① 未参与规则编写的标注者提供新问询表达 → 冻结束期望槽；② 两名评分者对同一批会话独立标注 → 复核评分机会 → 修改细则另开版本；③ 场景复核后用小荷+通用模型做同条件小样本试评；④ 同模型上跑原始/状态增强对照。

---

## 7. 已建成的完整能力链（S2→S5 全链路脚本）

| 阶段 | 脚本族 | 数量 |
|---|---|---|
| S2 | `eval_s2_*`（intent routing / source routing / live retrieval / negation / dailyMed truth / joint pipeline） | 6 |
| S3 | `eval_s3_*`（claim verification / proposition extraction / safety errors / structured entailment / compositional verifier） | 5 |
| S3a | 抽取与帧解析（ontology extractor / compositional frame parser / semantic frame extractor） | ~15 |
| S3b | 蕴含引擎（entailment engine / structured entailment runner） | ~5 |
| S4 | truth ledger（v0.1 / v0.1.1）+ eval | 4 |
| S5 | trust policy（6 版）+ lineage detector（4 版）+ release gate + freeze control + eval/verify/test/materialize/generate/calibrate/check | ~50 |
| 医疗校验 | `validate_medical_case_families.py`、`validate_medical_knowledge_sources.py`、`build_medical_knowledge_graph.py` | 3 |

---

## 8. 状态字段汇总（收尾，均为文件自述）

| 字段 | 值 | 来源 |
|---|---|---|
| `gold_approved` | `false` | `S5_INTEGRATION_STATUS.md` 第 64 行 |
| `s6_automatic_trust` | `BLOCKED` | 同文件第 65 行 |
| 病例族 `status` | 12/12 `gold_review_needed` | 各族 `manifest.json` |
| `formal_approval` | `false` | `pilot/.../MANIFEST.json` |
| `clinical_gold` | `false` | 同上 |
| 真实模型调用 | `0` | 各 window 报告一致 |
| `independent_clinical_validation` | `false` | AP07 FINAL_REPORT §3 |

---

## 9. 本盘点的验证边界

- 本文是**工程资产盘点**，不是临床验证、不是发布声明、不是科学抽象审计。
- 状态列以**文件自述字段**为准，**未逐条人工确认**。凡需临床判断的状态（如"某族可否用于研究"）一律照实记录为未完成。
- 测试数字来自真实运行（`~/venvs/m1env/bin/python`），非引用。
- 搜不到或读不到的内容未编造。
