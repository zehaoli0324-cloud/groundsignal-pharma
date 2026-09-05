# GroundSignal 10-Stage Evaluation Taskbook

> Goal: every stage must be independently observable, testable, and regressable. Final-answer failure alone is not sufficient for debugging.

## Core rule

Every stage must define:

```text
Stage Input
→ Expected Output / Gold
→ Metrics
→ Failure Taxonomy
→ Regression Set
```

A downstream failure must never be diagnosed before upstream stages are checked.

## Stage map

| Stage | Eval object | Core metrics | Typical failures |
|---|---|---|---|
| S1 User Need Discovery | user/workflow coverage | frequency, importance, risk, realism, coverage | TASK_NOT_REAL, COVERAGE_GAP, ROLE_MISMATCH |
| S2 Knowledge Search & Source Routing | query → authoritative source(s) | Authoritative Source Recall@K, Source-Type Accuracy, Current-Version Recall, Wrong-Authority Rate, Critical Source Miss Rate | WRONG_SOURCE_TYPE, STALE_SOURCE, SECONDARY_AS_GOLD, SOURCE_MISS |
| S3 Evidence Verification | document → passage/atomic claim | Passage Localization, Entailment, Scope Accuracy, Threshold Accuracy, Temporal Accuracy, Contradiction/Supersession Accuracy | CLAIM_ESCALATION, NEGATION_MISS, SCOPE_ERROR, THRESHOLD_ERROR |
| S4 KG Construction | verified claims → nodes/edges | Edge Precision/Recall, Provenance Completeness, Type Accuracy, Temporal Edge Accuracy, Collision Rate | WRONG_EDGE, MISSING_EDGE, TYPE_ERROR, STALE_ACTIVE_EDGE |
| S5 Case Factory | user task + graph → controlled cases | construct validity, variable isolation, leakage, held-out quality, expert validity | LEAKAGE, MULTI_VARIABLE_CHANGE, BAD_GOLD, UNREALISTIC_CASE |
| S6 Harness | config + case → reproducible run | run reproducibility, prompt/config fidelity, logging completeness, provider parity | CONFIG_DRIFT, MISSING_TRACE, NONREPRODUCIBLE_RUN |
| S7 Evaluation | response/trace → score | human agreement, safety recall, dimension consistency, deterministic-rule accuracy | JUDGE_LENIENCY, JUDGE_HARSHNESS, SAFETY_MISS, STYLE_BIAS |
| S8 Failure Diagnosis | eval records → capability hypothesis | diagnosis precision, cluster stability, causal attribution accuracy | WRONG_ROOT_CAUSE, OVERAGGREGATION, FAILURE_ALIASING |
| S9 Intervention Routing | failure → intervention candidate/data | routing accuracy, reviewer approval rate, training-data precision, leakage control | WRONG_INTERVENTION, BAD_TRAINING_EXPORT, GOLD_CONTAMINATION |
| S10 Regression | candidate vs baseline | target delta, guardrail deltas, new critical errors, held-out generalization | OVERFIT, CAPABILITY_REGRESSION, SAFETY_REGRESSION |

---

# Recommended execution order

Do not evaluate stages strictly in numerical order.

Start with the truth supply chain:

```text
S2 → S3 → S4 → S5
```

Then execution and judging:

```text
S6 → S7
```

Then model-development diagnosis:

```text
S8 → S9 → S10
```

S1 should run in parallel through continuous user research.

Reason: if S2/S3 are wrong, every downstream gold, graph edge, model failure label and training example may be wrong.

---

# S2 acceptance criteria for v0.1

S2 v0.1 evaluates source routing only, before retrieval-engine quality is mixed in.

Minimum benchmark:

- ≥40 queries;
- ≥8 source families;
- medication label, approval status, DDI/PK, PGx, trial registry, terminology, lab terminology, safety signal, clinical guideline/pathway;
- current-version-sensitive queries;
- hard negatives where secondary sources are topically relevant but not acceptable as gold.

Metrics:

```text
Primary Source Recall@1
Acceptable Source Recall@3
Correct Source-Type Accuracy
Current-Source Routing Accuracy
Wrong-Authority Rate
Secondary-as-Gold Rate
Critical Source Miss Rate
```

Release target for a simple deterministic router:

```text
Primary Source Recall@1 >= 0.80
Acceptable Source Recall@3 >= 0.95
Wrong-Authority Rate <= 0.05
Secondary-as-Gold Rate = 0 on high-risk prescribing queries
```

The router baseline is not expected to solve full retrieval. It establishes whether the query is sent to the right evidence system.

---

# S2 v0.2

After routing is stable, evaluate the actual search/retrieval stack:

```text
query
→ routed source family
→ search/API call
→ result ranking
→ current document version
→ critical passage
```

Add:

- Critical Passage Recall@K;
- Current Document Recall@K;
- Evidence Precision@K;
- Stale Result Rate;
- Duplicate/near-duplicate rate;
- query-rewrite gain;
- reranker gain.

---

# Debugging rule

For any final wrong answer, debug in this order:

```text
S2 source correct?
↓ yes
S3 passage/claim correct?
↓ yes
S4 graph correct?
↓ yes
S5 case/gold valid?
↓ yes
S6 run faithful?
↓ yes
S7 score correct?
↓ yes
S8 root cause plausible?
↓
Only then route S9 intervention.
```

This prevents model training from compensating for benchmark or infrastructure bugs.
