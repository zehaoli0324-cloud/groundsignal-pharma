# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5 development FAIL** | immutable S3a v0.2/v0.3/v0.4 fresh failures; S3b fresh v0.3 40/40 / HFSR 0; v0.5 compositional scope architecture implemented; exposed v0.4 recovered to 56/56 | repair v0.5 condition-scope, negation-scope and fallback-trace regressions; rerun all exposed gates green; only then freeze a new S3a fresh held-out |
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

### Immutable fresh history

```text
v0.2 fresh: F1 62.50%   Critical Recall 52.17%   FAIL
v0.3 fresh: F1 30.77%   Critical Recall 17.86%   HARD FAIL
v0.4 fresh: F1 40.00%   Critical Recall 25.58%   FAIL
```

The v0.4 fresh suite also measured:

```text
Polarity Accuracy             80.00%
Population Accuracy           94.12%
Condition Binding Accuracy   100.00%
```

The v0.4 result localized the major bottleneck upstream of threshold arithmetic: event recognition, negation/modality scope, argument direction, frame-local population scope and cross-clause composition.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`

### S3a v0.5 compositional frame parser — development FAIL

Implementation commit:

- `35d484cb4b385363b06d048ef64628ef654aa991`

Architecture:

```text
free text
→ sentence segmentation
→ clause / scope graph
→ sentence shared-context inventory
→ frame-local population + condition binding
→ semantic event-family recognition
→ directed argument canonicalization
→ local negation + modality
→ canonical frame
→ proposition compilation
→ unresolved-critical abstention
```

No fresh held-out was created in this version. Development used only the already-exposed v0.1-v0.4 suites.

Regression workflow:

- `33985834584`

Observed exposed metrics:

```text
v0.1   F1 95.24%   Critical Recall 93.75%   Polarity 100%    Condition 95.24%   FAIL
v0.2   F1 96.67%   Critical Recall 95.65%   Polarity 96.67%  Population 100%   PASS
v0.3   F1 97.44%   Critical Recall 96.43%   Polarity 97.44%  Population 100%   PASS
v0.4   F1 100.0%   Critical Recall 100.0%   Polarity 100%    Population 100%   PASS
```

The aggregate development gate is **FAIL** because v0.1 Critical Proposition Recall is 93.75%, below the preregistered 95% threshold. The trace contract also failed because some retained v0.4 fallback frames lacked the new v0.5 `scope_trace` provenance field.

Current v0.5 failure taxonomy:

```text
A. CONDITION_SCOPE_INHERITANCE_ERROR
   local bare comparative `under 30` was missed and an earlier sentence condition `<45` leaked into the frame

B. NEGATION_SCOPE_GAP
   `is not a contraindication` / `is not contraindicated` were emitted as positive contraindication

C. LEGACY_TRACE_ADAPTER_GAP
   v0.4 fallback frames were semantically usable but not adapted into the v0.5 trace schema
```

Detailed audit report:

- `medical/stage-evals/S3/S3A_V0.5_DEV_FAIL_REPORT.md`

The positive development signal is that the formerly failing exposed v0.4 suite is now recovered at 56/56 propositions with 100% on F1, critical recall, polarity, population and condition binding. This is **regression evidence only**, not fresh generalization evidence.

---

## Current S3 release decision

```text
S3b structured truth engine      = CONDITIONAL PASS
S3a v0.5 exposed regression      = FAIL
S3a v0.5 trace contract          = FAIL
S3a v0.5 fresh validation        = NOT RUN
S3a free-text release status     = HARD FAIL / BLOCKED
End-to-end S3                    = HARD FAIL
```

Therefore unrestricted automatic free-text → Knowledge Graph truth insertion remains blocked.

Immediate order:

```text
S3a v0.5.1 architectural repair
→ parse clause-local elided comparatives without threshold leakage
→ generalize target-local copular/passive negation
→ adapt all legacy fallback frames into v0.5 trace/provenance schema
→ rerun exposed v0.1/v0.2/v0.3/v0.4 regression + trace contract
→ only if every development gate is green, freeze a brand-new S3a held-out
→ if fresh S3a passes, freeze brand-new end-to-end S3 held-out
→ if end-to-end S3 passes, begin S4 dedicated eval
```
