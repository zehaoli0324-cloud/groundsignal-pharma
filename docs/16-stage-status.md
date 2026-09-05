# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.4 development PASS, fresh NOT RUN** | immutable S3a v0.2-v0.5.2 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.4 passes all exposed proposition, abstention, trace and unsafe-simplification gates | freeze and first-run a brand-new v0.5.4 fresh/shadow held-out; only after fresh PASS run new end-to-end S3 held-out |
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
v0.5.2 fresh  F1 78.20%   Critical Recall 67.27%   FAIL
```

Historical fresh first-run results remain immutable. The latest independent fresh evidence is still **v0.5.2 FAIL**. v0.5.3 and v0.5.4 have no fresh result and must not be described as independently validated.

Detailed fresh reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`

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

v0.5.3 introduced semantic typing and a stronger guard, but whole-family management rebuilding and additive relation repair caused regressions.

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

## S3a v0.5.4 — typed event graph + relation-family arbitration development PASS

Implementation commit:

- `33dde2507afb8d34d47f3103ee0bfbfaf716ec5f`

Primary regression workflow:

- `33999957392` — **SUCCESS**, including final enforced combined gate

Raw-metric persistence workflow:

- `33999993603`

Raw-result preservation commit:

- `12690961a5dfadd21ac6a092fd4c596db189fd2c`

Raw results:

- `medical/stage-evals/S3/runs/s3a-v054-exposed-dev-pass/`

v0.5.4 changes the composition strategy rather than expanding one-case regex answers:

```text
1. start from mature v0.5.2 base frames
2. typed event-local condition/population/polarity ownership
3. non-destructive frame repair
4. relation-family arbitration before proposition compilation
5. normalized active/passive high-risk guard morphology
```

### Exposed proposition regression

| Suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 96.43% | 96.43% | 96.43% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.5.2 | 98.63% | 98.63% | 98.63% | 98.18% | 100.00% | 100.00% | 98.63% | PASS |

### Exposed abstention safety

```text
v0.5.1 mandatory abstentions             4/4 correct
v0.5.1 known-case false abstentions      0/38
v0.5.2 mandatory abstentions             6/6 correct
v0.5.2 known-case false abstentions      0/40
abstention gate                          PASS
```

### Safety invariant and trace

```text
v0.5.2 required-abstention items             6
unsafe simplified propositions               0
unsafe-simplification invariant            PASS
trace rows                                  190
trace failures                                0
trace contract                             PASS
```

Combined development gate:

```text
all exposed proposition suites          PASS
abstention safety                       PASS
trace contract                          PASS
unsafe-simplification invariant         PASS
combined development release            PASS
fresh validation                        NOT RUN
```

Residual exposed diagnostics are deliberately retained:

```text
S3A4-021  shared preposed eGFR condition is not propagated to second event
S3A4-022  same-eGFR clause does not receive the antecedent condition
S3A52-037 immutable gold interprets same eGFR as EQ 42 after antecedent LT 42;
           v0.5.4 preserves the antecedent operator; annotation ambiguity remains
```

Detailed report:

- `medical/stage-evals/S3/S3A_V0.5.4_DEV_PASS_REPORT.md`

---

## Current S3 release decision

```text
S3b structured truth engine             = CONDITIONAL PASS
S3a v0.5.4 exposed proposition gate     = PASS
S3a v0.5.4 exposed abstention gate      = PASS
S3a v0.5.4 trace contract               = PASS
S3a unsafe-simplification invariant     = PASS
S3a v0.5.4 fresh validation             = NOT RUN
S3a free-text release status            = HARD FAIL / BLOCKED
End-to-end S3                           = HARD FAIL
S4 automatic truth ingestion            = BLOCKED
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
v0.5.4 implementation is now frozen at 33dde250...
→ do not modify the parser before the next fresh suite is created
→ freeze a brand-new v0.5.4 fresh/shadow-held-out using capability-level stressors
→ permanently preserve its first observation
→ if fresh FAIL: sync raw result + taxonomy + stage status before any repair
→ if fresh PASS: freeze a brand-new end-to-end S3 held-out
→ only if end-to-end S3 passes begin S4 dedicated eval
```
