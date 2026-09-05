# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.3 development FAIL** | immutable S3a v0.2-v0.5.2 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.3 fixes exposed unsafe simplification but regresses proposition/abstention gates | typed event graph + family arbitration repair, exposed regression, then a new fresh held-out |
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

Historical fresh first-run results remain immutable. The latest independent fresh evidence remains **v0.5.2 FAIL**. v0.5.3 has no fresh result and must not be described as independently validated.

Detailed fresh reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`

---

## S3a v0.5.2 — preserved fresh FAIL

Implementation commit:

- `0200076a66454246de03fc015b9fd0911ea087f2`

Fresh first-run workflow:

- `33996658862`

First-run metrics:

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

Detailed report:

- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`

Raw first-run outputs:

- `medical/stage-evals/S3/runs/s3a-v052-fresh-first-run/`

---

## S3a v0.5.3 — semantic-typing development FAIL

Implementation commit:

- `e602e5d20623dcef519a9e51475ebbc6ef32606d`

v0.5.3 attempted five structural changes:

```text
1. typed numeric-condition mentions
2. sentence-bounded management scope + explicit anaphora handling
3. relation direction separated from relation polarity
4. type-aware ontology coverage guard before proposition emission
5. hard invariant: unrepresentable high-risk rules may not emit simplified truth
```

No fresh set was created. All v0.1-v0.5.2 suites are exposed development/regression data for this version.

Initial exposed-regression workflow:

- `33997403549` — combined development gate FAIL

A deterministic diagnostic replay was then run **without modifying the parser** so the raw metrics/failures would be permanently committed:

- replay workflow `33997463136`
- raw replay preservation commit `fec3aa3ca31a84cfe9d988f6f3499055a3b78416`
- artifact `s3a-v053-exposed-first-fail-replay` / ID `9978486176`
- artifact SHA-256 `683df9f34fd17ab16f085b4035678be373207779155be8cc8bb5e2f1b33b1f25`

### Exposed proposition regression

| Suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 96.67% | 96.67% | 96.67% | 95.65% | 100.00% | 96.67% | 100.00% | PASS |
| v0.3 | 97.44% | 97.44% | 97.44% | 96.43% | 97.44% | 100.00% | 100.00% | PASS |
| v0.4 | 82.76% | 85.71% | 84.21% | 81.40% | 96.00% | 92.31% | 100.00% | **FAIL** |
| v0.5.1 | 95.38% | 93.94% | 94.66% | 91.67% | 98.41% | 96.88% | 98.41% | **FAIL** |
| v0.5.2 | 84.00% | 86.30% | 85.14% | 83.64% | 100.00% | 96.92% | 91.30% | **FAIL** |

### Exposed abstention safety

```text
v0.5.1 mandatory abstention accuracy      75.00%   FAIL
v0.5.1 known-case abstention rate          0.00%   PASS
v0.5.2 mandatory abstention accuracy     100.00%   PASS
v0.5.2 known-case abstention rate          0.00%   PASS
```

The v0.5.1 miss is the QTc/torsades permanent-suspension case `S3A51-039`.

### New safety invariant

```text
v0.5.2 required-abstention cases             6
unsafe simplified propositions               0
unsafe-simplification invariant            PASS
```

This is a real improvement: the exposed ALT/bilirubin rule that v0.5.2 had simplified into unconditional discontinuation is now blocked rather than emitted as automatic truth.

### Trace contract

Trace remains PASS across the replayed exposed suites.

### Combined development gate

```text
all exposed proposition suites       FAIL
abstention safety                    FAIL
trace contract                       PASS
unsafe-simplification invariant      PASS
combined development release         FAIL
fresh validation                     NOT RUN
```

Preserved failure families:

```text
F1  population-role recognition regression after whole-family management rebuild
F2  event-to-threshold ownership remains too coarse inside one sentence
F3  negative management clauses can inherit unrelated eGFR conditions
F4  contraindication negation grammar remains non-compositional
F5  whole-family management rebuild damages mature v0.4/v0.5.1 behavior
F6  additive relation repair leaves contradictory legacy frames alive
F7  endpoint declaration vs endpoint achievement precedence gap
F8  passive trial-support determiner/paraphrase gaps + malformed legacy objects
F9  explicit currentness misses short anaphoric guideline entities
F10 mandatory-abstention guard misses passive/permanent suspension morphology
F11 anaphoric `same eGFR` semantics remain ambiguous
F12 lack of typed event ownership + relation-family arbitration is now dominant blocker
```

Detailed report:

- `medical/stage-evals/S3/S3A_V0.5.3_DEV_FAIL_REPORT.md`

Raw diagnostic replay:

- `medical/stage-evals/S3/runs/s3a-v053-exposed-first-fail/`

---

## Current S3 release decision

```text
S3b structured truth engine             = CONDITIONAL PASS
S3a v0.5.3 exposed proposition gate     = FAIL
S3a v0.5.3 exposed abstention gate      = FAIL
S3a v0.5.3 trace contract               = PASS
S3a unsafe-simplification invariant     = PASS on exposed v0.5.2 cases
S3a v0.5.3 fresh validation             = NOT RUN
S3a free-text release status            = HARD FAIL / BLOCKED
End-to-end S3                           = HARD FAIL
S4 automatic truth ingestion            = BLOCKED
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
v0.5.3 development FAIL is permanently recorded
→ do not patch the individual failed items in this iteration
→ build one coherent S3a v0.5.4 typed event graph + relation-family arbitration repair
→ preserve mature base frames and replace only frames proven inconsistent by typed ownership
→ normalize active/passive high-risk action morphology for the abstention guard
→ run all v0.1-v0.5.2 exposed proposition + abstention + trace + unsafe-simplification regressions
→ only after every development gate passes freeze a brand-new fresh/shadow-held-out
→ only after a fresh S3a PASS create a brand-new end-to-end S3 held-out
→ only if end-to-end S3 passes begin S4 dedicated eval
```
