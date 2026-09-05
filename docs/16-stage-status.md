# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a fresh FAIL** | full v0.1–v0.6 failure history; split S3a/S3b; S3b fresh v0.3 40/40 with HFSR 0; population-aware S3a evaluator; immutable S3a v0.2 fresh failure | improve S3a semantic generalization and pass a new untouched extraction held-out, then re-test end-to-end S3 |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | RxNorm/LOINC normalization, persistent graph DB/index, update impact engine, dedicated stage eval |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible model runner, evidence injection, CI fixture | production retriever/reranker, live multi-provider runs, real Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete, real-scale run pending | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full 60-case model scoring |
| S8 | Failure Diagnosis | Framework + some real examples | failure taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters from new 60-case benchmark |
| S9 | Intervention / Post-training Data | Interface complete, training proof pending | SFT/preference/Agent/Judge schemas and reviewed export | actual LoRA/SFT/DPO/RL or system intervention experiment |
| S10 | Candidate + Held-out Regression | CI/fixture proof | baseline-vs-candidate regression gate and held-out split contracts | real post-intervention checkpoint/system improvement on held-out cases |

---

## S2 checkpoint

**S2 = Stage 2, Knowledge Search & Source Routing（知识搜索与来源路由）** is independently observable at four layers:

```text
Intent recognition
→ Source policy
→ Live authoritative-record retrieval
→ Current version + critical passage retrieval
```

Key evidence:

```text
v0.2b untouched shadow routing          Primary@1 73.3%  FAIL
v0.3 fresh intent/source held-out       Primary@1 91.7%  PASS
10-test official live retrieval         10/10             PASS
3-test DailyMed current version         100%              PASS
3-test critical passage Recall@1        100%              PASS
```

S2 remains a **conditional pass**, not a claim of comprehensive medical search.

---

## S3 checkpoint

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** asks whether already-retrieved evidence supports a candidate medical claim.

### End-to-end historical fresh tests

```text
v0.1 lexical baseline            Accuracy 58.3%   HFSR  8.3%   FAIL
v0.2 fresh semantic held-out     Accuracy 50.0%   HFSR 15.4%   FAIL
v0.3 fresh ClaimFrame shadow     Accuracy 50.0%   HFSR 58.3%   HARD FAIL
v0.4 fresh atomic shadow         Accuracy 60.0%   HFSR 14.3%   FAIL
v0.5 fresh compositional shadow  Accuracy 75.0%   HFSR  6.25%  FAIL
v0.6 fresh post-v0.5.4 shadow    Accuracy 40.0%   HFSR 17.6%   HARD FAIL
```

The history is preserved because regression-only performance repeatedly overstated fresh semantic generalization.

### Split architecture

```text
S3a — Semantic Proposition Extraction
free text
→ canonical propositions

S3b — Structured Proposition Entailment
canonical evidence + candidate propositions
→ proposition verdicts
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

---

## S3b — conditional pass

Fresh v0.3 structured held-out, first-run workflow `33976929442`:

```text
items                              40
Relation Accuracy                100.0%
High-risk negative items             22
High-risk False-Support Count         0
High-risk False-Support Rate         0.0%
Release Gate                         PASS
```

The suite includes numeric threshold algebra, `EXACT_DOMAIN` vs `SUFFICIENT_ONLY`, population scope, polarity, causality, incidence, temporal supersession, partial support, pharmacogenomics management boundaries and categorical diagnosis polarity.

Detailed report:

- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

S3b can be used conditionally on **reviewed/gold canonical propositions**. It does not validate free-text-to-truth automation.

---

## S3a — current blocker

### Historical lower bound

Original deterministic extraction diagnostic:

```text
Precision                    55.6%
Recall                       47.6%
F1                           51.3%
Critical Proposition Recall  43.75%
```

An ontology-guided v0.2.2 extractor reached 21/21 propositions on the **exposed** v0.1 development set. That result was used only as development evidence.

Before creating a new held-out, the evaluator itself was tightened to include:

```text
F1
Critical Proposition Recall
Polarity Accuracy
Population Accuracy
Condition Binding Accuracy
```

### Fresh S3a v0.2 first run

The new held-out was frozen after extractor commit `c71ef1a2d7d6aebd02a93d844a61222765210a20` and evaluator commit `50a9a7a2f4a5409297434cf0c29f05d1fa6780c5`.

First-run workflow: `33977294927`.

```text
items                                      24
expected propositions                       30
Precision                                83.33%
Recall                                   50.00%
F1                                       62.50%
Critical Proposition Recall              52.17%
Polarity Accuracy                        93.75%
Population Accuracy                      93.75%
Condition Binding Accuracy              100.00%
Release Gate                              FAIL
```

The fresh result is now immutable and the v0.2 set becomes exposed regression data.

Main failure families:

1. initiation/existing-user paraphrase normalization;
2. negation/polarity variants such as `does not render ... contraindicated`;
3. evidence-strength verbs such as `flag` and `cannot determine whether ... caused`;
4. trial endpoint vocabulary such as `primary outcome`, `prespecifies`, `reached`;
5. trial/guideline role and recommendation-object normalization;
6. management absence such as `no dosing instruction`;
7. diagnostic category verbs such as `categorizes`;
8. association negation such as `shows no association`.

Detailed report:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`

### Current S3 release decision

End-to-end S3 remains **HARD FAIL**.

```text
S3b = conditional pass on normalized propositions
S3a = fresh FAIL
therefore
free text → automatic KG truth insertion remains blocked
```

Immediate priority:

```text
S3a generalized semantic normalization v0.2.3+
→ exposed v0.1 + v0.2 regression
→ freeze a completely new S3a held-out
→ if S3a passes, freeze a new end-to-end S3 held-out
```

Historical reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`
- `medical/stage-evals/S3/V0.4_REPORT.md`
- `medical/stage-evals/S3/V0.5_REPORT.md`
- `medical/stage-evals/S3/V0.6_REPORT.md`
- `medical/stage-evals/S3/S3_SPLIT_V0.1_REPORT.md`
- `medical/stage-evals/S3/S3B_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`

---

## Overall project checkpoint

- **S2** conditionally supplies controlled authoritative evidence downstream.
- **S3b** independently passed its fresh structured safety gate.
- **S3a** is now empirically confirmed as the active bottleneck on fresh natural-language variants.
- **S4** must not automatically accept free-text-derived machine truth until S3a and a new end-to-end S3 held-out pass.

Immediate order:

```text
S3a semantic-extraction improvement
→ fresh S3a held-out
→ new end-to-end S3 held-out
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```
