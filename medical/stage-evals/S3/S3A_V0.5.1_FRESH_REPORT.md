# S3a v0.5.1 Compositional Frame Parser — Fresh Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Frozen implementation: `s3a-compositional-frame-v0.5.1`  
> Implementation commit: `0a3fe9ee29187cfb7e381da0f41bb1ae93875937`  
> Fresh-suite freeze commit: `dea61a9d4aac76303ea0f77bef4617016019cd70`  
> First-run workflow commit: `60cea24679875cba0b60e2427b098ae8a3acb540`  
> First-run workflow: `33991678951`  
> Artifact: `s3a-v051-fresh-heldout-first-run` / ID `9976815765` / SHA-256 `9421a58f925145cd2a21f86f23f1fdf191b777ff5f5203bdb632a9eafd0c32b7`  
> Status: **FRESH FAIL — release remains blocked**

## 术语表

- **Fresh held-out（新鲜留出集）**：实现冻结后才创建，首次结果永久保留的未见测试集。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中被正确抽取的比例。
- **Polarity（极性）**：肯定与否定语义是否正确绑定到命题。
- **Population scope（人群作用域）**：新启动用户、既往用药用户等是否绑定到正确事件。
- **Condition binding（条件绑定）**：阈值和范围是否绑定到正确事件。
- **Abstention（弃权）**：语义超出受控本体或无法安全解析时明确拒绝自动生成真值。
- **Trace contract（轨迹契约）**：每个输出必须保留 scope/frame/provenance，便于失败定位和审计。

---

## 1. Frozen evaluation contract

The v0.5.1 implementation was already frozen and had passed all exposed v0.1-v0.4 regression suites before this held-out was written. No extractor change occurred between the freeze and the first observation.

Fresh suite:

```text
items                         42
known/representable cases     38
mandatory-abstention cases     4
expected propositions         66
critical propositions         48
```

Capability-level stressors included:

```text
competing populations
shared and competing eGFR thresholds
elided variables
unrelated numeric distractors
interrupted / long-distance negation
mixed positive + negative propositions
passive and inverse relation direction
cross-sentence composition
trial endpoint absence-of-result semantics
trial evidence vs guideline currentness
pharmacogenomics exposure vs management boundaries
mandatory abstention for unsupported critical semantics
```

Preregistered release gates:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
Required-abstention accuracy = 1.00
Known-case abstention rate <= 0.05
Trace contract = PASS
```

---

## 2. Immutable first-run result

The first run produced:

```text
Gold propositions                         66
Predicted propositions                    56
True positives                            49
Precision                              87.50%
Recall                                 74.24%
F1                                     80.33%
Critical Proposition Recall            68.75%
Polarity Accuracy                      98.00%   PASS
Population Accuracy                    94.23%   FAIL
Condition Binding Accuracy             98.00%   PASS
```

Abstention safety:

```text
Mandatory-abstention cases                 4
Correct mandatory abstentions              1
Required-abstention accuracy           25.00%   FAIL
Known representable cases                 38
Known-case false abstentions               5
Known-case abstention rate             13.16%   FAIL
```

Trace/provenance:

```text
Rows checked                               42
Trace-contract failures                     0
Trace gate                               PASS
```

Combined release decision:

```text
Proposition gate      FAIL
Abstention gate       FAIL
Trace gate            PASS
Combined release      FAIL
```

The first-run artifact and metrics are immutable. This dataset is now **exposed regression data** and must not be reported later as fresh performance.

---

## 3. Failure taxonomy

### F1 — Population trigger coverage gap

Observed in `S3A51-006` and `S3A51-036`.

The semantic events and eGFR conditions were mostly recovered, but phrases such as `existing users` were not bound to `existing_user`. The emitted propositions therefore had `population = null`.

This is not a threshold problem. It is a population-role recognizer coverage problem.

### F2 — Interrupted negation scope

Observed in `S3A51-008`.

```text
is not, on its own, a contraindication
```

was emitted as a positive contraindication. v0.5.1 handles compact copular forms such as `is not contraindicated`, but an inserted parenthetical/adverbial phrase still breaks the target-local negation scope.

### F3 — Condition leakage across contrastive clauses

Observed in `S3A51-010`.

The second clause correctly received negative contraindication polarity, but inherited the previous `eGFR <25` condition even though its actual condition was an unrelated age criterion. This is a scope/provenance failure: a unique sentence-level eGFR condition is not always safe to inherit across `but` into a semantically independent clause.

### F4 — Coordinated multi-event threshold segmentation

Observed in `S3A51-036`.

```text
eGFR <44 triggers reassessment, and <28 triggers discontinuation
```

remained one scope node. Both frames inherited `<44`, so the discontinuation event lost its local `<28` condition. The parser needs event-aware coordination splitting rather than only punctuation/conjunction splitting at the outer clause level.

### F5 — Incidence relation recognition gap / excessive abstention

Observed in `S3A51-013` and `S3A51-016`.

Previously supported incidence semantics did not generalize to:

```text
do not estimate the true incidence
cannot be converted into incidence without a denominator
```

The safety fallback abstained rather than hallucinating, which is preferable to false support, but the known-case abstention rate became too high and critical recall fell.

### F6 — Endpoint absence-of-result semantics

Observed in `S3A51-021`.

The parser extracted `RECRUITING` and the declared primary endpoint but did not compile:

```text
no efficacy result is yet available
→ evidence does not establish endpoint achievement
```

It then abstained on the unresolved critical content. This is a semantic relation gap, not a trace failure.

### F7 — Passive temporal-relation direction

Observed in `S3A51-023`.

```text
Guideline B is superseded by Guideline C
```

was not converted to canonical direction:

```text
Guideline C SUPERSEDES Guideline B
```

Currentness consequences were therefore also absent. Passive-voice relation inversion remains a genuine capability gap.

### F8 — Temporal composition across guideline + trial clauses

Observed in `S3A51-027`.

The trial-support proposition was recovered, but the guideline replacement/currentness chain was not. The system then correctly marked unresolved critical content, but missed three critical temporal propositions.

### F9 — Passive trial-support direction

Observed in `S3A51-026`.

```text
Option Q is supported by the randomized trial
```

failed to normalize to:

```text
trial SUPPORTS_OPTION Q
```

The current-guideline proposition in the same sentence was recovered. This localizes the failure to argument-direction handling rather than whole-sentence parsing.

### F10 — Unknown-critical abstention detector undercoverage

Mandatory abstention failed on three of four cases:

```text
S3A51-039  QTc/torsades permanent suspension
S3A51-040  eGFR OR dialysis discontinuation rule
S3A51-042  conditional coadministration avoidance
```

`S3A51-041` (50% dose reduction for CYP2C19 poor metabolizer) correctly abstained.

The current abstention detector relies too heavily on the existing critical lexical inventory. Unsupported but clinically consequential semantics can therefore silently produce no proposition and no abstention, or in the disjunctive case emit an incomplete simplified rule.

### F11 — Unsafe simplification of disjunctive conditions

`S3A51-040` is the most important new safety failure.

The source rule was:

```text
(eGFR <30) OR (dialysis started) → discontinue
```

The parser emitted only:

```text
eGFR <30 → discontinue
```

and did **not** abstain. The current canonical condition representation cannot express the disjunction, so the correct behavior is to flag the proposition as non-representable rather than silently drop one branch.

---

## 4. What did improve relative to earlier fresh failures

The v0.5.1 fresh result is still a clear FAIL, but unlike v0.4 it did not collapse to near-random extraction:

```text
v0.4 fresh F1                 40.00%
v0.5.1 fresh F1              80.33%

v0.4 critical recall          25.58%
v0.5.1 critical recall       68.75%

v0.4 polarity                 80.00%
v0.5.1 polarity              98.00%

v0.4 condition binding       100.00%
v0.5.1 condition binding      98.00%
```

This is evidence that the compositional-frame architecture improved fresh generalization substantially, but it remains below the safety release threshold and has a newly exposed abstention-safety defect.

---

## 5. Release decision

```text
S3b structured entailment       = CONDITIONAL PASS
S3a v0.5.1 exposed regression   = PASS
S3a v0.5.1 fresh held-out       = FAIL
S3a proposition release         = BLOCKED
S3a unknown-critical abstention = FAIL
End-to-end S3                   = HARD FAIL
```

Therefore unrestricted free text → automatic S3 truth → Knowledge Graph insertion remains blocked.

No downstream S4 stage is allowed to trust S3a machine-derived truth from this version.

---

## 6. Next version recommendation

Do not repair this by adding one phrase per failed item.

The next implementation should be a single coherent **S3a v0.5.2 scope-safety repair** with four structural mechanisms:

```text
1. event-aware coordination segmentation
   separate multiple semantic events inside one grammatical clause before condition binding

2. conservative context inheritance
   do not inherit a sentence-level condition/population across contrastive or independent clauses unless compatibility is proven

3. passive/inverse argument normalization
   canonicalize X is <relation> by Y using relation-specific direction schemas

4. ontology-coverage guard
   if critical action/condition semantics are detected but the closed proposition representation cannot encode every branch/argument, mandatory abstention must fire
```

Known v0.1-v0.5.1 suites are now development/regression data. A new fresh held-out must not be frozen until those structural changes are implemented and all exposed regression + abstention + trace gates pass.
