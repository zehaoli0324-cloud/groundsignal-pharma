# S3a v0.5.5 Typed Scope Linker + Safety Error Gate — Development FAIL

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.5`  
> Parser last-change commit: `3caad022ab9b070a206a4d2307d74cc78093fcc9`  
> Safety evaluator last-change commit: `419bd6f0af79ba3b8665ff5dc09995c9f37d4e82`  
> Workflow source commit: `7fd97d8f207ca699369cc342d6c6e58aaa375c33`  
> Workflow: `34003220909`  
> Raw-result preservation commit: `69429d721aed4c7233bccdcaac6ea15f2dcaf2a4`  
> Artifact: `s3a-v055-exposed-scope-safety-regression` / ID `9980111993`  
> Artifact SHA-256: `bfb075e60207792b647dbb0761686014ac2bf6e2c9f611615963dacb6b8719ce`  
> Status: **DEVELOPMENT FAIL — fresh validation NOT RUN**

## 术语表

- **Typed scope linker（类型化作用域链接器）**：把人群连续性、条件连续性和事件作用域作为不同类型的边处理，而不是共享一个句子级上下文。
- **Endpoint scope（终点作用域）**：区分“声明了终点”“终点达成”“证据证明终点达成”三个不同语义事件。
- **Abstention（弃权）**：当高风险语义无法由当前封闭本体安全表示时拒绝生成自动真值。
- **High-risk false positive（高风险假阳性）**：负向或不足证据被系统升级为临床/研究正向结论。
- **Exposed regression（已暴露回归集）**：开发者已经看过的数据，只用于防回归，不构成新的泛化证据。

---

## 1. Evaluation contract

No new fresh or shadow held-out was created for v0.5.5. The development evaluation reused all previously exposed suites, including the immutable v0.5.4 fresh first-run dataset after it became exposed regression data.

Historical fresh artifacts and labels were not modified.

The existing proposition gates were reused:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
```

Abstention gates were reused:

```text
Required-abstention accuracy = 1.00
Known-case abstention rate <= 0.05
No partial truth on mandatory-abstention items
```

A new development-only semantic safety gate was added to address evaluation blind spots diagnosed in v0.5.4:

```text
silent unknown-critical non-abstention count = 0
partial/simplified truth emission count      = 0
high-risk semantic false-positive count      = 0
```

This new evaluator is not applied retroactively to historical fresh reports.

---

## 2. v0.5.5 architecture

v0.5.5 wraps the mature v0.5.4 parser instead of rebuilding semantic families.

Structural additions:

```text
1. population continuity and condition continuity are independent discourse links
2. one typed preposed eGFR condition may link to multiple compatible management events
3. endpoint declaration / achievement / evidence-for-achievement are separately arbitrated
4. endpoint negation/evidence scope is evaluated before positive achievement emission
5. unsupported continue-only-if / otherwise-hold structures enter a semantic high-risk gate
6. safety evaluation separates silent non-abstention, partial truth, and semantic false-positive escalation
```

No item IDs are used in parser logic.

---

## 3. Immutable first development observation

Workflow `34003220909` ran the frozen v0.5.5 implementation. Raw predictions and reports were committed before the final release gate was enforced.

### Proposition regression

| Exposed suite | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 98.21% | 97.67% | 100.00% | 100.00% | 98.21% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.5.2 | 95.89% | **94.55%** | 100.00% | 100.00% | 95.89% | **FAIL** |
| v0.5.4 fresh-now-exposed | 98.36% | 97.83% | 100.00% | 100.00% | 100.00% | PASS |

The overall proposition gate therefore fails only because the v0.5.2 exposed suite is 0.45 percentage points below the preregistered critical-recall threshold.

### Abstention safety

```text
v0.5.1 mandatory abstentions       4/4   PASS
v0.5.1 known false abstentions     0/38  PASS

v0.5.2 mandatory abstentions       6/6   PASS
v0.5.2 known false abstentions     0/40  PASS

v0.5.4 exposed mandatory           6/6   PASS
v0.5.4 exposed known false abst.   0/32  PASS

combined mandatory abstentions    16/16
combined known cases             110
combined known false abstentions   0
Abstention gate                  PASS
```

The previously failing `continue treatment only if ... otherwise hold the next dose` family now correctly triggers abstention.

### Semantic safety error gate

The new evaluator confirms:

```text
mandatory silent non-abstention       0
mandatory partial truth emissions     0
high-risk false positives             1
Safety error gate                  FAIL
```

The single high-risk false positive remains in the exposed v0.5.4 suite: an explicit absence-of-evidence endpoint statement is still converted into positive endpoint achievement in one cross-sentence construction.

### Trace contract

```text
rows checked                          228
trace failures                          0
Trace gate                            PASS
```

### Combined development release

```text
all exposed proposition suites       FAIL
abstention safety                    PASS
semantic safety error gate           FAIL
trace contract                       PASS
combined development release         FAIL
fresh validation                  NOT RUN
```

---

## 4. What materially improved

The v0.5.4 fresh first-run dataset is now exposed, so the following numbers are regression diagnostics rather than new fresh evidence.

On that exact dataset:

```text
                                  v0.5.4 first-run     v0.5.5 regression
F1                                      93.44%              98.36%
Critical Proposition Recall             91.30%              97.83%
Population Accuracy                     98.28%             100.00%
Condition Binding Accuracy              98.28%             100.00%
Required-abstention accuracy            83.33%             100.00%
Known-case abstention rate               3.125%              0.00%
```

The new linker fixes the prior cross-sentence population-continuity failure and shared preposed condition failure on the v0.5.4 dataset. The new high-risk structure gate also fixes its only mandatory-abstention failure.

One of the two endpoint-negation inversions is fixed; one remains.

---

## 5. Failure taxonomy frozen before repair

No parser repair was performed after observing this FAIL.

### F1 — Anaphoric condition type/cardinality over-propagation

Observed in exposed item `S3A52-005`.

The source first defines an eGFR **range**, then says `the same renal value` for a second event. v0.5.5's shared-condition linker propagates the whole range. The frozen v0.5.2 gold expects the second event to remain condition-unspecified.

This exposes a general linker defect: an anaphor such as `same value` should not inherit a range-valued antecedent without type/cardinality compatibility. The repair should operate on typed reference compatibility, not phrase-specific exceptions.

### F2 — Shared-preposed condition leaks into a non-renal negative event

Observed in `S3A52-010`.

The first event is benefit-risk review at `eGFR <45`; a later contrastive clause says a platelet threshold does **not** trigger discontinuation. The v0.5.4 event owner had removed the renal condition from the negative discontinuation frame, but the new shared-preposed linker can add it back.

This shows that shared-condition edges require explicit target compatibility and local-variable conflict vetoes at the clause/event level. A sentence-level single-condition rule is still too permissive.

### F3 — Historical anaphoric-gold ambiguity remains exposed

`S3A52-037` remains the previously documented ambiguity: the antecedent says `below eGFR 42`, while the frozen gold interprets `same eGFR` as `eGFR =42`. v0.5.5 preserves the antecedent `<42` operator.

The historical dataset and result are not changed. This item contributes to the frozen development metric, but the next structural repair must not hardcode the benchmark label. If this ambiguity is later adjudicated, it should be reported separately rather than rewriting historical evidence.

### F4 — Endpoint entity continuity is sentence-local

Observed in exposed item `S3A54F-019`.

```text
Sentence 1: study ... specifies a primary endpoint.
Sentence 2: Nothing in the supplied results establishes that the endpoint was met.
```

The v0.5.5 endpoint classifier correctly handles the corresponding construction when `primary endpoint` occurs in the negative-evidence sentence, but fails when sentence 2 contains only the anaphor `the endpoint`.

As a result, lexical `endpoint was met` survives as positive `ACHIEVES_ENDPOINT`, producing a high-risk false positive.

This is not primarily a negation-regex gap. The missing structure is an endpoint-entity discourse link from the declaration in sentence 1 to the anaphoric endpoint in sentence 2, followed by evidence-scope resolution before achievement arbitration.

---

## 6. Evaluation finding

The new safety evaluator behaves as intended on the key v0.5.4 blind spot: although the historical structural polarity metric would not count a predicate-family-changing inversion, the new `high_risk_false_positive_count` explicitly catches the endpoint success escalation.

It also now separates:

```text
silent unknown-critical non-abstention
partial/simplified truth emission
semantic high-risk false positive
```

Therefore the evaluator improvement should be retained in the next version even though v0.5.5 itself fails.

---

## 7. Release decision

```text
S3b structured entailment              = CONDITIONAL PASS
S3a v0.5.5 exposed proposition         = FAIL
S3a v0.5.5 exposed abstention          = PASS
S3a v0.5.5 semantic safety gate        = FAIL
S3a v0.5.5 trace contract              = PASS
S3a v0.5.5 fresh validation            = NOT RUN
S3a free-text release                  = HARD FAIL / BLOCKED
End-to-end S3                          = HARD FAIL
S4 automatic KG truth ingestion        = BLOCKED
```

No downstream stage may automatically trust v0.5.5 free-text truth extraction.

---

## 8. Next coherent target

Do not create a new fresh suite yet.

The next version should be **S3a v0.5.6 Typed Reference Graph + Endpoint Discourse State**, with only structural development on already-exposed data:

```text
1. represent anaphora as typed reference edges with scalar/range/threshold compatibility
2. require shared-condition target compatibility; a local non-renal variable or negative independent clause vetoes renal propagation
3. maintain endpoint entity state across adjacent sentences
4. resolve endpoint evidence/negation scope after endpoint-reference linking but before achievement emission
5. retain the v0.5.5 semantic safety evaluator unchanged as a regression gate
```

Only after every exposed proposition, abstention, semantic-safety and trace gate passes should another brand-new fresh/shadow held-out be frozen.
