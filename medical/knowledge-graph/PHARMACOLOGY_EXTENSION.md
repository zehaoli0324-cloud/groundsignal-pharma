# Pharmacology / Metabolism Knowledge-Graph Extension v0.1

> Purpose: extend the current task-oriented medical graph so medication questions can be evaluated at **identity, mechanism, PK/PD, interaction, safety and management** levels.

## 1. Why the current graph is insufficient

The existing graph is strong for case-local facts, guideline/label recommendations and evidence provenance, but selected pharma `TARGET` nodes do not constitute a systematic pharmacology graph.

A clinical model should be testable on questions such as:

- What active ingredient/product/formulation is this?
- What target/mechanism produces the intended effect?
- How is the drug absorbed, metabolized and eliminated?
- Is it a CYP or transporter substrate/inhibitor/inducer?
- Why does another drug increase/decrease exposure?
- Does a mechanistic DDI actually require a management change?
- Does renal/hepatic dysfunction change exposure or dosing?
- Does a genotype alter metabolism, toxicity or treatment?

## 2. New node classes

### Drug identity

```text
ACTIVE_INGREDIENT
BRAND_PRODUCT
DOSE_FORM
ROUTE
STRENGTH
FORMULATION
DRUG_CLASS
```

### Pharmacodynamics / mechanism

```text
TARGET
PATHWAY
MECHANISM_OF_ACTION
PD_EFFECT
BIOMARKER
THERAPEUTIC_EFFECT
```

### Pharmacokinetics / disposition

```text
PK_PARAMETER
ENZYME
TRANSPORTER
METABOLITE
EXCRETION_ROUTE
ABSORPTION_PROCESS
CLEARANCE_PROCESS
```

Key enzymes/transporters should support normalized identifiers/genes when appropriate:

```text
CYP1A2 / CYP2B6 / CYP2C8 / CYP2C9 / CYP2C19 / CYP2D6 / CYP3A4/5
UGT family where clinically relevant
P-gp (ABCB1)
BCRP (ABCG2)
OATP1B1/1B3 (SLCO1B1/SLCO1B3)
OAT1/OAT3
OCT2
MATE1/MATE2-K
```

### Clinical pharmacology / safety

```text
INTERACTION
CONTRAINDICATION
WARNING
ADVERSE_REACTION
TOXICITY_SYNDROME
MONITORING_RULE
DOSE_RULE
ORGAN_FUNCTION_STATE
SPECIAL_POPULATION
```

### Pharmacogenomics

```text
GENE
ALLELE
GENOTYPE
METABOLIZER_PHENOTYPE
TRANSPORTER_PHENOTYPE
PGX_MANAGEMENT_RULE
```

## 3. Core edge classes

### Identity

```text
BRAND_PRODUCT HAS_INGREDIENT ACTIVE_INGREDIENT
BRAND_PRODUCT HAS_DOSE_FORM DOSE_FORM
BRAND_PRODUCT HAS_ROUTE ROUTE
ACTIVE_INGREDIENT MEMBER_OF DRUG_CLASS
```

### Pharmacodynamics

```text
ACTIVE_INGREDIENT BINDS TARGET
ACTIVE_INGREDIENT INHIBITS_TARGET TARGET
ACTIVE_INGREDIENT AGONIZES TARGET
ACTIVE_INGREDIENT ANTAGONIZES TARGET
ACTIVE_INGREDIENT HAS_MOA MECHANISM_OF_ACTION
MECHANISM_OF_ACTION PRODUCES_PD_EFFECT PD_EFFECT
PD_EFFECT MAY_SUPPORT THERAPEUTIC_EFFECT
```

Avoid collapsing mechanism into clinical outcome without evidence.

### PK / metabolism

```text
ACTIVE_INGREDIENT SUBSTRATE_OF ENZYME
ACTIVE_INGREDIENT INHIBITS_ENZYME ENZYME
ACTIVE_INGREDIENT INDUCES_ENZYME ENZYME
ACTIVE_INGREDIENT TRANSPORTED_BY TRANSPORTER
ACTIVE_INGREDIENT INHIBITS_TRANSPORTER TRANSPORTER
ACTIVE_INGREDIENT FORMS_METABOLITE METABOLITE
ACTIVE_INGREDIENT ELIMINATED_VIA EXCRETION_ROUTE
ACTIVE_INGREDIENT HAS_PK_PARAMETER PK_PARAMETER
```

Each enzyme/transporter relation should carry qualifiers:

```yaml
strength: strong|moderate|weak|sensitive|unknown
setting: in_vitro|clinical|label
clinical_relevance: established|possible|unknown
source_passage_ids: []
```

### DDI

Mechanism and management must be separate edges.

```text
DRUG_A INHIBITS_ENZYME CYP3A
DRUG_B SUBSTRATE_OF CYP3A
INTERACTION increases_exposure_of DRUG_B
INTERACTION HAS_CLINICAL_CONSEQUENCE TOXICITY_OR_LOSS_OF_EFFECT
INTERACTION HAS_MANAGEMENT_RULE DOSE/AVOID/MONITOR_RULE
```

Forbidden shortcut:

```text
shares CYP pathway → contraindicated together
```

### Organ impairment

```text
DOSE_RULE APPLIES_TO ORGAN_FUNCTION_STATE
ACTIVE_INGREDIENT HAS_DOSE_RULE DOSE_RULE
ORGAN_FUNCTION_STATE CHANGES_EXPOSURE_OF ACTIVE_INGREDIENT
```

Represent separately:

```text
renal impairment
hepatic impairment
initiation rule
continuation rule
dose reduction
avoidance
contraindication
monitoring
```

### Safety

```text
ACTIVE_INGREDIENT HAS_WARNING WARNING
ACTIVE_INGREDIENT HAS_ADVERSE_REACTION ADVERSE_REACTION
ACTIVE_INGREDIENT ASSOCIATED_WITH_SAFETY_SIGNAL ADVERSE_REACTION
WARNING REQUIRES_MONITORING MONITORING_RULE
WARNING MAY_REQUIRE_ACTION DOSE_RULE
```

Do not treat `ASSOCIATED_WITH_SAFETY_SIGNAL` as `CAUSES`.

### PGx

```text
ALLELE INFERS_PHENOTYPE METABOLIZER_PHENOTYPE
METABOLIZER_PHENOTYPE CHANGES_EXPOSURE_OF ACTIVE_INGREDIENT
GENOTYPE CHANGES_TOXICITY_RISK_OF ACTIVE_INGREDIENT
PGX_MANAGEMENT_RULE APPLIES_TO GENOTYPE_OR_PHENOTYPE
ACTIVE_INGREDIENT HAS_PGX_RULE PGX_MANAGEMENT_RULE
```

PGx layers must distinguish:

```text
PK-only evidence
response/toxicity association
explicit management recommendation
```

## 4. Edge provenance contract

Safety-critical edge example:

```yaml
edge_id: EDGE-DRUG-CYP3A-SUBSTRATE-001
subject_id: drug:example
predicate: SUBSTRATE_OF
object_id: enzyme:CYP3A
status: OBSERVED
qualifiers:
  setting: clinical
  strength: sensitive
  clinical_relevance: established
source_passage_ids:
  - passage:current_label_clinical_pharmacology
review_status: SOURCE_VERIFIED
valid_from: 2026-01-01
valid_to: null
```

Management should use a different edge:

```yaml
edge_id: EDGE-DDI-MANAGEMENT-001
subject_id: interaction:drugA_drugB
predicate: HAS_MANAGEMENT_RULE
object_id: rule:avoid_combination
source_passage_ids:
  - passage:current_label_drug_interaction
review_status: DOMAIN_REVIEWED
```

## 5. Minimum high-risk pharmacology modules

Build controlled modules around mechanism families rather than random drugs:

1. CYP3A strong inhibitor + sensitive substrate
2. CYP3A inducer + efficacy loss
3. CYP2D6 poor/ultrarapid metabolizer
4. CYP2C19 activation failure / exposure change
5. P-gp interaction
6. OATP1B1/BCRP statin exposure context
7. OCT2/MATE metformin transport context
8. anticoagulant + hemostasis-affecting drug
9. QT-prolongation multi-factor risk
10. serotonergic combination
11. CNS/respiratory depressant combination
12. nephrotoxic combination / renal impairment
13. hepatotoxicity / DILI context
14. hypoglycemia-producing combinations
15. genotype-associated severe cutaneous reaction

For each module create:

```text
mechanism graph
+ direct label/guidance evidence
+ clinical consequence edge only when supported
+ management edge only when supported
+ base / controlled / adversarial / held-out cases
```

## 6. Normalization

Recommended mappings:

- drugs/products: RxNorm;
- labs/observations: LOINC;
- genes: stable gene symbols/IDs;
- enzymes/transporters: gene/protein canonical labels;
- conditions: local IDs initially; optional SNOMED mapping only after licensing/implementation decision.

## 7. Evaluation metrics enabled by this extension

```text
Drug Identity Accuracy
Mechanism Relation Precision
CYP/Transporter Relation Precision
DDI Mechanism Accuracy
Clinical-Management Scope Precision
Unsupported Interaction Edge Rate
Organ-Function Rule Accuracy
PGx Scope Accuracy
Temporal Pharmacology Accuracy
```

This lets GroundSignal distinguish:

```text
mechanism knowledge failure
vs
clinical consequence overclaim
vs
management overclaim
vs
retrieval/source failure
```

which is necessary for useful post-training routing.
