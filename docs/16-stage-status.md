# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.2 development PASS, fresh NOT RUN** | immutable S3a v0.2-v0.5.1 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.2 exposed proposition+abstention+trace gates pass | freeze and first-run a brand-new v0.5.2 S3a held-out; only then consider a new end-to-end S3 held-out |
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

Historical fresh first-run results remain immutable. The last independent evidence is still v0.5.1 FAIL.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`

### S3a v0.5.1 fresh held-out — preserved FAIL

First-run workflow `33991678951`:

```text
items                                      42
expected propositions                       66
critical propositions                       48
mandatory abstentions                        4
Precision                                87.50%
Recall                                   74.24%
F1                                       80.33%   FAIL
Critical Proposition Recall              68.75%   FAIL
Polarity Accuracy                        98.00%   PASS
Population Accuracy                      94.23%   FAIL
Condition Binding Accuracy               98.00%   PASS
Required-abstention accuracy             25.00%   FAIL
Known-case abstention rate               13.16%   FAIL
Trace contract                              PASS
Combined release                            FAIL
```

Failure taxonomy remains preserved:

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

The highest-priority safety defect was F11: a source rule `(eGFR <30) OR (dialysis started) → discontinue` was incompletely simplified to `eGFR <30 → discontinue` without abstention.

---

## S3a v0.5.2 — scope-safety development PASS

Implementation commit:

- `0200076a66454246de03fc015b9fd0911ea087f2`

v0.5.2 introduces four structural mechanisms:

```text
1. event-aware coordination segmentation
2. conservative condition/population inheritance
3. passive/inverse argument normalization
4. ontology-coverage guard with mandatory abstention for non-representable critical semantics
```

The ontology-coverage guard suppresses partial propositions when the current closed schema cannot represent every critical branch/condition/action. It therefore changes unsupported disjunctions and unsupported critical management rules from silent simplification to explicit abstention.

Development workflow:

- `33994442500`

Artifact:

- `s3a-v052-exposed-scope-safety-regression` / ID `9977613430`
- SHA-256 `0c80593b0d6bc8802667d12a6e0819b4aa04720f1de748e86b602b455b61d6e0`

Exposed proposition regression:

| Suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 91.53% | 96.43% | 93.91% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |

Exposed v0.5.1 abstention safety:

```text
mandatory cases                     4
correct mandatory abstentions       4
required-abstention accuracy      100%
known representable cases          38
known-case false abstentions        0
known-case abstention rate          0%
Gate                              PASS
```

Trace contract:

```text
rows checked                       144
failures                             0
Gate                               PASS
```

Combined development gate:

```text
all exposed proposition suites     PASS
abstention safety                  PASS
trace contract                     PASS
development release                PASS
fresh validation                   NOT RUN
```

Important: v0.4 is above all preregistered thresholds but is not perfect. Four exposed diagnostics remain, including two shared-condition/anaphora binding misses and two spurious option-object normalizations. These failures are preserved in `S3A_V0.5.2_DEV_PASS_REPORT.md`; development PASS must not be represented as 100% across every exposed suite.

Detailed report:

- `medical/stage-evals/S3/S3A_V0.5.2_DEV_PASS_REPORT.md`

---

## Current S3 release decision

```text
S3b structured truth engine          = CONDITIONAL PASS
S3a v0.5.2 development gate          = PASS
S3a v0.5.2 abstention development    = PASS
S3a v0.5.2 trace contract            = PASS
S3a v0.5.2 fresh validation          = NOT RUN
S3a free-text release status         = HARD FAIL / BLOCKED
End-to-end S3                        = HARD FAIL
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
freeze brand-new S3a v0.5.2 fresh held-out with implementation unchanged
→ preserve its first observation permanently
→ if fresh S3a FAIL: sync report/taxonomy/status before any repair
→ if fresh S3a PASS: freeze brand-new end-to-end S3 held-out
→ only if end-to-end S3 passes: begin S4 dedicated eval
```
