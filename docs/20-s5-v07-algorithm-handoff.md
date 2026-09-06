# Algorithm Handoff — S5 v0.7 Semantic Lineage Detection

> Handoff status: READY  
> Evidence source: S5 v0.7 independent fresh first observation  
> Repair scope for algorithm team: **F25 + F26 only**. F24/F27 remain deterministic platform/eval-infrastructure work.

## 1. Objective

Build a reusable semantic-lineage detector that can identify whether a candidate training/source record is derived from protected benchmark/held-out content after paraphrase, field-level edits, wrapper changes, or partial fragment reuse.

The goal is **not** to recognize the two exposed v0.7 fixtures. The goal is to produce a generic contamination signal that can generalize to unseen transformations.

## 2. Current exposed failures

### F25 — paraphrased heldout-derived ordinary laundering

Current exact `semantic_core_sha256` changes when wording changes, even when the underlying case remains benchmark-derived.

### F26 — partial heldout fragment reuse

A whole-record hash cannot detect reuse of only `evidence_snapshot`, `expected_behavior`, `graph_eval`, `safety`, scoring rules, prompt fragments, or other protected substructures inside a new wrapper.

## 3. Allowed and prohibited data

Allowed for algorithm development:

- S5 development/dev cases;
- all already exposed S5 v0.2–v0.7 fixtures after their first observation;
- synthetic paraphrase/partial-reuse variants generated only from development/exposed material;
- independently curated ordinary-source negatives.

Prohibited:

- any next-round hidden fresh suite;
- any held-out/regression content that has not already been exposed by a completed first observation;
- gold-review answers or hidden evaluator metadata as training features.

If a hidden fresh case becomes visible to the repair implementer, that case loses fresh status.

## 4. Required interface

```json
{
  "candidate_id": "candidate-123",
  "reference_snapshot": "protected-benchmark-vX",
  "nearest_reference_id": "case-456",
  "record_similarity": 0.0,
  "field_matches": [
    {"field": "evidence_snapshot", "similarity": 0.0, "matched_reference": "case-456"}
  ],
  "span_matches": [
    {"candidate_path": "interaction.prompt", "reference_path": "interaction.prompt", "similarity": 0.0}
  ],
  "decision": "ALLOW|REVIEW|BLOCK",
  "method_version": "lineage-detector-vX"
}
```

Detector output must be explainable enough for a reviewer to see **which reference and which field/span caused the alert**. A single opaque similarity score is insufficient for hard-gate use.

## 5. Candidate algorithm families to compare

The algorithm team should benchmark at least one method from each level rather than jump directly to a large model:

1. lexical near-duplicate baseline: shingling + MinHash/SimHash or equivalent;
2. embedding similarity: record-level and field-level vector similarity;
3. learned pair classifier or cross-encoder（交叉编码器：同时读取 candidate/reference 并直接输出两者关系分数）;
4. hybrid detector: deterministic exact fingerprints + lexical + semantic + field/span evidence.

The exposed v0.7 cases are regression examples only; model/threshold selection must use development data.

## 6. Development metrics

Before implementation freeze, report at minimum:

```text
record-level contamination recall
field-level contamination recall
ordinary-source false-block rate
review rate
precision / recall by transformation family
threshold calibration curve
latency and index size
```

Suggested engineering target for the first candidate—not a release claim—is high recall on deliberately contaminated development variants while keeping clean ordinary-source false blocking low enough for human review. Final thresholds are set jointly after calibration and are not chosen on the next hidden fresh suite.

## 7. Required ablations

Return ablations for:

```text
exact fingerprint only
+ lexical near-duplicate
+ embedding
+ field-level matching
+ learned/cross-encoder layer (if used)
```

This is required so the project can distinguish real semantic-lineage gains from a detector that simply memorizes exposed fixtures.

## 8. Algorithm deliverables

```text
implementation commit / PR
model or index version
reproducible build + inference commands
protected-reference index manifest
threshold configuration
baseline-vs-candidate metrics
per-transformation error breakdown
ablation results
latency / memory / storage delta
known failure modes
```

No next-fresh data or labels should appear in the training/index manifest.

## 9. Eval-side responsibilities after handoff

Eval owner will:

1. keep F25/F26 as exposed regression;
2. review detector traceability and false-block behavior;
3. freeze the integrated implementation;
4. only after freeze author new hidden lineage families not shown to the algorithm implementer;
5. run first observation and preserve it immutably;
6. decide whether S5 has enough repeated fresh evidence for bounded structural release.

## 10. Definition of Done for this handoff

Algorithm work is ready for freeze when the exposed regression is blocked through the generic detector, clean development sources remain usable, metrics/ablation are reproducible, and no hidden fresh material has been used. This still does not equal S5 release; release requires a new post-freeze independent fresh evaluation plus the separate gold-review gate.
