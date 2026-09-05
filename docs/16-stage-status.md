# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a v0.5.2 fresh FAIL** | immutable S3a v0.2-v0.5.2 fresh history; S3b fresh v0.3 40/40 / HFSR 0; v0.5.2 exposed development gates pass but independent fresh gate fails | structural S3a repair, exposed regression, then a new fresh held-out; end-to-end S3 remains blocked |
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

Historical fresh first-run results remain immutable. The latest independent evidence is now **v0.5.2 FAIL**.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.4_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`

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

The highest-priority v0.5.1 safety defect was silent simplification of a disjunctive rule `(eGFR <30) OR (dialysis started) → discontinue` into a partial renal rule without abstention.

---

## S3a v0.5.2 — development PASS, fresh FAIL

Implementation commit:

- `0200076a66454246de03fc015b9fd0911ea087f2`

v0.5.2 introduced:

```text
1. event-aware coordination segmentation
2. conservative condition/population inheritance
3. passive/inverse argument normalization
4. ontology-coverage guard with mandatory abstention for non-representable critical semantics
```

### Exposed development evidence

Development workflow `33994442500` passed all preregistered development gates.

Exposed proposition regression:

| Suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.3 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |
| v0.4 | 91.53% | 96.43% | 93.91% | 95.35% | 100.00% | 100.00% | 96.43% | PASS |
| v0.5.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | PASS |

Exposed v0.5.1 abstention safety was 4/4 mandatory abstentions correct with 0/38 false abstentions; trace audit was 144/144 valid. These results remain development evidence only.

Detailed development report:

- `medical/stage-evals/S3/S3A_V0.5.2_DEV_PASS_REPORT.md`

### Fresh v0.5.2 first observation — preserved FAIL

Fresh suite freeze commit:

- `fcce2dbcbf780e8a4378fdfb987b7e92e0196f30`

First-run workflow:

- `33996658862`

Raw-result preservation commit:

- `0b20aefd8400472833b6fb86f53b24d23cd489d8`

Artifact:

- `s3a-v052-fresh-heldout-first-run` / ID `9978253888`
- SHA-256 `012d2d7eb8f91e3abc99f13ba5acbcf9329366c7ead3e3bf187b35f90f47a7a3`

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

Mandatory-abstention failures:

```text
S3A52-041
S3A52-042
S3A52-046
```

Known-case false abstentions:

```text
S3A52-012
S3A52-019
S3A52-038
S3A52-039
```

Preserved failure taxonomy:

```text
F1  cross-sentence condition carryover overreach
F2  coordinated event-to-threshold binding failure
F3  non-eGFR numeric distractor falsely typed as eGFR
F4  representable causality phrasing causes false abstention
F5  trial-status / ontology-guard collision
F6  endpoint absence-of-result paraphrase gap
F7  passive trial-support / guideline composition gap
F8  temporal supersession canonicalization / currentness composition
F9  passive inverse association polarity inversion
F10 anaphoric condition + contrastive action scope
F11 negated passive supersession false abstention
F12 ontology-coverage guard undercoverage on unknown critical rules
```

The highest-priority v0.5.2 safety defect is `F12`: `S3A52-041` contains a non-representable ALT/bilirubin disjunctive stopping rule, yet the parser emits an unconditional positive `DISCONTINUE` proposition and does not abstain. `S3A52-042` and `S3A52-046` also return neither propositions nor abstention for unsupported high-risk rules.

An eval-quality note is also preserved: `S3A52-037` contains an ambiguous `same eGFR` gold interpretation. The frozen set/result will not be edited, and excluding that ambiguity cannot change the aggregate FAIL decision.

Detailed fresh report:

- `medical/stage-evals/S3/S3A_V0.5.2_FRESH_REPORT.md`

Raw first-run outputs:

- `medical/stage-evals/S3/runs/s3a-v052-fresh-first-run/`

---

## Current S3 release decision

```text
S3b structured truth engine          = CONDITIONAL PASS
S3a v0.5.2 development gate          = PASS (exposed only)
S3a v0.5.2 fresh proposition gate    = FAIL
S3a v0.5.2 fresh abstention gate     = FAIL
S3a v0.5.2 trace contract            = PASS
S3a free-text release status         = HARD FAIL / BLOCKED
End-to-end S3                        = HARD FAIL
S4 automatic truth ingestion         = BLOCKED
```

Therefore unrestricted automatic free text → S3 truth → Knowledge Graph insertion remains blocked. S4 must not automatically trust S3a-derived truth.

Immediate order:

```text
v0.5.2 fresh FAIL is permanently frozen/exposed
→ do not repair individual fresh items by hardcoding
→ build one coherent S3a v0.5.3 semantic-typing + guard-composition repair
→ run all exposed proposition + abstention + trace + unsafe-simplification regressions
→ only after implementation freeze create a brand-new fresh/shadow-held-out
→ only after a fresh PASS create a brand-new end-to-end S3 held-out
→ only if end-to-end S3 passes begin S4 dedicated eval
```
