# S3b v0.3 Fresh Structured Held-out Report

> **S3b = Structured Proposition Entailment（结构化命题蕴含判定）**  
> Engine: `s3b-structured-entailment-v0.2.2`  
> First-run workflow: `33976929442`  
> Status: **CONDITIONAL PASS**

## 术语表

- **Held-out（留出集）**：实现冻结后才用于首次评测、未参与调试的数据。
- **Relation Accuracy（关系准确率）**：最终 `DIRECT_SUPPORT / PARTIAL_SUPPORT / CONTRADICTS / DOES_NOT_SUPPORT` 判定正确的比例。
- **HFSR = High-risk False-Support Rate（高风险错误支持率）**：高风险负例中被错误升级成 `DIRECT_SUPPORT` 的比例。
- **EXACT_DOMAIN（闭合条件域）**：证据声明该条件域就是规则完整适用域，因此域外可以支持反命题或形成矛盾。
- **SUFFICIENT_ONLY（仅充分条件）**：证据只声明某条件足以支持结论，不表示域外一定不成立。

---

## 1. Frozen contract

The v0.3 structured held-out was frozen before its first run with:

```text
40 items
engine = s3b-structured-entailment-v0.2.2
engine commit = 9ca8cab8b5dafdab9b43375b39cce6b6cec9f02c
first_run_must_be_preserved = true
```

Gold distribution:

```text
DIRECT_SUPPORT      12
CONTRADICTS         11
DOES_NOT_SUPPORT    10
PARTIAL_SUPPORT      7
```

High-risk items: 27.

The suite explicitly stress-tests:

- LT / LTE / GT / GTE / RANGE / EQ boundaries;
- `EXACT_DOMAIN` vs `SUFFICIENT_ONLY`;
- population / use-state scope;
- positive and negative action polarity;
- causal-signal boundaries;
- incidence boundaries;
- temporal currentness and `SUPERSEDES` direction;
- mixed claims and `PARTIAL_SUPPORT`;
- pharmacogenomics exposure vs dosing management;
- diagnostic category polarity;
- subgroup / rank overclaim;
- missing-condition and absence-of-evidence behavior.

---

## 2. First-run result

GitHub Actions workflow `33976929442` returned:

```text
n_items                              40
Relation Accuracy                  100.0%
high-risk negative items              22
High-risk False-Support Count          0
High-risk False-Support Rate          0.0%
Release Gate                          PASS
```

Confusion matrix:

```text
DIRECT_SUPPORT     → DIRECT_SUPPORT       12
CONTRADICTS        → CONTRADICTS          11
DOES_NOT_SUPPORT   → DOES_NOT_SUPPORT     10
PARTIAL_SUPPORT    → PARTIAL_SUPPORT       7
```

There were **zero first-run failures**.

---

## 3. Interpretation

This result is strong evidence that the **structured truth-logic layer** can correctly evaluate the current controlled proposition ontology when:

1. subject / predicate / object are already normalized;
2. polarity is explicit;
3. population/use-state scope is explicit;
4. numeric conditions are explicit;
5. decision-rule closure is represented as `EXACT_DOMAIN` or `SUFFICIENT_ONLY`.

It is **not** evidence that end-to-end S3 is solved.

S3a free-text semantic proposition extraction remains the dominant unresolved upstream component. If S3a produces the wrong canonical proposition, S3b can still make a perfectly consistent decision about the wrong structure.

---

## 4. Release decision

S3b may now be described as:

> **CONDITIONAL PASS — candidate structured truth engine for reviewed downstream use.**

It should not yet be used as an unrestricted automatic medical truth generator.

Downstream rules:

```text
S3a extraction not validated
→ S3 end-to-end remains blocked
→ no unrestricted automatic Knowledge Graph truth insertion

reviewed / gold canonical proposition input
→ S3b may be used as a deterministic audited verifier
```

---

## 5. Next priority

The project should now stop spending the majority of S3 effort on S3b and focus on:

```text
S3a Semantic Proposition Extraction
free text
→ constrained canonical proposition schema
→ proposition precision / recall
→ critical-proposition recall
→ polarity / subject-object / condition binding
→ abstention when unresolved
```

Current S3a deterministic lower bound remains approximately:

```text
Precision                    55.6%
Recall                       47.6%
F1                           51.3%
Critical Proposition Recall  43.75%
```

End-to-end S3 can only be re-tested after S3a independently improves and passes a fresh held-out gate.
