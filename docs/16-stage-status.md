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
| S5 | Controlled Case / Benchmark Factory | **v0.2.1 EXPOSED REGRESSION PASS / RELEASE BLOCKED** | v0.2 first fresh FAIL is immutable; F4–F7 now pass exposed regression with authenticated manifest authority + payload digest | freeze v0.2.1, then create a genuinely new fresh boundary suite; gold review remains independent blocker |
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

The v0.1.1 workflow is now historical-preservation only: it reproduces the exact stored metrics against commit `37a89d14...`, rather than demanding that later implementations reproduce the same byte-level output.

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

Current historical decision remains:

```text
fresh structural gate                   FAIL
S5 release               BLOCKED_GOLD_REVIEW
S6 automatic trust                     BLOCKED
```

The v0.2 first observation is immutable. Its preservation workflow now reproduces the result at the exact first-observation commit `c2ea0a58...`, so later repaired code cannot overwrite or reinterpret it.

---

## S5 v0.2.1 checkpoint — generic boundary repair exposed regression

Evidence class: **development exposed regression**. The v0.2 suite is not fresh anymore.

Generic repairs:

1. **Authenticated partition authority** — training export resolves the source family manifest, verifies manifest/source-case SHA-256 values, finds the authoritative case reference, and rejects any local split mismatch.
2. **Explicit fail-closed split semantics** — only `dev` is allowlisted; `regression`, `heldout`, missing partition identity, unknown split labels, or partitioned cases without authenticated provenance are blocked.
3. **Materialized payload binding** — materialization records `materialized_payload_sha256` over the canonical complete payload; exporter recomputes it immediately before export and rejects mutation.
4. **Decision-contract alignment** — the clinical-case schema now requires either a complete `graph_eval` contract or a typed `decision_contract_exemption`, matching materializer semantics.
5. **Non-benchmark compatibility is not a bypass** — standalone training fixtures are accepted only through an in-process trusted file-loader context; direct unprovenanced case objects cannot self-assert trust.

Exposed regression metrics:

```text
family count                              1
case count                                5
split counts                dev 3 / regression 1 / heldout 1
training eligible                         3
training blocked                          2
payload digest present                  5/5
payload digest self-consistent          5/5

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

Historical failure disposition:

```text
S5-F4  REPAIRED_EXPOSED_REGRESSION
S5-F5  REPAIRED_EXPOSED_REGRESSION
S5-F6  REPAIRED_EXPOSED_REGRESSION
S5-F7  REPAIRED_EXPOSED_REGRESSION
```

Release status does **not** change to PASS:

```text
v0.2 fresh family gold approved        0/1
P0 family gold approved               0/12
release predicate       BLOCKED_GOLD_REVIEW
S5 stage release                      BLOCKED
S6 automatic trust                    BLOCKED
```

Detailed artifacts:

- `medical/stage-evals/S5/boundary-regression-v0.2.1.json`
- `medical/stage-evals/S5/S5_V0.2.1_BOUNDARY_REPAIR_REPORT.md`
- `scripts/eval_s5_boundary_regression_v021.py`

Interpretation: F4–F7 are repaired on exposed regression probes, but S5 still lacks a **new independent post-repair fresh boundary observation** and still lacks required gold approval. Therefore this version is not sufficient to release S5 or to let S6 automatically trust S5 partitions.

---

## S2 evidence backfill

S2 still has an exposed v0.4 negation-development FAIL and remains a bounded conditional pass. It is not the current sequential blocker because S3 and S4 have bounded independent release evidence. Return to S2 when a downstream stage requires stronger source-routing evidence or after the S5–S10 sequence reaches an upstream dependency.

---

## Immediate order

```text
1. freeze S5 v0.2.1 implementation and blob identities

2. after that freeze only, author a genuinely new S5 fresh boundary suite
   - do not reuse v0.2 as fresh
   - attack manifest authority and manifest/source hash tampering
   - attack stripped/unknown split and alternate metadata placement
   - attack post-materialization payload mutation
   - attack decision-contract exemption/graph semantic disagreement
   - retain prompt leakage and gold-containment probes
   - preserve the first result permanently whether PASS or FAIL

3. gold review remains an independent blocker
   - P0: 0/12 gold-approved
   - v0.2 family: 0/1 gold-approved
   - never fabricate approval

4. only when the applicable bounded S5 release gates are satisfied proceed to S6 dedicated harness evaluation

5. continue S6 → S7 → S8 → S9 → S10

6. backfill S1/S2 only when required by a downstream blocker or after sequential evaluation
```
