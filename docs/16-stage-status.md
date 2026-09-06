# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`  
> Evaluation/optimization ledger: `docs/17-evaluation-methods-and-optimization-ledger.md`  
> Reusable method: `docs/18-reusable-stage-eval-optimization-playbook.md`  
> Algorithm collaboration: `docs/19-algorithm-collaboration-handoff-guide.md`

The system has **10 lifecycle stages**. `PASS` always refers to the explicitly tested slice, not unrestricted clinical deployment. Historical fresh/first observations are immutable; once observed, a suite may only be reused as exposed regression evidence.

| Stage | Name | Current maturity | Strongest current evidence | Main blocker / next proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; S2→S3 94.44%; live DailyMed 3/3 | clause-level negation/exclusion; broader live sources |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS** | S3a fresh F1 98.90%, critical recall 100%; S3b 40/40; joint 17/18 | larger real-source/noisy-passage held-out |
| S4 | Medical KG Construction / Update | **CONDITIONAL PASS / independent fresh PASS** | new fresh 20/20; must-reject 7/7; stale ACTIVE 0; invariant violations 0 | persistent/real-source graph proof; production ingest disabled |
| S5 | Controlled Case / Benchmark Factory | **v0.7 INDEPENDENT FRESH LINEAGE-GENERALIZATION FAIL / RELEASE BLOCKED** | v0.6.1 exposed F20–F23 PASS; new v0.7 preconditions PASS but F24–F27 FAIL | deterministic repair F24/F27 + algorithm handoff F25/F26; then re-freeze and new hidden fresh; gold review remains separate |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | dedicated S6 eval only after S5 bounded release |
| S7 | Evaluation & Safety Gate | Protocol complete | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration + real model scoring |
| S8 | Failure Diagnosis | Framework ready | taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters |
| S9 | Intervention / Post-training Data | Interface ready | SFT/preference/Agent/Judge schemas | actual intervention/training experiment |
| S10 | Candidate + Held-out Regression | Fixture proof | candidate-vs-baseline gate + held-out contracts | real post-intervention held-out improvement |

## S3 checkpoint

```text
S3a independent fresh: F1 98.90%; critical recall 100%; abstention 6/6; high-risk semantic FP 0
S3b structured held-out: 40/40; relation accuracy 100%; high-risk false-support 0
S2→S3 vertical slice: 17/18 = 94.44%; high-risk false-support 0
```

S3 remains bounded `CONDITIONAL PASS`; long/noisy real multi-source passages remain under-tested.

## S4 checkpoint

```text
v0.1 development                         12/12 PASS
v0.1 first independent fresh             18/20 FAIL
v0.1.1 exposed regression                20/20 PASS on prior fresh
v0.1.1 new independent fresh             20/20 PASS
must-reject                                7/7 PASS
stale ACTIVE                                 0
invariant violations                         0
```

Controlled truth-ledger state machine is `CONDITIONAL PASS`; unrestricted production clinical ingest remains disabled.

## S5 evidence history

```text
v0.1   F1–F3    development failures
v0.2   F4–F7    first independent fresh boundary                         FAIL
v0.2.1           exposed repair                                           PASS
v0.3   F8–F11   second independent fresh trust-root                       FAIL
v0.3.1           exposed repair                                           PASS
v0.4   F12–F15  third independent fresh policy-root                       FAIL
v0.4.1           exposed repair                                           PASS
v0.5   F16–F19  fourth independent fresh authority composition            FAIL
v0.5.1           exposed repair                                           PASS
v0.6   F20–F23  fifth independent fresh identity / lineage / TOCTOU       FAIL
v0.6.1           exposed identity / lineage / atomic-snapshot repair       PASS
v0.7   F24–F27  sixth independent fresh lineage generalization            FAIL
```

Recent immutable first-observation blobs:

```text
v0.4  45a10ed2cc522b555a3f3eecf785dffedf8cd4c3
v0.5  c300d301cb6bf23e5ec1cc0472666f44a1148e77
v0.6  f855e853ea2af9705cd3db478a3a40848459e0ea
v0.7  b14f9e8f348976ee4823e26a5d3923b7417efa0b
```

Gold approval remains separate from structural evaluation: P0 `0/12`, v0.2 family `0/1`, v0.3 family `0/1`, v0.4 family `0/1`; no expert/clinical approval is inferred. v0.5–v0.7 are structural-only suites.

## S5 v0.6.1 exposed repair checkpoint

```text
v0.6 first observation preservation      PASS
v0.5.1 exposed regression                PASS
F20 transformed lineage                  BLOCKED
F21 Unicode NFC identity collision       BLOCKED
F22 registry TOCTOU                      BLOCKED
F23 source TOCTOU                        BLOCKED
regression gate                          PASS
```

This remains exposed evidence only.

## S5 v0.7 first observation — immutable independent FAIL

Implementation freeze: `b2e2696bae9cf57bbf255e67e64dd63bd8773ff8`.

All v0.7 evaluator logic and fixtures were created after the freeze. All normal preconditions passed, then:

```text
S5-F24 cross-split semantic duplicate isolation        FAIL
S5-F25 paraphrased heldout-derived ordinary laundering FAIL
S5-F26 partial heldout fragment reuse                  FAIL
S5-F27 NFKC compatibility-equivalent case identity     FAIL
precondition failures                                     0
fresh structural gate                                  FAIL
S5 release                               BLOCKED_GOLD_REVIEW
S6 automatic trust                                    BLOCKED
```

Ownership split:

```text
F24 deterministic benchmark/eval infrastructure
F27 deterministic identifier contract
F25 algorithm-required semantic near-duplicate lineage
F26 algorithm-required field/span partial-lineage detection
```

Concrete algorithm handoff: `docs/20-s5-v07-algorithm-handoff.md` and GitHub Issue #1.

## Immediate order

```text
1. preserve v0.4/v0.5/v0.6/v0.7 first observations exactly
2. never relabel v0.7 after repair; it is exposed forever
3. repair F24/F27 through generic deterministic contracts, not fixture-specific rules
4. hand F25/F26 capability gaps to algorithm owner using docs/20 / Issue #1
5. algorithm owner may use dev + exposed data only; no next hidden fresh
6. integrate detector + exposed regression + cross-stage non-regression
7. freeze repaired implementation
8. eval owner creates another unseen S5 lineage family
9. gold review remains independent; never fabricate approval
10. only after bounded S5 release proceed to S6 dedicated evaluation
```
