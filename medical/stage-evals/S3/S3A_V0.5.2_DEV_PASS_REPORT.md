# S3a v0.5.2 Scope-Safety Repair — Development Audit

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.2`  
> Implementation commit: `0200076a66454246de03fc015b9fd0911ea087f2`  
> Regression workflow: `33994442500`  
> Artifact: `s3a-v052-exposed-scope-safety-regression` / ID `9977613430`  
> Artifact SHA-256: `0c80593b0d6bc8802667d12a6e0819b4aa04720f1de748e86b602b455b61d6e0`  
> Status: **DEVELOPMENT PASS — fresh validation NOT RUN**

## 术语表

- **Scope safety（作用域安全）**：条件、人群、否定和事件只绑定到它们实际修饰的命题，避免跨子句泄漏。
- **Ontology coverage guard（本体覆盖保护）**：若安全关键语义无法被当前封闭命题结构无损表示，系统必须弃权，而不是静默删掉条件分支。
- **Abstention（弃权）**：无法安全表达或解析时拒绝自动产出真值。
- **Trace contract（轨迹契约）**：输出保留 scope node、semantic frame、trigger family 和 provenance，支持逐层审计。
- **Exposed regression（已暴露回归集）**：开发者已经看过的测试，只能用于防回归，不能证明泛化。

---

## 1. Why v0.5.2 exists

The immutable v0.5.1 fresh run failed with:

```text
F1                                  80.33%
Critical Proposition Recall         68.75%
Population Accuracy                 94.23%
Required-abstention accuracy        25.00%
Known-case abstention rate          13.16%
Combined release                    FAIL
```

The highest-risk defect was silent simplification of a disjunctive rule:

```text
(eGFR <30) OR (dialysis started) -> discontinue
```

into only:

```text
eGFR <30 -> discontinue
```

without abstention. v0.5.2 therefore changes scope and representation safety rather than adding item-specific answers.

---

## 2. Architectural changes

### A. Event-aware coordination segmentation

Management events are rebound inside local coordination segments before final proposition emission. When one sentence contains multiple actions and thresholds, the parser uses the nearest event-local eGFR condition instead of one sentence-wide condition.

### B. Conservative context inheritance

A renal condition is not allowed to leak across an independent or contrastive segment merely because it is the only eGFR condition in the sentence. Population inheritance is also restricted to a unique compatible local/sentence context.

### C. Passive / inverse argument normalization

Relation-specific grammars normalize direction for:

```text
Guideline B is superseded by Guideline C
-> Guideline C SUPERSEDES Guideline B

Option Q is supported by the randomized trial
-> trial SUPPORTS_OPTION Q
```

### D. Ontology-coverage guard

For clinically consequential semantics that cannot be losslessly represented by the closed proposition schema, v0.5.2 suppresses partial propositions and mandates abstention. The guard covers non-representable disjunctions, unsupported critical condition variables, unsupported management actions and conditional exceptions.

This directly changes the behavior of the four previously exposed mandatory-abstention cases from 1/4 correct to 4/4 correct.

---

## 3. Reused preregistered development gates

No new fresh set was created in this version. The development evaluation reused the already-exposed v0.1-v0.5.1 suites and the v0.5.1 abstention/trace contracts.

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
```

---

## 4. CI result

GitHub Actions workflow `33994442500` completed successfully.

| Exposed suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 91.53% | 96.43% | 93.91% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |

Abstention safety on the exposed v0.5.1 suite:

```text
Mandatory-abstention cases          4
Correct mandatory abstentions       4
Required-abstention accuracy      100%
Known representable cases          38
Known-case false abstentions        0
Known-case abstention rate          0%
Gate                              PASS
```

Trace audit:

```text
Rows checked                       144
Trace-contract failures              0
Gate                               PASS
```

Combined development release:

```text
all_exposed_proposition_suites = PASS
abstention_safety              = PASS
trace_contract                 = PASS
combined development gate      = PASS
fresh_validation               = NOT_RUN
```

---

## 5. Residual exposed errors

Development PASS does not mean the exposed sets are perfect. The v0.4 suite remains above every preregistered threshold but still contains four diagnostic errors:

1. `S3A4-015`: extra trial/current-guideline objects normalized as `approach`;
2. `S3A4-021`: initiation restriction loses inherited `eGFR <25` in one shared-condition contrastive construction;
3. `S3A4-022`: initiation restriction loses shared `eGFR =42` in one anaphoric `same eGFR` construction;
4. `S3A4-034`: extra trial-support object normalized as `to`.

These failures are deliberately preserved. They are not sufficient to fail the preregistered v0.4 gate, but they should remain regression diagnostics and must not be hidden by reporting only aggregate PASS.

---

## 6. Release decision

This run does **not** change S3a to a released capability.

```text
S3b structured entailment        = CONDITIONAL PASS
S3a v0.5.2 development gate      = PASS
S3a v0.5.2 abstention gate       = PASS on exposed v0.5.1 cases
S3a v0.5.2 trace contract        = PASS
S3a v0.5.2 fresh validation      = NOT RUN
S3a free-text release            = HARD FAIL / BLOCKED
End-to-end S3                    = HARD FAIL
S4 automatic truth ingestion     = BLOCKED
```

The last independent fresh evidence remains the v0.5.1 FAIL. Therefore no downstream stage is allowed to treat v0.5.2 as validated free-text truth extraction.

---

## 7. Next step

Freeze a brand-new S3a v0.5.2 fresh held-out **without modifying the implementation**. The next set should stress capability families not copied from the exposed v0.5.1 wording, especially:

```text
nested conjunction/disjunction
shared conditions expressed anaphorically
cross-sentence population carryover
passive + negated relation combinations
multiple non-eGFR numeric distractors
modality/exception scope
unknown critical variables/actions requiring abstention
known representable cases that should NOT abstain
```

Only a passing first observation on that untouched set can justify proceeding to a brand-new end-to-end S3 held-out.
