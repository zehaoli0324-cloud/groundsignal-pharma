# S3 Split Design — Extraction vs Entailment

## Why split S3

The v0.6 untouched first run showed that end-to-end S3 mixes two materially different capabilities:

```text
free-text understanding
and
deterministic truth reasoning
```

A failure such as `no_candidate_propositions` is not an entailment failure: the entailment engine never received the proposition it needed to judge. Conversely, a correctly extracted `<30 contraindication` proposition can still be mishandled by bad threshold algebra.

S3 is therefore decomposed into two independently evaluated components.

---

## S3a — Semantic Proposition Extraction

Input:

```text
free-text evidence passage
or
free-text candidate claim
```

Output:

```text
subject
predicate
object
polarity
conditions
population/scope when decision-critical
```

Primary metrics:

- micro proposition precision;
- micro proposition recall;
- micro proposition F1;
- critical-proposition recall;
- polarity accuracy on matched proposition identities;
- condition/action binding accuracy;
- directional subject/object accuracy.

Safety emphasis:

A missing or polarity-flipped proposition is especially serious when it represents:

- contraindication;
- discontinuation / mandatory management;
- diagnosis;
- causality;
- incidence;
- endpoint achievement / efficacy;
- current-vs-superseded recommendation;
- dose recommendation.

S3a does **not** decide whether a candidate claim is ultimately supported.

---

## S3b — Structured Proposition Entailment

Input:

```text
canonical evidence propositions
+
canonical candidate propositions
```

The free-text parser is bypassed.

Output per candidate proposition:

```text
SUPPORTED
CONTRADICTED
UNSUPPORTED
```

Whole-claim aggregation:

```text
DIRECT_SUPPORT
PARTIAL_SUPPORT
CONTRADICTS
DOES_NOT_SUPPORT
```

Primary metrics:

- relation accuracy;
- high-risk false-support rate;
- threshold algebra accuracy;
- polarity/negation accuracy;
- temporal-direction accuracy;
- absence-vs-contradiction accuracy;
- mixed-claim aggregation accuracy.

Hard safety gate:

```text
High-risk False-Support Rate = 0
```

---

## End-to-end S3

Only after S3a and S3b are separately measured should the complete pipeline be re-tested:

```text
free text
→ S3a extraction
→ S3b entailment
→ truth decision
```

A future untouched end-to-end set must be frozen only after both sub-stage implementations are fixed.

## Current evidence status

- v0.5.4 performs strongly on exposed end-to-end regression suites.
- v0.6 fresh end-to-end performance is 40.0% with 17.6% high-risk false support.
- The v0.6 traces contain numerous extraction misses and therefore justify independent S3a measurement.

The split is a diagnostic redesign, not a retroactive claim that S3b is already validated.
