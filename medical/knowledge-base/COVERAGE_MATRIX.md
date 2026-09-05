# Medical Knowledge Coverage Matrix v0.1

> Date: 2026-09-05
> Scale: **3 = strong prototype coverage; 2 = partial; 1 = sparse; 0 = essentially missing**.

This matrix measures **platform knowledge coverage**, not whether the model itself knows the content.

| Domain | Current | Evidence | Priority | What must be added |
|---|---:|---|---|---|
| Evidence provenance / temporal truth | 3 | paragraph/source/version framework + temporal cases | maintain | automated update/diff and stale-edge invalidation |
| Pharma company / pipeline / target / events | 3 within selected advanced-therapy areas | existing `pharma/` graph | P2 for clinical model | keep as specialist evidence track, do not over-expand first |
| Real user task design | 2 | 48 seed tasks, 12 P0 families / 60 controlled cases | P0 | validate against interviews/questionnaires and expand common workflows |
| Medication identity / normalization | 1 | mostly free-text names in current cases | P0 | ingredient, brand, strength, route, dose form, RxNorm mapping |
| Indications / labeled use | 2 selected drugs | label-backed cases + pharma assets | P0 | systematic indication + population + route/formulation scope |
| Contraindications / boxed warnings | 2 selected drugs | metformin/apixaban examples | P0 | high-risk drug classes + current label extraction |
| Renal impairment dosing | 2 selected | metformin family | P0 | dose/avoid/monitor rules across common medications |
| Hepatic impairment dosing | 0–1 | no systematic track | P0 | Child-Pugh / hepatic contraindication / dose rules from labels |
| Drug-drug interactions | 1–2 selected | apixaban + NSAID | P0 | label DDI + CYP/transporter-mediated interactions |
| Drug-food / supplement / herb interactions | 0 | no systematic coverage | P0/P1 | food/alcohol/grapefruit/St John's wort etc. where authoritative evidence exists |
| CYP / UGT metabolism | 0–1 | target graph is not metabolism graph | P0 | substrate/inhibitor/inducer relationships + effect direction + strength |
| Transporters | 0 | none systematic | P0 | P-gp/BCRP/OATP/OAT/OCT/MATE substrate/inhibitor relationships |
| PK / ADME | 0–1 | sparse drug facts | P0/P1 | absorption, bioavailability, Tmax, half-life, clearance, metabolites, route dependence |
| Pharmacodynamics / MOA / targets | 1–2 | selected targets in pharma track | P1 | drug→target→mechanism→effect with scope/evidence |
| Adverse reactions / serious toxicity | 1–2 selected | clinical safety rules + label snippets | P0 | serious AE, boxed warnings, DILI, bleeding, QT, respiratory depression, hypoglycemia etc. |
| Post-marketing safety signals | 1 | principles exist | P0 | FAERS signal objects with explicit non-causal semantics |
| Monitoring / TDM / labs | 1 | case-local labs | P0/P1 | monitoring frequency/threshold/source + TDM relationships |
| Pregnancy / lactation | 0 | seed questions only | P0 | current label/guideline passages; separate fertility/pregnancy/lactation |
| Pediatrics | 0–1 | seed tasks | P0/P1 | age/weight restrictions, formulation, dosing and contraindications |
| Geriatrics | 0–1 | scattered demographics | P1 | age-related risk, renal function, polypharmacy, anticholinergic/sedative risk |
| Pharmacogenomics | 0 | absent | P0/P1 | gene/allele/phenotype→PK/response/toxicity→management edges |
| Allergy / severe cutaneous reactions | 0–1 | generic safety concepts | P0 | allergy class cross-reactivity when supported; HLA-linked severe reaction examples |
| Toxicology / overdose | 0 | absent | P0/P1 | overdose signs, toxic dose only when official, poison/emergency escalation semantics |
| Antibiotic stewardship | 0 | absent | P1 | indication, spectrum, AWaRe, resistance context, duration only from guideline-specific cases |
| Triage / red flags | 2 limited | chest + neurologic P0 families | P0 | dyspnea, sepsis, GI bleed, anaphylaxis, hypoglycemia, overdose, pregnancy emergencies etc. |
| Lab interpretation | 2 limited | CBC + anemia + renal examples | P1 | electrolytes, liver, thyroid, coagulation, acid-base, cardiac biomarkers etc. |
| Imaging / pathology interpretation | 1–2 | indeterminate radiology case | P1 | more observation→interpretation→diagnosis boundaries and multimodal linkage |
| Disease / differential knowledge | 1–2 | anemia and AKI families | P1 | common symptom→differential→discriminating evidence graph |
| Guideline recommendations | 1–2 | temporal synthetic family + source policy | P0/P1 | versioned real guidelines/pathways across high-frequency topics |
| Trial evidence / cross-trial reasoning | 2 | EVIDENCE families + pharma track | maintain | systematic study-design metadata and effect estimates |
| China regulatory/clinical source coverage | 1 | NMPA/CDE/NHC appear in pharma methodology | P0 | formal source routing for CDE/NMPA/NHC and China-local labels/pathways |
| Terminology / interoperability | 0–1 | local node IDs only | P0/P1 | RxNorm for drugs; LOINC for labs; optional SNOMED mapping under license |
| Multimodal knowledge | 0 | schema-ready only | P2 | licensed/open image datasets + report linkage + modality provenance |

## Overall assessment

### What is already good enough to run P1 model evaluation?

Yes:

- evaluation architecture;
- controlled-case methodology;
- evidence provenance;
- safety gating;
- several real high-value domains.

### What is not yet good enough to call the platform medically comprehensive?

The knowledge backbone is too sparse in **pharmacology, metabolism, DDI, organ impairment, special populations, pharmacogenomics and broad high-risk medication safety**.

## Recommended expansion target before broad public benchmarking

Do not target “all medicine.” Target **coverage of the most consequential 80–120 medication/safety concepts and 30–50 high-frequency clinical workflows**, each represented by verified knowledge modules and controlled cases.

A reasonable first backbone target:

```text
30–50 common/high-risk active ingredients or classes
10–15 pharmacology / DDI mechanism modules
10 organ-function / special-population rule families
10–15 emergency/safety syndromes
15–20 common lab/report/differential modules
10 current guideline/pathway families
```

This produces breadth without turning the project into an unmaintainable encyclopedia.
