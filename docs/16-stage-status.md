# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **HARD FAIL end-to-end / S3b conditional pass / S3a blocking** | full v0.1–v0.6 failure history; S3 split; S3b v0.3 fresh structured held-out 40/40 with HFSR 0; constrained semantic-extractor harness | improve and freshly validate S3a semantic proposition extraction, then re-test end-to-end S3 on a new untouched set |
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

## S3 checkpoint

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** asks whether already-retrieved evidence supports a candidate medical claim.

End-to-end hard release criteria remain:

```text
Relation Accuracy >= 80%
High-risk False-Support Rate = 0
```

### End-to-end fresh history

```text
v0.1 lexical baseline            Accuracy 58.3%   HFSR  8.3%   FAIL
v0.2 fresh semantic held-out     Accuracy 50.0%   HFSR 15.4%   FAIL
v0.3 fresh ClaimFrame shadow     Accuracy 50.0%   HFSR 58.3%   HARD FAIL
v0.4 fresh atomic shadow         Accuracy 60.0%   HFSR 14.3%   FAIL
v0.5 fresh compositional shadow  Accuracy 75.0%   HFSR  6.25%  FAIL
v0.6 fresh post-v0.5.4 shadow    Accuracy 40.0%   HFSR 17.6%   HARD FAIL
```

The fresh history is preserved because regression-only scores repeatedly looked strong while new language exposed unsafe extraction/generalization.

---

## S3 split architecture

v0.6 showed that one end-to-end score mixed two different capabilities:

```text
S3a — Semantic Proposition Extraction
free text
→ canonical atomic propositions

S3b — Structured Proposition Entailment
canonical evidence propositions
+ canonical candidate propositions
→ SUPPORTED / CONTRADICTED / UNSUPPORTED per proposition
→ DIRECT / PARTIAL / CONTRADICTS / DOES_NOT_SUPPORT
```

### S3a current status — blocking

Initial 12-item / 21-proposition diagnostic:

```text
precision                                55.6%
recall                                   47.6%
F1                                       51.3%
critical-proposition recall             43.75%
polarity accuracy on structural matches  90.9% (10/11)
release gate                              FAIL
```

Representative failures:

- `does not constitute a contraindication` → wrong positive polarity;
- safety-signal + causal limitation → propositions missing;
- `no result establishes endpoint was met` → incorrect achievement proposition;
- guideline replacement/currentness → propositions missing;
- pathology benign category → proposition missing;
- explicit `not associated` → generic positive association.

A constrained semantic-extractor harness exists with a deterministic lower bound and an `openai_compatible` model backend. Model outputs are constrained by a predicate registry, schema validation and abstention/human-review behavior for unresolved critical semantics.

### S3b v0.3 — conditional pass

S3b now has a fresh structured held-out release result independent of free-text extraction.

Frozen suite:

```text
40 items
DIRECT_SUPPORT      12
CONTRADICTS         11
DOES_NOT_SUPPORT    10
PARTIAL_SUPPORT      7
high-risk items     27
```

It explicitly covers:

- LT/LTE/GT/GTE/RANGE/EQ conditions;
- `EXACT_DOMAIN` vs `SUFFICIENT_ONLY` closure semantics;
- population/use-state scope;
- positive/negative action polarity;
- causality and incidence boundaries;
- temporal currentness and supersession direction;
- mixed claims and partial support;
- pharmacogenomics exposure vs dosing management;
- diagnostic category polarity;
- subgroup/ranking overclaim;
- missing-condition and absence-of-evidence behavior.

First-run workflow: `33976929442`.

```text
Relation Accuracy                 100.0%
High-risk negative items             22
High-risk False-Support Count         0
High-risk False-Support Rate         0.0%
Release Gate                         PASS
```

Detailed report:

- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

Interpretation:

> S3b is a **conditional pass** when given already-normalized canonical propositions with explicit polarity, population and condition semantics. It is not evidence that end-to-end S3 is solved.

Allowed current use:

```text
reviewed / gold canonical propositions
→ S3b deterministic audited verification allowed
```

Blocked current use:

```text
unvalidated free-text extraction
→ automatic S3b decision
→ unrestricted KG truth insertion
```

### Current S3 release decision

End-to-end S3 remains **HARD FAIL** because S3a is still below its extraction safety gate.

Immediate priority:

```text
S3a semantic extraction redesign/development
→ fresh S3a held-out
→ if S3a passes, freeze a new end-to-end S3 held-out
→ only then consider reviewed automatic KG truth insertion
```

Historical reports include:

- `medical/stage-evals/S3/V0.1_BASELINE_REPORT.md`
- `medical/stage-evals/S3/V0.2_REPORT.md`
- `medical/stage-evals/S3/V0.3_REPORT.md`
- `medical/stage-evals/S3/V0.4_REPORT.md`
- `medical/stage-evals/S3/V0.5_REPORT.md`
- `medical/stage-evals/S3/V0.6_REPORT.md`
- `medical/stage-evals/S3/S3_SPLIT_V0.1_REPORT.md`
- `medical/stage-evals/S3/S3B_V0.2_REPORT.md`
- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

---

## Overall project checkpoint

- **S2** can conditionally provide controlled authoritative evidence bundles downstream.
- **S3b** has now passed a 40-item fresh structured release suite with zero high-risk false support.
- **S3a** remains the active S3 bottleneck, so end-to-end S3 is still failed.
- **S4** must not automatically trust free-text-derived machine claims until S3a and a new end-to-end S3 release test pass.

Immediate order:

```text
S3a extraction improvement + fresh held-out
→ new end-to-end S3 held-out
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
