# Medical Knowledge Search & Verification Protocol v0.1

> Purpose: convert a medical question or graph gap into a **versioned, scope-preserving, evidence-backed claim**, suitable for evaluation/RAG/post-training.

## 0. First classify the question

Every query must be routed before retrieval.

| Intent | Example | Primary source route |
|---|---|---|
| Drug identity | “Lipitor 是什么成分/剂型？” | RxNorm → current label |
| Indication / approval | “这个药获批用于什么？” | Drugs@FDA / EMA / NMPA/CDE |
| Dose / contraindication | “eGFR 低还能用吗？” | current label first |
| Interaction | “A 和 B 能不能一起用？” | current labels → FDA DDI tables/guidance → clinical evidence if needed |
| Metabolism / CYP | “这个药主要经 CYP3A 代谢吗？” | Clinical Pharmacology label section → FDA DDI reference → literature |
| Transporter | “是不是 P-gp substrate？” | label / FDA transporter table → clinical pharmacology literature |
| PK | “半衰期/清除/活性代谢物？” | label Clinical Pharmacology → regulatory review / literature |
| MOA / target | “作用靶点和机制？” | label pharmacodynamics → regulatory review → peer-reviewed literature |
| Adverse effect | “这个症状是不是药引起的？” | label/safety communication; FAERS only as signal; causality requires stronger evidence |
| Guideline | “指南现在推荐什么？” | current guideline/pathway exact version |
| Trial status | “III 期了吗？还在招募吗？” | ClinicalTrials.gov |
| Trial efficacy | “这个试验证明有效吗？” | publication/result + study design; registry alone is insufficient |
| PGx | “CYP2C19 poor metabolizer 怎么办？” | drug label + FDA PGx association/biomarker source; guideline when relevant |
| Patient instructions | “漏服怎么办/饭前饭后？” | approved patient labeling / Medication Guide / label |
| Emergency/triage | “是否有 red flag？” | current clinical guideline/public-health emergency source; explicit escalation policy |

## 1. Normalize entities before search

### Drug

Resolve:

```text
user string
→ active ingredient
→ brand/generic relationship
→ strength
→ dose form
→ route
→ jurisdiction
→ RxNorm identifier when available
```

Never assume two products with the same ingredient have identical instructions when route/formulation differs.

### Lab / observation

Resolve, where useful:

```text
name
→ specimen/system
→ units
→ method/context
→ LOINC mapping
```

Interpretation thresholds remain evidence-dependent; LOINC identifies the observation but does not define all clinical meaning.

## 2. Retrieve in authority order

### Tier 0 — authoritative primary truth

- current drug label / SmPC;
- regulator approval records;
- regulator safety communication;
- national/current clinical guideline/pathway where applicable;
- regulator clinical pharmacology/DDI guidance.

### Tier 1 — authoritative structured/reference sources

- RxNorm / LOINC for normalization;
- ClinicalTrials.gov for registered trial metadata;
- NIH domain references such as LiverTox;
- WHO normative medicine resources.

### Tier 2 — scientific evidence / signal / patient-information support

- PubMed-indexed literature;
- FAERS/openFDA for signal discovery only;
- patient-facing information such as MedlinePlus for task/counseling context.

### Tier 3 — discovery only

News, search snippets, company marketing pages, forums, social media, LLM summaries.

Tier 3 cannot become a production-grade clinical rule without primary verification.

## 3. Extract claims, not pages

A URL is not evidence until the relevant proposition is located.

For each claim record:

```yaml
claim_id:
subject:
predicate:
object:
qualifiers:
  population:
  indication:
  route:
  formulation:
  dose:
  organ_function:
  genotype:
  time:
source_id:
document_version:
publication_or_update_date:
locator:
passage_id:
evidence_role:
claim_scope:
temporal_status:
review_status:
```

Examples of scope errors that must fail verification:

```text
Phase III positive → approved                    # invalid upgrade
trial registered → effective                     # invalid upgrade
FAERS reports → drug caused event                # invalid causal upgrade
PK association → clinical benefit/toxicity       # unsupported upgrade
same target → direct competitor                  # relation shortcut
subgroup signal → whole-population recommendation# population scope error
old guideline → current recommendation           # temporal error
```

## 4. Verification rules by knowledge type

### A. Contraindication / dose / organ function

Required:

1. current label or current jurisdiction-specific product information;
2. exact population/threshold/route/formulation;
3. section locator;
4. distinguish initiation vs continuation vs dose reduction vs avoidance.

### B. Drug-drug interaction

Record separately:

```text
mechanism
perpetrator/victim roles
CYP/transporter
inhibitor/inducer/substrate strength if established
exposure direction
clinical consequence
management instruction
source of each layer
```

Do not infer a patient management recommendation solely from an in-vitro interaction.

### C. PK / metabolism

Separate:

```text
absorbed_by / bioavailability
metabolized_by
active_metabolite / inactive_metabolite
substrate_of
inhibits
induces
transported_by
half_life
clearance
renal_excretion
hepatic_metabolism
```

A drug can have multiple pathways; “metabolized by CYP3A” does not imply CYP3A is the only or dominant clinically relevant pathway unless the source supports that scope.

### D. Adverse events / safety

Distinguish:

```text
label adverse reaction
boxed warning
regulatory safety communication
post-marketing reported event
causal association
incidence
class effect
```

FAERS/openFDA rule:

> report presence/count ≠ causality ≠ incidence.

### E. Pharmacogenomics

Represent:

```text
gene / allele or phenotype
→ effect on enzyme/transporter/target
→ PK effect
→ response/toxicity evidence
→ management recommendation (only if supported)
```

Do not upgrade a PK-only association into a treatment recommendation.

### F. Guidelines

Capture:

```text
guideline title
issuing organization
version/year
recommendation text paraphrase
recommendation strength
quality/certainty if stated
population
exceptions
superseded version
```

A new trial may change the evidence landscape without immediately changing the current guideline.

## 5. Contradiction protocol

When two sources disagree:

1. do not delete either claim;
2. check jurisdiction, population, formulation, date and source role;
3. classify as `APPARENT_SCOPE_CONFLICT`, `TEMPORAL_SUPERSESSION`, `TRUE_DISPUTE`, or `UNRESOLVED`;
4. choose current production truth only when the conflict can be resolved;
5. otherwise preserve uncertainty and create an eval case if clinically meaningful.

## 6. Review levels

```text
DISCOVERED
→ MACHINE_PARSED
→ SOURCE_VERIFIED
→ DOMAIN_REVIEWED
→ GOLD_APPROVED
```

Definitions:

- `DISCOVERED`: source found only.
- `MACHINE_PARSED`: structured extraction done, not trusted.
- `SOURCE_VERIFIED`: human/agent verified that source/locator supports the paraphrased claim.
- `DOMAIN_REVIEWED`: relevant clinician/pharmacology reviewer confirms clinical scope.
- `GOLD_APPROVED`: allowed in frozen benchmark gold / safety gate / production post-training export.

High-risk medication or triage claims should not be called final gold before domain review.

## 7. Freshness / update rules

Track per source:

```text
last_checked_at
source_version
published_or_updated_at
next_review_due
change_hash
```

Suggested refresh policy:

- regulator safety communications: weekly/daily watch where feasible;
- current labels for benchmark drugs: monthly or event-triggered;
- ClinicalTrials records: API timestamp/event-triggered;
- guidelines: monthly metadata check + release-triggered full diff;
- static terminology: update on official releases;
- PubMed evidence: task-specific, not blind bulk refresh.

Source update should trigger:

```text
source diff
→ affected passage/claim
→ affected graph edge
→ affected case families
→ temporal regression suite
```

## 8. Search query templates

### Current label

```text
<active ingredient> current prescribing information <jurisdiction>
<active ingredient> renal impairment label
<active ingredient> drug interactions label
```

### CYP / transporter

```text
<active ingredient> CYP substrate inhibitor inducer FDA
<active ingredient> transporter P-gp BCRP OATP OCT MATE clinical pharmacology
```

### Organ impairment

```text
<active ingredient> renal impairment dosage label
<active ingredient> hepatic impairment dosage label
```

### Trial

```text
<drug> <indication> ClinicalTrials.gov
registry_id when known
```

### Literature

Use concept blocks rather than natural-language questions:

```text
(drug) AND (interaction/mechanism/outcome) AND (population) AND (study type)
```

## 9. Production rejection conditions

Reject a candidate claim when any applies:

- no retrievable source or locator;
- citation does not entail the claim;
- claim exceeds population/route/dose/formulation scope;
- current truth is based only on an obsolete document;
- approval claim is based on trial/company/news rather than regulator;
- causal safety claim is based only on spontaneous reports;
- DDI management instruction is inferred only from mechanism/in-vitro data;
- exact drug identity is unresolved;
- high-risk gold lacks required domain review.

## 10. Benchmark use

Verified knowledge can be converted into controlled cases by varying one decision-critical factor:

```text
threshold above vs below
current vs superseded document
interaction partner present vs absent
renal/hepatic function known vs missing
adult vs pediatric/pregnancy context
genotype known vs unknown
retrieval success vs miss
critical passage present vs ignored
```

This keeps knowledge construction directly connected to model diagnosis and post-training rather than becoming a detached encyclopedia project.
