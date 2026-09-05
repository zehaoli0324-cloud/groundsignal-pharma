# S3 — Evidence Verification & Temporal Truth Eval

> **S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）**

## 目标

S2 已负责找到权威来源、当前文档和关键证据段落。S3 不再评价“有没有搜到”，而评价：

> **系统有没有把已经找到的证据理解对。**

## S3 v0.1 输入输出

```text
verified evidence passage / normalized evidence proposition
        +
candidate medical claim
        ↓
Evidence Verifier
        ↓
relation
scope
numeric threshold
negation / exception
temporal status
        ↓
S3 evaluator
```

### relation（证据关系）

- `DIRECT_SUPPORT`：证据直接支持候选结论。
- `PARTIAL_SUPPORT`：只支持结论的一部分，候选结论仍包含未被证据覆盖的扩展。
- `CONTRADICTS`：证据与候选结论直接冲突。
- `DOES_NOT_SUPPORT`：证据没有提供足够信息支持该结论。

## v0.1 核心指标

```text
Relation Accuracy
High-risk False-Support Rate
Threshold Accuracy
Scope Accuracy
Negation / Limitation Accuracy
Temporal Status Accuracy
```

其中最重要的是：

> `High-risk False-Support Rate = 0`

即高风险情况下，系统不能把“不支持/矛盾/仅部分支持”的 claim 错判成 `DIRECT_SUPPORT`。

## v0.1 failure taxonomy

```text
CLAIM_ESCALATION
THRESHOLD_ERROR
SCOPE_EXPANSION
NEGATION_MISS
EXCEPTION_MISS
CAUSALITY_ESCALATION
INCIDENCE_ESCALATION
REGISTRATION_TO_EFFICACY
TEMPORAL_STATUS_ERROR
SUPERSEDED_AS_CURRENT
```

## 首个 vertical slice（纵向闭环）

1. metformin renal threshold；
2. apixaban + NSAID bleeding-risk evidence；
3. sertraline serotonin-syndrome warning；
4. FAERS signal ≠ causality / incidence；
5. trial registration ≠ efficacy；
6. current vs superseded evidence negative controls。

## 边界

v0.1 使用短的、来源约束的 normalized evidence propositions（标准化证据命题）和受控候选 claims，不复制长篇原始标签文本。

它评价的是 verifier 的证据边界判断，不等于完整临床专家 gold，也不等于开放式医学推理已经解决。
