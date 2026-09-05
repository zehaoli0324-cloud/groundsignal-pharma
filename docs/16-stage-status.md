# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh routing 91.7%; 10-test live official retrieval; DailyMed version + passage vertical slice | broader passage-source diversity and terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a architecture pivot** | complete failure history; independent S3a/S3b evals; S3b fresh v0.3 40/40 / HFSR 0; immutable S3a v0.2/v0.3 fresh failures | replace phrase-dominated S3a extraction with a materially stronger semantic-role/relation/argument architecture, freshly validate it, then re-test end-to-end S3 |
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

The structured suite covers numeric threshold algebra, `EXACT_DOMAIN` vs `SUFFICIENT_ONLY`, population/use-state scope, polarity, causality, incidence, temporal supersession, mixed claims, pharmacogenomics management boundaries and diagnostic-category polarity.

Detailed report:

- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

Allowed use:

```text
reviewed/gold canonical propositions
→ S3b deterministic audited verification
```

Not allowed:

```text
unvalidated free text
→ automatic truth
→ unrestricted KG insertion
```

---

## S3a — active blocker

### Initial lower bound

```text
Precision                    55.6%
Recall                       47.6%
F1                           51.3%
Critical Proposition Recall  43.75%
```

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

The v0.2 failures were used to implement generalized semantic canonicalization. On the **exposed** v0.1 and v0.2 regression suites, `s3a-ontology-guided-v0.2.3` subsequently reached 100% on all measured dimensions. Those numbers are regression evidence only.

### Fresh v0.3 first run — architecture rejection

A new 30-item / 39-proposition held-out was frozen after `s3a-ontology-guided-v0.2.3` implementation commit `519d524d10f4e5e0b9aa505b9e27dc8f683106f9`.

First-run workflow: `33977528229`.

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

The fresh v0.3 set introduced new natural-language realizations such as:

```text
therapy commencement / commencing therapy
maintained on medicine / established user
does not amount to / insufficient to classify
surface a safety signal / attribute causally
spontaneous-report totals
primary efficacy outcome / succeeded
displaces guideline
randomized experiment
linked to exposure / dose-management advice
deems / characterized as / describes as
unrelated to / relationship between / no detectable association
```

The collapse from exposed regression 100% to fresh F1 30.8% shows that the current deterministic S3a approach remains **phrase-normalization dominated**.

Detailed reports:

- `medical/stage-evals/S3/S3A_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3A_V0.3_REPORT.md`

### S3a architecture decision

Do **not** continue the loop:

```text
new synonym fails
→ add synonym
→ old suites become 100%
→ create another held-out
```

The next S3a version must make a material architecture change:

```text
lexical normalization
→ semantic role detection
→ relation/event classification
→ subject/object + condition argument binding
→ polarity/modality detection
→ canonical proposition emission
→ confidence / abstention
```

Preferred direction:

> Hybrid constrained semantic extraction: a semantic model or language-understanding component proposes propositions under a closed predicate ontology; deterministic validators enforce predicate allowlists, argument types, polarity, conditions, evidence spans and mandatory abstention/review for unresolved high-risk semantics.

The repository already contains an `openai_compatible` constrained semantic-extractor harness for this next stage when an appropriate model endpoint is available.

---

## Current S3 release decision

```text
S3b structured truth engine = conditional pass
S3a free-text extraction     = hard fail
End-to-end S3                = hard fail
```

Therefore unrestricted automatic free-text → Knowledge Graph truth insertion remains blocked.

Immediate order:

```text
S3a architecture-level redesign
→ exposed regression only during development
→ brand-new fresh S3a held-out
→ brand-new end-to-end S3 held-out
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```
