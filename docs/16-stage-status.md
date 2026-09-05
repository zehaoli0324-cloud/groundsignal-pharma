# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. This file prevents architecture completeness from being confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | source governance; v0.1/v0.2 routing regressions; v0.3 fresh intent held-out 91.7%; 10-test live record retrieval; real DailyMed version consistency + critical-passage Recall@1 on 3 high-risk examples | broader source-family passage retrieval, larger fresh-language routing sets, robust concept-type inference, ambiguous-jurisdiction routing |
| S3 | Evidence Verification & Temporal Truth | **Evaluated HARD FAIL / v0.4 redesign in progress** | v0.1 lexical baseline; v0.2 semantic-cue verifier; v0.3 directional ClaimFrame schema; three frozen diagnostic/held-out suites; explicit false-support safety gate | clause-scoped atomic proposition parsing, polarity-preserving negative relations, safe threshold/action binding, zero high-risk false support on a new untouched held-out |
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

## S3 checkpoint after v0.3

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** evaluates whether an already-retrieved evidence passage actually supports a candidate medical claim.

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

### v0.2 structured semantic verifier

On the already-known v0.1 regression set:

```text
relation accuracy                    91.7%
high-risk false-support rate          0.0%
release gate                          PASS
```

On its separate 24-item fresh held-out:

```text
relation accuracy                    50.0%
high-risk negative items              13
high-risk false-support count           2
high-risk false-support rate          15.4%
release gate                          FAIL
```

This exposed temporal-direction and causality-polarity failures.

### v0.3 directional ClaimFrame verifier

v0.3 introduced explicit directional fields:

```text
subject → predicate → object
condition
modality
causal status
temporal status
polarity
```

The verifier was committed first (`e10efe81533766e3fd586c07f2cd4f4365c5e82b`). Only afterward was the new untouched 24-item shadow-heldout frozen (`ba1f60d56cd5421fcb7c00d41551b2a3e87525b1`).

First shadow-heldout run:

```text
relation accuracy                    50.0%
high-risk negative items              12
high-risk false-support count           7
high-risk false-support rate          58.3%
release gate                          FAIL
```

This is a **hard failure** and is worse than v0.2 on the safety metric.

The result does not show that directional structure is useless. It shows that the **extractor feeding the directional frame is unsafe**.

Main root causes:

1. `CLAUSE_ACTION_BINDING_ERROR` — a broad text window attaches the wrong action to a nearby numeric threshold in compound sentences;
2. `NEGATION_POLARITY_LOSS` — phrases such as “does not provide a contraindication rule” can still create positive contraindication features;
3. `UNSAFE_POSITIVE_FALLBACK` — high frame/lexical overlap can still promote an unresolved claim to `DIRECT_SUPPORT`;
4. incomplete causal-polarity parsing;
5. negative clinical-management evidence is not represented as an explicit negative predicate.

Examples of dangerous v0.3 false support include:

```text
eGFR 34 → incorrectly treated as contraindicated
existing user eGFR 41 → incorrectly treated as requiring discontinuation
risk increase → incorrectly upgraded to absolute prohibition
possible syndrome → incorrectly upgraded to confirmed diagnosis
raw spontaneous-report count → incorrectly upgraded to true incidence
trial registration → incorrectly upgraded to efficacy
CYP3A mechanism → incorrectly upgraded to clinical contraindication
```

Detailed reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`

### S3 release rule

S3 must not automatically approve Knowledge Graph truth while:

```text
High-risk False-Support Rate > 0
```

Current untouched v0.3 shadow-heldout result:

```text
58.3% → HARD FAIL
```

Therefore S3 is explicitly **not ready for automatic KG truth insertion**.

### S3 v0.4 redesign target

The next architecture is:

```text
Evidence passage
→ clause segmentation
→ atomic propositions
→ polarity-preserving proposition frames
→ candidate proposition frames
→ fieldwise/constraint comparison
```

Important safety rules:

- bind a numeric condition only to the action in the same atomic proposition;
- a negated clause must produce negative polarity, never a positive modality;
- unresolved high-risk structural mismatch defaults to `DOES_NOT_SUPPORT` or human review, never `DIRECT_SUPPORT`;
- v0.3 shadow-heldout is now frozen as diagnostic/regression evidence and must not be renamed as untouched held-out after tuning.

---

## Overall project checkpoint

The 10-stage lifecycle has an implemented end-to-end scaffold.

- **S2** has a complete eval → diagnosis → fix → held-out/regression → live retrieval story and can conditionally provide controlled evidence bundles downstream.
- **S3** now has three generations of independent stage eval and is correctly blocking unsafe machine-generated truth from entering the Knowledge Graph.

The immediate truth-pipeline order is:

```text
S3 v0.4 atomic-proposition redesign + new untouched shadow held-out
→ S4 Knowledge-Graph Construction Eval
→ S5 Case-Factory Eval
```

S4 must not treat S3 machine-approved claims as automatic gold until S3 passes its high-risk false-support gate on a genuinely new untouched held-out set.

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
