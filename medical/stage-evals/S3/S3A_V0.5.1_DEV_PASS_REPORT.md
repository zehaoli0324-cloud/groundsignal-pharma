# S3a v0.5.1 Compositional Frame Parser — Development PASS Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Implementation: `s3a-compositional-frame-v0.5.1`  
> Frozen implementation commit: `0a3fe9ee29187cfb7e381da0f41bb1ae93875937`  
> Regression workflow: `33988726656`  
> Artifact: `s3a-v051-exposed-regression` (artifact ID `9975956882`, 90-day retention)  
> Status: **DEVELOPMENT PASS / ELIGIBLE FOR A NEW FRESH FREEZE; NOT A FRESH PASS**

## 术语表

- **Regression（回归测试）**：在已经暴露的数据上检查新实现是否破坏既有能力；不能证明新数据泛化。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中被正确抽取的比例。
- **Scope graph（作用域图）**：记录句子、子句、条件、人群、否定与模态归属的中间结构。
- **Frame-local binding（逐框架局部绑定）**：每个语义事件独立绑定人群、条件和极性。
- **Trace contract（轨迹契约）**：每个 frame 必须保留可审计的来源、触发族和作用域轨迹。
- **Fresh held-out（新鲜留出集）**：实现冻结后才创建、首次结果永久保留的未见测试集。

---

## 1. Version scope

v0.5.1 is a narrow architectural repair of the recorded v0.5.0 development failures. It does not introduce a new fresh dataset and does not claim generalization.

The three repaired mechanisms are:

```text
A. clause-local elided eGFR comparative resolution
B. target-local copular/passive negation
C. v0.4 fallback → v0.5 trace/provenance adaptation
```

Implementation remains compositional:

```text
free text
→ sentence segmentation
→ clause / scope graph
→ local-vs-inherited condition provenance
→ frame-local population + condition binding
→ event-family recognition
→ directed argument canonicalization
→ target-local polarity/modality
→ canonical semantic frame
→ proposition compilation
→ unresolved-critical abstention
```

---

## 2. Stage-specific development eval

The existing population-aware S3a evaluator was reused. No release threshold was changed after seeing results.

Required gates:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
Trace contract = PASS
```

Only already-exposed suites were used:

```text
s3a-extraction-gold-v0.1.json
s3a-extraction-heldout-v0.2.json
s3a-extraction-heldout-v0.3.json
s3a-semantic-frame-heldout-v0.4.json
```

---

## 3. Observed results

GitHub Actions workflow `33988726656` completed successfully.

| Exposed suite | Gold props | Pred props | TP | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 21 | 21 | 21 | 100% | 100% | 100% | n/a | 100% | PASS |
| v0.2 | 30 | 30 | 30 | 100% | 100% | 100% | 100% | 100% | PASS |
| v0.3 | 39 | 39 | 39 | 100% | 100% | 100% | 100% | 100% | PASS |
| v0.4 | 56 | 56 | 56 | 100% | 100% | 100% | 100% | 100% | PASS |

Aggregate exposed regression gate: **PASS**.

The v0.5.1 trace contract also passed. It now requires:

```text
scope_nodes
condition_source
semantic_frames
trigger_family
scope_trace
event_type
subject
object
polarity
modality
source_span
predicted_propositions
```

All emitted frames satisfied the contract.

---

## 4. What was repaired

### A. Condition scope

v0.5.0 could parse:

```text
existing user under eGFR 45 → reassess
```

but miss a later clause-local comparator:

```text
discontinuation only under 30
```

and incorrectly inherit `<45`.

v0.5.1 separates explicit local condition candidates from sentence inheritance. A bare comparator can recover an elided eGFR variable only when the enclosing sentence has already established eGFR context. Plain numbers are not promoted to eGFR conditions. Every node records whether its final condition came from:

```text
clause_local
sentence_inherited_unique
unresolved_or_ambiguous
```

### B. Negation scope

Target-local copular/passive negation is now evaluated structurally around the target predicate, covering constructions of the form:

```text
is not <target>
is not a/an <target>
was/were not <target>
```

This repairs the v0.5 wrong-positive contraindication polarity without making negation passage-global.

### C. Fallback provenance

A retained v0.4 semantic frame is no longer allowed to enter the v0.5.1 output without adaptation. Every fallback receives:

```text
trigger_family = v0.4_fallback:<event_type>
scope_trace.scope = legacy_fallback_adapted
scope_trace.adapter = s3a-compositional-frame-v0.5.1
scope_trace.source_extractor = s3a-semantic-frame-v0.4
scope_trace.node_id = matched scope node when available
```

This resolves the prior `LEGACY_TRACE_ADAPTER_GAP`.

---

## 5. Interpretation

The result is a **development pass**, not a S3a release pass.

The exposed regression history now shows that the v0.5 compositional architecture can preserve all previously discovered S3a behaviors while making condition provenance and legacy fallback use auditable. However, v0.2, v0.3 and v0.4 have all already been observed and cannot serve as evidence of unseen-language generalization.

No claim is made that S3a free-text extraction is safe for automatic Knowledge Graph truth insertion.

---

## 6. Release decision

```text
S3b structured entailment          = CONDITIONAL PASS
S3a v0.5.1 exposed regression      = PASS
S3a v0.5.1 trace contract          = PASS
S3a v0.5.1 fresh validation        = NOT RUN
S3a free-text release              = HARD FAIL / BLOCKED
End-to-end S3                      = HARD FAIL
```

Therefore downstream automatic trust remains blocked.

---

## 7. Next permitted step

The implementation is now eligible to be frozen for a brand-new S3a held-out. The next iteration should not modify `s3a_compositional_frame_parser_v051.py` before the first observation.

The new fresh suite should stress capabilities rather than known phrases, especially:

```text
multiple numeric variables in one sentence
elided variable resolution with competing candidate variables
nested / coordinated negation
modal language (may, should, must, insufficient to conclude)
condition scope across conjunction and disjunction
multiple populations in one sentence
passive/inverse directed relations
multi-frame sentences sharing only some arguments
adversarial distractor clauses
unknown critical semantics requiring abstention
```

The first run must be preserved whether PASS or FAIL. Only a fresh S3a pass should unlock a new end-to-end S3 held-out.
