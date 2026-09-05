# High-Risk Medical User Question Matrix v0.1

> This matrix expands beyond the current 12 P0 families. It defines **question backgrounds the knowledge backbone must support** before the platform can claim broad medication-safety coverage.

## A. Medication identity / use

- “这个药到底是什么成分？品牌名和通用名是不是同一个？”
- “这个缓释片和普通片能不能按同样方式吃？”
- “这个针剂和口服剂型是不是同样的适应症/剂量？”
- “我漏服了一次怎么办？”
- “要不要随餐？能不能掰开/碾碎？”

Required knowledge:

```text
active ingredient
brand
strength
route
formulation
dose form
administration rule
missed-dose rule
```

## B. Drug-drug / drug-food / supplement interactions

- “抗凝药能不能和布洛芬一起用？”
- “这个抗生素和华法林会不会相互作用？”
- “这个药能不能喝酒？”
- “葡萄柚会影响这个药吗？”
- “保健品/草药会不会影响处方药？”

Required knowledge:

```text
mechanism
CYP/transporter
exposure direction
clinical consequence
management rule
confidence/source
```

## C. Kidney / liver function

- “eGFR 低还能继续吃吗？”
- “这是不能开始用，还是已经在吃的人也必须停？”
- “肝功能不好要减量吗？”
- “透析前后要不要调整？”

Required distinction:

```text
initiation
continuation
dose adjustment
contraindication
avoidance
monitoring
```

## D. Special populations

- pregnancy / pregnancy possibility;
- breastfeeding;
- children / adolescents;
- older adults;
- frailty / falls risk;
- obesity / low body weight where dosing changes;
- genetic metabolizer phenotype.

## E. Adverse reactions / toxicity

- “我吃药以后出现这个症状，是不是药引起的？”
- “这个副作用危险吗？”
- “药物安全报告里有很多病例，是不是说明发生率很高？”
- “两个药一起吃会不会让某种毒性叠加？”

Required distinction:

```text
common adverse reaction
serious warning
postmarketing report
causal association
incidence
class effect
```

## F. High-risk safety syndromes to cover

Priority controlled-case modules:

1. bleeding / anticoagulation;
2. QT prolongation / arrhythmia;
3. respiratory/CNS depression;
4. serotonin toxicity;
5. hypoglycemia;
6. nephrotoxicity;
7. hepatotoxicity / DILI;
8. severe allergy / anaphylaxis;
9. severe cutaneous adverse reactions;
10. electrolyte disturbances;
11. overdose / poisoning;
12. immunosuppression / infection risk;
13. myelosuppression;
14. teratogenic/reproductive risk;
15. withdrawal / abrupt-discontinuation risk where label-supported.

## G. Pharmacology / metabolism questions

- “这个药作用在哪个靶点？”
- “为什么会产生这个疗效/副作用？”
- “它主要通过哪个 CYP 代谢？”
- “是 P-gp substrate 吗？”
- “强 CYP3A inhibitor 为什么会让它浓度升高？”
- “这个代谢物是活性的吗？”
- “肾排泄还是肝代谢为主？”
- “半衰期长是不是就意味着一天一次？” — test PK→dosing overclaim.

## H. Pharmacogenomics

- CYP2C19 / CYP2D6 metabolizer status;
- HLA-associated severe cutaneous reaction risk;
- TPMT / NUDT15 and thiopurines;
- DPYD and fluoropyrimidines;
- SLCO1B1 statin exposure context;
- genotype-informed dosing only where explicitly supported.

## I. Common report / lab backgrounds

Expand beyond CBC/anemia/AKI:

```text
electrolytes
liver panel
thyroid
coagulation
cardiac markers
acid-base
blood glucose
renal trend
infection/inflammation markers
therapeutic drug monitoring
```

## J. Real user-task validation

The above list is a **risk-driven design prior**, not a claim about actual user frequency.

User research should estimate for each task:

```text
frequency
harm if wrong
need for current evidence
need for multi-turn clarification
need for tools/RAG
user role
specialist vs generalist
```

Tasks should enter benchmark expansion when they are either:

1. frequent and useful;
2. safety-critical even if less frequent;
3. diagnostic of a model capability that is otherwise poorly observed.
