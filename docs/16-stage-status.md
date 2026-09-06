# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. `PASS` always refers to the explicitly tested slice, not unrestricted clinical deployment. Historical fresh first observations are immutable; once observed, a fresh suite may only be reused as exposed regression data.

| Stage | Name | Current maturity | Strongest current evidence | Main blocker / next proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; S2→S3 joint intent/source 94.44%; live DailyMed 3/3 | clause-level negation/exclusion + role-separated features; broader live sources |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS** | S3a v0.5.6.1 fresh F1 98.90%, critical recall 100%; S3b 40/40; joint S2→S3 17/18, high-risk false support 0 | larger real-source/noisy-passage held-out |
| S4 | Medical KG Construction / Update | **CONDITIONAL PASS / v0.1.1 independent fresh PASS** | new fresh 20/20; all required tags 100%; must-reject 7/7; stale ACTIVE 0; state-invariant violations 0 | persistent/real-source graph proof; unrestricted production auto-ingestion remains disabled |
| S5 | Controlled Case / Benchmark Factory | **P0 complete / dedicated eval not yet run** | 12 families / 60 controlled cases / held-out design | stage-specific S5 eval: materialization correctness, leakage, difficulty composition, family held-out behavior |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | live multi-provider runs + dedicated S6 eval |
| S7 | Evaluation & Safety Gate | Protocol complete | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration + real model scoring |
| S8 | Failure Diagnosis | Framework ready | taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters |
| S9 | Intervention / Post-training Data | Interface ready | SFT/preference/Agent/Judge schemas | actual intervention/training experiment |
| S10 | Candidate + Held-out Regression | Fixture proof | candidate-vs-baseline gate + held-out contracts | real post-intervention held-out improvement |

---

## S3 checkpoint

```text
S3a v0.5.6.1 independent fresh
  F1                              98.90%
  Critical Proposition Recall   100.00%
  mandatory abstention             6/6
  high-risk semantic false positives 0
  release                           PASS

S3b independent structured held-out
  items                             40
  Relation Accuracy              100.0%
  High-risk False-Support Count      0
  release                           PASS

S2→S3 controlled vertical slice
  items                             18
  End-to-end Accuracy             94.44%
  High-risk False-Support Count      0
  combined release                  PASS
```

S3 remains a bounded `CONDITIONAL PASS`. Long/noisy real multi-source passages are still under-tested.

---

## S4 checkpoint — independent fresh PASS at v0.1.1

Historical evidence remains immutable:

```text
v0.1 development                           12/12   PASS
v0.1 first independent fresh               18/20   FAIL
v0.1.1 exposed development regression      12/12   PASS
v0.1.1 v0.1 fresh-now-exposed regression  20/20   PASS
```

The v0.1.1 implementation was frozen before the new fresh suite:

```text
freeze commit            8d0406df9bb91b16d3201e2b0cf97a0f084e1dad
implementation blob      3063927fb22c711ee35f6d629d61284455363cd5
base v0.1 blob           860e8b38131e74d9dc06160bd95ade8bd04e77df
fresh suite blob         a2c253ea3583445e9666d9475f378df75d123799
fresh evaluator blob     9a368ae06f9497805469364ca75f6d0c6278ea9d
```

New independent first observation:

```text
cases                                  20
passed                                 20
failed                                  0
case accuracy                       100.0%
all required capability tags        100.0%
must-reject                             7/7
high-risk false accepts                  0
stale ACTIVE edges                       0
state invariant violations               0
fresh integrity                         PASS
release                                 PASS
```

Current S4 decision:

```text
S4 controlled truth-ledger state machine = CONDITIONAL PASS
independent fresh gate                   = PASS
unrestricted production clinical ingest = DISABLED
```

This is not a claim of clinical validation. The held-out propositions are controlled synthetic fixtures. Persistent graph scale, terminology normalization, real clinical source ingestion and concurrent update semantics remain outside the validated slice.

Detailed report: `medical/stage-evals/S4/S4_V0.1.1_FRESH_PASS_REPORT.md`.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have independent bounded release evidence. Return to S2 when a downstream stage requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. S5 v0.1 dedicated stage evaluation
   - validate controlled-case materialization and family contracts
   - test answer/gold leakage and information-disclosure shortcuts
   - quantify difficulty composition and decision-node coverage
   - check deterministic verifier alignment
   - establish held-out family protocol before implementation tuning

2. if S5 first observation FAILs:
   - preserve raw failure result
   - write failure taxonomy and stage status
   - repair only in the next version

3. only after S5 bounded release proceed to S6 dedicated harness evaluation

4. continue S6 → S7 → S8 → S9 → S10

5. backfill S1/S2 only when required by a downstream blocker or after the sequential stack is evaluated
```
