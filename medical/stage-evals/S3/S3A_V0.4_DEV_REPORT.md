# S3a v0.4 Semantic-Frame Development Report

> S3a = Semantic Proposition Extraction（语义命题抽取）  
> Version: `s3a-semantic-frame-v0.4.0`  
> Implementation commit: `4cef42e749f0f53dc7de2e8bae77e640640ddcf6`  
> Regression workflow: `33979442330`  
> Status: **DEVELOPMENT REGRESSION PASS / FRESH VALIDATION PENDING**

## 1. Why v0.4 exists

Fresh S3a v0.3 rejected the previous phrase-normalization architecture:

```text
exposed v0.1/v0.2 regression = 100%
fresh v0.3 F1               = 30.77%
fresh critical recall       = 17.86%
```

The failure pattern showed that direct phrase/synonym normalization was not a reliable semantic extraction strategy.

v0.4 therefore changes the internal representation rather than adding another flat layer of case-specific rewrites.

## 2. Architecture

```text
free text
→ clause segmentation
→ semantic event / relation frames
→ subject/object argument binding
→ population/use-state binding
→ numeric condition binding
→ polarity + modality
→ canonical proposition compilation
→ unresolved-critical-content abstention
```

Each emitted proposition is now traceable to an intermediate `semantic_frames` record containing:

```text
event_type
subject
object
polarity
conditions
population
modality
confidence
source_span
```

The centralized semantic grammar lives in:

- `medical/configs/s3a-semantic-frame-v0.4.json`

The frame extractor lives in:

- `scripts/s3a_semantic_frame_extractor_v04.py`

This separates lexical cues from canonical proposition emission and makes role, relation, argument, polarity and condition binding independently inspectable.

## 3. Evaluation protocol

No new fresh held-out was created in this version.

Reason: v0.4 is an architecture-development checkpoint. The previously fresh v0.1/v0.2/v0.3 suites are now exposed regression data and are used only to verify that the architecture can represent all already-observed failure families without regression.

Evaluator reused:

- `scripts/eval_s3a_proposition_extraction_v02.py`

Regression gates:

```text
F1 >= 90%
Critical Proposition Recall >= 95%
Polarity Accuracy >= 95%
Population Accuracy >= 95%
Condition Binding Accuracy >= 95%
```

The workflow additionally checks that every prediction includes the semantic-frame trace contract.

## 4. CI results

GitHub Actions workflow `33979442330` completed successfully.

### Exposed v0.1

```text
Gold propositions                    21
Predicted propositions               21
True positives                       21
Precision                         100%
Recall                            100%
F1                                100%
Critical Proposition Recall       100%
Polarity Accuracy                 100%
Condition Binding Accuracy        100%
Release gate                     PASS
```

Population scoring is disabled in the historical v0.1 suite.

### Exposed v0.2

```text
Gold propositions                    30
Predicted propositions               30
True positives                       30
Precision                         100%
Recall                            100%
F1                                100%
Critical Proposition Recall       100%
Polarity Accuracy                 100%
Population Accuracy               100%
Condition Binding Accuracy        100%
Release gate                     PASS
```

### Exposed v0.3

```text
Gold propositions                    39
Predicted propositions               39
True positives                       39
Precision                         100%
Recall                            100%
F1                                100%
Critical Proposition Recall       100%
Polarity Accuracy                 100%
Population Accuracy               100%
Condition Binding Accuracy        100%
Release gate                     PASS
```

The frame/proposition trace contract also passed.

The general repository `medical-development-ci` workflow for the same implementation commit completed successfully.

## 5. Interpretation

These scores are **not fresh evidence**.

They establish only that the new architecture:

1. preserves all known S3a capabilities;
2. can represent the v0.2/v0.3 failure families through explicit semantic frames;
3. makes population, polarity and numeric-condition binding inspectable;
4. removes the previous direct `phrase → proposition` coupling;
5. is stable under repository CI.

The v0.3 suite is exposed and must never be re-labelled as fresh after this run.

## 6. Release decision

```text
S3a v0.4 exposed regression = PASS
S3a v0.4 fresh validation   = NOT RUN
S3a release status          = HARD FAIL / BLOCKED
S3b release status          = CONDITIONAL PASS
End-to-end S3               = HARD FAIL
```

Automatic free-text → KG truth insertion remains blocked.

## 7. Next required checkpoint

Freeze a brand-new S3a held-out only after v0.4 is considered implementation-frozen.

The next fresh suite should deliberately test semantic generalization beyond all exposed lexical families, including:

- unseen event verbs with stable roles;
- long-distance negation and modality;
- multiple propositions sharing one numeric condition;
- competing populations/use states in the same passage;
- mixed evidence-strength statements;
- argument-order inversions;
- conjunction/disjunction scope;
- irrelevant distractor clauses;
- source-language variants that preserve the same canonical semantics.

If v0.4 fails that fresh suite, preserve the first result and diagnose frame-level failure before changing the extractor.
