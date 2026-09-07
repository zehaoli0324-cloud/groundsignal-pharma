# Algorithm Handoff — S5 v0.7 Semantic Lineage Detection

> Handoff status: **v0.9.1 EXPOSED REPAIR PASS; v0.9 FRESH FAIL PRESERVED**
> Evidence source: S5 v0.7 independent fresh first observation  
> Repair scope for algorithm team: **F25 + F26 only**. F24/F27 remain deterministic platform/eval-infrastructure work.

## v0.7.3 checkpoint

The handoff's development Definition of Done is now met on public/exposed data. The selected
`s5-lineage-exclusive-anchor-v0.7.3` candidate was calibrated with 30 protected references,
45 allowed-dev references, 163 attributable contamination variants and 62 clean/shared hard
negatives. Development recall was 163/163 with 0/62 false blocks; a family-grouped learned-pair
comparator reached 158/163 recall with 0/62 false blocks. p95 runtime was 158.537 ms/candidate
against 30 protected references on the recorded host.

This checkpoint is not fresh evidence and does not establish S5 release. After commit freeze,
the eval owner must create a new unseen lineage suite before any bounded-release claim.

## v0.8 post-freeze result

The required post-freeze suite was created only after v0.7.3 merge commit
`62b791cef47d1f5c7296220557db970d618b7bcf`. Its immutable first observation is `FAIL`:

```text
F28 cross-language protected lineage       ALLOW
F29 semantic abstraction                   BLOCK
F30 cross-field flattening                  BLOCK
F31 multi-protected-source mosaic          REVIEW
clean English same-domain                  REVIEW
clean Chinese same-domain                   ALLOW
```

The next algorithm round may now use F28/F31 as exposed data. It must address multilingual semantic
equivalence and how `REVIEW` is resolved at the export boundary, while expanding clean multilingual
controls. A blanket REVIEW→BLOCK conversion is disallowed because a frozen clean control already
entered review. No next fresh suite may be used during repair or threshold selection.

## v0.8.1 repair checkpoint

The current candidate adds bilingual reasoning concepts, protected-exclusive hyphenated identifiers,
multi-reference mosaic aggregation and stricter evidence for `REVIEW`. It blocks all four exposed
v0.8 attacks, allows both v0.8 clean controls, and preserves the v0.7.3 development matrix at
163/163 contamination blocks with 0/62 false blocks and 0/62 clean reviews.

The broader follow-up matrix adds 12 English-to-Chinese/Japanese/Spanish contaminated translations,
6 noisy two-reference mosaics and 18 multilingual clean near-neighbours. All 18 contaminated cases
block, all 6 mosaics carry the explicit mosaic reason, and all 18 clean cases allow. The matrix also
removed concept-only blocking unless case-specific identity or a distinctive numeric constellation is
present. This satisfies the development calibration checkpoint and makes the candidate ready for an
explicit freeze decision. It remains synthetic exposed evidence, not S5 release evidence.

The pre-freeze attestation at `medical/stage-evals/S5/freeze-readiness-v0.8.1.json` pins 22 runtime,
compatibility and evidence artifacts with both Git blob SHA-1 and SHA-256. Its historical fields stay
unchanged. PR #4 was explicitly approved and squash merged as
`b5dffbe366904a46d3b6a44172a4f1626daa8924`; the separate canonical receipt materializes the
freeze without rewriting the pre-freeze record.

`scripts/check_s5_next_fresh_admission.py` adds a second authority boundary. Before any v0.9 fresh
asset may exist, it requires a canonical freeze receipt, verifies that the named commit is an ancestor
of `origin/main`, and compares all 22 pinned blobs against that commit. Once fresh assets exist, their
protocol must also name the same freeze commit and state that authoring occurred afterward. The
current decision is `ALLOW_AFTER_VERIFIED_FREEZE`, with 18 protocol-valid v0.9 JSON assets. This
confirms authoring chronology only; the separate first observation is FAIL and release remains blocked.

`scripts/materialize_s5_v081_freeze_receipt.py` is the only documented receipt path. It requires the
exact canonical `origin/main` tip, a non-placeholder `user-approval:` reference and an unchanged
22-file candidate. The resulting receipt asserts neither fresh evidence nor gold approval and keeps
S5 release plus S6 automatic trust blocked. The materialized receipt validates all 22 candidate and
9 control-plane pins at the canonical merge commit.

The candidate-byte attestation and the control plane are intentionally separate. The former pins 22
algorithm, dependency and evidence artifacts; `control-plane-readiness-v0.8.1.json` pins 9 files that
authorize and verify freeze/fresh transitions. Its verifier checks both content hashes and 10 state
boundaries. That immutable pre-freeze manifest still records `control_plane_frozen=false`; the
separate canonical receipt now records the completed transition.

Receipt contract v0.3 joins the independent candidate and control-plane checks only at freeze time.
The same canonical `main` tip must contain all 22 candidate and all 9 control-plane pins. Missing or
incorrect control-plane hashes/counts, legacy receipt schemas and drifted gate bytes are rejected.
The freeze commit must also predate both the canonical receipt and the v0.9 fresh tree; either one
already present at that commit is a chronology failure.
The receipt now exists on a post-freeze branch and changes only authoring admission. It creates no
fresh, gold, release or S6 trust claim.

The authorized v0.9 suite was then authored in a separate commit and observed exactly once. It failed
on F32 (a Korean, identifier-free translation was allowed) and on a clean numeric near-neighbour (a
glucose/meal-timing case was blocked as if it were the protected ALT/specimen-handling case). Four
other contamination attacks and three other clean controls passed. The result isolates both an
unseen-script recall gap and a typed-clinical-role precision gap; it does not authorize threshold
tuning against the fresh suite or any S5/S6 release claim.

## v0.9.1 repair checkpoint

The candidate adds an inspectable Korean/Hangul concept layer for the exposed F32 translation and a
typed measurement-role precision guard for the exposed numeric clean neighbour. Typed-role mismatch
can downgrade only a dense-anchor-only block and cannot override identifier, exact-field or near-field
lineage evidence. The candidate blocks all 5 exposed v0.9 attacks, allows all 4 exposed v0.9 clean
controls, and preserves v0.7.3, v0.8 and v0.8.1 historical matrices without regression.

This is exposed repair evidence. The v0.9 first-observation blob remains unchanged and records FAIL;
`gold_approved=false`, S5 bounded release is not established and S6 automatic trust remains blocked.
A new suite may be authored only after this candidate is reviewed and explicitly frozen.

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
