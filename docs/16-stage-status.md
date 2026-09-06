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
| S5 | Controlled Case / Benchmark Factory | **FRESH v0.2 BOUNDARY FAIL / v0.1.1 STRUCTURAL PASS / RELEASE BLOCKED** | new post-freeze 5-case family materializes 5/5 and baseline split guard passes, but four generic boundary failures were observed | provenance authority, fail-closed split identity, payload integrity, decision-contract alignment; 0/12 P0 + 0/1 fresh family gold-approved |
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

Historical evidence remains immutable:

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

This is not clinical validation. Persistent graph scale, terminology normalization, real-source ingestion and concurrent update semantics remain outside the validated slice.

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

Immutable artifacts:

- `medical/stage-evals/S5/development-first-observation-v0.1.json`
- `medical/stage-evals/S5/failures-v0.1.json`
- `medical/stage-evals/S5/S5_V0.1_DEVELOPMENT_FAIL_REPORT.md`

The historical preservation workflow checks the exact Git blob SHAs rather than recomputing v0.1 against later repaired code.

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
S5-F1 SPLIT_PROVENANCE_NOT_ENFORCED          REPAIRED_EXPOSED_REGRESSION
S5-F2 GOLD_READINESS_UNSATISFIED             CONTAINED_RELEASE_BLOCKED_NO_FAKE_APPROVAL
S5-F3 DECISION_CONTRACT_NOT_SCHEMA_ENFORCED  REPAIRED_EXPOSED_REGRESSION
```

The repair deliberately does not fabricate review:

```text
gold approved families                 0/12
pending gold families                 12/12
release predicate              BLOCKED_GOLD_REVIEW
S5 stage release                     BLOCKED
S6 automatic trust                   BLOCKED
```

Key implementation rules at the v0.1.1 freeze:

1. raw case JSON is a design source, not the downstream partition authority;
2. `materialize_s5_cases.py` joins case + family manifest + suite contract and records `suite_id`, `family_id`, `split`, source paths, SHA-256 hashes, materializer version and training eligibility;
3. only `dev` is training-eligible in the exposed P0 suite;
4. `heldout` and `regression` are fail-closed in `export_training_data.py` on the ordinary materialized path;
5. `clinical-case.schema.json` requires the decision contract;
6. `s5_release_gate.py` requires explicit `status=gold_approved` for every family and never infers approval.

Detailed artifacts:

- `medical/stage-evals/S5/S5_V0.1.1_EXPOSED_REGRESSION_SPEC.md`
- `medical/stage-evals/S5/structural-regression-v0.1.1.json`
- `medical/stage-evals/S5/release-gate-v0.1.1.json`
- `medical/stage-evals/S5/blockers-v0.1.1.json`
- `medical/stage-evals/S5/S5_V0.1.1_STRUCTURAL_PASS_REPORT.md`

---

## S5 v0.2 checkpoint — post-freeze fresh boundary first observation FAIL

Target implementation was frozen at:

```text
commit  37a89d14b37a1e2b3b823e933b4a7bfbd3038af8
```

The new `S5FRESH-BOUNDARY-001` synthetic family did not exist at that freeze. It contains 5 first-use cases (`dev 3 / regression 1 / heldout 1`) and is fresh relative to the frozen target. This is not third-party expert review or clinical validation.

Preconditions and baseline behavior:

```text
frozen implementation blob identity      PASS
fresh family referential integrity       PASS
fresh materialization                    5/5 PASS
decision contracts                       5/5
provenance complete                      5/5
baseline heldout export                  BLOCKED
baseline regression export               BLOCKED
baseline dev export                      PASS
gold sentinel prompt leakage             NONE
fresh-family gold approval               0/1
gold release predicate                   BLOCKED_GOLD_REVIEW
```

First-use adversarial hard-gate failures:

```text
S5-F4 PROVENANCE_AUTHORITY_NOT_VERIFIED
  heldout provenance relabeled -> dev + training_eligible=true
  result: EXPORTABLE

S5-F5 UNPROVENANCED_OR_UNKNOWN_SPLIT_NOT_FAIL_CLOSED
  provenance stripped + top-level split=dev
  result: EXPORTABLE
  unknown provenance split=train + training_eligible=true
  result: EXPORTABLE

S5-F6 MATERIALIZED_PAYLOAD_INTEGRITY_NOT_ENFORCED
  materialized dev prompt mutated after provenance/source hash creation
  result: EXPORTABLE

S5-F7 DECISION_EXEMPTION_SCHEMA_MATERIALIZER_DIVERGENCE
  materializer accepts typed exemption without graph_eval
  JSON schema still requires graph_eval
  result: CONTRACT DIVERGENCE
```

Controls behaved correctly: an unchanged heldout split remained blocked even with `training_eligible=true`, and `training_eligible=false` remained blocking after a split flip.

Current decision:

```text
fresh structural gate                   FAIL
S5 release               BLOCKED_GOLD_REVIEW
S6 automatic trust                     BLOCKED
```

The v0.2 suite is now exposed and can only be used as regression evidence. It must never be relabeled fresh after repair.

Immutable first-observation artifacts:

- `medical/stage-evals/S5/fresh-boundary-v0.2/protocol-v0.2.json`
- `medical/stage-evals/S5/fresh-boundary-v0.2/suite-fresh-boundary-v0.2.json`
- `medical/stage-evals/S5/fresh-first-observation-v0.2.json`
- `medical/stage-evals/S5/failures-v0.2.json`
- `medical/stage-evals/S5/S5_V0.2_FRESH_BOUNDARY_SPEC.md`
- `medical/stage-evals/S5/S5_V0.2_FRESH_BOUNDARY_FAIL_REPORT.md`

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 when a downstream stage requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. repair S5 v0.2 failures generically
   - authenticate partition authority against the suite/manifest contract
   - require explicit allowlisted materialized split; remove permissive fallback
   - bind and verify materialized-payload integrity before training export
   - unify schema/materializer decision-contract exemption semantics

2. rerun S5 v0.2 only as exposed regression
   - preserve fresh-first-observation-v0.2.json unchanged

3. freeze the repaired S5 implementation

4. only after that freeze, create a second genuinely new S5 boundary suite
   - do not reuse v0.2 as fresh
   - retest provenance tamper, missing/unknown split, payload mutation and contract alignment
   - retain leakage/shortcut and gold-containment probes

5. gold review remains an independent blocker
   - P0: 0/12 gold-approved
   - new v0.2 family: 0/1 gold-approved
   - never fabricate approval

6. only after bounded S5 release proceed to S6 dedicated harness evaluation

7. continue S6 → S7 → S8 → S9 → S10

8. backfill S1/S2 only when required by a downstream blocker or after sequential evaluation
```
