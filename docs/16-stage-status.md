# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. This file prevents architecture completeness from being confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | source governance; v0.1/v0.2 routing regressions; v0.3 fresh intent held-out 91.7%; 10-test live record retrieval; real DailyMed version consistency + critical-passage Recall@1 on 3 high-risk examples | broader source-family passage retrieval, larger fresh-language routing sets, robust concept-type inference, ambiguous-jurisdiction routing |
| S3 | Evidence Verification & Temporal Truth | Strong prototype, dedicated eval next | passage/locator/scope/time/review contracts and source-backed fixtures | atomic-claim extraction eval, entailment/scope/threshold/negation/temporal/contradiction metrics, more domain review |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | RxNorm/LOINC normalization, persistent graph DB/index, update impact engine, dedicated stage eval |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible model runner, evidence injection, CI fixture | production retriever/reranker, live multi-provider runs, real Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete, real-scale run pending | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full 60-case model scoring |
| S8 | Failure Diagnosis | Framework + some real examples | failure taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters from new 60-case benchmark |
| S9 | Intervention / Post-training Data | Interface complete, training proof pending | SFT/preference/Agent/Judge schemas and reviewed export | actual LoRA/SFT/DPO/RL or system intervention experiment |
| S10 | Candidate + Held-out Regression | CI/fixture proof | baseline-vs-candidate regression gate and held-out split contracts | real post-intervention checkpoint/system improvement on held-out cases |

## S2 checkpoint after v0.3

**S2 = Stage 2, Knowledge Search & Source Routing（知识搜索与来源路由）** is now independently observable at four layers:

```text
Intent recognition
→ Source policy
→ Live authoritative-record retrieval
→ Current version + critical passage retrieval
```

### Routing history

```text
v0.1 40-query regression                         PASS
v0.2 30-query diagnostic/regression              PASS
v0.2b 15-query untouched shadow held-out         FAIL (Primary@1 73.3%)
v0.3 24-query fresh intent/source held-out       PASS (Primary@1 91.7%)
```

The v0.3 fresh set still preserved two non-critical misses: an unseen LOINC observation-normalization phrasing and an RxNorm drug-normalization phrasing. These are not patched away inside the same held-out result.

### Live retrieval

```text
10-test official record retrieval                 PASS 10/10
```

### Current-version / passage retrieval

The first high-risk DailyMed vertical slice tests:

```text
metformin renal threshold
apixaban + NSAID bleeding-risk evidence
sertraline serotonin-syndrome warning
```

After an initial HTTP content-negotiation adapter bug was diagnosed and fixed:

```text
source availability                               100%
current SPL version consistency                   100%
critical passage Recall@1                         100%
critical passage Recall@3                         100%
```

This is evidence that the Stage can retrieve current authoritative evidence on the current three-example slice. It is **not** evidence of comprehensive medical-search coverage.

Detailed reports:

- `medical/stage-evals/S2/V0.2_REPORT.md`
- `medical/stage-evals/S2/V0.3_REPORT.md`

## Overall project checkpoint

The 10-stage lifecycle has an implemented end-to-end scaffold, and **S2 is now the first stage with a full eval → bug diagnosis → fix → held-out/regression → live evidence retrieval story**.

S2 is strong enough to hand controlled evidence bundles to S3 while continuing S2 regression in parallel.

The immediate truth-pipeline order is now:

```text
S3 Evidence Verification Eval
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```

S2 remains continuously monitored and should expand passage/version tests across more source families rather than blocking all downstream work until it becomes a comprehensive medical search engine.

## After upstream stage evals

```text
60 frozen cases (S5)
→ 3–4 real model configurations (S6)
→ human + calibrated automated scoring (S7)
→ cross-case failure taxonomy (S8)
→ select ONE intervention (S9)
→ held-out regression (S10)
```

This is the shortest path from an evaluation-platform prototype to evidence that the platform can drive medical-model improvement.
