# S3a v0.5.2 Scope-Safety Parser — Fresh Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Frozen implementation: `s3a-compositional-frame-v0.5.2`  
> Implementation commit: `0200076a66454246de03fc015b9fd0911ea087f2`  
> Implementation blob SHA: `fff81db9d9e80bc608f5b4dce3c0503a6207421b`  
> Fresh-suite freeze commit: `fcce2dbcbf780e8a4378fdfb987b7e92e0196f30`  
> First-run workflow commit: `09942c67e7b7961e7252ae86b26f77a88c94f262`  
> First-run workflow: `33996658862`  
> Raw-result preservation commit: `0b20aefd8400472833b6fb86f53b24d23cd489d8`  
> Artifact: `s3a-v052-fresh-heldout-first-run` / ID `9978253888` / SHA-256 `012d2d7eb8f91e3abc99f13ba5acbcf9329366c7ead3e3bf187b35f90f47a7a3`  
> Dataset SHA-256: `f931bef62f63b6775cb8d81b8d8766c4586aa30e5dc533f1b2fcb62a019cbd39`  
> Status: **FRESH FAIL — no parser repair performed in this iteration**

## 术语表

- **Fresh held-out（新鲜留出集）**：实现冻结后才创建，并将首次观察永久保留的独立测试集。
- **Critical Proposition Recall（关键命题召回率）**：安全关键标准命题被完整抽出的比例。
- **Abstention（弃权）**：当语义无法由当前封闭本体安全表达时，明确拒绝自动生成真值。
- **False abstention（错误弃权）**：本可由当前本体表达的案例却被系统拒绝处理。
- **Trace contract（轨迹契约）**：每条输出保留 scope/frame/provenance 结构，允许定位错误发生在哪一层。

---

## 1. Freshness / immutability contract

The v0.5.2 implementation had already passed the exposed development gates before this suite existed. The fresh suite was then frozen at `fcce2dbc...` and the implementation blob was rechecked before the first observation. The workflow additionally asserted:

```text
parser last-change commit = 0200076a66454246de03fc015b9fd0911ea087f2
parser blob SHA           = fff81db9d9e80bc608f5b4dce3c0503a6207421b
fresh-suite freeze commit = fcce2dbcbf780e8a4378fdfb987b7e92e0196f30
```

The suite contains controlled synthetic capability tests, not real user logs, expert-reviewed clinical gold, model-training outcomes, or clinical validation.

Frozen suite composition:

```text
items                          46
known/representable cases      40
mandatory-abstention cases      6
gold propositions              73
critical propositions          55
```

The preregistered release gates were reused unchanged from the previous S3a fresh evaluation:

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

Workflow `33996658862` executed the untouched v0.5.2 parser. Its final gate intentionally failed.

### Proposition extraction

```text
Gold propositions                         73
Predicted propositions                    60
True positives                            52
Precision                              86.67%   FAIL
Recall                                 71.23%   FAIL
F1                                     78.20%   FAIL
Critical Proposition Recall            67.27%   FAIL
Polarity Accuracy                      98.11%   PASS
Population Accuracy                   100.00%   PASS
Condition Binding Accuracy             92.86%   FAIL
```

### Abstention safety

```text
Mandatory-abstention cases                 6
Correct mandatory abstentions              3
Required-abstention accuracy           50.00%   FAIL
Known representable cases                 40
False abstentions                           4
Known-case abstention rate             10.00%   FAIL
```

Mandatory-abstention failures:

```text
S3A52-041
S3A52-042
S3A52-046
```

False abstentions on known/representable cases:

```text
S3A52-012
S3A52-019
S3A52-038
S3A52-039
```

### Trace contract

```text
rows checked                               46
trace failures                              0
Trace gate                               PASS
```

### Combined gate

```text
proposition gate      FAIL
abstention gate       FAIL
trace gate            PASS
combined release      FAIL
```

Raw outputs are permanently committed under:

`medical/stage-evals/S3/runs/s3a-v052-fresh-first-run/`

They must not be overwritten. From this point onward the v0.5.2 fresh suite is exposed regression data and must never again be reported as fresh evidence.

---

## 3. Failure taxonomy before repair

No implementation change was made after seeing these results.

### F1 — Cross-sentence condition carryover overreach

Observed in `S3A52-004`.

A negative discontinuation statement in the second sentence inherited the previous sentence's `eGFR <27` condition. The parser preserved population correctly but failed to terminate condition scope across the sentence boundary.

### F2 — Coordinated event-to-threshold binding failure

Observed in `S3A52-006`.

The text contains reassessment at `eGFR <46` and discontinuation at `<29`. The parser failed to emit reassessment and attached `<46` to discontinuation. Event-aware segmentation therefore still does not generalize to all compact coordination forms.

### F3 — Non-eGFR numeric distractor falsely typed as eGFR

Observed in `S3A52-010`.

A platelet threshold of `100` was converted into an `eGFR <100` condition on a negative discontinuation proposition. This is a variable-typing defect, not merely a numeric-boundary error.

### F4 — Representable causality phrasing causes false abstention

Observed in `S3A52-012`.

`must not be treated as proof of causation` belongs to the already-supported causality family, but no semantic frame was emitted and the semantic-coverage guard abstained. The safety guard is conservative, but recall is too dependent on surface phrasing.

### F5 — Trial-status / ontology-guard collision

Observed in `S3A52-019`.

The legitimate study status `SUSPENDED` plus an endpoint statement was interpreted by the guard as an unsupported clinical management action, producing a false abstention and losing the trial-status and endpoint propositions. Guard routing is therefore not sufficiently type-aware.

### F6 — Endpoint absence-of-result paraphrase gap

Observed in `S3A52-021` and `S3A52-038`.

The parser recovered trial status and endpoint declaration but failed to compile phrasing such as `does not constitute an efficacy result` / `no supplied result establishes endpoint achievement` into the negative endpoint-achievement evidence proposition. `S3A52-038` then false-abstained.

### F7 — Passive trial-support / guideline composition gap

Observed in `S3A52-025` and `S3A52-040`.

Positive passive support (`Option T is supported by a randomized trial`) failed together with the current-guideline clause in `S3A52-025`. Negated passive support (`Option Y is not supported by the randomized trial`) was also missed in `S3A52-040`, although the guideline clause was recovered. Direction normalization is therefore incomplete, especially under polarity.

### F8 — Temporal supersession canonicalization / currentness composition

Observed in `S3A52-027`.

The supersession relation was emitted with a punctuation-contaminated object (`guideline q.`), and the implied current/not-current propositions were not generated. Surface extraction and temporal consequence composition remain coupled too tightly.

### F9 — Passive inverse association polarity inversion

Observed in `S3A52-032`.

`Outcome P was not found to be associated with biomarker O` was direction-normalized to the correct subject/object but emitted with **positive** rather than negative polarity. This is a safety-relevant passive+negation interaction.

### F10 — Anaphoric condition + contrastive action scope

Observed in `S3A52-037`.

The second sentence's `same eGFR` reference and `rather than automatically discontinue` were not compositionally resolved. The parser inherited a threshold mechanically and emitted discontinuation with positive polarity.

Important eval-quality note: the frozen gold labels `same eGFR` as `eGFR =42`, while the antecedent phrase is `below eGFR 42`. That label is potentially ambiguous. The first-run dataset/result will **not** be edited. Even if this item is excluded or its anaphoric condition is interpreted differently in a later shadow audit, aggregate v0.5.2 release remains far below threshold, so the FAIL decision is unchanged.

### F11 — Negated passive supersession false abstention

Observed in `S3A52-039`.

`Guideline W is not superseded by Guideline X` produced no relation frame and triggered the representable-family coverage guard. The same sentence's explicit currentness statement was also lost.

### F12 — Ontology-coverage guard undercoverage on unknown critical rules

Observed in mandatory-abstention cases `S3A52-041`, `S3A52-042`, and `S3A52-046`.

`S3A52-042` and `S3A52-046` silently returned no proposition **and no abstention**. More seriously, `S3A52-041` contained a non-representable ALT/bilirubin disjunctive stopping rule, yet the parser emitted an unconditional positive `DISCONTINUE` proposition and did not abstain.

This is the highest-priority safety failure in the run because it converts a conditional high-risk management rule into an unconditional machine truth.

By contrast, `S3A52-043`, `S3A52-044`, and `S3A52-045` correctly abstained, showing that the coverage guard exists but remains trigger-dependent rather than semantically complete.

---

## 4. What improved and what did not

Compared with the historical fresh v0.5.1 run:

```text
v0.5.1 fresh F1                        80.33%
v0.5.2 fresh F1                        78.20%

v0.5.1 Critical Recall                 68.75%
v0.5.2 Critical Recall                 67.27%

v0.5.1 Polarity Accuracy               98.00%
v0.5.2 Polarity Accuracy               98.11%

v0.5.1 Population Accuracy             94.23%
v0.5.2 Population Accuracy            100.00%

v0.5.1 Condition Binding Accuracy      98.00%
v0.5.2 Condition Binding Accuracy      92.86%

v0.5.1 Required-abstention Accuracy    25.00%
v0.5.2 Required-abstention Accuracy    50.00%

v0.5.1 Known-case abstention rate      13.16%
v0.5.2 Known-case abstention rate      10.00%
```

The scope-safety repair improved population binding and partially improved abstention behavior, but did **not** improve overall fresh proposition generalization. The result therefore does not support advancing to end-to-end S3.

---

## 5. Release decision

```text
S3b structured entailment       = CONDITIONAL PASS
S3a v0.5.2 exposed development  = PASS
S3a v0.5.2 fresh proposition    = FAIL
S3a v0.5.2 fresh abstention     = FAIL
S3a v0.5.2 trace contract       = PASS
S3a free-text release           = HARD FAIL / BLOCKED
End-to-end S3                   = HARD FAIL
S4 automatic truth ingestion    = BLOCKED
```

No downstream stage may automatically trust free-text-derived S3a truth from v0.5.2.

---

## 6. Next-version recommendation

Do not add one regex or synonym per failed item. The next coherent version should target the failure mechanisms as **S3a v0.5.3 semantic-typing and guard-composition repair**, with the following architectural objectives:

```text
1. typed numeric-condition recognizer
   distinguish eGFR from platelet/liver/vital-sign variables before condition binding

2. sentence-boundary + coordination scope graph
   terminate unsafe condition inheritance and bind each event to its local threshold

3. relation-direction/polarity transducer
   handle active/passive/inverse + negation independently of lexical templates

4. typed ontology-coverage detector
   detect unsupported condition/action semantics before proposition emission;
   never emit a partial unconditional management proposition from an unrepresentable rule

5. semantic-family coverage routing
   separate known-representable-but-unparsed cases from truly out-of-ontology cases,
   reducing both dangerous non-abstention and excessive false abstention
```

Development of v0.5.3 may use v0.5.2 only as **exposed regression**. A new fresh/shadow-held-out must not be created until the implementation is frozen and all exposed proposition, abstention, trace, and unsafe-simplification regression gates pass.
