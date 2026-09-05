# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. This file prevents architecture completeness from being confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | source governance; v0.1/v0.2 routing regressions; v0.3 fresh intent held-out 91.7%; 10-test live record retrieval; real DailyMed version consistency + critical-passage Recall@1 on 3 high-risk examples | broader source-family passage retrieval, larger fresh-language routing sets, robust concept-type inference, ambiguous-jurisdiction routing |
| S3 | Evidence Verification & Temporal Truth | **Evaluated FAIL / redesign required** | v0.1 24-item evidence-verification benchmark; naive lower bound; structured semantic verifier; fresh v0.2 24-item held-out; explicit false-support safety gate | directional ClaimFrame extraction, zero high-risk false support on a new untouched held-out, broader expert-reviewed evidence relations |
| S4 | Medical KG Construction / Update | Working prototype | case graphs + two reusable backbones + canonical builder | RxNorm/LOINC normalization, persistent graph DB/index, update impact engine, dedicated stage eval |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible model runner, evidence injection, CI fixture | production retriever/reranker, live multi-provider runs, real Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete, real-scale run pending | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full 60-case model scoring |
| S8 | Failure Diagnosis | Framework + some real examples | failure taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters from new 60-case benchmark |
| S9 | Intervention / Post-training Data | Interface complete, training proof pending | SFT/preference/Agent/Judge schemas and reviewed export | actual LoRA/SFT/DPO/RL or system intervention experiment |
| S10 | Candidate + Held-out Regression | CI/fixture proof | baseline-vs-candidate regression gate and held-out split contracts | real post-intervention checkpoint/system improvement on held-out cases |

## S2 checkpoint after v0.3

**S2 = Stage 2, Knowledge Search & Source Routing（知识搜索与来源路由）** is independently observable at four layers:

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

---

## S3 checkpoint after v0.2

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** evaluates whether the system interprets an already-retrieved evidence passage correctly.

### v0.1 naive lexical baseline

```text
24 items
relation accuracy                    58.3%
high-risk false-support rate          8.3%
high-risk false-support count         1
release gate                          FAIL
```

The critical failure was a metformin action/scope error:

```text
evidence: eGFR <45 → reassess benefit/risk
claim:    eGFR <45 → must discontinue
```

The lexical verifier incorrectly returned `DIRECT_SUPPORT`.

### v0.2 structured semantic verifier on known regression set

```text
relation accuracy                    91.7%
high-risk false-support rate          0.0%
release gate                          PASS
```

However, this set had already influenced the verifier design and is therefore only regression evidence.

### v0.2 fresh held-out

A separate 24-item held-out set was frozen after implementation and before first run.

```text
relation accuracy                    50.0%
high-risk negative items              13
high-risk false-support count           2
high-risk false-support rate          15.4%
release gate                          FAIL
```

Two dangerous false-support failures were observed:

1. **temporal supersession** — `Guideline B supersedes A` was incorrectly used to support the claim that A remains current;
2. **observational association → causality** — evidence explicitly saying causality was not established was incorrectly used to support a causal claim.

This shows that unordered semantic cue labels are still insufficient. The next verifier needs directional `ClaimFrame` structure with subject/predicate/object, condition, modality, causal polarity and temporal direction.

Detailed reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`

### S3 release rule

S3 must not automatically approve Knowledge Graph truth while:

```text
High-risk False-Support Rate > 0
```

Current fresh held-out result is 15.4%, therefore S3 is explicitly **not ready for automatic KG truth insertion**.

---

## Overall project checkpoint

The 10-stage lifecycle has an implemented end-to-end scaffold.

- **S2** is the first stage with a full eval → bug diagnosis → fix → held-out/regression → live evidence-retrieval story and can conditionally provide controlled evidence bundles downstream.
- **S3** now has its own real eval and has successfully blocked an apparently strong regression-only verifier from contaminating downstream truth.

The immediate truth-pipeline order remains:

```text
S3 verifier redesign + fresh shadow held-out
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```

S4 should not treat S3 machine-approved claims as automatic gold until S3's high-risk false-support gate passes on a new untouched held-out set.

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
