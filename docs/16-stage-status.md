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
| S5 | Controlled Case / Benchmark Factory | **v0.6 INDEPENDENT FRESH IDENTITY/TOCTOU FAIL / RELEASE BLOCKED** | v0.5.1 exposed F16–F19 regression PASS; new post-freeze v0.6 preconditions PASS but F20–F23 all fail | preserve v0.6 first observation; repair lineage/canonical-ID/atomic-snapshot boundaries; rerun only as exposed regression |
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

S3 remains a bounded `CONDITIONAL PASS`; long/noisy real multi-source passages remain under-tested.

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

Historical first observations remain immutable.

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
v0.2.1 exposed regression                            F4–F7 REPAIRED / PASS

v0.3 second independent fresh trust-root
  F8 location laundering                             FAIL
  F9 recomputable self-auth digest                   FAIL
  F10 suite identity                                 FAIL
  F11 foreign manifest substitution                  FAIL
v0.3.1 exposed regression                            F8–F11 REPAIRED / PASS

v0.4 third independent fresh policy-root
  F12 caller-supplied policy laundering              FAIL
  F13 off-repo policy root                           FAIL
  F14 cross-suite case_id collision                  FAIL
  F15 suite blob replay / alternate family root      FAIL
v0.4.1 exposed regression                            F12–F15 REPAIRED / PASS

v0.5 fourth independent fresh authority composition
  F16 ordinary payload mutation after load           FAIL
  F17 forged ordinary context bearer                 FAIL
  F18 ordinary/benchmark case_id collision           FAIL
  F19 declared-family case-path containment          FAIL
v0.5.1 exposed regression                            F16–F19 REPAIRED / PASS

v0.6 fifth independent fresh identity / TOCTOU boundary
  F20 transformed heldout-derived ordinary source    FAIL
  F21 Unicode-normalization case_id collision        FAIL
  F22 registry check/read TOCTOU substitution        FAIL
  F23 source check/read TOCTOU substitution          FAIL
```

Gold approval remains separate from structural evaluation: P0 `0/12`, v0.2 family `0/1`, v0.3 family `0/1`, v0.4 family `0/1`; no expert/clinical approval is inferred. v0.5 and v0.6 are structural-only suites and create no new clinical-gold family.

### Immutable recent first observations

```text
v0.4 first observation blob  45a10ed2cc522b555a3f3eecf785dffedf8cd4c3
v0.5 first observation blob  c300d301cb6bf23e5ec1cc0472666f44a1148e77
```

The v0.6 first-observation file is created in the same commit as its post-freeze evaluator/fixtures; after this commit it is exposed forever and must never be relabeled fresh.

---

## S5 v0.5.1 checkpoint — authority-composition repair exposed regression

Evidence class: **development exposed regression**, not fresh held-out.

```text
historical v0.5 first-observation preservation       PASS
authenticated policy registry                         PASS
carrier materialization                              5/5
baseline dev export                            EXPORTABLE
baseline regression export                         BLOCKED
baseline heldout export                            BLOCKED
ordinary allowlisted source                    EXPORTABLE
S5-F16 mutated ordinary payload                    BLOCKED
S5-F17 borrowed ordinary context                   BLOCKED
S5-F18 ordinary/benchmark case_id collision        BLOCKED
S5-F19 sibling-family path escape                  BLOCKED
decision-contract alignment                          PASS
prompt gold leakage                                  NONE
gold approved                                         0
pending gold                                          1
regression gate                                      PASS
```

This repair is exposed evidence only and does not establish independent generalization.

---

## S5 v0.6 checkpoint — fifth genuinely fresh identity / TOCTOU FAIL

Target implementation freeze:

```text
60f74c7f30c007008ee73df3eed6eacf4a9bab0a
```

All v0.6 evaluator logic and attack fixtures were authored after this freeze. Previously registered v0.4 cases are reused only as authenticated carrier controls.

Preconditions:

```text
frozen target identity                               PASS
authenticated trust root                             PASS
carrier materialization                              5/5
baseline dev export                           EXPORTABLE
baseline regression export                        BLOCKED
baseline heldout export                           BLOCKED
ordinary allowlisted source                     EXPORTABLE
decision-contract alignment                          PASS
prompt gold sentinel leakage                         NONE
gold release containment                             PASS
precondition failures                                   0
```

New hard-gate failures:

```text
S5-F20 DERIVED_HELDOUT_ORDINARY_SOURCE_LAUNDERING             FAIL
S5-F21 UNICODE_CASE_ID_NORMALIZATION_COLLISION                 FAIL
S5-F22 REGISTRY_TOCTOU_POST_HASH_SUBSTITUTION                  FAIL
S5-F23 SOURCE_TOCTOU_POST_HASH_SUBSTITUTION                    FAIL
```

Interpretation:

- F20: exact blob/case-id uniqueness does not encode source lineage; a transformed heldout-derived case can be proposed as ordinary training data.
- F21: raw Unicode string equality is not a canonical identity namespace.
- F22: registry hash verification and JSON parsing use separate filesystem reads, so the verified bytes can differ from parsed bytes.
- F23: source hash verification and payload parsing have the same check/read race.

Current decision:

```text
fresh structural gate                     FAIL
S5 bounded release          NOT ESTABLISHED
S5 release              BLOCKED_GOLD_REVIEW
S6 automatic trust                   BLOCKED
```

No S6 automatic trust is permitted.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 only when a downstream blocker requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. preserve S5 v0.6 first observation exactly
   - never relabel it as fresh after repair

2. repair F20–F23 generically
   - authenticate + parse one immutable byte snapshot rather than check path then reopen
   - normalize identity keys to a documented Unicode canonical form before collision checks
   - introduce explicit benchmark lineage / derivation exclusion for ordinary training sources
   - keep fail-closed behavior for unknown authority

3. rerun v0.6 only as exposed regression
   - retain v0.5.1 and older boundary regressions

4. freeze the repaired implementation

5. create another genuinely new post-freeze S5 boundary suite
   - attack file-descriptor/symlink replacement and snapshot reuse
   - attack lineage metadata omission/forgery and multi-step transformations
   - attack normalization confusables beyond canonical equivalence
   - retain baseline split, decision-contract, prompt-leakage and gold-containment controls

6. gold review remains an independent blocker
   - never fabricate approval

7. only after bounded S5 release proceed to S6 dedicated harness evaluation

8. continue S6 → S7 → S8 → S9 → S10
```
