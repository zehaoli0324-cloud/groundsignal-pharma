# S2 Source-Routing Eval — Baseline Report v0.1

> Benchmark: `S2-source-routing-v0.1`
> Queries: 40
> Date: 2026-09-05

## Goal

Evaluate whether a medical information need is routed to the correct authoritative evidence source before retrieval, passage extraction, and model generation.

This is S2 routing evaluation only. It does **not** yet prove web/API retrieval quality or passage Recall@K.

---

# Run 1 — deterministic-s2-v0.1

Metrics:

```text
n_queries                         40
primary_source_recall_at_1       0.950
acceptable_source_recall_at_3    0.975
source_type_accuracy             0.925
freshness_routing_accuracy       0.970
wrong_authority_rate             0.025
secondary_as_gold_rate           0.000
critical_source_miss_rate        0.000
```

Failure counts:

```text
WRONG_SOURCE_TYPE         3
PRIMARY_SOURCE_NOT_TOP1   1
SOURCE_MISS               1
WRONG_AUTHORITY           1
```

## Bugs found

### 1. Approval-vs-trial routing priority

A query asking whether a product had FDA approval **or merely a Phase 3 registration** was routed to ClinicalTrials.gov first because the generic trial rule fired before the approval rule.

Root cause:

```text
rule-order bug
```

Fix:

```text
approval truth → Drugs@FDA before trial-registry routing
```

### 2. DDI methodology keyword gap

A general question about enzyme/transporter-mediated drug-interaction study design did not contain one of the narrow CYP/transporter lookup keywords and fell through to a generic drug fallback.

Root cause:

```text
intent-pattern coverage gap
```

Fix:

```text
explicit general DDI-methodology route → FDA/ICH M12
```

### 3. Eval schema assumed one source type per query

Some valid information needs allow more than one authoritative source class. Example: a current U.S. prescribing-label question may accept DailyMed SPL or Drugs@FDA.

The first evaluator treated the scalar `expected_source_type` as the only valid type and therefore reported a false `WRONG_SOURCE_TYPE` even when an explicitly acceptable source was returned.

Root cause:

```text
evaluator/gold-model bug
```

Fix:

```text
source-type correctness is evaluated against the registered types of all explicitly acceptable source IDs
```

This is an important example of why stage-level eval must test the evaluator itself, not only the production component.

---

# Run 2 — deterministic-s2-v0.1.1

After the three fixes:

```text
n_queries                         40
primary_source_recall_at_1       1.000
acceptable_source_recall_at_3    1.000
source_type_accuracy             1.000
freshness_routing_accuracy       1.000
wrong_authority_rate             0.000
secondary_as_gold_rate           0.000
critical_source_miss_rate        0.000
failure_counts                   {}
release_gate                     PASS
```

GitHub Actions step `Run S2 source-routing eval` passed.

---

# Interpretation

The result proves only that the current deterministic router correctly routes this **frozen 40-query v0.1 set**.

It does **not** prove robust generalization to arbitrary user queries.

A perfect score on a small rule-driven benchmark creates a new risk: benchmark overfitting. Therefore the next S2 work is not to tune these same 40 queries further.

## Next: S2 v0.2 held-out routing + real retrieval

1. Freeze these 40 as development/regression queries.
2. Add 20–40 paraphrased and compositional held-out routing queries that the router has not been tuned against.
3. Execute actual source search/API retrieval.
4. Score:
   - Current Document Recall@K
   - Critical Passage Recall@K
   - Evidence Precision@K
   - stale-result rate
   - duplicate/near-duplicate rate
   - query-rewrite gain
   - reranker gain
5. Preserve source-routing metrics separately so retrieval failures are not confused with routing failures.

## S2 exit criterion

S2 should be considered production-ready only when both routing and real retrieval pass held-out evaluation without relying on query-specific rules.
