# S3a v0.5.4 Typed Event Graph — Fresh Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Frozen implementation: `s3a-compositional-frame-v0.5.4`  
> Parser implementation commit: `33dde2507afb8d34d47f3103ee0bfbfaf716ec5f`  
> Parser blob SHA: `a72e0eb8ad2ace097b1756e2040a20f5ec56745f`  
> Fresh-suite definition freeze commit: `87de9757f1defd480cdd2a13c0b6c452742a5196`  
> First-run workflow commit: `4d3f5d87e147cb94bf48dcabf51953276db539fb`  
> First-run workflow: `34002761349`  
> Raw-result preservation commit: `ed1d684a6bf46478b4092cb314f7d5844d8e98da`  
> Artifact: `s3a-v054-fresh-heldout-first-run` / ID `9979976451`  
> Artifact SHA-256: `5938138544e5db28d08fe346112d9aaacea80e8cbe523b2c3831330efe158851`  
> Generated dataset SHA-256: `11ea362c6c0592b6886fae2dacaf39adc205b9947fa6cbe0a44c88d115cb69ed`  
> Status: **FRESH FAIL — no parser repair performed in this iteration**

## 术语表

- **Fresh held-out（新鲜留出集）**：解析实现冻结后才定义，首次观察永久保留的独立测试。
- **Typed event ownership（类型化事件归属）**：条件、人群、极性等信息必须绑定到正确事件，而不是机械继承整句上下文。
- **Critical Proposition Recall（关键命题召回率）**：安全关键标准命题中被精确抽取的比例。
- **Abstention（弃权）**：高风险语义无法被当前封闭本体安全表达时，拒绝生成自动真值。
- **False abstention（错误弃权）**：本可表达的语义被系统错误拒绝。
- **Relation-family arbitration（关系族仲裁）**：在多个关系候选之间统一方向、极性和参数，避免互相冲突的命题并存。
- **Trace contract（轨迹契约）**：每个输出保留 scope/frame/provenance，支持逐层定位错误。

---

## 1. Freshness and immutability

The v0.5.4 parser had already passed all exposed development gates before the held-out definition existed.

Fresh definition freeze:

```text
suite definition commit    87de9757f1defd480cdd2a13c0b6c452742a5196
parser last-change commit  33dde2507afb8d34d47f3103ee0bfbfaf716ec5f
parser blob SHA            a72e0eb8ad2ace097b1756e2040a20f5ec56745f
evaluator last commit      50a9a7a2f4a5409297434cf0c29f05d1fa6780c5
```

The workflow verified these values before generating the held-out JSON and before the first observation. No parser modification occurred between development PASS, suite freeze and first run.

The suite is controlled synthetic capability data. It is **not** real user data, clinical validation, expert-reviewed clinical gold, or evidence of model-training benefit.

Frozen suite composition:

```text
items                            38
known / representable cases      32
mandatory-abstention cases        6
gold propositions                61
critical propositions            46
```

Preregistered gates were reused unchanged:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
Required-abstention accuracy = 1.00
Known-case abstention rate <= 0.05
Trace contract = PASS
No mandatory-abstention case may become partial machine truth
```

---

## 2. Immutable first observation

Workflow `34002761349` executed the untouched parser and intentionally failed at the final release enforcement step after all raw outputs had already been committed.

### Proposition metrics

```text
Gold propositions                         61
Predicted propositions                    61
True positives                            57
Precision                              93.44%   PASS
Recall                                 93.44%
F1                                     93.44%   PASS
Critical Proposition Recall            91.30%   FAIL
Polarity Accuracy                     100.00%   PASS
Population Accuracy                    98.28%   PASS
Condition Binding Accuracy             98.28%   PASS
```

The proposition gate fails solely because critical recall is below the preregistered 95% threshold.

### Abstention safety

```text
Mandatory-abstention cases                 6
Correct mandatory abstentions              5
Required-abstention accuracy           83.33%   FAIL
Known representable cases                 32
Known-case false abstentions               1
Known-case abstention rate              3.125%  PASS
```

Mandatory-abstention failure:

```text
S3A54F-034
```

Known-case false abstention:

```text
S3A54F-016
```

### Trace contract

```text
rows checked                               38
trace failures                              0
Trace gate                               PASS
```

### Combined decision

```text
proposition gate                    FAIL
abstention gate                     FAIL
unsafe-simplification safety gate   FAIL
trace gate                          PASS
combined release                    FAIL
```

Raw outputs are permanently stored under:

`medical/stage-evals/S3/runs/s3a-v054-fresh-first-run/`

The generated `gold.json` is stored beside predictions and metrics. From this point forward, this suite is exposed regression data and must never again be described as fresh evidence.

---

## 3. Failure taxonomy before repair

No implementation change was made after observing these failures.

### F1 — Cross-sentence population carryover gap

Observed in `S3A54F-003`.

The parser correctly extracted both discontinuation statements and correctly prevented the previous eGFR condition from leaking into the second sentence. However, the negative second-sentence event lost the `existing_user` population and emitted `population = null`.

This is a useful localization: sentence-level condition isolation works here, but entity/population continuity is not represented independently from condition continuity.

### F2 — Shared preposed condition is not inherited across a contrastive event

Observed in `S3A54F-004`.

The sentence gives one renal condition (`eGFR <46`) before two population-specific events. The initiation event receives the condition, while the existing-user reassessment event receives the correct population but no condition.

This independently reproduces the remaining exposed `S3A4-021` family. The correct repair should represent explicit condition sharing/ownership rather than add wording-specific propagation.

### F3 — Endpoint-negation semantic inversion

Observed in `S3A54F-016` and `S3A54F-019`.

Phrases of the form:

```text
No posted outcome demonstrates that the primary endpoint was achieved.
Nothing in the supplied results establishes that the endpoint was met.
```

should compile to:

```text
evidence ESTABLISHES_ENDPOINT_ACHIEVEMENT primary_endpoint NEGATIVE
```

Instead, the endpoint-success recognizer notices the embedded surface phrase `was achieved` / `was met` and emits a positive `study ACHIEVES_ENDPOINT primary_endpoint` proposition. `S3A54F-016` additionally triggers semantic-coverage abstention, whereas `S3A54F-019` does not.

This is the most important representable-semantic error in the fresh run because an explicit absence-of-evidence sentence can be inverted into a positive success claim.

The failure indicates that endpoint declaration, endpoint achievement and evidence-for-achievement require a typed scope relation; lexical arbitration after independent recognizers is insufficient.

### F4 — Unknown high-risk conjunction/action silently unresolved

Observed in mandatory-abstention item `S3A54F-034`:

```text
Continue treatment only if oxygen saturation >=95% AND systolic BP >92;
otherwise hold the next dose.
```

The closed proposition schema cannot represent the compound physiologic condition and hold-dose action. The parser emits no proposition, but also fails to set `abstain = true`.

Five other newly worded mandatory-abstention cases are handled correctly. Thus the high-risk guard generalizes substantially better than v0.5.2, but remains trigger-dependent and incomplete for `continue only if ... otherwise hold` constructions.

---

## 4. Evaluation-quality findings

The raw first-run metrics are immutable. Two diagnostic limitations should be fixed only in a future evaluator version; they must not be retroactively applied to this fresh run.

### E1 — Polarity metric blind spot

Reported Polarity Accuracy is 100%, yet `S3A54F-016` and `S3A54F-019` contain a clinically important negative-to-positive semantic inversion.

The current evaluator computes polarity only after subject/predicate/object/condition/population structurally match. Because the erroneous prediction changes the predicate from `ESTABLISHES_ENDPOINT_ACHIEVEMENT` to `ACHIEVES_ENDPOINT`, these failures are excluded from the polarity denominator.

A future safety evaluator should therefore add a high-risk contradiction / false-positive family metric independent of exact predicate matching.

### E2 — `unsafe-simplification-report` naming is broader than its implementation

The raw report flags `S3A54F-034` under `unsafe_simplifications`, but the item emitted **zero propositions**. The actual failure is missing mandatory abstention, not partial-truth simplification.

The current invariant implementation treats either `(not abstain)` **or** emitted propositions as a violation. This is conservative and correctly fails the safety gate, but future reports should separate:

```text
A. silent unknown-critical non-abstention
B. partial / simplified truth emission
```

The first-run raw report is not modified.

---

## 5. Comparison with the previous independent fresh result

v0.5.4 remains FAIL, but independent performance improved materially relative to v0.5.2:

```text
                                      v0.5.2 fresh     v0.5.4 fresh
F1                                        78.20%           93.44%
Critical Proposition Recall               67.27%           91.30%
Polarity metric                            98.11%          100.00%*
Population Accuracy                       100.00%           98.28%
Condition Binding Accuracy                 92.86%           98.28%
Required-abstention accuracy               50.00%           83.33%
Known-case abstention rate                 10.00%            3.125%
Trace contract                               PASS             PASS
```

`*` The polarity number has the structural-match blind spot documented above and must not be interpreted as absence of semantic sign errors.

The result supports the typed-event/non-destructive architecture direction, but does not meet safety release criteria.

---

## 6. Release decision

```text
S3b structured entailment              = CONDITIONAL PASS
S3a v0.5.4 exposed development         = PASS
S3a v0.5.4 fresh proposition           = FAIL
S3a v0.5.4 fresh abstention            = FAIL
S3a v0.5.4 fresh trace                 = PASS
S3a free-text release                  = HARD FAIL / BLOCKED
End-to-end S3                          = HARD FAIL
S4 automatic KG truth ingestion        = BLOCKED
```

No downstream component may treat v0.5.4 free-text output as validated truth.

---

## 7. Next version recommendation

The next coherent implementation should be **S3a v0.5.5 Typed Scope Linker + Safety Error Gate** rather than a wording patch.

Architecture targets:

```text
1. independent discourse links for population continuity vs condition continuity
2. explicit shared-condition edges from a preposed condition to multiple compatible events
3. typed endpoint scope graph:
   endpoint declaration != endpoint achievement != evidence establishes achievement
4. negation attached before endpoint-relation arbitration
5. semantic high-risk detector for unsupported condition/action structures,
   including continue-only-if / otherwise-hold constructions
6. next development evaluator adds diagnostic high-risk false-positive count
   and separates silent-non-abstention from partial-truth emission
```

Development must use only already-exposed suites, including this v0.5.4 fresh set. No new fresh held-out should be created until the new structural implementation is frozen and every development + safety gate passes.
