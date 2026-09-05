# S3b Structured Entailment Held-out v0.2 — First-run Report

> Date: 2026-09-05  
> Sub-stage: S3b — Structured Proposition Entailment  
> Entailment engine: `s3-compositional-proposition-v0.5.4`  
> Engine commit frozen before held-out: `98923941b40ead8a5ed983862fe9755efb805631`  
> Held-out freeze commit: `65938e5b4ed658c8f258c6fba233eb2b4cdff93c`  
> First-run workflow commit: `af71d3a2ce1fd0d64f556370cd00fadc15ea97fa`  
> GitHub Actions run: `33975428903`  
> Artifact: `s3b-v02-heldout-first-run` / `9972162823`

## Status

**FAIL — immutable first-run structured-entailment evidence.**

This 36-item set was created only after the S3b v0.1 runner/evaluator and the existing v0.5.4 entailment implementation were fixed. Free-text parsing is bypassed. The result therefore isolates proposition-level truth logic more cleanly than end-to-end S3.

## Release criteria

```text
Relation Accuracy >= 90%
High-risk False-Support Rate = 0
```

## First-run metrics

```text
items                                      36
Relation Accuracy                        88.9%
high-risk negative items                   20
High-risk False-Support Count                2
High-risk False-Support Rate             10.0%
Release Gate                              FAIL
```

Gold distribution:

```text
DIRECT_SUPPORT                            10
CONTRADICTS                                8
DOES_NOT_SUPPORT                          10
PARTIAL_SUPPORT                            8
```

Confusion:

```text
DIRECT_SUPPORT    -> DIRECT_SUPPORT         9
CONTRADICTS       -> CONTRADICTS             7
DOES_NOT_SUPPORT  -> DOES_NOT_SUPPORT        8
PARTIAL_SUPPORT   -> PARTIAL_SUPPORT         8
DOES_NOT_SUPPORT  -> DIRECT_SUPPORT          2
DIRECT_SUPPORT    -> DOES_NOT_SUPPORT        1
CONTRADICTS       -> DOES_NOT_SUPPORT        1
```

## Critical false-support failures

### S3B2-007 — initiation population scope ignored

Evidence proposition:

```text
INITIATION_NOT_RECOMMENDED
population = new_or_initiating_user
eGFR 30–45
```

Candidate proposition:

```text
INITIATION_NOT_RECOMMENDED
population = existing_user
eGFR = 40
```

```text
Gold:       DOES_NOT_SUPPORT
Prediction: DIRECT_SUPPORT
```

Failure class: `POPULATION_SCOPE_ERROR`.

The engine compared action + eGFR but ignored population/scope.

### S3B2-008 — reassessment population scope ignored

Evidence proposition:

```text
REASSESS_BENEFIT_RISK
population = existing_user
eGFR <45
```

Candidate proposition:

```text
REASSESS_BENEFIT_RISK
population = new_or_initiating_user
eGFR = 40
```

```text
Gold:       DOES_NOT_SUPPORT
Prediction: DIRECT_SUPPORT
```

Failure class: `POPULATION_SCOPE_ERROR`.

This independently confirms that population is currently decorative metadata rather than part of entailment semantics.

## Non-false-support logic failures

### S3B2-009 — same negative action not recognized

Evidence and candidate both contain:

```text
CONTRAINDICATED polarity=NEGATIVE
```

Gold is `DIRECT_SUPPORT`, but the engine returns `DOES_NOT_SUPPORT`. The action-specific path handles positive scoped rules better than exact negative rules.

### S3B2-018 — inverse supersession direction

Evidence:

```text
Guideline H SUPERSEDES Guideline G
```

Candidate:

```text
Guideline G SUPERSEDES Guideline H
```

Gold is `CONTRADICTS`; prediction is `DOES_NOT_SUPPORT`.

The engine currently performs exact directed-edge matching but lacks an explicit anti-symmetry rule for `SUPERSEDES`.

## Architectural interpretation

The split-stage picture is now more precise:

```text
S3a v0.1
critical proposition recall = 43.75%   FAIL

S3b v0.1
12/12 = 100%, HFSR 0                    preliminary PASS

S3b v0.2 fresh
36 items = 88.9%, HFSR 10.0%            FAIL
```

Therefore:

- S3a remains the larger bottleneck;
- S3b is **not** fully solved;
- S3b failures are much narrower and structurally interpretable: population scope, negative-action equivalence, and inverse temporal relation.

## Next S3b changes

A new S3b development version may use v0.2 only as exposed regression evidence and should add:

1. population/scope compatibility as a first-class entailment constraint;
2. exact same-polarity negative action support;
3. anti-symmetry for directional predicates such as `SUPERSEDES`;
4. regression coverage for the original S3b v0.1 set and all 36 exposed v0.2 items.

Any claim of improved S3b generalization after tuning requires another newly frozen structured held-out.
