# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **Evaluated HARD FAIL / split redesign required** | v0.1–v0.6 fresh evaluation history; immutable v0.5/v0.6 first-run reports; strong exposed-suite regression control; deterministic threshold/polarity/aggregation logic | independently validate S3a semantic proposition extraction and S3b structured entailment, then re-test end-to-end on a new untouched set |
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

Two v0.3 routing misses remain preserved: LOINC observation normalization and RxNorm drug normalization. S2 is therefore a **conditional pass**, not a claim of comprehensive medical search.

---

## S3 checkpoint through v0.6

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** asks whether an already-retrieved evidence passage supports a candidate medical claim.

Hard release criteria:

```text
Relation Accuracy >= 80%
High-risk False-Support Rate = 0
```

### Fresh-test history

```text
v0.1 lexical baseline            Accuracy 58.3%   HFSR  8.3%   FAIL
v0.2 fresh semantic held-out     Accuracy 50.0%   HFSR 15.4%   FAIL
v0.3 fresh ClaimFrame shadow     Accuracy 50.0%   HFSR 58.3%   HARD FAIL
v0.4 fresh atomic shadow         Accuracy 60.0%   HFSR 14.3%   FAIL
v0.5 fresh compositional shadow  Accuracy 75.0%   HFSR  6.25%  FAIL
v0.6 fresh post-v0.5.4 shadow    Accuracy 40.0%   HFSR 17.6%   HARD FAIL
```

`HFSR = High-risk False-Support Rate（高风险错误支持率）`.

The history is intentionally preserved because regression-only scores repeatedly looked strong while genuinely new language exposed unsafe generalization.

### v0.5.4 regression recovery before v0.6

Before the v0.6 set was frozen, `s3-compositional-proposition-v0.5.4` had the following **exposed-suite** results:

```text
v0.1 diagnostic             100.0%   high-risk false support 0
v0.2 diagnostic              91.7%   high-risk false support 0
v0.3 diagnostic             100.0%   high-risk false support 0
v0.4 diagnostic             100.0%   high-risk false support 0
v0.5 exposed regression     100.0%   high-risk false support 0
```

These numbers correctly demonstrate regression control, but v0.6 proves they do **not** demonstrate free-text semantic generalization.

### v0.6 untouched first run

The 40-item v0.6 shadow set was frozen at commit `56c8a7b8af98fec284006edbeebe837199fea5fa`, after verifier implementation commit `98923941b40ead8a5ed983862fe9755efb805631`.

First-run workflow: `33974863676`.

```text
items                                      40
Relation Accuracy                        40.0%
high-risk negative items                   17
High-risk False-Support Count                3
High-risk False-Support Rate             17.6%
Release Gate                              HARD FAIL
```

Critical false-support classes:

1. `MISSING_CONDITION_OVERCLAIM` — a management action was asserted despite the decision-critical eGFR being unmeasured;
2. `NEGATION_POLARITY_ERROR` — `does not constitute a contraindication` was promoted to a positive contraindication;
3. `PGX_TO_MANAGEMENT_ESCALATION` — an exposure association plus no dosing rule was promoted to a mandatory dosing claim.

Detailed first-run report:

- `medical/stage-evals/S3/V0.6_REPORT.md`

### Architectural conclusion from v0.6

The dominant problem is now identifiable: one end-to-end number mixes **semantic extraction** with **truth logic**.

Many v0.6 failures contain `no_candidate_propositions` or an incorrect canonical proposition. In those cases the deterministic threshold/polarity/temporal logic never receives the right structure.

S3 is therefore split into two independently observable sub-stages:

```text
S3a — Semantic Proposition Extraction
free-text evidence / candidate claim
→ canonical atomic propositions

S3b — Structured Proposition Entailment
canonical evidence propositions
+ canonical candidate propositions
→ SUPPORTED / CONTRADICTED / UNSUPPORTED per proposition
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

The intended measurement becomes:

```text
S3a:
- proposition precision / recall / F1
- critical-proposition recall
- polarity accuracy
- condition/action binding accuracy
- subject/object direction accuracy

S3b:
- relation accuracy
- high-risk false-support rate
- threshold algebra accuracy
- temporal-direction accuracy
- absence-vs-contradiction accuracy
- mixed-claim aggregation accuracy

End-to-end S3:
- only re-tested after S3a and S3b each have independent evidence
```

### Current release decision

S3 remains **HARD FAIL** and is **not eligible for automatic KG truth insertion**.

The immediate next step is not another lexical patch to v0.6. Instead:

```text
build S3a extraction gold + evaluator
→ build S3b structured-entailment gold + evaluator
→ identify which sub-stage limits performance
→ improve that sub-stage
→ freeze a new end-to-end untouched set only after the split-stage gates pass
```

Historical first-run reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`
- `medical/stage-evals/S3/V0.4_REPORT.md`
- `medical/stage-evals/S3/V0.5_REPORT.md`
- `medical/stage-evals/S3/V0.6_REPORT.md`

---

## Overall project checkpoint

- **S2** can conditionally provide controlled authoritative evidence bundles downstream.
- **S3** has a valuable failure history: fresh sets repeatedly reveal problems hidden by regression success. v0.6 now localizes the architectural ambiguity to semantic extraction versus deterministic entailment.
- **S4** must not automatically trust machine-approved S3 claims while S3 remains failed.

Immediate order:

```text
S3a extraction eval
→ S3b structured entailment eval
→ new end-to-end S3 held-out after sub-stage stabilization
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```

After upstream truth stages are sufficiently validated:

```text
60 frozen cases (S5)
→ 3–4 real model configurations (S6)
→ human + calibrated automated scoring (S7)
→ cross-case failure taxonomy (S8)
→ select ONE intervention (S9)
→ held-out regression (S10)
```
