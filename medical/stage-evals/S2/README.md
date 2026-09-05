# S2 — Knowledge Search & Source Routing Eval

S2 asks one narrow question:

> Given a medical/pharma information need, does the system route it to the correct authoritative evidence source before retrieval and generation?

This is intentionally separated from S3 passage verification and from retrieval ranking.

## v0.1 scope

`routing-gold-v0.1.json` contains 40 frozen queries across:

- current prescribing information;
- regulatory approval status;
- CYP/transporter DDI and clinical pharmacology;
- pharmacogenomics;
- clinical-trial registry metadata;
- drug terminology normalization;
- lab/observation terminology normalization;
- post-marketing safety signals;
- professional/public-health guidance;
- literature/domain safety discovery.

Each query records:

```text
query_id
query
intent
expected_primary_source_id
acceptable_source_ids
expected_source_type
freshness_sensitive
high_risk
forbidden_as_gold
notes
```

## Metrics

- `primary_recall_at_1`
- `acceptable_recall_at_3`
- `source_type_accuracy`
- `freshness_routing_accuracy`
- `wrong_authority_rate`
- `secondary_as_gold_rate`
- `critical_source_miss_rate`

## Failure taxonomy

- `SOURCE_MISS`
- `WRONG_SOURCE_TYPE`
- `WRONG_AUTHORITY`
- `STALE_SOURCE_ROUTE`
- `SECONDARY_AS_GOLD`
- `JURISDICTION_MISMATCH`
- `TERMINOLOGY_AS_CLINICAL_TRUTH`
- `REGISTRY_AS_EFFICACY_TRUTH`
- `SIGNAL_AS_CAUSAL_TRUTH`

## Commands

```bash
python scripts/s2_source_router.py \
  --input medical/stage-evals/S2/routing-gold-v0.1.json \
  --out /tmp/s2-predictions.json

python scripts/eval_s2_source_routing.py \
  --gold medical/stage-evals/S2/routing-gold-v0.1.json \
  --pred /tmp/s2-predictions.json \
  --out /tmp/s2-report.json
```

The deterministic router is only a baseline. Its errors become the first S2 debugging backlog before a production retrieval engine is introduced.
