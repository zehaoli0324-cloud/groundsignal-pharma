# Medical Knowledge Graph

> The graph is the platform's versioned truth substrate for evaluation, retrieval attribution and post-training data provenance.

## 1. Design principles

1. **Evidence-backed** — clinically important edges must link to one or more evidence passages.
2. **Versioned** — guidelines, labels and recommendations must preserve document version/date.
3. **Temporal** — changed recommendations are superseded, not silently overwritten.
4. **Patient-context aware** — case-specific facts are separate from general medical knowledge.
5. **Uncertainty preserving** — ASSOCIATED_WITH, MAY_SUPPORT and CONFIRMED_BY are not interchangeable.
6. **Observed vs inferred separated** — extracted facts, derived relations and hypotheses use different statuses.
7. **Evaluation-friendly** — a case can pre-register required nodes, required edges, forbidden edges and acceptable reasoning paths.

## 2. Node classes

### Patient/case nodes

- `CASE`
- `SYMPTOM`
- `SIGN`
- `LAB_RESULT`
- `VITAL`
- `IMAGING_FINDING`
- `PATHOLOGY_FINDING`
- `HISTORY_ITEM`
- `ALLERGY`

### Medical knowledge nodes

- `CONDITION`
- `MEDICATION`
- `DRUG_CLASS`
- `INTERACTION`
- `TEST`
- `PROCEDURE`
- `BIOMARKER`
- `RISK_FACTOR`
- `CONTRAINDICATION`
- `MONITORING_RULE`
- `GUIDELINE_RECOMMENDATION`
- `LABEL_RECOMMENDATION`

### Evidence nodes

- `DOCUMENT`
- `DOCUMENT_VERSION`
- `EVIDENCE_PASSAGE`
- `TABLE_OR_FIGURE`
- `TEMPORAL_EVENT`

## 3. Edge classes

### Patient-state edges

```text
CASE HAS_SYMPTOM SYMPTOM
CASE HAS_LAB LAB_RESULT
CASE HAS_FINDING IMAGING_FINDING
CASE TAKES MEDICATION
CASE HAS_HISTORY HISTORY_ITEM
```

### Clinical knowledge edges

```text
MEDICATION INDICATED_FOR CONDITION
MEDICATION CONTRAINDICATED_IN CONTRAINDICATION
MEDICATION INTERACTS_WITH MEDICATION
CONDITION SUGGESTED_BY FINDING
TEST EVALUATES CONDITION
GUIDELINE_RECOMMENDATION APPLIES_TO POPULATION_OR_CONTEXT
LABEL_RECOMMENDATION APPLIES_TO MEDICATION_OR_CONTEXT
```

### Evidence edges

```text
CLAIM_OR_RULE SUPPORTED_BY EVIDENCE_PASSAGE
EVIDENCE_PASSAGE LOCATED_IN DOCUMENT_VERSION
DOCUMENT_VERSION SUPERSEDES DOCUMENT_VERSION
EVIDENCE_PASSAGE CONTRADICTS EVIDENCE_PASSAGE
```

## 4. Relation status

Every edge uses one of:

- `OBSERVED` — directly present in the frozen case or source;
- `DERIVED` — deterministically/computationally derived from observed facts;
- `HYPOTHESIS` — plausible but not established;
- `DISPUTED` — conflicting evidence exists;
- `SUPERSEDED` — historically valid but no longer current;
- `UNKNOWN` — unresolved.

## 5. Minimal edge record

```yaml
edge_id: edge-med-0001
subject_id: medication:metformin
predicate: CONTRAINDICATED_IN
object_id: renal_rule:egfr_lt_30
status: OBSERVED
valid_from: 2026-07-01
valid_to: null
source_passage_ids:
  - dailymed-metformin-er-2026-07-sec2.2-p3
confidence: high
review_status: reviewed
```

## 6. Case-local graph

Each clinical case should instantiate a small case-local subgraph.

Example:

```text
CASE-001
├─ HAS_LAB → eGFR=27
├─ TAKES → metformin ER
└─ HAS_HISTORY → type 2 diabetes

metformin ER
└─ CONTRAINDICATED_IN → eGFR <30
       └─ SUPPORTED_BY → label passage 2.2-p3
```

Expected reasoning path:

```text
CASE-001 HAS_LAB eGFR=27
→ SATISFIES_THRESHOLD eGFR<30
→ metformin CONTRAINDICATED_IN eGFR<30
→ SUPPORTED_BY current label passage
```

Forbidden unsupported edge example:

```text
eGFR<30 → REQUIRES insulin
```

The graph therefore supports scoring of semantic behavior without requiring a single exact reference answer.

## 7. Graph truth vs ontology ambition

GroundSignal is not trying to build a complete medical ontology from scratch.

The practical priority is a **task-oriented evidence graph** that contains the entities and relations required to:

- answer and audit evaluation cases;
- evaluate retrieval;
- evaluate reasoning paths;
- detect unsupported claim escalation;
- preserve temporal changes;
- generate post-training examples with provenance.

External ontologies can later be mapped in where licensing and engineering permit, but they are not required for the first platform proof.

## 8. Knowledge graph coverage metrics

Track:

- evidence-backed edge ratio;
- reviewed-edge ratio;
- current-version coverage;
- orphan node rate;
- unresolved contradiction count;
- required case-path coverage;
- stale/superseded active-edge rate;
- entity normalization error rate.

## 9. Graph update trigger

A source update can trigger:

```text
new/updated document
→ passage diff
→ affected claims/edges
→ graph version update
→ identify affected case families
→ temporal regression run
```

This is the core mechanism behind GroundSignal LiveEval for medical models.
