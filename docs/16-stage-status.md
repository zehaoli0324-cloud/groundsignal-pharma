# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. This file prevents architecture completeness from being confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Evaluated prototype; generalization gap remains** | source registry, strict-host governance, v0.1/v0.2 routing regressions, fresh shadow-heldout run, 10-test live official-source retrieval suite | robust open-ended intent routing, current-version/canonical-document selection, critical-passage Recall@K |
| S3 | Evidence Verification & Temporal Truth | Strong prototype | passage/locator/scope/time/review contracts | more domain review, automated document diff, contradiction workflow, dedicated stage eval |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | RxNorm/LOINC normalization, persistent graph DB/index, update impact engine, dedicated stage eval |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible model runner, evidence injection, CI fixture | production retriever/reranker, live multi-provider runs, real Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete, real-scale run pending | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full 60-case model scoring |
| S8 | Failure Diagnosis | Framework + some real examples | failure taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters from new 60-case benchmark |
| S9 | Intervention / Post-training Data | Interface complete, training proof pending | SFT/preference/Agent/Judge schemas and reviewed export | actual LoRA/SFT/DPO/RL or system intervention experiment |
| S10 | Candidate + Held-out Regression | CI/fixture proof | baseline-vs-candidate regression gate and held-out split contracts | real post-intervention checkpoint/system improvement on held-out cases |

## S2 checkpoint after v0.2

**S2 = Stage 2, Knowledge Search & Source Routing（知识搜索与来源路由）** has now been evaluated independently rather than inferred from downstream model behavior.

What passed:

```text
40-query v0.1 regression                 PASS
30-query v0.2 diagnostic/regression      PASS
10-test live official-source retrieval   PASS
```

What did not pass:

```text
15-query fresh shadow held-out
Primary Source Recall@1      73.3%
Acceptable Source Recall@3   80.0%
Release Gate                 FAIL
```

The shadow result shows that the current deterministic router remains too dependent on lexical patterns for previously unseen wording. The failed set is preserved rather than tuned until it becomes green and then misrepresented as held-out performance.

Detailed report: `medical/stage-evals/S2/V0.2_REPORT.md`.

## Overall project checkpoint

The 10-stage lifecycle has an implemented end-to-end scaffold, but **stage-level empirical validation has only begun**. S2 is the first stage with a dedicated eval → bug diagnosis → fix → regression workflow.

The immediate truth-pipeline order is now:

```text
S2 v0.3 intent routing + passage retrieval
→ S3 Evidence Verification Eval
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```

Only after the upstream truth pipeline is sufficiently observable should downstream model failures be treated as evidence about the model itself.

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
