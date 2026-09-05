# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-05  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**, but maturity differs by stage. Architecture completeness must not be confused with empirical validation completeness.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **Conditional pass / evaluated prototype** | v0.3 fresh intent held-out 91.7%; 10-test live official-source retrieval; real DailyMed current-version consistency + critical-passage Recall@1 on 3 high-risk examples | broader passage-source diversity, larger open-language routing sets, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **Evaluated HARD FAIL / bottleneck localized to S3a** | v0.1–v0.6 fresh history; S3a/S3b split evaluation; S3b initial 12/12 structured diagnostic; constrained semantic-extractor harness; immutable first-run reports | improve and freshly validate S3a semantic extraction; validate S3b on a larger untouched structured set; then re-test end-to-end S3 |
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

## S3 checkpoint through split evaluation v0.1

**S3 = Stage 3, Evidence Verification & Temporal Truth（证据验证与时间真值）** asks whether an already-retrieved evidence passage supports a candidate medical claim.

End-to-end hard release criteria remain:

```text
Relation Accuracy >= 80%
High-risk False-Support Rate = 0
```

### Fresh end-to-end history

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

### v0.5.4 exposed regression before v0.6

```text
v0.1 diagnostic             100.0%   HFSR 0
v0.2 diagnostic              91.7%   HFSR 0
v0.3 diagnostic             100.0%   HFSR 0
v0.4 diagnostic             100.0%   HFSR 0
v0.5 exposed regression     100.0%   HFSR 0
```

These numbers demonstrate regression control, not free-text generalization. The new v0.6 untouched set subsequently fell to 40.0% accuracy with 17.6% HFSR.

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

1. `MISSING_CONDITION_OVERCLAIM`;
2. `NEGATION_POLARITY_ERROR`;
3. `PGX_TO_MANAGEMENT_ESCALATION`.

Detailed first-run report:

- `medical/stage-evals/S3/V0.6_REPORT.md`

---

## S3 split architecture

v0.6 showed that one end-to-end score mixed two materially different capabilities:

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

Design:

- `medical/stage-evals/S3/S3_SPLIT_DESIGN.md`

### S3a v0.1 — semantic proposition extraction

Initial 12-item / 21-proposition diagnostic:

```text
precision                                55.6%
recall                                   47.6%
F1                                       51.3%
critical-proposition recall             43.75%
polarity accuracy on structural matches  90.9% (10/11)
release gate                              FAIL
```

This is the current primary bottleneck. More than half of safety-critical propositions were not recovered in the required canonical structure.

Representative failures:

- `does not constitute a contraindication` → positive contraindication;
- safety-signal + causal limitation → propositions missing;
- `no result establishes endpoint was met` → incorrect endpoint-achievement representation;
- guideline replacement/currentness → missing propositions;
- pathology benign category → missing proposition;
- explicit `not associated` → generic positive association.

### S3b v0.1 — structured proposition entailment

The free-text parser was bypassed and manually standardized propositions were supplied directly.

```text
items                                      12
Relation Accuracy                       100.0%
high-risk negative items                   10
High-risk False-Support Count                0
High-risk False-Support Rate              0.0%
release gate                              PASS
```

The 12-item structured slice includes threshold algebra, action scope, explicit negation, causal polarity, incidence polarity, supersession/currentness, PGx management overclaim, diagnostic category conflict, partial support, and subgroup-ranking absence.

This is useful localization evidence, **not sufficient proof that S3b is universally solved**. A larger independently frozen S3b held-out is still required.

Full split report:

- `medical/stage-evals/S3/S3_SPLIT_V0.1_REPORT.md`

---

## S3a semantic-extractor redesign

The regex-style parser is retained only as a reproducible lower bound. A constrained semantic-extraction interface now exists:

```text
free text
→ semantic extractor
→ canonical predicate registry
→ structured proposition validation
→ critical unresolved semantic content?
     yes → abstain + human review
     no  → S3b deterministic entailment
```

Implemented interfaces:

- `medical/stage-evals/S3/proposition-registry-v0.1.json`
- `medical/stage-evals/S3/semantic-extractor-output.schema.json`
- `medical/stage-evals/S3/S3A_SEMANTIC_EXTRACTOR_PROMPT.md`
- `scripts/s3_semantic_extractor.py`
- `medical/configs/s3-semantic-extractor.baseline.json`
- `medical/configs/s3-semantic-extractor.openai-compatible.example.json`

The harness supports:

1. `deterministic_baseline` — current parser as lower bound/regression;
2. `openai_compatible` — constrained model-based semantic extraction.

CI reproduces the deterministic lower-bound S3a metrics exactly. No real model-based S3a run has yet been claimed; that requires an actual configured model endpoint/API credential.

### Current S3 release decision

S3 remains **HARD FAIL** and is **not eligible for automatic KG truth insertion**.

The development priority is now explicit:

```text
1. independently validate S3b on a larger fresh structured held-out
2. run / improve model-based S3a semantic extraction
3. freeze a fresh S3a held-out only after extractor design is fixed
4. only after S3a and S3b gates pass, freeze a new end-to-end S3 held-out
5. then consider reviewed KG truth insertion
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
- **S3** has localized the current bottleneck: free-text semantic extraction is weak, while an initial structured truth-logic slice passes when supplied correct propositions.
- **S4** must not automatically trust machine-approved S3 claims while end-to-end S3 remains failed.

Immediate order:

```text
larger fresh S3b structured held-out
→ model-based S3a development + fresh S3a held-out
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
