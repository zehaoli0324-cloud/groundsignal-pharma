# S3a v0.2 Fresh Semantic-Extraction Held-out Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Extractor: `s3a-ontology-guided-v0.2.2`  
> First-run workflow: `33977294927`  
> Status: **FAIL**

## 术语表

- **F1 Score（F1 分数）**：Precision（精确率）和 Recall（召回率）的调和平均。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中被正确抽取的比例。
- **Polarity（极性）**：命题是肯定还是否定，例如“构成禁忌”与“不构成禁忌”。
- **Population scope（人群作用域）**：规则针对新启动患者、既往用药患者或其他人群的限制。
- **Condition binding（条件绑定）**：数值阈值、范围等条件是否绑定到正确的医学动作或关系。
- **Held-out（留出集）**：实现冻结后才用于首次评测、未参与调试的数据。

---

## 1. Frozen contract

The v0.2 S3a held-out was frozen after both the extractor and the stricter evaluator were implemented.

```text
extractor version = s3a-ontology-guided-v0.2.2
extractor commit  = c71ef1a2d7d6aebd02a93d844a61222765210a20
evaluator commit  = 50a9a7a2f4a5409297434cf0c29f05d1fa6780c5
items             = 24
expected propositions = 30
population-aware evaluation = true
first_run_must_be_preserved = true
```

Release criteria were preregistered as:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
```

---

## 2. First-run result

GitHub Actions workflow `33977294927` returned:

```text
Gold propositions                         30
Predicted propositions                    18
True positives                            15
Precision                               83.33%
Recall                                  50.00%
F1                                      62.50%
Critical Proposition Recall             52.17%
Polarity Accuracy                       93.75%
Population Accuracy                     93.75%
Condition Binding Accuracy             100.00%
Release Gate                             FAIL
```

Gate outcome:

```text
F1                     FAIL
Critical recall        FAIL
Polarity accuracy      FAIL
Population accuracy    FAIL
Condition accuracy     PASS
```

This first-run result is immutable historical evidence and must not later be described as a fresh test after the extractor has been tuned on it.

---

## 3. Failure taxonomy

The failures cluster into reusable semantic families rather than isolated cases.

### A. Initiation / use-state paraphrase normalization

Examples:

```text
starting therapy
beginning treatment
already on treatment
```

The extractor did not consistently normalize these expressions to:

```text
new_or_initiating_user
existing_user
```

This affects both proposition recall and population scope.

### B. Negation / polarity paraphrases

Example:

```text
Condition N by itself does not render treatment A contraindicated.
```

The extractor produced a positive contraindication instead of:

```text
CONTRAINDICATED / NEGATIVE
```

This is a safety-critical polarity failure.

### C. Evidence-strength verb normalization

Fresh expressions such as:

```text
flag a safety signal
cannot determine whether the medicine caused the event
provide the true event incidence
```

were not consistently normalized to:

```text
SUPPORTS_SIGNAL_DETECTION
ESTABLISHES_CAUSALITY / NEGATIVE
ESTIMATES_TRUE_INCIDENCE / POSITIVE
```

### D. Trial endpoint lexical normalization

The extractor under-recovered variants such as:

```text
primary outcome
prespecifies a primary endpoint
endpoint was reached
```

Both `HAS_PRIMARY_ENDPOINT` and the negative `ESTABLISHES_ENDPOINT_ACHIEVEMENT` proposition were missed in some cases.

### E. Trial / guideline lexical-role normalization

Example:

```text
A randomized study favors option R, while the current guideline still recommends option P.
```

Problems included:

- `study` not normalized to the trial evidence role;
- guideline recommendation object parsed incompletely (`option` instead of `p`).

### F. Management-absence normalization

Example:

```text
The source offers no dosing instruction.
```

The intended canonical proposition is:

```text
PROVIDES_MANAGEMENT_RULE / NEGATIVE
```

but this paraphrase was missed.

### G. Diagnostic category verb normalization

Example:

```text
The pathology report categorizes finding X as benign.
```

The extractor did not map `categorizes` to:

```text
CLASSIFIED_AS(lesion, benign)
```

and correctly abstained rather than inventing a category.

### H. Association-negation normalization

Example:

```text
Biomarker K shows no association with outcome Z.
```

The extractor did not recover:

```text
ASSOCIATED_WITH / NEGATIVE
```

---

## 4. What the result proves

The result confirms that the previous 21/21 exposed-development result did **not** demonstrate general semantic extraction capability.

It also shows that the stricter S3a evaluator is useful: the fresh test separately exposed population and polarity errors that an evaluator ignoring population could have hidden.

The positive signal is that **condition binding itself scored 100% whenever the semantic relation was recognized**. Therefore the next version should primarily improve lexical/semantic normalization and role/polarity recognition rather than rewriting the numeric condition parser again.

---

## 5. Release decision

S3a remains **FAIL**.

Therefore end-to-end S3 remains blocked even though S3b has independently passed its fresh structured held-out.

Current allowed flow:

```text
reviewed/gold canonical propositions
→ S3b deterministic verification
```

Current blocked flow:

```text
free text
→ current S3a automatic extraction
→ unrestricted S3b decision
→ automatic Knowledge Graph truth insertion
```

---

## 6. Next version

The v0.2 held-out is now an **exposed regression set**.

S3a v0.2.3/v0.3 development should address the semantic families above using reusable lexical/ontology normalization rather than one-item conditionals.

Recommended implementation modules:

```text
use-state normalizer
negation / polarity normalizer
evidence-strength verb normalizer
trial endpoint vocabulary normalizer
guideline-role/object normalizer
management-absence normalizer
diagnostic-category verb normalizer
association-negation normalizer
```

After the exposed v0.1 + v0.2 regression suites stabilize, a completely new S3a held-out must be frozen before any claim of fresh improvement.
