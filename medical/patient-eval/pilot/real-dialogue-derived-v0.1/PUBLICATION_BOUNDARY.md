# Publication boundary and privacy controls

## Public-release principle

This release uses **data minimisation**: publish only what is required to reproduce the evaluation mechanics. The public package contains synthetic or generalised scenario text, not original patient utterances.

## Excluded from the repository

The following materials must remain in ignored local storage or another access-controlled location:

1. Original dialogue corpora and exact-source replay contexts.
2. Completed candidate-review HTML/JSON files and any reviewer-identifying metadata.
3. Exact evidence spans, original turn numbers, source dialogue identifiers, candidate identifiers, and source-review hashes.
4. Raw redaction strings, addresses, names, location combinations, appointment details, or other direct/quasi-identifiers.
5. Real model transcripts, local run logs, screenshots, exports, and adjudication notes unless separately deidentified and approved.
6. Any file that sets `formal_approval`, `clinical_gold`, or an equivalent trust flag to true without an external approval process.

## Public derivatives

Public case text is paraphrased and uses new `GS-PUB-*` identifiers. These derivatives preserve evaluation intent but are not guaranteed to be semantically or statistically identical to the private source cases. Results from the public synthetic suite and private exact-source suite must be labelled separately.

## Release gate

Run:

```bash
python scripts/validate_public_release.py .
```

The validator blocks common direct identifiers, forbidden provenance keys, original candidate identifiers, raw review filenames, local run logs, and unexpected file types.

## Clinical boundary

This package is an evaluation-development artifact. It is not a diagnostic system, clinical guideline, medical device, or clinical gold standard. Clinical scoring requires independent professional review and adjudication.
