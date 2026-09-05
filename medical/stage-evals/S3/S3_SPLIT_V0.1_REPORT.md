# S3 Split Evaluation v0.1 — Extraction vs Structured Entailment

> Date: 2026-09-05  
> Workflow run: `33975075580`  
> Artifact: `s3-split-eval-v01` / `9972063521`

## Purpose

The v0.6 untouched end-to-end failure showed that a single S3 score conflated free-text semantic parsing with downstream truth logic. This evaluation measures the two layers separately for the first time.

---

## S3a — Semantic Proposition Extraction

Input: free-text evidence or candidate claim.  
Output: canonical atomic propositions.

Current extractor: `s3-compositional-proposition-v0.5.4` parsing path.

### Metrics

```text
items                                      12
gold propositions                           21
predicted propositions                      18
true-positive propositions                  10
precision                                55.6%
recall                                   47.6%
F1                                       51.3%
critical-proposition recall              43.75%
polarity accuracy on structural matches   90.9%  (10/11)
release gate                              FAIL
```

The low critical-proposition recall is the most important result. It means more than half of the safety-relevant gold propositions were not recovered in the required canonical form.

Representative extraction failures:

1. `does not constitute a contraindication` → polarity flipped to positive contraindication;
2. spontaneous-report `signal detection + causal limitation` → propositions missing;
3. `no result establishes endpoint was met` → false positive endpoint-achievement proposition;
4. `Guideline H replaces G` → supersession/currentness propositions missing;
5. randomized trial favors Q + current guideline recommends P → canonical temporal proposition mismatch;
6. pathology `finding X is benign` → category proposition missing;
7. biomarker `not associated` → generic positive association proposition.

### Interpretation

S3a is currently the dominant end-to-end bottleneck.

The parser has high polarity accuracy **conditional on finding the correct structural proposition**, but critical proposition recall is only 43.75%. This explains why downstream logic can look strong on exposed phrasing yet collapse on fresh language.

---

## S3b — Structured Proposition Entailment

Input: manually supplied canonical evidence and candidate propositions.  
The free-text parser is bypassed completely.

### Metrics

```text
items                                      12
relation accuracy                       100.0%
high-risk negative items                   10
high-risk false-support count                0
high-risk false-support rate              0.0%
release gate                              PASS
```

Confusion:

```text
DIRECT_SUPPORT    -> DIRECT_SUPPORT         1
CONTRADICTS       -> CONTRADICTS             7
DOES_NOT_SUPPORT  -> DOES_NOT_SUPPORT        1
PARTIAL_SUPPORT   -> PARTIAL_SUPPORT         3
```

The initial structured set covers:

- eGFR threshold algebra;
- reassess vs discontinue action scope;
- explicit contraindication negation;
- causal polarity;
- incidence polarity;
- guideline supersession/currentness;
- absence of management rule;
- PGx association + unsafe management extension;
- mutually-exclusive diagnostic categories;
- mixed-claim partial support;
- subgroup-ranking absence.

### Important limitation

This is a **12-item initial isolated diagnostic**, not sufficient evidence that S3b is universally solved. The result shows that, on the current targeted proposition-level slice, downstream truth logic works when supplied the intended canonical structure.

---

## Root-cause localization

The combined result is:

```text
S3a semantic extraction                 FAIL
critical-proposition recall            43.75%

S3b structured entailment               PASS
relation accuracy                      100.0%
high-risk false support                  0.0%
```

Therefore the immediate development priority changes from:

```text
add more end-to-end verifier rules
```

to:

```text
improve S3a semantic extraction
→ keep S3b frozen behind regression tests
→ create a new S3a held-out after extractor redesign
→ only later return to a new end-to-end S3 held-out
```

## Architectural implication

A production S3 should not pretend that a small regex-style parser is a general natural-language understanding layer.

The preferred architecture is now:

```text
Free text
→ semantic proposition extractor
   - structured output schema
   - entity / predicate normalization
   - explicit negation and scope
   - condition binding
   - confidence / abstention
→ deterministic S3b truth engine
→ optional expert review for high-risk unresolved propositions
```

The current deterministic extractor remains a useful lower bound and regression oracle for known high-risk structures, but it should not be treated as the final semantic parser.
