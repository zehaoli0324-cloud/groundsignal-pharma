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
| S5 | Controlled Case / Benchmark Factory | **v0.3 INDEPENDENT FRESH TRUST-ROOT FAIL / RELEASE BLOCKED** | v0.2.1 exposed F4–F7 regression PASS; new v0.3 fresh preconditions PASS but F8–F11 all bypass export authority | replace path/self-asserted trust with external suite/source authority, then rerun v0.3 as exposed regression and create another fresh suite after repair freeze |
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

Current decision:

```text
S4 controlled truth-ledger state machine = CONDITIONAL PASS
independent fresh gate                   = PASS
unrestricted production clinical ingest = DISABLED
```

---

## S5 historical checkpoint — v0.1 first development observation

The v0.1 first observation at commit `811a755120210a14863a485e31c42ed5d3dd5f28` is permanently preserved:

```text
S5-F1 split provenance / training export guard     FAIL
S5-F2 release-grade gold readiness                 FAIL
S5-F3 decision-node contract schema enforcement    FAIL
S5 release                                         FAIL
```

Original P0 assets were already exposed and can never be relabeled as fresh evidence.

---

## S5 v0.1.1 checkpoint — structural repair exposed regression

Evidence class: **development exposed regression**, not fresh held-out.

```text
families                                  12
cases                                     60
split counts              dev 36 / regression 12 / heldout 12
materialized provenance                  60/60
decision-contract coverage               60/60
training eligible                            36
training blocked                             24
approved heldout export                 BLOCKED
approved regression export              BLOCKED
approved dev export                         PASS
prompt gold sentinel leakage               NONE
structural gate                            PASS
```

Historical failure disposition:

```text
S5-F1  REPAIRED_EXPOSED_REGRESSION
S5-F2  CONTAINED_RELEASE_BLOCKED_NO_FAKE_APPROVAL
S5-F3  REPAIRED_EXPOSED_REGRESSION
```

Gold approval remains `0/12`; S5 release and S6 automatic trust remain blocked.

---

## S5 v0.2 checkpoint — first independent fresh boundary FAIL

Target implementation freeze: `37a89d14b37a1e2b3b823e933b4a7bfbd3038af8`.

The post-freeze 5-case family (`dev 3 / regression 1 / heldout 1`) passed baseline materialization, normal split guarding, prompt-gold containment and gold-release containment, but exposed four generic boundary failures:

```text
S5-F4 PROVENANCE_AUTHORITY_NOT_VERIFIED                  FAIL
S5-F5 UNPROVENANCED_OR_UNKNOWN_SPLIT_NOT_FAIL_CLOSED    FAIL
S5-F6 MATERIALIZED_PAYLOAD_INTEGRITY_NOT_ENFORCED       FAIL
S5-F7 DECISION_EXEMPTION_SCHEMA_MATERIALIZER_DIVERGENCE FAIL
```

The first observation is immutable and reproduced only against its historical commit.

---

## S5 v0.2.1 checkpoint — generic boundary repair exposed regression

The already-exposed v0.2 probes were repaired without fabricating gold approval:

```text
baseline dev export              EXPORTABLE
baseline regression export          BLOCKED
baseline heldout export             BLOCKED
S5-F4 forged heldout -> dev          BLOCKED
S5-F5 stripped provenance            BLOCKED
S5-F5 unknown split=train            BLOCKED
S5-F5 heldout + eligible=true        BLOCKED
S5-F5 dev + eligible=false           BLOCKED
S5-F6 post-materialization tamper     BLOCKED
S5-F7 exemption schema alignment        PASS
exposed regression gate                  PASS
```

The implementation added manifest/source SHA-256 checks, explicit split allowlisting, a canonical materialized-payload digest and schema/materializer decision-contract alignment. This was useful but remained exposed regression evidence only.

---

## S5 v0.3 checkpoint — second genuinely fresh trust-root FAIL

Target implementation freeze:

```text
commit  c938dc86c992f13015585b813aad11c2dca55b24
```

All v0.3 fixture files, decoy authority files, evaluator logic and workflow were authored after this freeze. The fresh family contains 5 synthetic cases (`dev 3 / regression 1 / heldout 1`). No target implementation file changed before the first observation.

Preconditions:

```text
frozen target blob identity              PASS
fresh family validation                   PASS
fresh materialization                     PASS
baseline dev export                 EXPORTABLE
baseline regression export             BLOCKED
baseline heldout export                BLOCKED
decision-contract alignment              PASS
prompt gold sentinel leakage             NONE
gold release containment                 PASS
precondition failures                        0
```

New hard-gate failures:

```text
S5-F8 LOCATION_LAUNDERING_TRUST_BYPASS
  raw heldout case copied to ordinary path + loaded via trusted unpartitioned loader
  result: EXPORTABLE

S5-F9 SELF_AUTHENTICATED_PAYLOAD_DIGEST_RECOMPUTABLE
  materialized dev payload mutated + embedded SHA-256 recomputed
  result: EXPORTABLE

S5-F10 SUITE_IDENTITY_NOT_AUTHENTICATED
  benchmark_provenance.suite_id forged + embedded digest recomputed
  result: EXPORTABLE

S5-F11 FOREIGN_MANIFEST_AUTHORITY_SUBSTITUTION
  heldout provenance redirected to repo-local foreign manifest not listed by the suite
  foreign manifest declares same case_id as dev; hashes + embedded digest recomputed
  result: EXPORTABLE
```

Current decision:

```text
fresh structural gate                     FAIL
stage release              BLOCKED_GOLD_REVIEW
S6 automatic trust                      BLOCKED
```

Interpretation: v0.2.1 repaired local tamper/split failures, but v0.3 demonstrates that the system still lacks an external trust root. A digest stored inside the object it authenticates can be recomputed; repo-local manifest presence is not equivalent to suite authority; and path-derived trusted-loader context can launder benchmark identity.

Immutable artifacts:

- `medical/stage-evals/S5/fresh-boundary-v0.3/protocol-v0.3.json`
- `medical/stage-evals/S5/fresh-boundary-v0.3/suite-fresh-boundary-v0.3.json`
- `medical/stage-evals/S5/fresh-first-observation-v0.3.json`
- `medical/stage-evals/S5/failures-v0.3.json`
- `medical/stage-evals/S5/S5_V0.3_FRESH_BOUNDARY_FAIL_REPORT.md`
- `scripts/eval_s5_fresh_boundary_v03.py`

The v0.3 suite is now exposed and must never be relabeled fresh after repair.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 when a downstream stage requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. repair S5 v0.3 failures generically
   - remove location-derived implicit trust for unpartitioned sources
   - use an explicit external allowlist/policy for ordinary non-benchmark training inputs
   - bind materialized payload content back to authoritative source content, not only an embedded recomputable digest
   - bind suite_id to an authoritative suite path/hash and verify family membership
   - reject foreign manifests that are not members of the authenticated suite

2. rerun S5 v0.3 only as exposed regression
   - preserve fresh-first-observation-v0.3.json unchanged

3. freeze the repaired S5 implementation

4. only after that freeze create another genuinely new S5 boundary suite
   - attack external source-policy substitution
   - attack suite file/path/hash replay
   - attack cross-suite same-case-id collisions
   - attack source-content replacement and digest replay
   - retain baseline split, decision-contract, prompt-leakage and gold-containment probes

5. gold review remains an independent blocker
   - P0: 0/12 gold-approved
   - v0.2 family: 0/1 gold-approved
   - v0.3 family: 0/1 gold-approved
   - never fabricate approval

6. only after bounded S5 release proceed to S6 dedicated harness evaluation

7. continue S6 → S7 → S8 → S9 → S10

8. backfill S1/S2 only when required by a downstream blocker or after sequential evaluation
```
