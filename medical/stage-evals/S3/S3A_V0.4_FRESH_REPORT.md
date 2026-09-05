# S3a v0.4 Fresh Semantic-Frame Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Extractor: `s3a-semantic-frame-v0.4.0`  
> Extractor implementation commit: `4cef42e749f0f53dc7de2e8bae77e640640ddcf6`  
> Fresh-suite freeze/run commit: `c2e43432d92f573d3f023c4e649ac96e5782ed5a`  
> First-run workflow: `33982583817`  
> Status: **FRESH FAIL / RELEASE BLOCKED**

## 术语表

- **F1 Score（F1 分数）**：Precision（精确率）与 Recall（召回率）的调和平均。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中被正确抽取的比例。
- **Polarity（极性）**：肯定、否定和证据限制方向是否正确。
- **Population scope（人群作用域）**：新启用患者、既往用药患者等人群是否绑定到正确事件。
- **Condition binding（条件绑定）**：eGFR 等阈值/范围是否绑定到正确事件。
- **Semantic frame（语义框架）**：命题生成前的中间事件/关系结构，显式保存 event type、arguments、polarity、population、conditions、modality 和 source span。
- **Abstention（弃权）**：无法安全解析关键语义时停止自动判定而不是猜测。

---

## 1. Frozen evaluation contract

The fresh suite was created only after the v0.4 implementation and exposed-regression checkpoint were frozen.

```text
benchmark                         S3a-semantic-frame-heldout-v0.4
items                             36
expected propositions             56
critical propositions             43
evidence items                    32
candidate items                    4
extractor implementation          4cef42e749f0f53dc7de2e8bae77e640640ddcf6
development checkpoint            85b00fdd55deb4dca03f93f1fc5ac6665953d332
evaluator                         s3a-population-aware-eval-v0.2
first_run_must_be_preserved       true
```

Release gates were preregistered as:

```text
F1 >= 90%
Critical Proposition Recall >= 95%
Polarity Accuracy >= 95%
Population Accuracy >= 95%
Condition Binding Accuracy >= 95%
```

The suite deliberately stressed unseen event wording, long-distance negation/modality, shared numeric conditions, competing population scopes, argument-order inversion, mixed evidence strength, cross-sentence composition, temporal supersession and distractor clauses.

---

## 2. Immutable first-run result

GitHub Actions workflow `33982583817` produced:

```text
Gold propositions                         56
Predicted propositions                    24
True positives                            16
Precision                              66.67%
Recall                                 28.57%
F1                                     40.00%
Critical Proposition Recall            25.58%
Polarity Accuracy                      80.00%
Population Accuracy                    94.12%
Condition Binding Accuracy            100.00%
Release Gate                            FAIL
```

The semantic-frame trace contract itself passed. The workflow artifact `s3a-v04-fresh-heldout-first-run` was preserved (artifact ID `9974179998`, 90-day retention).

This first observation is permanent. The v0.4 suite becomes exposed data after this run and must never later be described as fresh.

---

## 3. Failure taxonomy

### A. Event / relation detection failure — dominant

The largest error class occurs before canonical proposition compilation: the frame parser fails to recognize a valid event/relation under unseen wording.

Representative families:

```text
first instituted / advised against              → initiation restriction missed
benefit versus risk reconsidered                 → reassessment missed
therapy should be withdrawn                      → discontinuation missed
early warning of a safety signal                 → signal-detection relation missed
spontaneous-case tally represents incidence      → incidence relation missed
endpoint attained                                → endpoint achievement missed
assigns / placed in category                     → diagnostic classification missed
```

This is the main reason recall collapsed to 28.57% and critical recall to 25.58%.

### B. Negation and modality scope failure — safety critical

Several cases were not merely missed; they were assigned the wrong polarity.

Examples include:

```text
does not treat ... as a contraindication          → positive contraindication
inadequate grounds for declaring contraindicated  → positive contraindication
insufficient evidence to prove causal attribution → positive causality
neither ... nor ... constitutes contraindication  → positive contraindication
```

Polarity Accuracy was only 80%. This is a direct safety blocker because wrong-positive management/causal propositions can propagate downstream even when S3b itself is correct.

### C. Population/use-state scope failure

Population Accuracy was 94.12%, close to but below the 95% gate. Errors were concentrated in multi-clause statements and paraphrases such as `continuing patient`, `remain on therapy`, and paired existing/new-user clauses.

The important architectural issue is not vocabulary alone: the current implementation can leak a passage-level population assignment across adjacent frames. Population must be assigned per frame/span.

### D. Argument extraction / canonicalization failure

The parser sometimes identified the relation type but failed to preserve the actual argument.

Example:

```text
randomized study supports approach C
current guideline recommends approach D
```

was reduced to generic object `approach` rather than canonical objects `c` and `d`.

Argument-order inversion also failed for forms such as:

```text
No association was observed between outcome Z and biomarker H.
```

The canonical direction should remain `biomarker_h ASSOCIATED_WITH outcome_z` regardless of surface order.

### E. Temporal / supersession grammar failure

Passive and inverse temporal forms were not robustly resolved:

```text
Guideline W retired in favor of X
Guideline Z ... replaced by AA
```

The system needs an explicit directed-relation frame for `newer supersedes older`, not a list of forward verbs.

### F. Multi-proposition and cross-clause composition failure

Fresh failures appeared when one passage contained:

- signal detection plus causal limitation;
- study status plus endpoint declaration plus endpoint non-achievement;
- one numeric condition shared by two management actions;
- existing-user and new-user actions in the same sentence;
- association plus explicit non-causality;
- cross-sentence pronoun continuation.

Clause splitting alone is insufficient. The parser needs a scope graph linking conditions, populations, contrast operators, negation and antecedents to each event frame.

### G. Abstention is partially working, but recall is too low

A number of difficult items safely produced `abstain=true` with unresolved critical content rather than hallucinated propositions. That behavior is preferable to false support, but cannot count as successful extraction.

Two separate targets are therefore needed:

```text
unsafe wrong-positive errors → must approach zero
safe abstention              → allowed when genuinely unresolved, but should decline as semantic coverage improves
```

### H. Numeric condition binding is not the current bottleneck

Condition Binding Accuracy was 100% on semantic matches. Therefore the next version should **not** spend its primary effort on threshold algebra or eGFR parsing.

The active bottleneck is upstream:

```text
event detection
→ argument binding
→ negation/modality scope
→ population/frame scope
→ cross-clause composition
```

---

## 4. Architectural interpretation

v0.4 successfully introduced an auditable semantic-frame intermediate representation, but the fresh result shows that its frame **recognizer** remains too trigger/grammar dominated.

The exposed v0.1/v0.2/v0.3 regressions reaching 100% did not generalize to the new suite. Therefore the correct conclusion is not to add the new v0.4 wording into the grammar and rerun the same set.

The next version must be a material parser change, tentatively **S3a v0.5**, centered on:

```text
typed clause/event spans
→ local semantic-role candidates
→ explicit negation/modal operators
→ per-frame population + condition scope
→ directed relation argument binding
→ cross-clause scope/antecedent graph
→ canonical argument normalization
→ validator + abstention
```

A constrained semantic model can be used as the event/argument proposer if an actual endpoint is available, but deterministic validation must remain responsible for the closed predicate ontology, argument types, source-span traceability, numeric conditions and release blocking.

---

## 5. Release decision

```text
S3b structured entailment            = CONDITIONAL PASS
S3a v0.4 exposed regression          = PASS (not fresh evidence)
S3a v0.4 fresh held-out              = FAIL
S3a free-text release                = HARD FAIL / BLOCKED
End-to-end S3                        = HARD FAIL
free-text → automatic KG truth       = BLOCKED
```

No S3a repair is performed in this checkpoint. The failure is recorded before any tuning, as required.

---

## 6. Next version

Do **not** freeze another fresh held-out yet.

Next development checkpoint:

> **S3a v0.5 compositional frame parser** — materially improve event detection, frame-local scope, negation/modality propagation, argument direction and cross-clause composition; run only exposed regression suites during development. Freeze the next fresh held-out only after that implementation is frozen.
