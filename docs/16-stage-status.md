# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. `PASS` always refers to the explicitly tested slice, not unrestricted clinical deployment. Historical fresh/first observations are immutable; once observed, a suite may only be reused as exposed regression evidence.

| Stage | Name | Current maturity | Strongest current evidence | Main blocker / next proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; S2→S3 joint intent/source 94.44%; live DailyMed 3/3 | clause-level negation/exclusion + role-separated features; broader live sources |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS** | S3a v0.5.6.1 fresh F1 98.90%, critical recall 100%; S3b 40/40; joint S2→S3 17/18 | larger real-source/noisy-passage held-out |
| S4 | Medical KG Construction / Update | **CONDITIONAL PASS / v0.1.1 independent fresh PASS** | fresh 20/20; must-reject 7/7; stale ACTIVE 0; invariant violations 0 | persistent/real-source graph proof; unrestricted production ingest disabled |
| S5 | Controlled Case / Benchmark Factory | **v0.4 INDEPENDENT FRESH POLICY-ROOT FAIL / RELEASE BLOCKED** | v0.3.1 exposed F8–F11 PASS; v0.4 fresh preconditions PASS but F12–F15 redefine root authority | authenticate trust-policy root, global case identity and suite↔family-root binding; gold review remains independent blocker |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | dedicated S6 eval only after S5 bounded release; do not auto-trust S5 partitions |
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

S3 remains a bounded `CONDITIONAL PASS`. Long/noisy real multi-source passages remain under-tested.

---

## S4 checkpoint

```text
v0.1 development                           12/12   PASS
v0.1 first independent fresh               18/20   FAIL
v0.1.1 exposed development regression      12/12   PASS
v0.1.1 v0.1 fresh-now-exposed regression  20/20   PASS
v0.1.1 new independent fresh               20/20   PASS
```

Current decision: controlled truth-ledger state machine = `CONDITIONAL PASS`; unrestricted production clinical ingest remains disabled.

---

## S5 evidence history

Historical first observations remain immutable:

```text
v0.1 development first observation
  F1 split/export provenance                         FAIL
  F2 gold readiness                                  FAIL
  F3 decision contract schema                        FAIL

v0.2 first independent fresh boundary
  F4 provenance authority                            FAIL
  F5 missing/unknown split fail-closed               FAIL
  F6 payload integrity                               FAIL
  F7 decision exemption alignment                    FAIL

v0.2.1 exposed regression
  F4–F7                                      REPAIRED / PASS

v0.3 second independent fresh trust-root
  F8 location laundering                             FAIL
  F9 recomputable self-auth digest                   FAIL
  F10 suite identity                                 FAIL
  F11 foreign manifest substitution                  FAIL

v0.3.1 exposed trust-root regression
  F8–F11                                     REPAIRED / PASS
```

Gold approval remains separate from structural evaluation: P0 `0/12`, v0.2 family `0/1`, v0.3 family `0/1`; no expert/clinical approval is inferred.

---

## S5 v0.4 checkpoint — third genuinely fresh policy-root FAIL

Target implementation freeze:

```text
64cd9288d0b13012d8b71989431dde493c4e8a59
```

All v0.4 family files, attack authorities, evaluator logic and workflow were authored after that freeze. The fresh family has 5 synthetic cases (`dev 3 / regression 1 / heldout 1`). The first executable observation is required to match the committed raw metrics exactly; no post-hoc rewrite is allowed.

Preconditions / controls:

```text
frozen target identity                     PASS
fresh family validation                    PASS
fresh materialization                    5/5 PASS
baseline dev export                  EXPORTABLE
baseline regression export              BLOCKED
baseline heldout export                 BLOCKED
source blob mismatch control            BLOCKED
decision-contract alignment               PASS
prompt gold sentinel leakage              NONE
gold release containment                  PASS
precondition failures                         0
```

New hard-gate failures:

```text
S5-F12 CALLER_SUPPLIED_POLICY_CAN_LAUNDER_HELDOUT
  byte-identical heldout copied to ordinary path
  caller-built policy allowlists it as ordinary source
  result: EXPORTABLE

S5-F13 OFF_REPO_POLICY_PATH_ACCEPTED_AS_ROOT
  policy JSON outside repository accepted as root authority
  result: EXPORTABLE

S5-F14 CROSS_SUITE_CASE_ID_COLLISION_NOT_REJECTED
  same case_id trusted in heldout suite and another dev suite
  policy builder accepts both
  collision dev result: EXPORTABLE

S5-F15 SUITE_BLOB_REPLAY_ALTERNATE_FAMILY_ROOT
  exact genuine suite blob replayed at alternate path
  alternate family root declares genuine heldout case_id as dev
  result: EXPORTABLE
```

Interpretation: v0.3.1 correctly authenticates suite/manifest/source **relative to the selected policy**, but the policy root itself is not independently authenticated. A caller that controls the policy argument can redefine root authority. The builder also lacks a global case-ID collision gate, and a suite blob is not canonically bound to one family-root/manifest set.

Current decision:

```text
fresh structural gate                    FAIL
S5 release                BLOCKED_GOLD_REVIEW
S6 automatic trust                     BLOCKED
```

Immutable v0.4 evidence paths:

- `medical/stage-evals/S5/fresh-boundary-v0.4/protocol-v0.4.json`
- `medical/stage-evals/S5/fresh-boundary-v0.4/suite-fresh-boundary-v0.4.json`
- `medical/stage-evals/S5/fresh-first-observation-v0.4.json`
- `medical/stage-evals/S5/failures-v0.4.json`
- `medical/stage-evals/S5/S5_V0.4_FRESH_POLICY_ROOT_FAIL_REPORT.md`
- `scripts/eval_s5_fresh_boundary_v04.py`

The v0.4 suite becomes exposed immediately after the first executable observation and must never be relabeled fresh after repair.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 only when a downstream blocker requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. preserve S5 v0.4 fresh first observation exactly

2. repair F12–F15 generically in S5 v0.4.1
   - canonical/authenticated trust-policy root independent of caller input
   - reject arbitrary/off-repo policy substitution in protected export flows
   - global benchmark case identity/collision policy across trusted suites
   - canonical suite path + family-root + manifest binding
   - preserve existing source/manifest/payload mismatch fail-closed behavior

3. rerun v0.4 only as exposed regression

4. freeze the repaired implementation

5. only after that freeze create another genuinely new fresh trust-root suite

6. gold review remains an independent blocker
   - P0: 0/12 gold-approved
   - v0.2: 0/1
   - v0.3: 0/1
   - v0.4: 0/1
   - never fabricate approval

7. only after bounded S5 release proceed to S6 dedicated harness evaluation

8. continue S6 → S7 → S8 → S9 → S10
```
