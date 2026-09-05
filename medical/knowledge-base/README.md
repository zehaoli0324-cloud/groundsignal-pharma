# GroundSignal Medical Knowledge Backbone

> Goal: build a **task-oriented, evidence-grounded medical knowledge backbone** for model evaluation, RAG/Agent attribution and post-training provenance.

This module does **not** attempt to reproduce an encyclopedic medical knowledge base. The platform should instead guarantee high-quality coverage of knowledge that materially changes answers, safety decisions, retrieval behavior or regression results.

## Current audit conclusion

The platform architecture is mature enough for evaluation, but the medical knowledge itself is **not comprehensive yet**.

Current strengths:

- evidence provenance and temporal truth;
- selected drug-label rules;
- selected medication-safety and triage controlled cases;
- clinical-reasoning/report/evidence-comparison case families;
- pharma entities, pipelines, targets, regulatory events and evidence audit;
- held-out and regression case design.

Current weak areas:

- systematic pharmacology / mechanism-of-action knowledge;
- PK/ADME, CYP enzymes and transporter relationships;
- broad drug-drug / drug-food / drug-supplement interaction coverage;
- renal/hepatic impairment dosing rules beyond a few examples;
- pregnancy, lactation, pediatrics and geriatrics;
- pharmacogenomics;
- monitoring / therapeutic drug monitoring;
- high-risk toxicity syndromes and overdose;
- antibiotic stewardship and resistance-related medication knowledge;
- administration, missed-dose and formulation-specific rules;
- normalization across ingredient / brand / dose form / route;
- broad guideline coverage across common clinical workflows.

The target is therefore a **Medical Knowledge Backbone**, not a full ontology dump.

## Backbone domains

1. Drug identity and normalization
2. Indication and labeled use
3. Contraindications / boxed warnings / precautions
4. Dose / route / formulation / administration rules
5. Renal and hepatic impairment
6. Drug-drug / drug-food / drug-supplement interactions
7. PK / ADME / metabolites
8. CYP / UGT / transporter substrate-inhibitor-inducer relationships
9. Pharmacodynamics / mechanism / targets
10. Adverse reactions / serious toxicity / safety communications
11. Monitoring / laboratory / therapeutic drug monitoring
12. Pregnancy / lactation / pediatrics / geriatrics
13. Pharmacogenomics
14. Clinical guideline / pathway recommendations
15. Emergency / triage / red-flag rules
16. Trial / literature / evidence hierarchy / temporality

See:

- `COVERAGE_MATRIX.md`
- `SOURCE_REGISTRY.json`
- `SEARCH_AND_VERIFICATION_PROTOCOL.md`
- `../knowledge-graph/PHARMACOLOGY_EXTENSION.md`

## Knowledge is not accepted merely because it is retrievable

Every production-grade claim should preserve:

```text
normalized subject/object
claim type
population/context
route/formulation/dose if relevant
source
source version/date
section/paragraph/table locator
evidence role
valid_from / valid_to
contradiction / supersession state
review status
```

High-risk clinical claims should never be promoted from a weak source when an authoritative primary source exists.

## Coverage strategy

### P0 — safety-critical backbone

Prioritize:

- common high-risk medications;
- contraindications / boxed warnings;
- renal/hepatic dosing boundaries;
- clinically important DDI;
- CYP/transporter rules;
- anticoagulation / bleeding;
- QT prolongation / arrhythmia;
- CNS/respiratory depression;
- serotonergic toxicity;
- hypoglycemia;
- nephrotoxicity / hepatotoxicity;
- severe cutaneous reactions / allergy;
- pregnancy / lactation / pediatric restrictions;
- current guideline/label supersession.

### P1 — common clinical workflows

Expand common disease / symptom / lab / medication questions that drive user traffic and clinician workflows.

### P2 — specialist depth

Oncology, immunology, rare disease, complex pharmacogenomics, advanced therapeutics and multimodal specialist reasoning.

## Key design principle

> A broad but weak medical graph is less useful than a smaller graph where every safety-critical edge has known scope, evidence and temporal validity.
