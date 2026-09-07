# Interview Candidate Promotion Pilot v0.1

> Status: **ROUTING PILOT ONLY — NO MEDICAL TRUTH, GOLD, BENCHMARK OR TRAINING PROMOTION**

This pilot is the first controlled use of the quarantined interview-derived question corpus. It
selects the first three items in the priority-review queue and converts them into auditable stage
work records. The question text remains unverified source material; no source answer is imported.

## Selected questions

| Candidate | Topic | Risk | Current boundary |
|---|---|---:|---|
| `INT-PM-04-02` | analysing a reported 70% CDSS recommendation accuracy | high | metric premise unverified |
| `INT-PM-04-06` | request to use unredacted patient data | high | jurisdiction and authority unresolved |
| `INT-PM-04-09` | designing a medical-data quality monitoring platform | medium | workflow and source-system context missing |

CDSS means Clinical Decision Support System（临床决策支持系统）.

## Stage use

```text
S1  candidate selected for workflow discovery; not real-user validated
S2  authoritative source route defined; retrieval not completed
S3  blocked because no evidence snapshot has been retrieved and frozen
S4  ineligible for knowledge-graph ingestion
S5  evaluation-design draft only; split unassigned; gold_approved=false
S6+ automatic use blocked
```

`promotion-records.jsonl` records the source routes and gate state. It intentionally contains no
answer, clinical advice, evidence claim, scoring rubric or benchmark split. A later reviewer must
resolve jurisdiction, intended use and local workflow, retrieve current authoritative sources, and
freeze an evidence snapshot before any S3 proposition or S5 behavior-gold work begins.

## Validation

```bash
python scripts/validate_interview_promotion_pilot.py
```

The validator checks exact linkage to the quarantined corpus, queue order, stage gates, absence of
answer payloads and non-entry into S4/S5 authority files.
