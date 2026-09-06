# GroundSignal Medical — 算法岗配合方案与交接指南

> 目标：明确评估/领域研究侧与算法侧的责任边界，保证算法优化可复现，同时保护 fresh evaluation 的独立性。

## 1. 术语表

- **RAG — Retrieval-Augmented Generation（检索增强生成）**：先检索外部证据，再让模型基于证据生成回答。
- **NLI — Natural Language Inference（自然语言推断）**：判断证据与命题之间是支持、反驳还是信息不足。
- **LLM-as-a-Judge — Large Language Model as a Judge（大模型裁判）**：使用模型对其他模型输出进行结构化评分，需要与人工标准校准。
- **SFT — Supervised Fine-Tuning（监督微调）**：用高质量输入-理想输出对训练模型。
- **DPO — Direct Preference Optimization（直接偏好优化）**：利用 chosen/rejected 偏好对优化模型行为。
- **LoRA — Low-Rank Adaptation（低秩适配）**：参数高效微调方法，只训练少量低秩参数。
- **Ablation（消融实验）**：移除或替换某个组件，确认收益究竟来自哪里。
- **RACI**：Responsible（执行）、Accountable（最终负责）、Consulted（需协商）、Informed（需知会）的协作责任划分。

## 2. 核心边界：评估侧定义“什么算对”，算法侧负责“怎样做到”

评估/领域侧主要负责：用户需求、科学/医学任务定义、Stage contract、数据与证据质量、rubric、hard gate、fresh suite、failure taxonomy、gold review 和最终 release decision。

算法侧主要负责：retrieval/rerank、模型推理、结构化抽取、NLI、embedding/相似度、Agent planner、tool policy、Judge、训练/微调、calibration 和效率优化。

共同负责：输入输出接口、trace、baseline、ablation、错误归因、实验设计、回归范围和资源预算。

最重要的隔离规则：**下一轮未曝光 fresh suite 不交给负责修复的算法工程师。**算法工程师只接收已经完成 first observation 的 failure pack；修复 freeze 后，由评估侧重新创建下一轮 fresh suite。

## 3. 本项目各 Stage 与算法岗的配合强度

| Stage | 算法协作强度 | 算法岗主要工作 | 评估/领域侧主要工作 |
|---|---:|---|---|
| S1 User Need / Workflow Discovery | 低 | 日志聚类/采样工具可选 | 用户访谈、任务频率、风险矩阵、workflow 定义 |
| S2 Knowledge Search & Source Routing | **高** | intent router、retriever、reranker、query decomposition、negation/exclusion 处理 | source policy、truth set、held-out queries、routing rubric |
| S3 Evidence Verification & Temporal Truth | **高** | proposition extraction、NLI/entailment、calibration、abstention、长文本建模 | 原子命题 gold、证据关系、时间语义、critical-error 定义 |
| S4 Medical KG Construction / Update | 中高 | entity linking、relation extraction、temporal conflict resolution、graph update | ontology、truth-state contract、冲突规则、不变量、专家审核 |
| S5 Controlled Case / Benchmark Factory | 中 | 语义近重复/血缘检测、hard-negative 生成、数据去重算法 | split/gold/authority/provenance、fresh suite、训练隔离、release gate |
| S6 Model / RAG / Agent Harness | **最高** | RAG、planner、tool calling、memory、prompt policy、model runtime | task contract、工具权限、安全约束、evidence injection contract、eval |
| S7 Evaluation & Safety Gate | **高** | Judge model、calibration model、安全分类器、uncertainty scoring | expert rubric、human calibration set、hard gate、裁判一致性分析 |
| S8 Failure Diagnosis | 中高 | embedding clustering、representation analysis、自动 attribution 辅助 | failure taxonomy、root-cause review、干预优先级 |
| S9 Intervention / Post-training Data | **最高** | SFT / LoRA / DPO、数据配比、训练、超参、ablation | 训练数据资格、failure→data mapping、held-out 隔离、回归要求 |
| S10 Candidate + Held-out Regression | **高** | candidate inference、统计/显著性、性能/成本优化 | frozen held-out、release criteria、安全回退、最终 decision |

## 4. 哪些部分必须找算法岗，哪些不应该甩给算法岗

### 必须算法岗深度参与

1. **S2 检索与路由**：当前 negation/exclusion 是明确缺口，仅靠增加规则会迅速失控，需要 retrieval/rerank/query representation 的算法实验。
2. **S3 命题抽取与证据推断**：真实长文本、噪声、多来源下的 recall、false-support、abstention 需要模型/NLI/calibration 能力。
3. **S5 语义血缘检测**：v0.6.1 目前是 exact semantic-core fingerprint。对 paraphrase、partial reuse、near-duplicate 的检测需要 embedding、近重复算法或 learned detector；这是 S5 中最需要算法协作的部分。
4. **S6 RAG/Agent Harness**：这是核心模型系统，算法岗应成为实现 owner。
5. **S7 Judge calibration**：LLM-as-a-Judge 需要人类标签对齐、偏差测量、阈值校准和模型选择。
6. **S9 真实干预实验**：SFT/LoRA/DPO、数据配比与 ablation 必须由算法训练链路完成。
7. **S10 真实 candidate regression**：需要统一推理配置、统计比较、成本/延迟/能力 trade-off。

### 不应直接交给算法岗决定

- 哪些临床/科学 claim 可以被证据支持；
- held-out/gold 的最终归属；
- fresh suite 的未曝光内容；
- failure severity；
- 医学 hard gate；
- 是否可以从 synthetic/CI 结果声称临床有效；
- release 的证据等级命名。

这些属于评估治理、领域判断和证据治理，否则会形成 self-grading（实现者给自己出题和判卷）。

## 5. 推荐团队结构

### Track A — Eval / Domain / Data

负责 Stage contract、数据、gold、fresh eval、failure taxonomy、release evidence。

### Track B — Algorithm / Model

负责模型、retrieval、NLI、Agent、Judge、training、calibration、efficiency。

### Track C — Eval Infrastructure / Platform

负责 evaluator runner、version pinning、trace、CI、artifact、reproduction、dashboard。

小团队可以一人兼任多个 Track，但 **fresh suite author 与本轮 repair implementer 在时间上仍需隔离**。

## 6. 一轮标准协作流程

```text
评估侧：定义 Stage contract + development eval
        ↓
算法侧：实现 baseline / 修 development issue
        ↓
双方：确认接口、trace、freeze candidate
        ↓
冻结 implementation commit
        ↓
评估侧：独立创建 fresh suite（算法侧不可见）
        ↓
first observation
        ↓
若 FAIL：评估侧生成 failure pack
        ↓
算法侧：根据 capability gap 做 generic repair + ablation
        ↓
评估侧：旧 failure pack 变 exposed regression
        ↓
双方：cross-stage regression
        ↓
重新 freeze
        ↓
评估侧：下一轮全新 fresh family
```

如果算法侧在 freeze 前看到了 fresh case，该 case 自动降级为 development/exposed，不能再用于 independent fresh 证据。

## 7. 评估侧交给算法侧的标准 Handoff Package

每个需要算法修复的 Stage，统一交付：

```text
01_STAGE_CARD.md
02_DATA_CONTRACT.json
03_BASELINE_METRICS.json
04_EXPOSED_FAILURES.json
05_CAPABILITY_GAPS.md
06_ACCEPTANCE_GATES.json
07_REPRO_COMMANDS.md
08_UPSTREAM_DOWNSTREAM_CONTRACT.md
```

其中：

**STAGE_CARD**：目标、scope、非目标、owner、上下游依赖。

**DATA_CONTRACT**：输入/输出字段、类型、版本、来源、缺失值规则、ID/时间语义。

**BASELINE_METRICS**：按 slice 输出，不只给一个总分。

**EXPOSED_FAILURES**：只包含已经完成 first observation 的样例；不得混入下一轮 fresh。

**CAPABILITY_GAPS**：用能力语言描述问题，例如“需识别语义近似的 held-out 血缘”，而不是“case 17 要返回 BLOCK”。

**ACCEPTANCE_GATES**：包括能力阈值与不可妥协 hard gates。

**REPRO_COMMANDS**：固定环境、模型、seed、命令、输出路径。

**UPSTREAM_DOWNSTREAM_CONTRACT**：说明修复改变哪些字段以及哪些 Stage 需要联动回归。

## 8. 算法侧返还的标准 Algorithm Change Package

算法岗完成修复后应返还：

```text
implementation_commit
change_summary
model_or_index_version
training_data_manifest（如有训练）
hyperparameters（如有）
reproduction_command
baseline_vs_candidate_metrics
ablation_results
known_failure_modes
latency_cost_memory_delta
interface_changes
```

禁止只返回“线上效果变好”或截图。任何训练数据必须能追溯到 source/split/review status，且 held-out/regression 不得进入训练。

## 9. Definition of Done（算法交付完成标准）

算法侧“做完”至少意味着：

```text
exposed failure regression PASS
原 baseline slice 不退化
critical hard gate 无新增失败
接口/schema/trace 可复现
ablation 能解释主要收益来源
资源变化已记录
实现 commit 可 freeze
```

这仍然**不等于 Stage release**。Stage release 需要 freeze 后的新 fresh evidence，由评估侧完成。

## 10. 当前项目的具体协作优先级

### P0：现在就可以并行给算法岗

**A. S5 semantic lineage detector（语义血缘检测器）**

目标：识别 benchmark/held-out 内容经过 paraphrase、字段局部改写、partial reuse 后的近重复污染。

算法侧只拿公开/开发 split 构造 detector，不拿下一轮 fresh。候选技术可以比较 lexical fingerprint、MinHash/SimHash、embedding cosine、cross-encoder 或组合方法；评估侧负责 contamination taxonomy、阈值 hard gate 和隐藏 fresh。

接口建议：

```json
{
  "candidate_id": "...",
  "nearest_reference_id": "...",
  "similarity": 0.0,
  "method": "...",
  "decision": "ALLOW|REVIEW|BLOCK",
  "evidence": ["matched_fields_or_spans"]
}
```

**B. S2 negation / exclusion routing**

算法目标：处理“不要某类证据”“排除某来源”“不是 X 而是 Y”等组合约束；需要与 source-role、query decomposition 和 reranker 联动。

**C. S3 long/noisy evidence verification**

算法目标：提高长文本、多来源、冲突证据下的 critical proposition recall，同时维持 high-risk false-support≈0，并给出可校准 abstention。

### P1：S5 bounded structural release 后启动

**D. S6 RAG/Agent dedicated evaluation + implementation**：算法岗成为主实现 owner，评估侧保留 task/tool/safety contract。

**E. S7 LLM-as-a-Judge calibration**：建立 50–100 个专家双标/复核样本，测 Judge 与专家的一致性、系统性偏差和阈值稳定性。

### P2：模型链路稳定后

**F. S8 failure clustering / attribution**；**G. S9 LoRA/SFT/DPO 干预**；**H. S10 held-out candidate regression**。

## 11. 当前 S5 v0.6.1 的交接说明

当前事实：

```text
v0.6 independent fresh F20–F23   FAIL（不可变历史证据）
v0.6.1 exposed regression         PASS
S5 bounded independent release    NOT ESTABLISHED
gold review                       INCOMPLETE
S6 automatic trust                BLOCKED
```

因此算法岗此刻不需要再修 F20–F23 的具体 case；它们已经变为 exposed regression。更有价值的任务是构建**不依赖隐藏测试的语义近重复/血缘检测能力**，供下一轮 S5 generalization 使用。

评估侧下一轮会独立测试：paraphrase、partial-derived contamination、cross-split semantic leakage、进一步 identity canonicalization 等新 family。算法侧不应提前拿到这些具体 fixture。

## 12. 一个可以直接复制到 Issue/任务书的交接模板

```markdown
# Algorithm Handoff — Stage SX

## Objective
要提升的可验证能力：

## Current Evidence
- implementation freeze:
- strongest evidence class:
- baseline metrics:
- hard-gate status:

## Exposed Failure Pack
- failure IDs:
- observations:
- root causes:

## Capability Gap
用能力语言描述，不写针对 fixture 的答案。

## Allowed Data
- dev:
- regression:
- prohibited held-out/fresh:

## Required Interface
input/output/schema/trace/version。

## Acceptance Before Freeze
- exposed regression:
- baseline non-regression:
- hard gates:
- latency/cost budget:
- ablation:

## Deliverables
implementation commit + reproducible command + metrics + ablation + known limitations。

## Fresh Evaluation Rule
实现 freeze 后，由 eval owner 独立创建下一轮 fresh suite；repair owner 不提前查看。
```

## 13. 最终责任原则

算法岗负责让系统能力提升；评估/领域侧负责证明提升是否真实、是否泛化、是否足够安全。两者必须协作，但不能把“实现”和“最终独立判卷”合成同一个角色，否则 benchmark 很快会退化为开发测试。
