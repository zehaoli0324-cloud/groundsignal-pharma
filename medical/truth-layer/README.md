# Medical Truth Layer v0.1

## Why this layer exists

A URL is provenance, not entailment.

For medical model development, GroundSignal must know **which exact passage supports which exact claim, at what time, under what scope and with what evidence role**.

The target unit is therefore an `evidence_passage`, not a bare source URL.

```text
document
→ section / table / paragraph
→ evidence passage
→ normalized proposition / claim
→ support role
→ temporal validity
→ contradiction / supersession links
→ tasks and model answers that consume the passage
```

## Source families

Initial source families:

1. `GUIDELINE` — professional guideline / consensus / official care pathway;
2. `DRUG_LABEL` — regulator-approved prescribing information / label;
3. `REGULATORY` — FDA/NMPA/EMA/CDE and equivalent regulatory documents;
4. `TRIAL_REGISTRY` — ClinicalTrials or equivalent registry facts;
5. `PEER_REVIEWED` — peer-reviewed primary study;
6. `SYSTEMATIC_REVIEW` — systematic review / meta-analysis;
7. `REFERENCE` — professional reference material with version/date;
8. `PHARMA_DISCLOSURE` — company disclosures, useful under explicit scope;
9. `MEDIA_LEAD` — discovery lead only, not production truth by itself.

Source family is not evidence strength. A high-quality journal article may still provide only exploratory evidence for a particular claim.

## Evidence-passage requirements

Each passage must preserve:

- stable `passage_id`;
- `source_id` and canonical URL/identifier;
- publisher / organization;
- document title and version/date;
- section, paragraph, table/figure locator where available;
- normalized passage text or proposition;
- evidence role relative to a claim;
- population / indication / intervention / outcome scope when relevant;
- `valid_from` / `valid_to` or snapshot date;
- source hierarchy;
- contradiction and supersession links;
- license/use note where relevant;
- extraction/reviewer metadata.

## Evidence roles

`DIRECT_SUPPORT`
: The passage directly entails the scoped claim.

`PARTIAL_SUPPORT`
: Supports only part of the claim or requires a narrower scope.

`CONTRADICTS`
: Provides evidence against the claim under a comparable scope.

`CONTEXT_ONLY`
: Relevant background but does not establish the claim.

`DOES_NOT_SUPPORT`
: A cited passage exists but does not entail the claim.

`SUPERSEDES`
: A newer authoritative passage changes the valid current state.

## Temporal truth

Medical truth can change. Do not overwrite prior state silently.

Example state sequence:

```text
T1 trial registered
→ T2 primary endpoint reported
→ T3 regulatory application accepted
→ T4 approval / label established
→ T5 label or guideline updated
```

Each state remains queryable with its own timestamp. A model evaluated at T2 should not receive T5 truth unless the task explicitly tests future leakage.

## Contradiction model

Contradiction is represented explicitly rather than resolved by deleting one side.

```yaml
claim_id: c-001
passages:
  - passage_id: p-old
    role: DIRECT_SUPPORT
    valid_to: 2026-01-12
  - passage_id: p-new
    role: SUPERSEDES
    valid_from: 2026-01-13
```

For scientific disagreement without clean supersession, both passages can remain valid with different scopes or uncertainty states.

## Ingestion acceptance checks

A passage cannot become production truth if any required check fails:

- source identity unresolved;
- date/version unavailable when temporally material;
- claim scope broader than the passage;
- paragraph/table locator missing when recoverable;
- passage is only a search snippet or generated summary;
- copyright/license handling is unclear for stored verbatim text;
- patient-identifying information is present.

When full copyrighted text should not be stored, preserve a normalized proposition plus locator and source identifier rather than copying large passages.

## Evaluation hooks

The truth layer directly enables:

- citation entailment;
- evidence sufficiency;
- source hierarchy;
- contradiction recall;
- temporal validity / stale-claim rate;
- RAG evidence recall@k;
- answer-to-evidence attribution;
- overclaim detection.

See `medical/schemas/evidence-passage.schema.json`.
