# S3b Scope Semantics — Exact Domain vs Sufficient Condition

## Problem

A structured proposition such as:

```text
CONTRAINDICATED when eGFR <30
```

is still ambiguous unless the truth layer records whether `<30` is:

1. the **complete applicability domain** of that rule; or
2. merely a **sufficient condition** stated by the available evidence.

Without this distinction, the same proposition cannot determine whether a claim at eGFR 30 is contradicted or merely unsupported.

## `condition_semantics`

Every condition-bearing proposition may carry:

```text
EXACT_DOMAIN
SUFFICIENT_ONLY
```

### EXACT_DOMAIN

The condition exhaustively defines the proposition on that decision dimension.

Example:

```text
CONTRAINDICATED
condition: eGFR <30
condition_semantics: EXACT_DOMAIN
```

Then:

```text
eGFR 29 → proposition supported
eGFR 30 → proposition contradicted
eGFR 40 → proposition contradicted
```

This should only be used when the source/rule representation is intentionally closed for that dimension.

### SUFFICIENT_ONLY

The source supports the proposition inside the condition but does not assert the complement.

Example:

```text
REASSESS_BENEFIT_RISK
condition: eGFR <45
condition_semantics: SUFFICIENT_ONLY
```

Then:

```text
eGFR 44 → proposition supported
eGFR 45 → unsupported, not contradicted
eGFR 50 → unsupported, not contradicted
```

## Why this matters medically

Medical evidence frequently mixes:

- explicit exhaustive thresholds;
- sufficient risk triggers;
- incomplete excerpts;
- recommendations whose complements are not logically stated.

Treating every condition as closed-world creates false contradictions. Treating every condition as open-world fails to reject claims that directly cross an explicit safety boundary.

## Interaction with population scope

Condition domain and population scope are independent constraints.

```text
population = existing_user
condition = eGFR <45
```

cannot support a candidate claim for `new_or_initiating_user`, even if the numeric condition matches.

Evidence with `population=null` is interpreted as population-unrestricted. Population-specific evidence cannot support a broader candidate claim with `population=null`.

## Backward compatibility

Historical propositions without `condition_semantics` remain unchanged and are interpreted conservatively as `SUFFICIENT_ONLY` by the new S3b engine unless an existing regression rule explicitly provides stronger semantics.

Fresh S3b held-outs after this design must specify `condition_semantics` for decision-critical conditional rules.
