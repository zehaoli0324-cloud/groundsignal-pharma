# GroundSignal Medical — Stage Maturity Status

> Date: 2026-09-06  
> Lifecycle definition: `docs/15-system-stages.md`

The system has **10 lifecycle stages**. `PASS` always refers to the explicitly tested slice, not unrestricted clinical deployment. Historical fresh first observations are immutable; once observed, a fresh suite may only be reused as exposed regression data.

| Stage | Name | Current maturity | Strongest current evidence | Main blocker / next proof |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks, high-risk matrix, user-research plan | real interview/log validation and frequency weighting |
| S2 | Knowledge Search & Source Routing | **CONDITIONAL PASS / v0.4 development FAIL** | v0.3 fresh routing 91.7%; S2→S3 joint intent/source 94.44%; live DailyMed 3/3 | clause-level negation/exclusion + role-separated features; broader live sources |
| S3 | Evidence Verification & Temporal Truth | **CONDITIONAL PASS** | S3a v0.5.6.1 fresh F1 98.90%, critical recall 100%; S3b 40/40; joint S2→S3 17/18, high-risk false support 0 | larger real-source/noisy-passage held-out |
| S4 | Medical KG Construction / Update | **FRESH FAIL / v0.1.1 exposed regression PASS / auto-ingestion blocked** | v0.1.1 dev 12/12; v0.1 fresh-now-exposed 20/20; must-reject 7/7; stale ACTIVE 0 | brand-new v0.1.1 independent fresh held-out |
| S5 | Controlled Case / Benchmark Factory | P0 complete | 12 families / 60 controlled cases / held-out design | clinical expert gold review + dedicated S5 eval |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | live multi-provider runs + dedicated S6 eval |
| S7 | Evaluation & Safety Gate | Protocol complete | v0.2 rubric, graph/RAG/Agent layers, regression safety gate | human/Judge calibration + real model scoring |
| S8 | Failure Diagnosis | Framework ready | taxonomy, stale-knowledge bad case, intervention router | multi-model cross-case failure clusters |
| S9 | Intervention / Post-training Data | Interface ready | SFT/preference/Agent/Judge schemas | actual intervention/training experiment |
| S10 | Candidate + Held-out Regression | Fixture proof | candidate-vs-baseline gate + held-out contracts | real post-intervention held-out improvement |

---

## S2 checkpoint

Independent evidence remains unchanged:

```text
v0.3 fresh routing                   Primary@1 91.7%   PASS
S2→S3 joint v0.1                     intent/source 94.44%
live DailyMed passage slice          3/3             PASS
S2 v0.4 negation development         90.00%          FAIL
```

Frozen v0.4 failure families are coordinated exclusion scope, modifier-separated exclusion, and context-role collapse. No v0.4 fresh validation was run. Next backfill after the current S4 blocker is **S2 v0.4.1 Clause-scope Negation + Role-separated Features**.

Detailed report: `medical/stage-evals/S2/S2_V0.4_DEV_FAIL_REPORT.md`.

---

## S3 checkpoint

```text
S3a v0.5.6.1 independent fresh
  F1                              98.90%
  Critical Proposition Recall   100.00%
  Polarity / Population / Condition 100.00%
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

S3 is a bounded `CONDITIONAL PASS`, not production readiness. Most non-DailyMed source passages in the joint slice are controlled; long/noisy real multi-source documents remain under-tested.

Reports:
- `medical/stage-evals/S3/S3A_V0.5.6.1_FRESH_REPORT.md`
- `medical/stage-evals/S3/S3B_V0.3_REPORT.md`
- `medical/stage-evals/S2S3/S2_S3_JOINT_V0.1_REPORT.md`

---

## S4 checkpoint — current blocker

### Immutable v0.1 independent fresh result

```text
cases                              20
passed                             18
failed                              2
case accuracy                    90.0%   FAIL
must-reject                         7/7   PASS
high-risk false accepts              0   PASS
stale ACTIVE edges                   1   FAIL
release                              FAIL
```

Frozen failures:

```text
S4-F1  late historical insertion can become ACTIVE behind a newer unresolved CONTESTED frontier
S4-F2  a third same-date conflict can become ACTIVE instead of joining the existing contested set
```

Historical report: `medical/stage-evals/S4/S4_V0.1_FRESH_FAIL_REPORT.md`.

### S4 v0.1.1 — Unified Temporal Frontier + Contested-set Closure

The repair treats `ACTIVE` and unresolved `CONTESTED` as one per-slot current temporal frontier. Older arrivals behind the frontier remain historical; same-date distinct claims join the complete contested set; a later fact supersedes the previous frontier whether it was active or contested.

No new fresh/shadow held-out was created in this iteration.

Exposed regression:

```text
original v0.1 development suite          12/12   PASS
v0.1 fresh-now-exposed suite             20/20   PASS
temporal tag                              100%   PASS
contradiction tag                         100%   PASS
scope / rollback / safety                100%   PASS
partition / provenance                    100%   PASS
must-reject                                 7/7   PASS
high-risk false accepts                      0   PASS
stale ACTIVE edges                           0   PASS
```

Current S4 decision:

```text
v0.1 historical independent fresh      = FAIL (immutable)
v0.1.1 exposed development/regression  = PASS
v0.1.1 independent fresh               = NOT RUN
S4 overall                             = FRESH FAIL / BLOCKED
automatic S3 → S4 clinical truth       = BLOCKED
```

Detailed report: `medical/stage-evals/S4/S4_V0.1.1_DEV_PASS_REPORT.md`.

---

## Immediate order

```text
1. Freeze S4 v0.1.1 implementation.
2. Create a brand-new S4 v0.1.1 independent fresh held-out only after freeze.
3. Preserve the first result permanently; on FAIL, record taxonomy/status before repair.
4. Only on new fresh PASS may S4 move to bounded CONDITIONAL PASS.
5. Then return to S2 v0.4.1 evidence backfill.
6. After S4 conditional release, proceed to S5 dedicated stage evaluation.
```

Unrestricted automatic free text → truth → Knowledge Graph insertion remains prohibited until the S4 independent fresh release gate passes.
