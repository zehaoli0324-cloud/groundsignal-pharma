# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`  
> Evaluation/optimization ledger: `docs/17-evaluation-methods-and-optimization-ledger.md`

The system has **10 lifecycle stages**. `PASS` always refers to the explicitly tested slice, not unrestricted clinical deployment. Historical fresh/first observations are immutable; once observed, a suite may only be reused as exposed regression evidence.

| Stage | Name | Current maturity | Strongest current evidence | Main blocker / next proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; S2→S3 94.44%; live DailyMed 3/3 | clause-level negation/exclusion; broader live sources |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS** | S3a fresh F1 98.90%, critical recall 100%; S3b 40/40; joint 17/18 | larger real-source/noisy-passage held-out |
| S4 | Medical KG Construction / Update | **CONDITIONAL PASS / independent fresh PASS** | new fresh 20/20; must-reject 7/7; stale ACTIVE 0; invariant violations 0 | persistent/real-source graph proof; production ingest disabled |
| S5 | Controlled Case / Benchmark Factory | **v0.6.1 EXPOSED IDENTITY/LINEAGE/TOCTOU REGRESSION PASS / RELEASE BLOCKED** | v0.6 independent fresh F20–F23 FAIL preserved; v0.6.1 exposed regression repairs all four | freeze v0.6.1 and create genuinely new post-freeze fresh suite; gold review remains independent blocker |
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
```

Recent immutable first-observation blobs:

```text
v0.4  45a10ed2cc522b555a3f3eecf785dffedf8cd4c3
v0.5  c300d301cb6bf23e5ec1cc0472666f44a1148e77
v0.6  f855e853ea2af9705cd3db478a3a40848459e0ea
```

Gold approval remains separate from structural evaluation: P0 `0/12`, v0.2 family `0/1`, v0.3 family `0/1`, v0.4 family `0/1`; no expert/clinical approval is inferred. v0.5/v0.6 are structural-only suites.

## S5 v0.6 first observation — immutable independent FAIL

Implementation freeze: `60f74c7f30c007008ee73df3eed6eacf4a9bab0a`.

All preconditions passed, then four new hard failures were observed:

```text
S5-F20 transformed heldout-derived ordinary source       FAIL
S5-F21 Unicode-normalization case_id collision           FAIL
S5-F22 registry check/read TOCTOU substitution           FAIL
S5-F23 ordinary-source check/read TOCTOU substitution    FAIL
fresh structural gate                                    FAIL
S5 release                                BLOCKED_GOLD_REVIEW
S6 automatic trust                                     BLOCKED
```

That result is exposed forever and is never relabeled fresh.

## S5 v0.6.1 — exposed repair checkpoint

Generic changes:

- case identifiers must be Unicode NFC canonical at construction and protected validation boundaries;
- a stable semantic-core fingerprint is reserved across benchmark and ordinary-source namespaces, preventing byte-distinct transformed benchmark content from being reclassified as ordinary training data;
- registry, registered policy, suite, manifest, source case and ordinary source authority JSON are hashed and parsed from the same in-memory byte snapshot;
- existing authenticated registry, exact payload, split guard and declared-family containment protections remain active.

Regression contract:

```text
v0.6 first observation preservation      PASS
v0.5.1 exposed regression                PASS
F20 transformed lineage                  BLOCKED
F21 Unicode identity collision           BLOCKED
F22 registry TOCTOU                      BLOCKED
F23 source TOCTOU                        BLOCKED
failed gates                                 0
regression gate                          PASS
```

Current decision:

```text
S5 v0.6.1 exposed regression             PASS
S5 bounded independent release           NOT ESTABLISHED
S5 gold review                           INCOMPLETE
S5 stage_release                         BLOCKED_GOLD_REVIEW
S6 automatic trust                       BLOCKED
```

## Immediate order

```text
1. preserve v0.4/v0.5/v0.6 first observations exactly
2. treat v0.6.1 only as exposed repair evidence
3. freeze v0.6.1 implementation
4. after freeze create a genuinely new S5 fresh suite
   - paraphrased / partial-derived benchmark leakage
   - semantic-core perturbations that should still count as derived
   - new path/identifier canonicalization attacks
   - snapshot-consistency attacks that do not reuse v0.6 mechanics
5. gold review remains independent; never fabricate approval
6. only after bounded S5 release proceed to S6 dedicated evaluation
7. then continue S6 → S7 → S8 → S9 → S10
```
