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
| S5 | Controlled Case / Benchmark Factory | **STRUCTURAL PASS v0.1.1 / RELEASE BLOCKED** | 60/60 provenance materialization; heldout/regression export blocked; decision contract schema PASS | 0/12 gold-approved; no genuinely fresh S5 release suite yet |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | dedicated S6 eval only after S5 bounded release; do not auto-trust P0 release partitions |
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

Key implementation rules:

1. raw case JSON is a design source, not the downstream partition authority;
2. `materialize_s5_cases.py` joins case + family manifest + suite contract and records `suite_id`, `family_id`, `split`, source paths, SHA-256 hashes, materializer version and training eligibility;
3. only `dev` is training-eligible in the exposed P0 suite;
4. `heldout` and `regression` are fail-closed in `export_training_data.py`, even when a training candidate is marked approved;
5. `clinical-case.schema.json` now requires the decision contract (`graph_eval` + required nodes/edges/reasoning path); typed exemptions must be explicit rather than silent omissions;
6. `s5_release_gate.py` requires explicit `status=gold_approved` for every family and never infers approval from source quality or model scores.

Detailed artifacts:

- `medical/stage-evals/S5/S5_V0.1.1_EXPOSED_REGRESSION_SPEC.md`
- `medical/stage-evals/S5/structural-regression-v0.1.1.json`
- `medical/stage-evals/S5/release-gate-v0.1.1.json`
- `medical/stage-evals/S5/blockers-v0.1.1.json`
- `medical/stage-evals/S5/S5_V0.1.1_STRUCTURAL_PASS_REPORT.md`

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 when a downstream stage requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. freeze S5 v0.1.1 implementation

2. only after freeze, create a genuinely new S5 family/suite
   - never reuse the 12 exposed P0 heldout cases as fresh
   - include new materialization/provenance paths
   - include leakage/shortcut probes
   - include decision-node coverage and verifier-alignment gates

3. run first-use independent fresh S5 evaluation
   - preserve the first result permanently, PASS or FAIL
   - if FAIL, synchronize raw result + taxonomy + stage status before repair

4. only after S5 bounded release proceed to S6 dedicated harness evaluation

5. continue S6 → S7 → S8 → S9 → S10

6. backfill S1/S2 only when required by a downstream blocker or after sequential evaluation
```
