# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.4 fresh FAIL** | immutable S3a v0.2-v0.5.4 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.4 exposed development PASS and substantially improved fresh performance | structural S3a repair for shared scope, endpoint negation and unknown-critical abstention; new fresh only after development gates pass |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | terminology normalization, persistent graph/index, update-impact engine, dedicated stage eval; automatic S3a truth ingestion remains blocked |
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

### Immutable fresh history

```text
v0.2 fresh    F1 62.50%   Critical Recall 52.17%   FAIL
v0.3 fresh    F1 30.77%   Critical Recall 17.86%   HARD FAIL
v0.4 fresh    F1 40.00%   Critical Recall 25.58%   FAIL
v0.5.1 fresh  F1 80.33%   Critical Recall 68.75%   FAIL
v0.5.2 fresh  F1 78.20%   Critical Recall 67.27%   FAIL
v0.5.4 fresh  F1 93.44%   Critical Recall 91.30%   FAIL
```

Historical first observations remain immutable. v0.5.4 is now exposed regression data and must not be described as fresh again.

Detailed fresh reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.4_FRESH_REPORT.md`

---

## S3a v0.5.2 — preserved fresh FAIL

Implementation commit `0200076a66454246de03fc015b9fd0911ea087f2`; fresh first-run workflow `33996658862`.

```text
items                                      46
known/representable cases                  40
mandatory abstentions                       6
gold propositions                          73
critical propositions                      55
Precision                                86.67%   FAIL
Recall                                   71.23%   FAIL
F1                                       78.20%   FAIL
Critical Proposition Recall              67.27%   FAIL
Polarity Accuracy                        98.11%   PASS
Population Accuracy                     100.00%   PASS
Condition Binding Accuracy               92.86%   FAIL
Required-abstention accuracy             50.00%   FAIL
Known-case abstention rate               10.00%   FAIL
Trace contract                              PASS
Combined release                            FAIL
```

The highest-priority v0.5.2 safety defect was an ALT/bilirubin conditional stopping rule being simplified to an unconditional positive `DISCONTINUE` truth. That first observation remains immutable.

Detailed report: `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`  
Raw outputs: `medical/stage-evals/S3/runs/s3a-v052-fresh-first-run/`

---

## S3a v0.5.3 — preserved development FAIL

Implementation commit `e602e5d20623dcef519a9e51475ebbc6ef32606d`.

v0.5.3 introduced semantic typing and a stronger ontology guard, but whole-family management rebuilding and additive relation repair caused regressions.

```text
v0.4 exposed F1 / Critical Recall      84.21% / 81.40%   FAIL
v0.5.1 exposed F1 / Critical Recall    94.66% / 91.67%   FAIL
v0.5.2 exposed F1 / Critical Recall    85.14% / 83.64%   FAIL
v0.5.1 mandatory abstention accuracy   75.00%             FAIL
v0.5.2 mandatory abstention accuracy  100.00%             PASS
unsafe-simplification invariant       PASS
trace contract                        PASS
combined development release          FAIL
```

Failure taxonomy F1-F12 remains preserved in `medical/stage-evals/S3/S3A_V0.5.3_DEV_FAIL_REPORT.md`.  
Raw diagnostic replay: `medical/stage-evals/S3/runs/s3a-v053-exposed-first-fail/`.

---

## S3a v0.5.4 — development PASS, fresh FAIL

Implementation commit:

- `33dde2507afb8d34d47f3103ee0bfbfaf716ec5f`

v0.5.4 uses:

```text
1. mature v0.5.2 base frames
2. typed event-local condition/population/polarity ownership
3. non-destructive frame repair
4. relation-family arbitration before proposition compilation
5. normalized high-risk guard morphology
```

### Exposed development evidence

Primary workflow `33999957392` passed the final combined development gate.

| Exposed suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 96.43% | 96.43% | 96.43% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.5.2 | 98.63% | 98.63% | 98.63% | 98.18% | 100.00% | 100.00% | 98.63% | PASS |

Exposed abstention, trace and unsafe-simplification gates also passed. These remain development evidence only.

Detailed development report: `medical/stage-evals/S3/S3A_V0.5.4_DEV_PASS_REPORT.md`

### Fresh v0.5.4 first observation — preserved FAIL

Fresh-suite definition freeze commit:

- `87de9757f1defd480cdd2a13c0b6c452742a5196`

First-run workflow commit:

- `4d3f5d87e147cb94bf48dcabf51953276db539fb`

First-run workflow:

- `34002761349`

Raw-result preservation commit:

- `ed1d684a6bf46478b4092cb314f7d5844d8e98da`

Artifact:

- `s3a-v054-fresh-heldout-first-run` / ID `9979976451`
- SHA-256 `5938138544e5db28d08fe346112d9aaacea80e8cbe523b2c3831330efe158851`

Generated dataset SHA-256:

- `11ea362c6c0592b6886fae2dacaf39adc205b9947fa6cbe0a44c88d115cb69ed`

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

`*` The current polarity metric has a structural-match blind spot: endpoint negative-to-positive semantic inversions in `S3A54F-016` and `S3A54F-019` change predicate family and therefore do not enter the polarity denominator. This is documented, not retroactively rescored.

Fresh failure taxonomy:

```text
F1 cross-sentence population carryover gap
F2 shared preposed condition not inherited across contrastive event
F3 endpoint-negation semantic inversion
F4 unknown high-risk conjunction/action silently unresolved
```

Highest-priority representable error: absence-of-evidence endpoint language can be interpreted as positive endpoint achievement because an embedded phrase such as `was achieved` is recognized before negated evidence scope is resolved.

Highest-priority unknown-critical error: `continue only if oxygen/BP criteria; otherwise hold` returns neither proposition nor mandatory abstention.

Evaluation-quality findings are also frozen:

```text
E1 polarity accuracy excludes semantic inversions that change predicate family
E2 unsafe-simplification report currently conflates silent non-abstention with partial-truth emission
```

Detailed report: `medical/stage-evals/S3/S3A_V0.5.4_FRESH_REPORT.md`  
Raw outputs: `medical/stage-evals/S3/runs/s3a-v054-fresh-first-run/`

---

## Current S3 release decision

```text
S3b structured truth engine             = CONDITIONAL PASS
S3a v0.5.4 exposed development          = PASS
S3a v0.5.4 fresh proposition            = FAIL
S3a v0.5.4 fresh abstention             = FAIL
S3a v0.5.4 fresh trace                  = PASS
S3a free-text release status            = HARD FAIL / BLOCKED
End-to-end S3                           = HARD FAIL
S4 automatic truth ingestion            = BLOCKED
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
v0.5.4 fresh result is now immutable exposed regression data
→ do not repair the frozen first-run artifact or relabel it as fresh
→ next implementation: S3a v0.5.5 Typed Scope Linker + Safety Error Gate
→ development only on already-exposed suites until proposition + abstention + trace + safety gates pass
→ freeze another brand-new fresh held-out only after v0.5.5 implementation is frozen
→ only after a future fresh S3a PASS run a brand-new end-to-end S3 held-out
→ only after end-to-end S3 PASS begin S4 dedicated eval
```
