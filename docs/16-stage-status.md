# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.4 development regression green** | complete failure history; independent S3a/S3b evals; S3b fresh v0.3 40/40 / HFSR 0; immutable S3a v0.2/v0.3 fresh failures; v0.4 semantic-frame architecture with exposed regressions 100% | brand-new fresh S3a validation of v0.4, then brand-new end-to-end S3 held-out |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | terminology normalization, persistent graph/index, update-impact engine, dedicated stage eval |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | live multi-provider runs, production retriever/reranker, Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full real model scoring |
| S8 | Failure Diagnosis | Framework ready | taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters |
| S9 | Intervention / Post-training Data | Interface ready | SFT/preference/Agent/Judge schemas and reviewed export | actual intervention/training experiment |
| S10 | Candidate + Held-out Regression | Fixture proof | candidate-vs-baseline gate and held-out contracts | real post-intervention held-out improvement |

---

## S2 checkpoint

**S2 = Knowledge Search & Source Routing（知识搜索与来源路由）** remains a conditional pass.

```text
v0.2b untouched shadow routing       Primary@1 73.3%  FAIL
v0.3 fresh routing                   Primary@1 91.7%  PASS
live official-record retrieval       10/10             PASS
DailyMed current-version slice       100%              PASS
critical-passage Recall@1 slice      100%              PASS
```

---

## S3 split architecture

```text
S3a — Semantic Proposition Extraction
free text
→ canonical propositions

S3b — Structured Proposition Entailment
canonical evidence/candidate propositions
→ proposition verdicts
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

### S3b — conditional pass

Fresh S3b v0.3, first-run workflow `33976929442`:

```text
items                              40
Relation Accuracy                100.0%
High-risk negative items             22
High-risk False-Support Count         0
High-risk False-Support Rate         0.0%
Release Gate                         PASS
```

S3b can be used only on reviewed/gold canonical propositions. It does not validate free-text-to-truth automation.

Detailed report:

- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

---

## S3a — active blocker

### Fresh v0.2 first run

Workflow `33977294927`:

```text
items                                  24
expected propositions                   30
Precision                            83.33%
Recall                               50.00%
F1                                   62.50%
Critical Proposition Recall          52.17%
Polarity Accuracy                    93.75%
Population Accuracy                  93.75%
Condition Binding Accuracy          100.00%
Release Gate                          FAIL
```

### Fresh v0.3 first run — architecture rejection

Workflow `33977528229`:

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

The collapse from exposed regression performance to fresh v0.3 showed that the previous direct phrase-normalization architecture was not a reliable semantic extractor.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`

### S3a v0.4 — semantic-frame architecture development checkpoint

Implementation commit:

- `4cef42e749f0f53dc7de2e8bae77e640640ddcf6`

v0.4 changes the internal representation to:

```text
free text
→ clause segmentation
→ semantic event / relation frames
→ subject/object argument binding
→ population/use-state binding
→ numeric condition binding
→ polarity + modality
→ canonical proposition compilation
→ unresolved-critical-content abstention
```

Each proposition now has an inspectable intermediate frame containing event type, arguments, polarity, conditions, population, modality, confidence and source span.

Centralized grammar:

- `medical/configs/s3a-semantic-frame-v0.4.json`

Extractor:

- `scripts/s3a_semantic_frame_extractor_v04.py`

Regression workflow `33979442330`:

```text
exposed v0.1   21/21 propositions   F1 100%   PASS
exposed v0.2   30/30 propositions   F1 100%   PASS
exposed v0.3   39/39 propositions   F1 100%   PASS
```

For v0.2 and v0.3, polarity, population and condition-binding accuracy were also 100%. The semantic-frame trace contract passed. The general `medical-development-ci` workflow for the same implementation commit also completed successfully.

These are **exposed regression results only**. They are not fresh evidence and do not change the S3 release state.

Detailed report:

- `medical/stage-evals/S3/S3A_V0.4_DEV_REPORT.md`

---

## Current S3 release decision

```text
S3b structured truth engine      = conditional pass
S3a v0.4 exposed regression      = pass
S3a v0.4 fresh validation        = not run
S3a free-text release status     = hard fail / blocked
End-to-end S3                    = hard fail
```

Therefore unrestricted automatic free-text → Knowledge Graph truth insertion remains blocked.

Immediate order:

```text
freeze brand-new S3a held-out for v0.4
→ preserve first observation
→ if S3a passes, freeze brand-new end-to-end S3 held-out
→ if end-to-end S3 passes, begin S4 dedicated eval
```
