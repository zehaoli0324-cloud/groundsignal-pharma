# S3a v0.5 Compositional Frame Parser — Development Contract

> **S3a = Semantic Proposition Extraction（语义命题抽取）**
> Version: `s3a-compositional-frame-v0.5.0`
> Status at creation: **development only / no fresh claim**

## 术语表

- **Semantic frame（语义框架）**：标准命题生成前的结构化事件/关系表示。
- **Scope graph（作用域图）**：记录句子、子句、条件、人群和否定/模态作用域的轻量结构。
- **Argument binding（参数绑定）**：把事件的 subject/object、患者人群和数值条件绑定到正确 frame。
- **Polarity（极性）**：肯定或否定方向。
- **Modality（模态）**：事实断言、证据不足、限制性陈述等强度/状态。
- **Regression（回归测试）**：只验证新实现没有破坏已经暴露的数据；不能证明新数据泛化。
- **Fresh held-out（新鲜留出集）**：实现完全冻结后才创建、首次结果永久保留的未见测试集。

## Why v0.5 exists

The immutable S3a v0.4 fresh run failed at:

```text
F1                              40.00%
Critical Proposition Recall     25.58%
Polarity Accuracy               80.00%
Population Accuracy             94.12%
Condition Binding Accuracy     100.00%
```

The failure localized the remaining bottleneck upstream of numeric-condition parsing: event/relation recognition, negation/modality scope, population leakage, directed arguments and cross-clause composition.

v0.5 therefore does **not** add another flat synonym list to the v0.4 parser. It introduces a compositional intermediate representation:

```text
free text
→ sentence segmentation
→ clause graph
→ sentence-level shared context inventory
→ frame-local condition/population binding
→ semantic event-family recognition
→ directed argument canonicalization
→ local negation/modality scope
→ canonical semantic frame
→ proposition compilation
→ unresolved-critical abstention
```

## Architectural rules

1. Population is frame-local. Passage-global population assignment is not allowed when competing populations occur in the same sentence.
2. A unique sentence-level eGFR condition may be inherited by multiple local frames; multiple distinct conditions must remain local.
3. `same eGFR`-style anaphora can inherit the unique sentence condition without copying unrelated conditions.
4. Negative evidence/modality is evaluated in a local window around the event family; a negative cue in another clause must not automatically flip all frames.
5. Biomarker/outcome associations are canonicalized as `biomarker → outcome` regardless of surface argument order.
6. Guideline supersession is a directed relation `newer → older`; active and passive/inverse syntax must compile to the same direction.
7. A v0.5 frame replaces same-event-type v0.4 fallback frames. The merge is not a union, preventing already-known v0.4 wrong-polarity/scope frames from surviving.
8. v0.4 remains fallback only to protect exposed regressions while v0.5 is under development. Fresh validation must evaluate the frozen combined implementation exactly as shipped.
9. Unresolved critical semantics remain eligible for abstention; v0.5 must not force a proposition merely to increase recall.

## Development eval contract

This version may use only these **already exposed** suites during implementation:

```text
s3a-extraction-gold-v0.1.json
s3a-extraction-heldout-v0.2.json
s3a-extraction-heldout-v0.3.json
s3a-semantic-frame-heldout-v0.4.json
```

The existing population-aware S3a evaluator is reused. Development gates remain:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
```

The GitHub Actions workflow also requires every output frame to retain an auditable trace with:

```text
scope_nodes
semantic_frames
trigger_family
scope_trace
event_type
subject
object
polarity
modality
source_span
```

Passing these regressions means only that v0.5 is eligible to be frozen for a new fresh evaluation. It does **not** mark S3a or end-to-end S3 as PASS.

## Fresh-eval rule

Do not create the v0.5 fresh held-out until:

1. the v0.5 implementation commit is frozen;
2. exposed v0.1-v0.4 regression CI is green;
3. the development metrics and any failures are written to the repository;
4. no implementation changes occur between freeze and held-out construction.

After the fresh suite is created, its first observation must be preserved permanently whether PASS or FAIL.
