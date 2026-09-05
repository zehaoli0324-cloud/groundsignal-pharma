# S3a v0.3 Fresh Semantic-Extraction Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Extractor: `s3a-ontology-guided-v0.2.3`  
> First-run workflow: `33977528229`  
> Status: **HARD FAIL**

## 术语表

- **F1 Score（F1 分数）**：Precision（精确率）与 Recall（召回率）的调和平均。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中成功抽取的比例。
- **Polarity（极性）**：肯定/否定语义是否被正确保留。
- **Population scope（人群作用域）**：新启动患者、既往用药患者等使用状态是否正确绑定。
- **Condition binding（条件绑定）**：阈值/范围是否绑定到正确的医学动作或关系。
- **Abstention（弃权）**：无法安全解析时不猜测，而是标记无法自动判定。

---

## 1. Frozen contract

The v0.3 held-out was frozen after `s3a-ontology-guided-v0.2.3` had already reached 100% on both exposed v0.1 and v0.2 regression suites.

```text
extractor version = s3a-ontology-guided-v0.2.3
extractor commit  = 519d524d10f4e5e0b9aa505b9e27dc8f683106f9
evaluator commit  = 50a9a7a2f4a5409297434cf0c29f05d1fa6780c5
items             = 30
expected propositions = 39
population-aware evaluation = true
first_run_must_be_preserved = true
```

Release criteria:

```text
F1 >= 90%
Critical Proposition Recall >= 95%
Polarity Accuracy >= 95%
Population Accuracy >= 95%
Condition Binding Accuracy >= 95%
```

---

## 2. First-run result

GitHub Actions workflow `33977528229` returned:

```text
Gold propositions                         39
Predicted propositions                    13
True positives                             8
Precision                               61.54%
Recall                                  20.51%
F1                                      30.77%
Critical Proposition Recall             17.86%
Polarity Accuracy                       80.00%
Population Accuracy                     80.00%
Condition Binding Accuracy              88.89%
Release Gate                         HARD FAIL
```

All preregistered gate dimensions failed.

This result is immutable first-run evidence. The v0.3 set is now exposed regression data and must never be presented later as untouched performance.

---

## 3. What changed relative to v0.2

The v0.2 fresh test exposed a finite set of paraphrase families. After generalized canonicalization for those families, the exposed v0.1 and v0.2 suites both reached 100%.

The v0.3 held-out deliberately used different natural-language realizations, including:

```text
therapy commencement
patient commencing therapy
maintained on the medicine
established user
does not amount to a contraindication
insufficient to classify ... as contraindicated
surface a safety signal
not sufficient to attribute causally
spontaneous-report totals
primary efficacy outcome
succeeded
displaces guideline
randomized experiment
linked to exposure
dose-management advice
deems / characterized as
unrelated to
reports a relationship
```

Performance collapsed, demonstrating that the current architecture is still **phrase-normalization dominated** rather than genuinely robust semantic extraction.

---

## 4. Failure families

### A. Use-state lexical generalization

Fresh phrases such as:

```text
therapy commencement
commencing therapy
maintained on the medicine
established user
those continuing the medicine
```

were not consistently mapped to:

```text
new_or_initiating_user
existing_user
```

Population Accuracy fell to 80% on semantic matches.

### B. Negation semantics remain surface-form dependent

Examples:

```text
does not amount to a contraindication
insufficient to classify ... as contraindicated
```

were misread as positive contraindications rather than negative propositions.

### C. Pharmacovigilance semantics are too verb-specific

The extractor missed or abstained on:

```text
surface a safety signal
not sufficient to attribute causally
spontaneous-report totals do not establish incidence
number of spontaneous reports gives incidence
prompt investigation of a signal
```

This shows that `identify/detect/flag`-style replacements are not enough.

### D. Trial endpoint semantics are too lexical

Unseen variants such as:

```text
primary efficacy outcome
specifies / prespecified
succeeded
no finding confirming success
```

were not reliably normalized to endpoint identity and endpoint-achievement propositions.

### E. Temporal-guideline semantics need relation grammar

Example:

```text
Guideline T displaces Guideline S and becomes the current operative source.
```

No propositions were recovered. The current parser depends on a small verb list such as `replaces/supersedes` rather than a generalized directed-relation grammar.

### F. Trial evidence vs current-guideline state

Example:

```text
A randomized experiment supports strategy U,
whereas the current guideline continues to recommend strategy V.
```

Both intended propositions were missed. Role classification (`experiment` → trial evidence) and recommendation-object extraction remain fragile.

### G. Pharmacogenomics management boundary

Example:

```text
genotype is linked to increased exposure
+ no dose-management advice
```

The exposure association may be recognized while the missing-management proposition is lost.

### H. Diagnostic classification verbs are open-ended

Examples:

```text
deems finding X benign
characterized as indeterminate
describes lesion as malignant
```

show that enumerating `classifies/categorizes/labels` is not a scalable solution.

### I. Association language is open-ended

Examples:

```text
was unrelated to
reports a relationship between
no detectable association between
```

were not robustly mapped to positive/negative `ASSOCIATED_WITH` propositions.

---

## 5. Architectural conclusion

The result rejects the strategy:

```text
new held-out synonym failure
→ add synonym replacement
→ regression 100%
→ repeat
```

That loop is benchmark overfitting even when each replacement is phrased as a reusable rule.

The next S3a architecture should instead separate:

```text
lexical normalization
→ semantic role detection
→ relation/event classification
→ argument binding
→ polarity/modality detection
→ canonical proposition emission
→ confidence / abstention
```

A central semantic lexicon/ontology may assist normalization, but it should not be the primary reasoning engine.

Recommended next direction:

> **Hybrid constrained semantic extraction**: a semantic model or language-understanding component proposes canonical propositions under a closed predicate schema; deterministic validation enforces allowed predicates, argument types, polarity, conditions, source spans, confidence, and mandatory abstention for unresolved high-risk semantics.

The repository already contains an `openai_compatible` constrained semantic-extractor harness that can support this architecture when a model endpoint is available.

---

## 6. Release decision

S3a remains **HARD FAIL**.

Therefore:

```text
S3b structured truth engine = conditional pass
S3a free-text extraction     = hard fail
End-to-end S3                = hard fail
```

Unrestricted automatic Knowledge Graph truth insertion remains blocked.

---

## 7. Next version

Do not create another fresh held-out immediately after adding a few v0.3 synonyms.

Next development work should:

1. create a centralized semantic-role / lexical ontology rather than scattered replacements;
2. make role, relation, argument, polarity and modality explicit intermediate outputs;
3. preserve abstention as a valid safe outcome;
4. use v0.1/v0.2/v0.3 only as exposed development/regression data;
5. freeze a new held-out only after the architecture itself changes materially.
