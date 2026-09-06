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
| S5 | Controlled Case / Benchmark Factory | **v0.5 INDEPENDENT FRESH AUTHORITY-COMPOSITION FAIL / RELEASE BLOCKED** | v0.4.1 exposed F12–F15 PASS; v0.5 fresh preconditions PASS but F16–F19 expose ordinary-source and family-containment gaps | repair F16–F19 generically, rerun v0.5 only as exposed regression, then freeze and create another fresh suite; gold review remains independent blocker |
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

v0.4 third independent fresh policy-root
  F12 caller-supplied policy laundering              FAIL
  F13 off-repo policy root                           FAIL
  F14 cross-suite case_id collision                  FAIL
  F15 suite blob replay / alternate family root      FAIL

v0.4.1 exposed policy-root regression
  F12–F15                                    REPAIRED / PASS

v0.5 fourth independent fresh authority composition
  F16 ordinary payload mutation after load           FAIL
  F17 forged ordinary context bearer                 FAIL
  F18 ordinary/benchmark case_id collision           FAIL
  F19 declared-family case-path containment          FAIL
```

Gold approval remains separate from structural evaluation: P0 `0/12`, v0.2 family `0/1`, v0.3 family `0/1`, v0.4 family `0/1`; no expert/clinical approval is inferred. The v0.5 suite is structural-only and creates no new clinical-gold family.

---

## S5 v0.4 first observation — immutable fresh FAIL

Target implementation freeze:

```text
64cd9288d0b13012d8b71989431dde493c4e8a59
```

Fresh preconditions all passed, but the first observation recorded four hard failures:

```text
S5-F12 CALLER_SUPPLIED_POLICY_CAN_LAUNDER_HELDOUT       FAIL
S5-F13 OFF_REPO_POLICY_PATH_ACCEPTED_AS_ROOT            FAIL
S5-F14 CROSS_SUITE_CASE_ID_COLLISION_NOT_REJECTED       FAIL
S5-F15 SUITE_BLOB_REPLAY_ALTERNATE_FAMILY_ROOT          FAIL

fresh structural gate                                  FAIL
S5 release                               BLOCKED_GOLD_REVIEW
S6 automatic trust                                    BLOCKED
```

Immutable first-observation blob:

```text
45a10ed2cc522b555a3f3eecf785dffedf8cd4c3
```

The v0.4 suite is exposed forever and is never relabeled fresh.

---

## S5 v0.4.1 checkpoint — policy-root repair exposed regression

Evidence class: **development exposed regression**, not fresh held-out.

The repair moves export authority above caller-selected policy data:

- `medical/configs/s5-trust-policy-registry-v0.4.1.json` is a canonical registry whose Git blob identity is pinned in the exporter.
- Protected export accepts only registry-listed canonical policy paths or policy objects exactly matching a registered policy.
- The registered policy binds canonical suite path/blob, family root, manifest path/blob, source-case path/blob, split, and variant metadata.
- Policy construction and authenticated-policy validation reject duplicate benchmark `case_id` values across suites.
- Ordinary source blobs may not equal any benchmark source-case blob in the authenticated policy.
- The prior v0.3.1 policy is explicitly registry-authenticated so historical exposed regression remains reproducible without trusting arbitrary policies.

Regression result:

```text
historical v0.4 first-observation preservation       PASS
authenticated policy registry                         PASS
canonical v0.4.1 policy rebuild                       PASS
materialization                                      5/5
baseline dev export                            EXPORTABLE
baseline regression export                         BLOCKED
baseline heldout export                            BLOCKED

S5-F12 caller policy laundering                    BLOCKED
S5-F13 off-repo policy root                        BLOCKED
S5-F14 cross-suite case_id collision               BLOCKED
S5-F15 suite blob replay / alternate root          BLOCKED

ordinary allowlisted source                    EXPORTABLE
decision-contract alignment                          PASS
prompt gold leakage                                  NONE
gold approved                                         0
pending gold                                          1
regression gate                                      PASS
```

Current decision:

```text
S5 v0.4.1 exposed structural regression             PASS
S5 bounded release                 NOT YET ESTABLISHED
S5 release                         BLOCKED_GOLD_REVIEW
S6 automatic trust                               BLOCKED
```

This regression repairs the exposed F12–F15 failure classes, but it cannot establish independent generalization because the v0.4 suite has already been observed.

---

## S5 v0.5 first observation — immutable fresh FAIL

Target implementation freeze:

```text
f1778c21710a743c1e7f1e6d531301c08afdbd14
```

Freshness scope is explicit: v0.5 reuses registered v0.4 cases only as authenticated carrier controls. All attack compositions, the ordinary-source collision fixture, the family-path escape fixture, evaluator logic, and protocol were created after the v0.4.1 freeze.

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
S5-F16 ORDINARY_SOURCE_PAYLOAD_NOT_BOUND_AFTER_LOAD                 FAIL
S5-F17 FORGED_ORDINARY_CONTEXT_BEARER_CAPABILITY                    FAIL
S5-F18 ORDINARY_BENCHMARK_CASE_ID_COLLISION_NOT_VALIDATED           FAIL
S5-F19 DECLARED_FAMILY_CASE_PATH_CONTAINMENT_MISSING                FAIL
```

Immutable first-observation blob:

```text
c300d301cb6bf23e5ec1cc0472666f44a1148e77
```

Current decision:

```text
fresh structural gate                     FAIL
S5 bounded release          NOT ESTABLISHED
S5 release              BLOCKED_GOLD_REVIEW
S6 automatic trust                   BLOCKED
```

Interpretation:

- F16 shows that ordinary-source authentication is bound to a backing file, but not to the exact in-memory case payload exported afterward.
- F17 shows that `_training_export_context` is transferable and can authorize unrelated raw heldout benchmark content.
- F18 shows that byte-identity collision prevention does not reserve `case_id` across benchmark and ordinary namespaces.
- F19 shows that manifest source paths are contained only by the broad family root, not by the declared family directory; the materializer mirrors the same gap.

The v0.5 first observation is exposed forever and must never be relabeled fresh after repair.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 only when a downstream blocker requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. preserve all S5 first observations exactly
   - v0.4 first-observation blob remains immutable
   - v0.5 first-observation blob remains immutable

2. repair S5 v0.5 failures generically
   - bind ordinary-source authorization to exact source payload
   - remove transferable bearer semantics from _training_export_context
   - reserve case_id across benchmark and ordinary authenticated sources
   - enforce case-path containment inside the declared family directory
     in both policy construction and materialization

3. rerun S5 v0.5 only as exposed regression
   - preserve fresh-first-observation-v0.5.json unchanged

4. freeze the repaired implementation

5. only after that freeze create another genuinely new S5 boundary suite
   - attack ordinary-source reconstruction/binding
   - attack context replay and cross-object substitution
   - attack identity aliasing across policy versions
   - attack nested path/symlink/canonicalization variants
   - retain baseline split, decision-contract, prompt-leakage and gold-containment controls

6. gold review remains an independent blocker
   - never fabricate approval

7. only after bounded S5 release proceed to S6 dedicated harness evaluation

8. continue S6 → S7 → S8 → S9 → S10
```
