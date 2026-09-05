# GroundSignal Medical Development System

### Evidence-Grounded Medical Model Evaluation, Diagnosis & Post-training Infrastructure

> **从动态医学证据 → 临床/医药任务 → 模型评测 → Failure Diagnosis → 干预路由 → 训练数据 → Regression Gate。**

GroundSignal 起源于 `groundsignal-pharma` 的医药情报系统，但当前目标已经扩展为：

> **Evidence-Grounded Medical Model Development System**

它不是一个“已经训练好的医疗大模型”，也不是患者侧临床决策系统。它要解决的是医疗大模型开发中更底层的一组问题：

- 什么医学事实在当前时间点成立？
- 哪一段指南 / 说明书 / 监管文件 / 文献真正支持这个 claim？
- 模型错在哪里：知识、检索、推理、证据充分性、overclaim、工具调用还是评测器？
- 这个 bad case 应该路由到 retrieval、prompt、SFT、preference、Agent trajectory 还是 judge calibration？
- 新模型版本虽然均分更高，有没有引入新的医疗安全退化？

---

## Development Loop

```text
Medical / Pharma Sources
        ↓
Evidence & Temporal Truth Layer
        ↓
Medical Task Factory
        ↓
Model / RAG / Agent Harness
        ↓
Evaluation & Safety Gates
        ↓
Failure Diagnosis
        ↓
Intervention Router
        ↓
Retrieval / Prompt / SFT / Preference / Agent-trajectory / Judge changes
        ↓
New Model / System Version
        ↓
Regression Gate
        └────────────────────────────→ loop
```

详细架构：[`docs/12-medical-model-development-architecture.md`](docs/12-medical-model-development-architecture.md)

---

## Why GroundSignal is useful for medical-model development

医疗模型的很多问题并不是简单的“知识答错”。典型失败包括：

```text
III 期阳性             → 被模型升级成“已经获批”
试验注册               → 被模型升级成“已经证明有效”
不良事件报告           → 被模型升级成“存在因果关系”
单个资产安全信号       → 被模型升级成“类别效应”
旧版指南/标签          → 覆盖了当前有效版本
有一个来源 URL         → 被误认为引用真的支持 claim
证据不足               → 模型仍给出高置信度诊断/结论
```

GroundSignal 的核心设计因此是 **claim scope + evidence role + temporal validity + uncertainty + regression**，而不是只做静态 QA。

---

# Two Tracks

## Track P — Pharma / drug-development evidence

原有 `pharma/` 不废弃，而作为已经有真实数据的 **Temporal Medical Evidence Track**。

当前对象包括：

```text
Company / Drug / Target / Trial / Event / Claim / Evidence
```

核心能力：

- ClinicalTrials / FDA / NMPA 等真实世界状态变化；
- 获批 / NDA / 临床阶段的 temporal truth；
- Claim-Evidence provenance；
- competition / target / indication reasoning；
- source hierarchy；
- stale knowledge / overclaim / contradiction 测试。

已有医药安全纪律见：[`docs/11-clinical-safety-boundaries.md`](docs/11-clinical-safety-boundaries.md)

## Track C — Clinical model development

新建 `medical/`，开始覆盖真正面向医疗模型的任务面：

- Medical QA
- Clinical reasoning / differential reasoning
- Medication safety
- Lab / pathology / imaging-report interpretation
- Longitudinal disease-course reasoning
- Multi-turn clarification / uncertainty
- Medical Agent / tool use
- Multimodal-ready task manifests

临床 Track 规范：[`medical/clinical-track/README.md`](medical/clinical-track/README.md)

> 临床数据必须来自 public / licensed / de-identified / synthetic sources；仓库不得保存可识别患者信息。

---

# 1. Medical Truth Layer

旧版主要是：

```text
claim → source_url
```

现在升级目标是：

```text
claim
  → evidence_passage_id
      → source / version / date
      → section / paragraph / table
      → normalized proposition
      → evidence role
      → scope
      → valid_from / valid_to
      → contradiction / supersession
```

证据角色包括：

```text
DIRECT_SUPPORT
PARTIAL_SUPPORT
CONTRADICTS
CONTEXT_ONLY
DOES_NOT_SUPPORT
SUPERSEDES
```

这允许系统真正评估：

- citation entailment；
- evidence sufficiency；
- source hierarchy；
- stale claim；
- contradiction；
- guideline / label update；
- RAG evidence recall@k。

规范：[`medical/truth-layer/README.md`](medical/truth-layer/README.md)  
Schema：[`medical/schemas/evidence-passage.schema.json`](medical/schemas/evidence-passage.schema.json)

---

# 2. Clinical Task Schema

临床 case 不只保存“问题 + 标准答案”，而显式区分：

```text
patient state
+ evidence snapshot
+ interaction state
+ expected behavior
+ must-not-claim
+ uncertainty behavior
+ critical safety errors
+ scoring contract
```

Schema：[`medical/schemas/clinical-case.schema.json`](medical/schemas/clinical-case.schema.json)

一个正确行为可以是：

- 给出结论；
- 排序 differential；
- 指出证据不足；
- 请求一个高信息量澄清项；
- 检索指南/说明书；
- 升级 / escalation；

而不强迫所有题都存在唯一疾病字符串答案。

---

# 3. Model / RAG Harness

新增：[`scripts/model_harness.py`](scripts/model_harness.py)

记录：

```text
model_id
provider
model_version
prompt_version
RAG on/off
retriever_version
top_k
tools
temperature
snapshot_id
response
latency
usage
run_id
```

当前首版支持：

- `fixture`：本地 pipeline / CI dry-run；
- `openai_compatible`：接 OpenAI-compatible `/chat/completions` endpoint；
- closed-book；
- frozen evidence injection / RAG-style context；
- 多模型 config matrix。

示例配置：[`medical/configs/model-matrix.example.json`](medical/configs/model-matrix.example.json)

```bash
python3 scripts/model_harness.py \
  --cases medical/examples \
  --config medical/configs/model-matrix.example.json \
  --evidence medical/examples/evidence.jsonl \
  --out runs/medical-v0.1.jsonl
```

> 当前 v0.1 尚未实现完整 production retriever / reranker / Agent tool executor；这些会在 harness adapter 上继续扩展。

---

# 4. Evaluation → Failure Diagnosis

已有 benchmark 已从单纯分数扩展到 Model Diagnosis：

```text
Evidence Graph
→ Model Query
→ Model Response
→ Rubric Eval
→ Failure Type
→ Optimization Candidate
→ Regression
```

现有 failure taxonomy 包括：

```text
STALE_KNOWLEDGE
SOURCE_HIERARCHY
OVERCLAIM
RELATION_SHORTCUT
METRIC_SALIENCE_BIAS
PRIORITIZATION_FAILURE
PASSIVE_ABSTENTION
EXPRESSION_HIERARCHY
AUDIENCE_MISMATCH
FORECAST_OVERCONFIDENCE
```

关键原则：

> **Observed Failure ≠ Capability Gap ≠ Proven Fix**

一次 bad case 只能先形成诊断假设，必须通过跨 case + held-out regression 才能证明 intervention 有效。

现有诊断：[`benchmark/diagnostics/failure-taxonomy.md`](benchmark/diagnostics/failure-taxonomy.md)

---

# 5. Intervention Router

新增：[`scripts/intervention_router.py`](scripts/intervention_router.py)

核心映射：

```text
stale knowledge      → retrieval / temporal truth
knowledge missing    → retrieval first; systematic gap → data / MidTrain
retrieval miss       → index / query / reranker
source hierarchy     → source-aware retrieval / hard negatives / SFT
overclaim            → preference pairs / uncertainty policy
reasoning failure    → reasoning SFT / task decomposition
unsafe medication    → safety gate + expert review + safety data
bad tool call        → Agent trajectory / tool schema / policy
passive abstention   → uncertain-but-actionable preference data
judge inconsistency  → judge calibration / human adjudication
```

规则配置：[`medical/configs/intervention-rules.json`](medical/configs/intervention-rules.json)

Router 输出的是 `intervention_hypothesis`，不是“已证明的修复方案”。

---

# 6. Training Data Export

新增：[`scripts/export_training_data.py`](scripts/export_training_data.py)

只有显式人工/专家审核为：

```json
{"training_candidate": {"review_status": "approved"}}
```

的 eval failure 才能进入 post-training export。

### SFT

```json
{
  "instruction": "...",
  "context": {"patient_context": {}, "evidence_snapshot": {}},
  "ideal_response": "...",
  "failure_type": "REASONING_FAILURE",
  "source_case_id": "..."
}
```

### Preference

```json
{
  "prompt": "...",
  "context": {},
  "chosen": "calibrated evidence-grounded response",
  "rejected": "overclaimed response",
  "failure_type": "OVERCLAIM",
  "source_case_id": "..."
}
```

**Eval failure 不自动等于训练数据。** 这是为了避免把错误的 gold / judge bias / 数据泄漏重新训练进模型。

---

# 7. Regression Gate

新增：[`scripts/regression_gate.py`](scripts/regression_gate.py)

每个 candidate model/system version 与 frozen baseline 比较：

```text
factuality
medical evidence sufficiency
temporal validity
useful abstention
target capability
critical clinical / medication safety errors
```

示例 policy：[`medical/configs/regression-policy.example.json`](medical/configs/regression-policy.example.json)

硬原则：

> **平均能力提升不能覆盖新增 Critical Medical Safety Error。**

```bash
python3 scripts/regression_gate.py \
  --baseline eval/baseline.jsonl \
  --candidate eval/candidate.jsonl \
  --policy medical/configs/regression-policy.example.json \
  --out eval/regression-report.json
```

失败时脚本以非零 exit code 退出，可以直接接 CI。

---

# Existing Decision Intelligence Benchmark

`benchmark/` 仍然保留，作为 Pharma / medical-evidence reasoning 的成熟测试床。

当前包含：

- controlled cases；
- frozen evidence snapshots；
- pre-registered gold / critical errors / anchors；
- blind scoring protocol；
- user-utility rubric；
- model diagnosis rubric；
- failure taxonomy；
- optimization cards；
- regression case 思路。

详情：[`benchmark/README.md`](benchmark/README.md)

---

# Repository

```text
pharma/                         # existing real-world pharma evidence track
benchmark/                      # decision intelligence + model diagnosis benchmark
medical/
  README.md
  clinical-track/               # clinical task families and case design
  truth-layer/                  # paragraph-level medical truth
  schemas/                      # case/evidence/run schemas
  configs/                      # harness/router/regression configs
  examples/                     # vertical-slice fixtures
scripts/
  model_harness.py              # multi-model runner
  intervention_router.py        # failure → intervention hypotheses
  export_training_data.py       # approved SFT / preference export
  regression_gate.py            # baseline vs candidate release gate
  ...                           # existing pharma intelligence scripts
docs/
  11-clinical-safety-boundaries.md
  12-medical-model-development-architecture.md
  13-medical-model-development-roadmap.md
```

---

# Current Status — 2026-09-05

## Already demonstrated

- real-world pharma evidence graph and temporal events;
- Claim / Evidence / Event representation;
- claim provenance audit;
- dynamic medical-state bad case (`STALE_KNOWLEDGE`); 
- controlled benchmark cases and pre-registered scoring;
- model failure taxonomy;
- clinical safety boundaries.

## Newly implemented in Medical Development v0.1

- development-loop architecture;
- Clinical Track task specification;
- paragraph-level evidence schema;
- clinical case schema;
- reproducible model-run schema;
- multi-model harness v0.1;
- deterministic Intervention Router v0.1;
- reviewed SFT / preference exporter v0.1;
- CI-style Regression Gate v0.1.

## Not yet proven / next validation

- production-scale guideline / drug-label ingestion;
- high-quality real clinical-case set;
- expert-reviewed medication-safety gold;
- full retriever / reranker evaluation;
- Agent tool execution and trajectory evaluation;
- multimodal image evaluation;
- calibrated LLM-as-Judge vs clinician agreement;
- actual SFT / preference intervention followed by held-out regression;
- sustained improvement on a medical model checkpoint.

The next milestone is deliberately small: **one fully traceable end-to-end clinical vertical slice**, then scale only after the loop works.

---

## Design Principle

```text
Evaluation is not the end of model development.
Evaluation should identify the failure,
locate the evidence boundary,
route the intervention,
and prove the fix with regression.
```
