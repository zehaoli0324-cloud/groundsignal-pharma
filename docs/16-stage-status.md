# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **Evaluated FAIL / v0.5.4 candidate ready for new held-out** | five generations of fresh stage eval; compositional atomic-proposition verifier; immutable v0.5 first-run report; all exposed suites recovered to zero high-risk false support | pass a genuinely new post-v0.5.4 untouched held-out with Accuracy >=80% and High-risk False-Support Rate = 0 |
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

Detailed reports:

- `medical/stage-evals/S2/V0.2_REPORT.md`
- `medical/stage-evals/S2/V0.3_REPORT.md`

---

## S3 checkpoint through v0.5.4

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** tests whether an already-retrieved evidence passage actually supports a candidate medical claim.

Hard release criteria:

```text
Relation Accuracy >= 80%
High-risk False-Support Rate = 0
```

### v0.1 — lexical lower bound

```text
24 items
Relation Accuracy                 58.3%
High-risk False-Support Rate       8.3%
Release Gate                      FAIL
```

Critical failure: `eGFR <45 → reassess` was incorrectly used to support `eGFR <45 → discontinue`.

### v0.2 — semantic cue verifier

```text
known regression accuracy         91.7%
fresh held-out accuracy           50.0%
fresh high-risk false support     15.4%
Release Gate                      FAIL
```

Fresh testing exposed temporal-direction and causal-polarity failures hidden by the regression result.

### v0.3 — directional ClaimFrame

The implementation was frozen before a new 24-item shadow set.

```text
fresh shadow accuracy             50.0%
high-risk false support           58.3% (7/12)
Release Gate                      HARD FAIL
```

Root cause: directional schema alone was insufficient because the extractor still attached actions, conditions and negation to the wrong clauses.

### v0.4 — atomic propositions

Architecture changed to:

```text
passage
→ clause segmentation
→ atomic propositions
→ polarity-preserving proposition frames
→ candidate proposition frames
```

A new 30-item untouched shadow was frozen only after implementation.

```text
fresh shadow accuracy             60.0%
high-risk false support           14.3% (2/14)
Release Gate                      FAIL
```

The key new failure was `COMPOSITION_EARLY_RETURN`: one supported subclaim caused the whole mixed claim to be returned as `DIRECT_SUPPORT`, while an unsupported causal or diagnostic extension was ignored.

### v0.5 — compositional proposition entailment

The verifier changed to:

```text
candidate claim
→ P1, P2, ... Pn
→ each proposition independently:
   SUPPORTED / CONTRADICTED / UNSUPPORTED
→ aggregate the full set
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

A new 36-item v0.5 untouched shadow was frozen after `v0.5.2` implementation. Its first run is preserved permanently.

#### v0.5 untouched first run

```text
items                              36
Relation Accuracy                 75.0%
high-risk negative items            16
High-risk False-Support Count        1
High-risk False-Support Rate       6.25%
Release Gate                      FAIL
```

The critical false-support case was explicit polarity:

```text
evidence: treatment A is NOT contraindicated solely because of condition B
claim:    condition B alone makes treatment A contraindicated
prediction: DIRECT_SUPPORT
truth:      CONTRADICTS
```

Other errors concentrated in bounded negative summaries, omitted mixed-claim extensions, endpoint-achievement scope, incidence normalization and mutually-exclusive report categories.

First-run evidence is recorded in:

- `medical/stage-evals/S3/V0.5_REPORT.md`

It must never be re-described as regression-only or overwritten by later tuned results.

### v0.5.3 / v0.5.4 diagnostic recovery

After the v0.5 set became exposed, it was used **only as development/regression evidence**.

`v0.5.3` fixed most v0.5 failures but regressed renal-threshold safety, demonstrating why all historical safety suites must remain in the regression matrix.

`v0.5.4` restored threshold relation algebra and repaired negated subgroup-ranking extraction.

Current **exposed-suite** results for `s3-compositional-proposition-v0.5.4`:

```text
v0.1 diagnostic             100.0%   high-risk false support 0
v0.2 diagnostic              91.7%   high-risk false support 0
v0.3 diagnostic             100.0%   high-risk false support 0
v0.4 diagnostic             100.0%   high-risk false support 0
v0.5 exposed regression     100.0%   high-risk false support 0
```

These numbers show regression recovery, **not fresh generalization**.

The important technical changes now include:

- clause-scoped atomic propositions;
- subject/predicate/object direction;
- condition/action binding;
- eGFR threshold relation algebra;
- positive vs negative polarity;
- absence-of-evidence vs explicit contradiction;
- mutually-exclusive categorical contradiction;
- candidate decomposition before whole-claim aggregation;
- `PARTIAL_SUPPORT` for mixed correct + unsupported claims;
- conservative handling of unresolved high-risk propositions.

### Current S3 release decision

S3 remains **FAIL** because the latest genuinely untouched set (v0.5 first run) failed the safety gate.

`v0.5.4` is now a **candidate verifier**, not a validated release.

Next release attempt:

```text
freeze a completely new post-v0.5.4 untouched held-out
→ run v0.5.4 exactly once before any tuning
→ preserve the first-run result
→ require Accuracy >= 80%
→ require High-risk False-Support Rate = 0
```

If that fresh set passes, S3 may be upgraded only to:

**Conditional pass / candidate for reviewed KG truth insertion**

It should still not be described as fully solved or as an unrestricted automatic medical-truth generator.

Detailed historical reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`
- `medical/stage-evals/S3/V0.4_REPORT.md`
- `medical/stage-evals/S3/V0.5_REPORT.md`

---

## Overall project checkpoint

- **S2** can conditionally provide controlled authoritative evidence bundles downstream.
- **S3** has repeatedly prevented strong regression performance from being mistaken for safe fresh generalization; the v0.5.4 implementation now needs a new untouched release test.
- **S4** must not automatically trust S3 machine-approved claims until S3 passes a genuinely new held-out safety gate.

Immediate order:

```text
S3 new post-v0.5.4 untouched held-out
→ if PASS: S4 Knowledge-Graph Construction Eval
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
