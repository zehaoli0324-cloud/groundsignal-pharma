# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; live official retrieval slice; DailyMed current-version + passage slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.5 development FAIL** | immutable S3a fresh history through v0.5.4; S3b fresh v0.3 40/40 / HFSR 0; v0.5.5 improves exposed scope/abstention but fails proposition+safety gates | typed reference compatibility + endpoint discourse state; new fresh only after all development gates pass |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | terminology normalization, persistent graph/index, update-impact engine, dedicated stage eval; automatic S3 truth ingestion blocked |
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

Detailed report: `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

---

## S3a — active blocker

### Immutable independent fresh history

```text
v0.2 fresh    F1 62.50%   Critical Recall 52.17%   FAIL
v0.3 fresh    F1 30.77%   Critical Recall 17.86%   HARD FAIL
v0.4 fresh    F1 40.00%   Critical Recall 25.58%   FAIL
v0.5.1 fresh  F1 80.33%   Critical Recall 68.75%   FAIL
v0.5.2 fresh  F1 78.20%   Critical Recall 67.27%   FAIL
v0.5.4 fresh  F1 93.44%   Critical Recall 91.30%   FAIL
```

Historical first observations remain immutable. v0.5.4 is now exposed regression data and must never again be described as fresh evidence.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.4_FRESH_REPORT.md`

### Preserved development/fresh milestones

```text
v0.5.3 development   FAIL   semantic typing improved guard safety but regressed mature frame families
v0.5.4 development   PASS   typed event graph + relation-family arbitration
v0.5.4 fresh         FAIL   F1 93.44%, Critical Recall 91.30%, required abstention 83.33%
v0.5.5 development   FAIL   proposition + semantic-safety gates fail; abstention + trace gates pass
```

Detailed development reports:

- `medical/stage-evals/S3/S3A_V0.5.3_DEV_FAIL_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.4_DEV_PASS_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.5_DEV_FAIL_REPORT.md`

---

## S3a v0.5.4 — last independent fresh observation

Frozen implementation commit:

- `33dde2507afb8d34d47f3103ee0bfbfaf716ec5f`

Fresh-suite freeze commit:

- `87de9757f1defd480cdd2a13c0b6c452742a5196`

First-run workflow:

- `34002761349`

Raw-result preservation commit:

- `ed1d684a6bf46478b4092cb314f7d5844d8e98da`

First-run metrics:

```text
items                                      38
known/representable cases                  32
mandatory abstentions                       6
gold propositions                          61
critical propositions                      46
Precision                                93.44%   PASS
Recall                                   93.44%
F1                                       93.44%   PASS
Critical Proposition Recall              91.30%   FAIL
Polarity Accuracy                       100.00%   PASS*  
Population Accuracy                      98.28%   PASS
Condition Binding Accuracy               98.28%   PASS
Required-abstention accuracy             83.33%   FAIL
Known-case abstention rate                3.125%  PASS
Trace contract                              PASS
Combined release                            FAIL
```

`*` Historical metric blind spot preserved: predicate-family-changing endpoint inversions were excluded from the old structural-match polarity denominator.

Frozen fresh failure taxonomy:

```text
F1 cross-sentence population carryover gap
F2 shared preposed condition not inherited across contrastive event
F3 endpoint-negation semantic inversion
F4 unknown high-risk conjunction/action silently unresolved
```

The raw first-run data and report remain unchanged.

---

## S3a v0.5.5 — Typed Scope Linker + Safety Error Gate — development FAIL

Implementation last-change commit:

- `3caad022ab9b070a206a4d2307d74cc78093fcc9`

New semantic safety evaluator commit:

- `419bd6f0af79ba3b8665ff5dc09995c9f37d4e82`

Development workflow source commit:

- `7fd97d8f207ca699369cc342d6c6e58aaa375c33`

Workflow:

- `34003220909`

Raw-result preservation commit:

- `69429d721aed4c7233bccdcaac6ea15f2dcaf2a4`

Artifact:

- `s3a-v055-exposed-scope-safety-regression` / ID `9980111993`
- SHA-256 `bfb075e60207792b647dbb0761686014ac2bf6e2c9f611615963dacb6b8719ce`

v0.5.5 adds:

```text
1. independent population-continuity and condition-continuity links
2. explicit shared-preposed typed-condition edges
3. typed endpoint declaration / achievement / evidence-for-achievement arbitration
4. negation/evidence scope before endpoint success emission
5. semantic high-risk gate for unsupported continue-only-if / otherwise-hold rules
6. safety evaluator separating silent non-abstention, partial truth, and high-risk semantic false positives
```

No new fresh or shadow held-out was created. The v0.5.4 fresh set was used only after it became exposed regression data.

### Exposed proposition regression

| Suite | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 98.21% | 97.67% | 100.00% | 100.00% | 98.21% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.5.2 | 95.89% | **94.55%** | 100.00% | 100.00% | 95.89% | **FAIL** |
| v0.5.4 fresh-now-exposed | 98.36% | 97.83% | 100.00% | 100.00% | 100.00% | PASS |

The proposition development gate fails because v0.5.2 Critical Recall is below the fixed 95% threshold.

### Abstention safety

```text
v0.5.1 mandatory abstentions       4/4
v0.5.2 mandatory abstentions       6/6
v0.5.4 exposed mandatory           6/6
combined mandatory                16/16

known representable cases           110
known false abstentions                0
Abstention gate                    PASS
```

The old v0.5.4 `continue only if oxygen/BP criteria; otherwise hold` failure is now correctly blocked.

### New semantic safety error gate

```text
mandatory silent non-abstention        0
mandatory partial truth emission       0
high-risk semantic false positives     1
Safety error gate                   FAIL
```

The remaining high-risk false positive is the exposed cross-sentence endpoint case in which sentence 1 declares a primary endpoint and sentence 2 states that nothing in the supplied results establishes that **the endpoint** was met. The endpoint entity is not carried into sentence 2 before scope arbitration, so positive `ACHIEVES_ENDPOINT` survives.

### Trace contract

```text
rows checked                           228
trace failures                           0
Trace gate                             PASS
```

### v0.5.5 frozen failure taxonomy

```text
F1 typed anaphoric condition cardinality over-propagation
   (`same value` inherits a range-valued antecedent)

F2 shared-preposed renal condition leaks into a local non-renal negative event

F3 preserved historical ambiguity: `same eGFR` antecedent LT 42 vs frozen gold EQ 42

F4 endpoint entity continuity remains sentence-local, allowing one
   absence-of-evidence → positive endpoint-achievement escalation
```

Full analysis: `medical/stage-evals/S3/S3A_V0.5.5_DEV_FAIL_REPORT.md`  
Raw outputs: `medical/stage-evals/S3/runs/s3a-v055-development/`

Combined development decision:

```text
all exposed proposition suites       FAIL
abstention safety                    PASS
semantic safety error gate           FAIL
trace contract                       PASS
combined development release         FAIL
fresh validation                  NOT RUN
```

---

## Current S3 release decision

```text
S3b structured truth engine             = CONDITIONAL PASS
S3a v0.5.5 exposed proposition           = FAIL
S3a v0.5.5 exposed abstention             = PASS
S3a v0.5.5 semantic safety gate           = FAIL
S3a v0.5.5 trace contract                 = PASS
S3a v0.5.5 fresh validation               = NOT RUN
S3a free-text release status              = HARD FAIL / BLOCKED
End-to-end S3                             = HARD FAIL
S4 automatic truth ingestion              = BLOCKED
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
v0.5.5 development FAIL is now immutable exposed development evidence
→ do not create a new fresh held-out yet
→ next implementation: S3a v0.5.6 Typed Reference Graph + Endpoint Discourse State
→ add typed reference compatibility (scalar/range/threshold) instead of phrase patches
→ add event-local variable-conflict veto for shared-condition edges
→ link endpoint entities across discourse before evidence/achievement arbitration
→ retain the v0.5.5 semantic safety evaluator unchanged as a gate
→ only after all exposed proposition + abstention + safety + trace gates PASS freeze a new fresh held-out
→ only after future fresh S3a PASS run a brand-new end-to-end S3 held-out
→ only after end-to-end S3 PASS begin S4 dedicated eval
```
