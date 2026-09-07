# GroundSignal Medical AI Capability Portfolio

> Portfolio status: all ten capability tracks are in scope. Inclusion in the portfolio does not mean
> clinical readiness or completed implementation.

## 术语表

- **Capability portfolio（能力版图）**：项目长期覆盖的产品与研究方向，以及每个方向的证据门槛。
- **Benchmark（基准评测集）**：用固定任务、答案契约和评分规则比较模型能力的测试集合。
- **Agent（智能体）**：能够规划步骤、检索信息、调用工具并根据结果继续行动的模型系统。
- **Multimodal model（多模态模型）**：能够联合处理文本、图像及其他数据形式的模型。
- **Decision support（辅助决策）**：帮助专业人员整理证据和风险，但不替代医生作出诊断或治疗决定。
- **Clinical validation（临床验证）**：在真实临床环境中，由合格专业人员和预先规定的方案验证安全性与有效性。

## 1. Portfolio decision

GroundSignal Medical formally includes these ten tracks:

| Track | Role in the system | Current maturity | Current evidence | Required next evidence |
|---|---|---|---|---|
| 医学问答 | 回答证据受限的医学问题 | 评测原型 | 路由、检索、命题与证据关系评测 | 更广真实问题、专家答案和多模型运行 |
| 辅助诊疗 | 组织鉴别诊断、缺失信息与风险 | 结构预研 | clinical-reasoning case family | 真实临床流程、医生验证和前瞻性安全评估 |
| 用药安全 | 药物禁忌、相互作用、阈值和升级处理 | 重点评测轨 | MEDSAFE families + safety hard gates | 更广药物/患者组合与药师审核 |
| 医学影像 | 影像发现、报告和随访建议的证据约束 | 接口预留 | imaging report schema + REPORT-004 | 原始影像输入、标注、模型和影像专家评测 |
| 报告解读 | 检验、影像、病理等报告的边界化解释 | 初步实现 | CBC 与不确定影像报告案例 | 多格式真实报告、纵向记录和专家 gold |
| 医疗 Agent | 检索、核验、工具调用和停止决策 | Harness 原型 | trajectory/tool-policy schema + AGENT-001 | S5 放行后开展独立 S6 评测 |
| 多模态医疗模型 | 联合处理文本、图像和结构化数据 | 结构预留 | modality references in case schema | 冻结模型、真实模态数据、跨模态 verifier |
| Benchmark | 构建受控 family、留出集与回归集 | 核心实现 | S5 v0.2–v0.8 fresh/evaluated lineage | fresh structural PASS + gold review |
| 评测 Agent | 自动运行、评分、归因和回归保护 | 工程原型 | staged evaluators, hard gates, CI | human/Judge calibration + multi-model trials |
| 训练数据 | 从错误到干预数据并控制污染 | 安全出口开发中 | authenticated provenance/export boundary | S5 bounded release 后才允许自动信任 |

## 2. Shared architecture

The ten tracks are not ten independent demos. They share one evidence and evaluation backbone:

```text
user task / medical input
→ source routing and retrieval
→ atomic claims and evidence relations
→ temporal knowledge graph
→ controlled case / benchmark identity
→ model or Agent execution
→ answer, citation and trajectory evaluation
→ failure diagnosis
→ training-data intervention
→ independent held-out regression
```

This design lets one failure be located at the correct layer. For example, an unsafe medication
answer may come from wrong retrieval, unsupported reasoning, missing uncertainty, an Agent that did
not stop, or contaminated training data. A single final-answer score cannot distinguish these causes.

## 3. Maturity ladder

Every track must use the same maturity vocabulary:

| Level | Meaning | Allowed claim |
|---|---|---|
| M0 | scope only | “included in roadmap” |
| M1 | schema/interface | “supports structured inputs/outputs” |
| M2 | synthetic evaluation | “passes the named synthetic slice” |
| M3 | real-source + expert reviewed | “validated on the stated retrospective dataset” |
| M4 | prospective workflow evaluation | “tested in the named real workflow” |
| M5 | governed clinical deployment | only after regulatory, safety and operational requirements |

No track may inherit a higher maturity level from another track. A Benchmark PASS does not make an
image model clinically valid; a medical expert review does not prove training-data lineage safety.

## 4. Track-specific definition of done

### 医学问答与报告解读

- source-backed answers and sentence-level evidence links;
- explicit separation of observation, interpretation and diagnosis;
- contradiction, stale evidence and missing-information handling;
- expert-reviewed real cases and calibrated abstention.

### 辅助诊疗与用药安全

- differential hypotheses rather than forced single diagnosis;
- contraindication, interaction, dose/organ-function threshold and red-flag gates;
- clear escalation to clinicians or emergency care when required;
- clinician/pharmacist review and prospective workflow testing before any clinical claim.

### 医学影像与多模态模型

- immutable image identity and de-identification provenance;
- text-image alignment, lesion/finding grounding and report consistency;
- modality-missing and modality-conflict cases;
- subgroup, device/site shift and image-quality evaluation;
- specialist review. Current repository does not yet satisfy these conditions.

### 医疗 Agent 与评测 Agent

- tool selection, retrieval freshness, evidence use and stop correctness;
- complete trajectory capture without leaking hidden gold data;
- deterministic checks plus calibrated human/model judging;
- adversarial tool failure, stale result and prompt-injection evaluation.

### Benchmark 与训练数据

- external trust root, immutable provenance and split isolation;
- held-out/regression lineage protection across copies and transformations;
- first-observation preservation and post-repair fresh evaluation;
- expert gold approval independent from structural safety;
- training export remains fail-closed until S5 bounded release.

## 5. Current sequencing

1. Preserve the completed S5 v0.8.1 broader development calibration as exposed-only evidence.
2. Explicitly freeze the repaired S5 implementation, then obtain a new independent fresh result.
3. Complete expert gold review independently.
4. Only then start dedicated S6 medical-question, report and Agent model runs.
5. Add real-source medication/report datasets before claiming M3.
6. Build the image/multimodal data contract before integrating an image model.
7. Keep clinical decision-support claims behind clinician and workflow validation.

## 6. Explicit non-claims

The current repository is not a medical device, autonomous diagnostic system, treatment recommender,
validated radiology model, or clinically deployed multimodal model. It is an evidence-grounded
evaluation and post-training infrastructure prototype with controlled medical task families.
