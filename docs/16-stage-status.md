# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. This file prevents architecture completeness from being confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **Evaluated FAIL / v0.5 compositional redesign in progress** | four generations of stage eval; atomic-proposition extraction; polarity-preserving negative propositions; untouched v0.4 shadow set; hard false-support gate | proposition-level entailment + whole-claim aggregation; zero high-risk false support on a new untouched v0.5 held-out |
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

## S3 checkpoint through v0.4

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** tests whether an already-retrieved evidence passage actually supports a candidate medical claim.

Hard safety rule:

```text
High-risk False-Support Rate must equal 0
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

Known regression set:

```text
Relation Accuracy                 91.7%
High-risk False-Support Rate       0.0%
```

Fresh held-out:

```text
Relation Accuracy                 50.0%
High-risk False-Support Rate      15.4%
Release Gate                      FAIL
```

This exposed directional temporal and causal-polarity failures.

### v0.3 — directional ClaimFrame

The verifier was implemented before freezing a new untouched shadow set.

Untouched shadow result:

```text
24 items
Relation Accuracy                 50.0%
High-risk False-Support Rate      58.3%
Release Gate                      HARD FAIL
```

Root cause: whole compound sentences were still parsed with unsafe clause/action binding and negation leakage.

### v0.4 — atomic propositions

Architecture changed to:

```text
passage
→ clause segmentation
→ atomic propositions
→ polarity-preserving proposition frames
→ candidate proposition frames
```

Before creating a new held-out, `v0.4.1` was tested only on already-exposed diagnostic suites:

```text
v0.1 diagnostic    95.8%   false support 0
v0.2 diagnostic   100.0%   false support 0
v0.3 diagnostic   100.0%   false support 0
```

These are development regressions only.

A new **30-item untouched v0.4 shadow-heldout** was then frozen after implementation.

First-run result:

```text
Relation Accuracy                 60.0%
High-risk negative/partial items    14
High-risk False-Support Count        2
High-risk False-Support Rate      14.3%
Release Gate                      FAIL
```

The two high-risk false supports were:

1. observational association + explicit causal limitation → causal claim incorrectly returned `DIRECT_SUPPORT`;
2. imaging evidence supports `indeterminate + MRI`, but candidate adds `probably malignant` → whole mixed claim incorrectly returned `DIRECT_SUPPORT` instead of `PARTIAL_SUPPORT`.

The new architectural diagnosis is **COMPOSITION_EARLY_RETURN**:

```text
one supported subclaim
→ verifier returns DIRECT_SUPPORT too early
→ unsupported dangerous extension is ignored
```

Therefore the next S3 design is **Compositional Proposition Entailment**:

```text
candidate claim
→ P1, P2, ... Pn
→ independently classify each proposition:
   SUPPORTED / CONTRADICTED / UNSUPPORTED
→ aggregate all proposition verdicts
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

Recommended aggregation:

```text
all supported
→ DIRECT_SUPPORT

some supported + some unsupported/contradicted
→ PARTIAL_SUPPORT

none supported + at least one contradicted
→ CONTRADICTS

none supported + no contradiction
→ DOES_NOT_SUPPORT
```

For high-risk causal / diagnostic / management / dose extensions:

```text
any unsupported or contradicted dangerous proposition
→ whole claim can NEVER be DIRECT_SUPPORT
```

Detailed reports:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`
- `medical/stage-evals/S3/V0.4_REPORT.md`

### Current S3 release decision

S3 is **not ready for automatic Knowledge Graph truth insertion**.

The v0.4 untouched shadow result is frozen permanently as diagnostic/regression evidence. It must not be tuned and later presented as untouched performance.

Next release attempt:

```text
S3 v0.5 compositional verifier
→ historical suites used only as diagnostics
→ freeze a new untouched v0.5 held-out after implementation
→ require Accuracy >= 80%
→ require High-risk False-Support Rate = 0
```

---

## Overall project checkpoint

- **S2** can conditionally provide controlled authoritative evidence bundles downstream.
- **S3** is doing its intended job as a truth gate: successive fresh held-outs have repeatedly prevented regression-only success from being mistaken for safe generalization.
- **S4** must not automatically trust S3 machine-approved claims until a new untouched S3 held-out passes the false-support gate.

Immediate order:

```text
S3 v0.5 Compositional Proposition Entailment
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
