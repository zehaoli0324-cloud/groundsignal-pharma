# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.1 fresh FAIL** | immutable S3a v0.2-v0.5.1 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.1 exposed regressions 100%; fresh v0.5.1 F1 80.33%; trace PASS | repair compositional scope + passive direction + ontology-coverage abstention; pass exposed gates, then freeze a new untouched S3a held-out |
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

S3b may be used only on reviewed/gold canonical propositions. It does not validate free-text-to-truth automation.

Detailed report:

- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

---

## S3a — active blocker

### Immutable fresh history

```text
v0.2 fresh    F1 62.50%   Critical Recall 52.17%   FAIL
v0.3 fresh    F1 30.77%   Critical Recall 17.86%   HARD FAIL
v0.4 fresh    F1 40.00%   Critical Recall 25.58%   FAIL
v0.5.1 fresh  F1 80.33%   Critical Recall 68.75%   FAIL
```

The v0.5.1 fresh run is a substantial improvement over v0.4 but remains below release thresholds.

Detailed historical reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5_DEV_FAIL_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_DEV_PASS_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`

### S3a v0.5.1 development checkpoint

Frozen implementation:

- `0a3fe9ee29187cfb7e381da0f41bb1ae93875937`

Exposed regression workflow `33988726656`:

| Exposed suite | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---|
| v0.1 | 100% | 100% | 100% | n/a | 100% | PASS |
| v0.2 | 100% | 100% | 100% | 100% | 100% | PASS |
| v0.3 | 100% | 100% | 100% | 100% | 100% | PASS |
| v0.4 | 100% | 100% | 100% | 100% | 100% | PASS |

Trace contract: **PASS**.

This remains regression evidence only.

### S3a v0.5.1 fresh held-out — FAIL

Fresh suite frozen after the implementation and development checkpoint:

```text
suite freeze commit      dea61a9d4aac76303ea0f77bef4617016019cd70
workflow commit          60cea24679875cba0b60e2427b098ae8a3acb540
first-run workflow       33991678951
artifact ID              9976815765
items                    42
expected propositions    66
critical propositions    48
mandatory abstentions     4
```

First observation:

```text
Precision                              87.50%
Recall                                 74.24%
F1                                     80.33%   FAIL
Critical Proposition Recall            68.75%   FAIL
Polarity Accuracy                      98.00%   PASS
Population Accuracy                    94.23%   FAIL
Condition Binding Accuracy             98.00%   PASS
Required-abstention accuracy           25.00%   FAIL
Known-case abstention rate             13.16%   FAIL
Trace contract                            PASS
Combined release                          FAIL
```

The first-run result is immutable. The v0.5.1 fresh suite is now exposed regression data.

Key failure taxonomy:

```text
F1  population trigger coverage gap
F2  interrupted negation scope
F3  condition leakage across contrastive clauses
F4  coordinated multi-event threshold segmentation
F5  incidence relation recognition gap / excessive abstention
F6  endpoint absence-of-result semantics
F7  passive temporal-relation direction
F8  temporal composition across guideline + trial clauses
F9  passive trial-support direction
F10 unknown-critical abstention detector undercoverage
F11 unsafe simplification of disjunctive conditions
```

The highest-priority safety defect is F11. A source rule of the form:

```text
(eGFR <30) OR (dialysis started) → discontinue
```

was simplified to:

```text
eGFR <30 → discontinue
```

without abstention. The current closed condition representation cannot encode the full disjunction, so silent branch deletion is not acceptable.

Full report:

- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`

---

## Current S3 release decision

```text
S3b structured truth engine          = CONDITIONAL PASS
S3a v0.5.1 exposed regression        = PASS
S3a v0.5.1 trace contract            = PASS
S3a v0.5.1 fresh proposition gate    = FAIL
S3a v0.5.1 abstention safety gate    = FAIL
S3a free-text release status         = HARD FAIL / BLOCKED
End-to-end S3                        = HARD FAIL
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
S3a v0.5.2 scope-safety architectural repair
→ event-aware coordination segmentation
→ conservative condition/population inheritance
→ passive/inverse argument normalization
→ ontology-coverage guard + mandatory abstention for non-representable critical semantics
→ rerun all exposed v0.1-v0.5.1 proposition + abstention + trace regressions
→ only if every development gate passes, freeze another brand-new S3a held-out
→ if fresh S3a passes, freeze brand-new end-to-end S3 held-out
→ only if end-to-end S3 passes, begin S4 dedicated eval
```
