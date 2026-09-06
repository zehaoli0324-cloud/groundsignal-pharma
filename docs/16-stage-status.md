# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. Architecture completeness must not be confused with empirical validation completeness. A `PASS` below always refers to the explicitly tested slice, not unrestricted clinical deployment.

| Stage | Name | Current maturity | What is already real | Main missing proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; joint v0.1 intent/source 94.44%; v0.4 legacy smoke 12/12; live DailyMed 3/3 | clause-level negation/exclusion scope, role-separated feature polarity, broader live passage/source diversity, terminology normalization |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS / controlled end-to-end vertical slice** | S3a v0.5.6.1 independent fresh PASS; S3b v0.3 fresh 40/40 / HFSR 0; S2→S3 joint v0.1 17/18 end-to-end / high-risk false support 0 | larger real-source/noisy-passage end-to-end held-out; long-document and multi-entity semantics |
| S4 | Medical KG Construction / Update | Working prototype / auto-ingestion blocked | case graphs + two reusable backbones + canonical builder | terminology normalization, persistent graph/index, update-impact engine, dedicated S4 eval; unrestricted automatic S3 truth ingestion remains blocked |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + broader validated user-task coverage + dedicated stage eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | live multi-provider runs, production retriever/reranker, Agent executor, dedicated stage eval |
| S7 | Evaluation & Safety Gate | Protocol complete | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration and full real model scoring |
| S8 | Failure Diagnosis | Framework ready | taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters |
| S9 | Intervention / Post-training Data | Interface ready | SFT/preference/Agent/Judge schemas and reviewed export | actual intervention/training experiment |
| S10 | Candidate + Held-out Regression | Fixture proof | candidate-vs-baseline gate and held-out contracts | real post-intervention held-out improvement |

---

## S2 — Knowledge Search & Source Routing

**S2 = Knowledge Search & Source Routing（知识搜索与来源路由）** remains a conditional pass.

Independent evidence already preserved:

```text
v0.2b untouched shadow routing       Primary@1 73.3%   FAIL
v0.3 fresh routing                   Primary@1 91.7%   PASS
live official-record retrieval       10/10              PASS
DailyMed current-version slice       100%               PASS
critical-passage Recall@1 slice      100%               PASS
```

The S2→S3 joint held-out adds a second independent routing observation:

```text
items                                18
Intent Accuracy                    94.44%   PASS
Primary Source Accuracy            94.44%   PASS
Source Handoff Accuracy           100.00%   PASS*
```

`*` Source Handoff means the expected source remained reachable in the ranked source list and controlled document bank. Top-1 source quality is separately measured by Primary Source Accuracy.

### S2 v0.4 Negation-aware Intent Router — development FAIL

The joint first-run failure `S2S3-013` motivated a structural v0.4 development pass. The stage-specific development eval was fixed before implementation and no new fresh/shadow held-out was created.

Version:

```text
intent-first-negation-aware-s2-v0.4.0
```

Development suite:

```text
n queries                            30
negation/exclusion stress            17
positive control                      1
legacy exposed smoke                 12
```

First development observation:

```text
Intent Accuracy                    90.00%   FAIL
Primary Source Accuracy            90.00%   FAIL
Acceptable Source Recall@3         96.67%
Negation Subset Accuracy           82.35%   FAIL
Legacy Subset Accuracy            100.00%   PASS
High-risk Source Miss Rate          0.00%   PASS
Failure Count                           3
Combined Development Gate             FAIL
Fresh validation                  NOT RUN
```

Frozen v0.4 failure taxonomy:

```text
S2-F1  coordinated exclusion scope gap
       an exclusion cue such as "不涉及" does not propagate across a coordinated list

S2-F2  modifier-separated exclusion gap
       "不要一般 study design guidance" is not represented as one excluded phrase/clause span

S2-F3  context-role collapse
       an excluded CDE mention suppresses the independently positive China jurisdiction context
```

No repair was performed after the first v0.4 FAIL. Historical S2 v0.3 fresh evidence and the S2→S3 joint first observation remain unchanged.

Detailed v0.4 report: `medical/stage-evals/S2/S2_V0.4_DEV_FAIL_REPORT.md`  
Raw metrics/failures: `medical/stage-evals/S2/runs/s2-v04-development-first-fail/report.json`

Next S2 target:

> **S2 v0.4.1 Clause-scope Negation + Role-separated Features** — build clause/coordinated exclusion spans, allow modifiers between exclusion cue and feature head, and separate jurisdiction/entity context from excluded task-intent evidence. Only after exposed development gates pass may a brand-new fresh held-out be frozen.

---

## S3 architecture

```text
S3a — Semantic Proposition Extraction
free text
→ canonical propositions

S3b — Structured Proposition Entailment
canonical evidence/candidate propositions
→ proposition verdicts
→ DIRECT_SUPPORT / PARTIAL_SUPPORT / CONTRADICTS / DOES_NOT_SUPPORT
```

---

## S3a — independent fresh PASS at v0.5.6.1

### Immutable fresh history

```text
v0.2 fresh      F1 62.50%   Critical Recall 52.17%   FAIL
v0.3 fresh      F1 30.77%   Critical Recall 17.86%   HARD FAIL
v0.4 fresh      F1 40.00%   Critical Recall 25.58%   FAIL
v0.5.1 fresh    F1 80.33%   Critical Recall 68.75%   FAIL
v0.5.2 fresh    F1 78.20%   Critical Recall 67.27%   FAIL
v0.5.4 fresh    F1 93.44%   Critical Recall 91.30%   FAIL
v0.5.6.1 fresh  F1 98.90%   Critical Recall 100.00%  PASS
```

All historical first observations remain immutable. Once observed, each fresh suite becomes exposed regression data.

### Development sequence after v0.5.4

```text
v0.5.5 development   FAIL
  typed scope linker improved v0.5.4 exposed performance
  but old v0.5.2 condition-link regressions + endpoint discourse gap remained

v0.5.6 development   FAIL
  all proposition suites PASS
  but semantic safety gate caught one conditional-rule broadening

v0.5.6.1 development PASS
  frame/event registry reconciliation
  all exposed proposition + abstention + semantic-safety + trace gates PASS
```

### v0.5.6.1 independent fresh first run

Frozen parser:

```text
commit  4b7aaabe490e3e477d1d1441b55c5ee656675e1f
blob    dc05a6eaccf02592652d0a48b9a712186e5b6507
```

Fresh suite:

```text
freeze commit  2147ee2d519305ba2bb2be0576a2e316e405b71f
blob           d24ddd0d1de4e5574024bd44f7f1764f1d9382c5
workflow       34004097408
raw commit     53f3fde6e8f2ef47975956b5e33c14e047a21a22
```

First-run metrics:

```text
items                                      34
known / representable cases                28
mandatory abstention cases                  6
gold propositions                          45
predicted propositions                     46
true positives                             45
Precision                                97.83%   PASS
Recall                                  100.00%
F1                                       98.90%   PASS
Critical Proposition Recall             100.00%   PASS
Polarity Accuracy                       100.00%   PASS
Population Accuracy                     100.00%   PASS
Condition Binding Accuracy              100.00%   PASS
Required-abstention accuracy            100.00%   PASS
Known-case abstention rate                0.00%   PASS
High-risk semantic false positives           0   PASS
Trace contract                              PASS
Combined fresh release                      PASS
```

There were no missing gold propositions. One conservative extra negative endpoint-evidence proposition was emitted for a record that listed an endpoint but posted no efficacy result; it did not create a positive success escalation and the semantic safety gate remained PASS.

Detailed report: `medical/stage-evals/S3/S3A_V0.5.6.1_FRESH_REPORT.md`  
Raw outputs: `medical/stage-evals/S3/runs/s3a-v0561-fresh-first-run/`

S3a current status:

> **CONDITIONAL PASS — independently fresh-validated controlled semantic extraction prototype.**

---

## S3b — independent conditional PASS

Fresh S3b v0.3 first-run workflow `33976929442`:

```text
items                              40
Relation Accuracy                100.0%
High-risk negative items             22
High-risk False-Support Count         0
High-risk False-Support Rate         0.0%
Release Gate                         PASS
```

This proves the structured entailment layer on the current controlled proposition ontology when subject/predicate/object, polarity, population and numeric conditions are already normalized.

Detailed report: `medical/stage-evals/S3/S3B_V0.3_REPORT.md`

S3b current status:

> **CONDITIONAL PASS — independently fresh-validated structured truth engine.**

---

## S2 → S3 joint vertical slice v0.1

The joint harness was committed before the held-out suite:

```text
harness commit  cca5a6bbf5bb56ca30c2a0dc06527d748d87e9a4
harness blob    48cf7eeb500ed9ba837f11394991a2e070a61971
suite freeze    65f6797c736792ea0da743c6f40303bf6f2825df
workflow        34004328424
raw commit      b31895c35a0875e7fd18c93ba1c97d5ff0a8f416
```

The tested chain is:

```text
user query
→ S2 intent/source routing
→ source-scoped controlled passage selection
→ S3a v0.5.6.1 free-text extraction
→ canonical propositions
→ S3b v0.2.2 entailment
→ final relation
```

No gold proposition is inserted between S3a and S3b.

First-run controlled metrics:

```text
n items                              18
S2 Intent Accuracy                94.44%   PASS
S2 Primary Source Accuracy        94.44%   PASS
Source Handoff Accuracy          100.00%   PASS
S3a non-abstention               100.00%   PASS
S3b Relation Accuracy            100.00%   PASS
End-to-end Accuracy               94.44%   PASS
High-risk False-Support Count          0   PASS
```

Failure attribution:

```text
S2_INTENT             1
S2_SOURCE             0
S2_SOURCE_HANDOFF     0
S3A                    0
S3B                    0
```

The same workflow reran the existing real-network DailyMed passage test:

```text
n tests                                  3
source availability                  100%
current-version consistency           100%
critical-passage Recall@1             100%
critical-passage Recall@3             100%
infrastructure failures                  0
release gate                          PASS
```

Combined joint decision:

```text
controlled S2→S3 handoff              PASS
S2 live DailyMed sidecar              PASS
S3a independent fresh precondition    PASS
S3b independent fresh precondition    PASS
combined release                      PASS
```

Detailed report: `medical/stage-evals/S2S3/S2_S3_JOINT_V0.1_REPORT.md`  
Raw outputs: `medical/stage-evals/S2S3/runs/s2-s3-joint-v01-first-run/`

---

## Current S3 release decision

The previous `HARD FAIL` is no longer accurate because:

1. S3a now has an independent fresh PASS;
2. S3b already has an independent fresh/conditional PASS;
3. a frozen S2→S3 free-text vertical slice passes without injecting gold propositions between S3a and S3b;
4. the joint high-risk false-support count is zero.

Current status:

```text
S2                                  = CONDITIONAL PASS / v0.4 development FAIL
S3a                                 = CONDITIONAL PASS / independent fresh PASS
S3b                                 = CONDITIONAL PASS / independent fresh PASS
S2→S3 controlled vertical slice     = PASS
S3 overall                          = CONDITIONAL PASS
S4 automatic KG truth ingestion     = BLOCKED
```

`CONDITIONAL PASS` is deliberately narrower than production readiness. The joint suite uses controlled source passages for most source families; only the DailyMed sidecar is a current real-network passage test. Long/noisy documents, broader terminology, multiple drugs/entities per passage, richer temporal composition and cross-document coreference remain under-tested.

---

## Immediate order

```text
1. S2 v0.4.1 clause-scope negation + role-separated features
   - coordinated-list and noun-phrase exclusion spans
   - positive jurisdiction/entity context must survive an excluded task mention
   - rerun exposed v0.4 development suite and prior S2 regression

2. after development PASS, freeze a brand-new S2 v0.4.1 fresh held-out

3. larger real-source S2→S3 passage-level held-out
   - expand beyond DailyMed to trial registry, literature and safety sources
   - preserve current-version/source provenance
   - stress noisy/longer passages and distractors

4. terminology normalization and entity resolution
   - especially drugs, observations, biomarkers and study identifiers

5. only after broader real-source S2→S3 proof begin S4 dedicated evaluation
   - graph insertion correctness
   - update/temporal replacement
   - contradiction handling
   - provenance preservation
   - rollback/update-impact behavior
```

Unrestricted automatic free text → truth → Knowledge Graph insertion remains prohibited until the S4-specific gate is built and passes.
