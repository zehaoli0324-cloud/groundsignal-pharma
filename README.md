# GroundSignal Medical

### Knowledge-Graph-Grounded Medical Model Evaluation & Post-training Infrastructure

[![medical-development-ci](https://github.com/zehaoli0324-cloud/groundsignal-pharma/actions/workflows/medical-development-ci.yml/badge.svg)](https://github.com/zehaoli0324-cloud/groundsignal-pharma/actions/workflows/medical-development-ci.yml)

> **真实用户任务 → 医学证据/知识图谱 → Model / RAG / Agent → 多层评测 → Failure Diagnosis → Post-training Data → Held-out Regression**

GroundSignal Medical 是一个面向医疗大模型开发的 **evidence-grounded evaluation platform prototype**。

它不是静态医学题库，也不是单纯的知识图谱。项目把 **版本化医学证据、任务导向知识图谱、controlled case families、模型/RAG/Agent Harness、失败归因、训练数据导出与安全回归** 接成一条开发闭环。

项目的正式能力版图现包括：**医学问答、辅助诊疗、用药安全、医学影像、报告解读、医疗 Agent、多模态医疗模型、Benchmark、评测 Agent 和训练数据**。这些方向共享同一套证据、知识图谱、分区隔离和分阶段评测底座，但成熟度分别记录；“纳入版图”不等于“已经具备临床能力”。完整边界与各方向完成标准见 [`docs/21-medical-ai-capability-portfolio.md`](docs/21-medical-ai-capability-portfolio.md)。

> **当前 S5 门禁：** v0.8.1 已在 `b5dffbe366904a46d3b6a44172a4f1626daa8924` 正式冻结。v0.9 fresh 首次观测仍是不可变 **FAIL**。v0.9.1 已在暴露数据上修复 F32 韩文召回与数字近邻误拦截，并通过 5/5 攻击、4/4 clean 及历史回归；这只是 **exposed repair PASS**，不是 fresh PASS。`gold_approved=false`，S5 bounded release 与 S6 自动信任继续阻断。

```text
Real User Needs / Clinical Workflows
                ↓
        User Task Bank
                ↓
     Controlled Case Families
                ↓
 Evidence + Temporal Knowledge Graph
                ↓
      Model / RAG / Agent Harness
                ↓
 Answer + Retrieval + Tool Trajectory
                ↓
      Multi-layer Evaluation
                ↓
         Failure Taxonomy
                ↓
       Intervention Router
                ↓
 Retrieval / Prompt / SFT / Preference / Agent / Judge
                ↓
       Candidate Model/System
                ↓
       Held-out Regression Gate
                └────────────────────→ loop
```

## Why this project exists

医疗模型最危险、也最难定位的问题，往往不是“知识点答错”这么简单：

```text
III 期阳性             → 被升级成“已经获批”
旧版指南               → 被当作当前真值
有来源 URL             → 但来源并不支持这个 claim
低 serum iron          → 被直接升级成“确诊缺铁”
影像写 indeterminate   → 被升级成“癌症”或降级成“良性”
RAG 已经找到关键证据   → 最终回答却没有使用
Agent 已有充分证据     → 仍然不断搜索
信息不足               → 模型仍强行给结论
```

GroundSignal 的核心问题不是：

> “模型答案和 reference answer 有多像？”

而是：

> **模型使用了什么事实、形成了什么关系、证据是否足够、时间状态是否正确、哪里发生了 claim escalation，以及这个 failure 应该由 retrieval、prompt、SFT、preference、Agent trajectory 还是 evaluator 修复？**

---

# Current Checkpoint

截至 **2026-09-05**，P0 数据资产已经完成并通过 CI integrity check：

- **12 个 scenario families**
- **60 个 controlled evaluation cases**
- 每个 family 固定 **5 个 case**
- 每个 family 包含 held-out / regression 设计
- case ↔ evidence passage ↔ graph node/edge 引用完整性由 CI 自动检查
- 统一评分协议：`medical-clinical-v0.2`

> **Important:** 60 个 case 已完成工程与证据契约构建，不等于 60 个 case 已完成最终临床专家验证。各 family 的 `status` / `review` 字段保留这一边界。

## P0 case families

| Family | Task | 主要能力 / Failure |
|---|---|---|
| `MEDSAFE-001` | Metformin × renal function | threshold reasoning / medication safety / abstention |
| `MEDSAFE-002` | Apixaban × OTC NSAID | interaction reasoning / clarification / safety |
| `TRIAGE-001` | Acute chest symptoms | red-flag recognition / false reassurance |
| `TRIAGE-003` | Neurologic warning signs | salience / anchoring / escalation boundary |
| `CLINREASON-001` | IDA vs inflammation anemia | differential reasoning / metric salience / mixed state |
| `CLINREASON-005` | Multifactorial AKI | competing hypotheses / evidence update / anchoring |
| `REPORT-001` | CBC interpretation | observation vs diagnosis / over-interpretation |
| `REPORT-004` | Indeterminate radiology finding | report grounding / uncertainty preservation |
| `EVIDENCE-002` | Cross-trial comparison | comparability / superiority overclaim / calibrated update |
| `EVIDENCE-003` | New RCT vs guideline | temporal truth / source role / supersession |
| `MULTITURN-001` | Medication clarification | critical-slot collection / correction propagation |
| `AGENT-001` | Current-label retrieval | tool selection / stale-result recovery / stop correctness / held-out transfer |

每个 family 不是 5 道随机题，而是一个 **controlled experiment**：

```text
Base
+ controlled variant
+ controlled variant
+ adversarial / regression variant
+ held-out variant
```

例如 `MEDSAFE-001`：

```text
eGFR 27   → 命中 <30 rule
eGFR 31   → 不能机械套用 <30 rule
缺 eGFR   → 应先澄清而不是强行判断
加入 distractor → 核心判断应保持稳定
eGFR 29 held-out → 检查 threshold generalization
```

因此训练后可以发现：

```text
base case ↑
但 missing-information case ↓
→ 模型可能变得更敢答，但 abstention 被破坏
```

这比只报告一个平均准确率更适合模型迭代。

---

# 1. Medical Knowledge Graph = Versioned Truth Substrate

`medical/knowledge-graph/` 不是为了“画一张大图”，而是给评测、RAG 归因和 Post-training provenance 提供统一真值层。

核心节点包括：

```text
CASE
SYMPTOM / SIGN
LAB_RESULT / VITAL
IMAGING_FINDING / PATHOLOGY_FINDING
CONDITION / DIFFERENTIAL
MEDICATION / DRUG_CLASS
CONTRAINDICATION / INTERACTION / MONITORING_RULE
GUIDELINE_RECOMMENDATION / LABEL_RECOMMENDATION
DOCUMENT / DOCUMENT_VERSION / EVIDENCE_PASSAGE
TEMPORAL_EVENT
```

核心关系包括：

```text
HAS_SYMPTOM / HAS_LAB / TAKES
SUPPORTS / MAY_SUPPORT / CONTRADICTS
CONTRAINDICATED_IN / INTERACTS_WITH
RECOMMENDED_BY / SUPPORTED_BY
SUPERSEDES
REQUIRES_TEST
TRIGGERS_TRIAGE_ACTION
```

关系状态显式区分：

```text
OBSERVED
DERIVED
HYPOTHESIS
DISPUTED
SUPERSEDED
UNKNOWN
```

### 为什么图谱能改善评测

例如报告写：

```text
indeterminate lesion
→ recommends MRI for further characterization
```

允许的图谱关系是：

```text
finding:indeterminate
→ RECOMMENDS_FOLLOWUP
MRI
```

而不是：

```text
indeterminate
→ CONFIRMS
cancer
```

模型可以使用任意自然语言表达；评分关注的是它有没有保留合法语义关系、有没有创造 evidence 不支持的 edge。

详细设计：[`medical/knowledge-graph/README.md`](medical/knowledge-graph/README.md)

---

# 2. Evidence & Temporal Truth

GroundSignal 从早期的：

```text
claim → source_url
```

升级为：

```text
claim
→ evidence_passage_id
→ document / version / date
→ section / paragraph / table
→ evidence role
→ claim scope
→ valid_from / valid_to
→ contradiction / supersession
```

这使同一个 truth layer 可以同时服务：

- factuality
- citation entailment
- evidence sufficiency
- RAG Recall@K
- source hierarchy
- stale knowledge detection
- guideline / label update
- Agent retrieval
- Post-training provenance

数据来源采用 **authoritative public evidence + explicitly synthetic controlled fixtures**。Synthetic fixture 用于控制变量实验时会显式标记，不冒充真实临床事实。

规范：[`medical/truth-layer/README.md`](medical/truth-layer/README.md)

---

# 3. Real User Tasks, not Medical Exam Questions

平台先定义用户任务，再生成 benchmark case。

当前 `medical/user-tasks/SEED_TASK_BANK.md` 有 **48 个 designer-generated scenario seeds**，覆盖：

- Medication safety
- Symptom / triage
- Clinical reasoning
- Lab / report interpretation
- Evidence-grounded treatment comparison
- Multi-turn medical dialogue
- Medical Agent / tool use
- Multimodal-ready tasks

这些 seed 是 **产品/评测假设**，不是“真实用户日志”。

真实任务发现流程单独记录在：

[`medical/user-tasks/USER_RESEARCH_PLAN.md`](medical/user-tasks/USER_RESEARCH_PLAN.md)

目标是：

```text
real workflow / user need
→ de-identify / abstract
→ synthetic or licensed case
→ evidence grounding
→ controlled variants
→ expert review
→ benchmark
```

---

# 4. Four-layer Evaluation

统一评测协议：

[`medical/evaluation/rubrics/medical-clinical-v0.2.md`](medical/evaluation/rubrics/medical-clinical-v0.2.md)

## E1 — Final Answer

```text
Factual correctness
Evidence sufficiency
Temporal validity
Clinical reasoning
Uncertainty calibration
Task usefulness
Communication
Safety
```

## E2 — Knowledge-Graph Grounding

```text
required-node recall
required-edge recall
unsupported-edge rate
evidence-linked claim precision
valid reasoning path rate
temporal graph accuracy
```

## E3 — RAG / Retrieval

```text
Evidence Recall@K
Critical Passage Recall@K
Evidence Precision@K
Current-version recall
Source hierarchy
Contradiction / supersession recall
```

核心归因规则：

```text
critical passage 没进 top-K
→ retrieval-side failure candidate

critical passage 已进 context，但答案仍错
→ generation / reasoning / evidence-use failure candidate
```

## E4 — Agent Trajectory

```text
Tool selection
Query quality
Current-source recall
Bad-result recovery
Tool-result utilization
Stop correctness
Clarification action
Trajectory safety
Held-out generalization
```

---

# 5. Safety is a Gate, not an Average-score Penalty

医疗模型不能只看：

```text
Model A = 84.2
Model B = 85.7
```

如果 B 新增了 pre-registered critical medical safety error，它不应因为均分更高而通过 release gate。

当前 critical-error classes 包括：

- contraindicated medication recommendation
- unsupported dose / prescription change
- red-flag miss / false reassurance
- fabricated patient fact used in reasoning
- association/signal → causal claim
- superseded critical rule treated as current
- fabricated source / citation / passage
- Agent 在要求取证前先做 high-risk claim
- critical tool result retrieved but silently ignored

`Regression Gate` 会把这些错误作为 blocker，而不是普通扣分项。

---

# 6. Model / RAG / Agent Harness

`scripts/model_harness.py` 记录：

```text
provider / model_id / model_version
prompt_version
temperature
RAG on/off
retriever_version / top_k
tools
snapshot_id
response
latency / usage
run_id
```

当前 v0.1 支持：

- fixture / CI dry-run
- OpenAI-compatible chat endpoint adapter
- closed-book
- frozen evidence injection / RAG-style context
- multi-model config matrix

> Production retriever/reranker 与真实 Agent tool executor 尚未完成，这是下一阶段系统验证的一部分。

---

# 7. Failure → Post-training

GroundSignal 不把所有 bad case 都解释成“加训练数据”。

```text
Observed Failure
        ↓
Capability Hypothesis
        ↓
Intervention Router
        ↓
┌──────────────┬──────────────┬──────────────┐
│ Retrieval    │ SFT          │ Preference   │
│ / Reranker   │ / reasoning  │ / safety     │
├──────────────┼──────────────┼──────────────┤
│ Agent traj.  │ Judge calib. │ Prompt/policy│
└──────────────┴──────────────┴──────────────┘
        ↓
Candidate model/system
        ↓
Held-out Regression
```

典型路由：

| Failure | 默认 intervention candidate |
|---|---|
| `STALE_KNOWLEDGE` | retrieval / temporal truth refresh |
| `KNOWLEDGE_MISSING` | retrieval first; broad gap → domain data / MidTrain candidate |
| `RETRIEVAL_MISS` | index / query rewrite / reranker |
| `REASONING_FAILURE` | reasoning SFT / decomposition |
| `OVERCLAIM` | preference / evidence-grounded SFT |
| `UNSAFE_RECOMMENDATION` | safety SFT + preference + gate |
| `FAILURE_TO_CLARIFY` | multi-turn SFT / policy |
| `BAD_TOOL_SELECTION` | Agent trajectory / tool routing |
| `TOOL_RESULT_IGNORED` | Agent/evidence-use trajectory |
| `JUDGE_INCONSISTENCY` | judge calibration / deterministic check |

完整接口：[`posttrain/README.md`](posttrain/README.md)

训练数据契约已经定义：

```text
posttrain/schemas/
  sft-example.schema.json
  preference-example.schema.json
  agent-trajectory.schema.json
  judge-label.schema.json
```

每条 production training candidate 必须保留：

```text
source_case
source_run
failure_type
evidence_passage_ids
graph_version
review_status
builder_version
split
intended_intervention
regression_suite
```

**Eval failure ≠ automatically approved training data.**

---

# 8. Regression before Claiming Improvement

训练或系统修改后必须回到 held-out case family：

```text
Baseline
vs
Candidate

factuality ↑ ?
reasoning ↑ ?
overclaim ↓ ?
retrieval ↑ ?
Agent behavior ↑ ?
abstention preserved ?
critical safety errors = 0 new ?
```

只有 held-out / regression 通过，才能把 intervention 从“优化假设”升级成“有证据支持的改进”。

---

# 9. Pharma Track remains useful

原有 `pharma/` 与 `benchmark/` 保留为 **real-world temporal medical/pharma evidence track**，继续提供：

- ClinicalTrials / FDA / NMPA 等状态变化
- drug / target / trial / event / claim / evidence graph
- temporal truth
- source hierarchy
- stale knowledge bad cases
- evidence-grounded decision reasoning

它不再是整个项目的终点，而是 Medical Platform 的一个真实动态 evidence domain。

---

# Repository Layout

```text
medical/
  case-families/             # 12 P0 families / 60 controlled cases
  knowledge-graph/           # task-oriented versioned truth graph
  truth-layer/               # paragraph-level evidence contracts
  user-tasks/                # task seed bank + user-research plan
  evaluation/                # evaluation protocol + frozen rubric
  schemas/                   # case / family / graph / evidence / run schemas
  configs/                   # harness / intervention / regression configs
  examples/                  # vertical-slice fixtures

posttrain/
  README.md                  # Eval → post-training contract
  schemas/                   # SFT / preference / Agent / Judge schemas

scripts/
  model_harness.py
  intervention_router.py
  export_training_data.py
  regression_gate.py
  validate_medical_case_families.py
  ...                        # existing pharma intelligence scripts

pharma/                      # real-world pharma evidence graph
benchmark/                   # earlier decision-intelligence/model-diagnosis benchmark
docs/                        # architecture / roadmap / safety boundaries
.github/workflows/           # CI integrity + vertical-slice checks
```

---

# Quick Start

## 1. Validate the benchmark asset

```bash
python scripts/validate_medical_case_families.py \
  --expect-families 12 \
  --expect-cases 60 \
  --expect-cases-per-family 5 \
  --rubric-version medical-clinical-v0.2
```

The validator checks:

```text
manifest → case path
case_id consistency
family / case counts
held-out split presence
case → evidence passage references
case → required graph nodes/edges
graph → evidence passage references
rubric version consistency
```

## 2. Run the existing vertical-slice fixture

```bash
python scripts/model_harness.py \
  --cases medical/examples/clinical-medication-safety-001.json \
  --config medical/configs/model-matrix.fixture.json \
  --evidence medical/examples/evidence.jsonl \
  --out /tmp/groundsignal-runs.jsonl
```

## 3. Route failures

```bash
python scripts/intervention_router.py \
  --eval medical/examples/eval-baseline.jsonl \
  --rules medical/configs/intervention-rules.json \
  --out /tmp/routed.jsonl
```

## 4. Export reviewed training candidates

```bash
python scripts/export_training_data.py \
  --cases medical/examples/clinical-medication-safety-001.json \
  --runs /tmp/groundsignal-runs.jsonl \
  --eval medical/examples/eval-baseline.jsonl \
  --out-dir /tmp/training
```

## 5. Run regression gate

```bash
python scripts/regression_gate.py \
  --baseline medical/examples/eval-baseline.jsonl \
  --candidate medical/examples/eval-candidate.jsonl \
  --policy medical/configs/regression-policy.medication-safety-v0.1.json \
  --out /tmp/regression-report.json
```

---

# What is implemented vs what is proven

## Implemented

- versioned Evidence / Claim / Graph data contracts
- 48 medical user-task seeds
- 12 controlled case families / 60 cases
- knowledge-graph evaluation contracts
- paragraph-level evidence provenance
- clinical / medication safety gates
- temporal truth / supersession cases
- multi-turn state-update cases
- Agent retrieval / recovery / stop / held-out cases
- model harness scaffold
- failure taxonomy + intervention router
- reviewed SFT / preference export path
- Post-training schemas
- held-out regression gate
- CI integrity validation

## Already demonstrated in repository

- pharma evidence graph + temporal events
- claim provenance audit
- stale-knowledge real-world bad case
- controlled benchmark design
- reproducible vertical-slice fixture
- full P0 12-family / 60-case referential-integrity validation in CI

## Not yet proven

- clinician-reviewed gold for the complete 60-case set
- production-scale guideline / label ingestion
- real multi-provider run across all 60 cases
- production retriever/reranker Recall@K results
- live Medical Agent tool execution results
- multimodal benchmark with licensed/open images
- calibrated LLM-as-Judge vs clinician agreement
- actual SFT / DPO / RL intervention with held-out improvement
- sustained improvement on a real medical model checkpoint

These are intentionally kept separate from implemented infrastructure.

---

# Safety & Data Boundary

This repository is for **research, evaluation and model-development infrastructure**. It is not a patient-facing clinical decision system and does not replace professional medical care.

Clinical cases committed to the repository must be:

```text
public
or licensed
or de-identified
or synthetic
```

Do not commit identifiable patient information.

Medical safety principles are documented in:

[`docs/11-clinical-safety-boundaries.md`](docs/11-clinical-safety-boundaries.md)

---

# Core Principle

```text
Evaluation is not the end of model development.

A useful medical evaluation system should:
find the failure,
locate the evidence boundary,
attribute the failure to the right subsystem,
route an intervention,
and prove the fix on held-out cases without creating a new safety regression.
```

Architecture: [`docs/14-kg-grounded-medical-eval-platform.md`](docs/14-kg-grounded-medical-eval-platform.md)  
Roadmap: [`docs/13-medical-model-development-roadmap.md`](docs/13-medical-model-development-roadmap.md)
