# S3a v0.5.4 Typed Event Graph + Relation-Family Arbitration — Development PASS

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.4`  
> Parser implementation commit: `33dde2507afb8d34d47f3103ee0bfbfaf716ec5f`  
> Primary exposed-regression workflow: `33999957392`  
> Raw-metric persistence workflow: `33999993603`  
> Raw-result preservation commit: `12690961a5dfadd21ac6a092fd4c596db189fd2c`  
> Status: **DEVELOPMENT PASS — fresh validation NOT RUN**

## 术语表

- **Typed event graph（类型化事件图）**：先识别事件、数值变量、人群和极性，再把条件/人群/否定明确绑定到对应事件节点。
- **Relation-family arbitration（关系族仲裁）**：同一语义关系存在多个 legacy/repaired 候选时，只保留方向、参数和极性一致的规范结果，避免“正确帧 + 错误帧”同时输出。
- **Non-destructive repair（非破坏式修复）**：保留成熟基线，只修改被类型化 ownership 证明存在冲突的字段，而不是整族重建。
- **Abstention（弃权）**：高风险语义无法由当前封闭本体无损表示时拒绝自动生成真值。
- **Unsafe simplification（不安全简化）**：把带复杂条件/分支的安全关键规则错误压缩成更简单的自动真值。
- **Exposed regression（已暴露回归集）**：开发者已经看过的数据，只能证明防回归，不能证明新的泛化能力。

---

## 1. Why v0.5.4 exists

v0.5.3 strengthened semantic typing and the ontology guard, but failed development regression because it rebuilt the whole management frame family and appended repaired relations without removing contradictory legacy frames.

The dominant v0.5.3 failure pattern was architectural:

```text
mature base frame
+ whole-family replacement
+ additive relation repair
-> population / scope regression
-> correct + incorrect frames can coexist
```

v0.5.4 changes the composition strategy rather than adding case-specific answers.

---

## 2. Structural changes

### A. Mature v0.5.2 baseline retained

The parser starts from the v0.5.2 semantic-frame output. Previously correct management and relation frames are retained by default.

### B. Event-local typed ownership

Management event mentions receive local windows inside each sentence. Typed eGFR conditions, population mentions and polarity cues are attached to those event windows.

A field is changed only when ownership evidence exists. Examples of generic repair behavior include:

```text
reassessment <46 AND discontinuation <29
-> each threshold binds to its nearest event

renal rule + negative platelet/age clause
-> renal condition cannot leak into the unrelated negative event

initiation restriction with no explicit population label
-> semantic event implies new_or_initiating_user
```

### C. Relation-family arbitration

Canonical relation candidates are generated for:

```text
causality
endpoint declaration / achievement / absence-of-result
trial option support
current-guideline recommendation
supersession/currentness
inverse biomarker association
```

When a canonical repaired candidate proves a legacy candidate inconsistent, the conflicting legacy frame is removed before proposition compilation.

### D. High-risk guard normalization

The v0.5.3 type-aware ontology guard is reused and extended to cover passive/permanent cardiac suspension morphology. Trial status `SUSPENDED` remains typed as a study-state relation and is not confused with a medication action.

---

## 3. Reused preregistered development gates

No new fresh data were created.

Proposition gates:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
```

Safety gates:

```text
Required-abstention accuracy = 1.00
Known-case abstention rate <= 0.05
Trace contract = PASS
No required-abstention item may emit partial/simplified truth
```

---

## 4. Development regression results

Primary workflow `33999957392` completed successfully, including the final enforced combined gate.

Raw deterministic replay was persisted under:

`medical/stage-evals/S3/runs/s3a-v054-exposed-dev-pass/`

| Exposed suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 96.43% | 96.43% | 96.43% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.5.2 | 98.63% | 98.63% | 98.63% | 98.18% | 100.00% | 100.00% | 98.63% | PASS |

Compared with the v0.5.3 exposed result on the v0.5.2 suite:

```text
F1                85.14% -> 98.63%
Critical Recall   83.64% -> 98.18%
Condition         91.30% -> 98.63%
Population        96.92% -> 100.00%
```

The older v0.1-v0.3 suites return to 100%, and v0.5.1 returns to 66/66 exact propositions. This supports the non-destructive-repair design choice, but remains exposed evidence only.

---

## 5. Abstention and safety results

```text
v0.5.1 mandatory-abstention cases       4/4 correct
v0.5.1 known-case false abstentions     0/38
v0.5.2 mandatory-abstention cases       6/6 correct
v0.5.2 known-case false abstentions     0/40
Abstention gate                         PASS
```

The older QTc/torsades permanent-suspension case is now blocked correctly together with all six v0.5.2 unknown-critical cases.

Unsafe-simplification invariant:

```text
required-abstention items                 6
unsafe simplified propositions            0
Gate                                    PASS
```

Therefore the exposed ALT/bilirubin, oxygen/BP, conditional-withholding and other non-representable high-risk rules do not become partial machine truth.

Trace contract:

```text
rows checked                             190
trace failures                             0
Gate                                    PASS
```

Combined development decision:

```text
all exposed proposition suites          PASS
abstention safety                       PASS
trace contract                          PASS
unsafe-simplification invariant         PASS
combined development release            PASS
fresh validation                        NOT RUN
```

---

## 6. Residual exposed diagnostics

Development PASS is not equivalent to perfect extraction.

Three exposed diagnostics remain:

1. `S3A4-021`: a single eGFR condition preceding two contrastive events is not propagated to the second initiation event;
2. `S3A4-022`: `same eGFR` in a second clause is not propagated to the initiation event;
3. `S3A52-037`: the immutable gold labels `same eGFR` as `eGFR =42` after an antecedent `below eGFR 42`, while v0.5.4 preserves the antecedent operator (`LT 42`).

The third case remains an evaluation-quality ambiguity already documented in the v0.5.2 fresh report. The immutable exposed dataset is not edited. Even with this disagreement, every preregistered development threshold passes.

These residuals must remain visible in future regression reports; they are not grounds for claiming 100% performance.

---

## 7. Release decision

```text
S3b structured entailment             = CONDITIONAL PASS
S3a v0.5.4 development proposition    = PASS
S3a v0.5.4 development abstention     = PASS
S3a v0.5.4 trace                      = PASS
S3a unsafe-simplification invariant   = PASS
S3a v0.5.4 fresh validation           = NOT RUN
S3a free-text release                 = HARD FAIL / BLOCKED
End-to-end S3                         = HARD FAIL
S4 automatic truth ingestion          = BLOCKED
```

The latest independent fresh evidence is still v0.5.2 FAIL. Therefore v0.5.4 is only qualified to enter a new independent held-out evaluation; it is not a released free-text truth extractor.

---

## 8. Next step

Freeze a brand-new **v0.5.4 fresh/shadow-held-out** only after the parser remains unchanged.

The new suite should emphasize capability families rather than reused wording:

```text
multi-event clauses with preposed/shared conditions
cross-sentence condition boundaries
multiple numeric variable types in one sentence
negative management statements with non-renal conditions
active/passive relation direction under negation
endpoint declaration vs achievement vs absence-of-result
short guideline anaphora and temporal replacement
high-risk unknown actions/conditions requiring abstention
known representable paraphrases that must not false-abstain
```

The first observation must be permanently preserved. Only a fresh v0.5.4 PASS can justify a new end-to-end S3 held-out.
