# GroundSignal Medical KG Quality Audit v0.1

> Date: 2026-09-05
> Scope: current canonical evaluation-oriented medical knowledge graph.

## Build result

The canonical builder completed successfully in CI after merging:

- 12 P0 case-family graph snapshots;
- 10 pharmacology/safety backbone modules.

Current canonical snapshot statistics from CI:

```text
nodes: 108
edges: 83
source_verified edges: 76
design_verified edges: 7
```

The graph build failed on neither node-ID nor edge-semantic collisions.

## Source/evidence metadata audit

Current validation summary:

```text
source registry entries: 17
case evidence manifests: 12
local source records: 19
case claims: 43
pharmacology backbone modules: 10
pharmacology backbone claims: 28
errors: 0
warnings: 6
```

Warnings are source-governance warnings, not claim-validation failures. They currently come from authoritative/recognized external hosts used by selected cases but not yet represented as first-class entries in `SOURCE_REGISTRY.json`:

- Merck Manual (`merckmanuals.com`);
- National Kidney Foundation (`kidney.org`);
- American Heart Association (`heart.org`, `professional.heart.org`);
- CDC (`cdc.gov`).

These should be registered explicitly with appropriate authority tier/scope before strict-host mode is enabled.

## Edge quality classes

### `source_verified`

Meaning:

- an external or frozen benchmark source exists;
- the locator/claim relation was checked for support;
- the graph edge is within the source's intended scope.

This is the dominant current class (76/83 edges).

### `design_verified`

Meaning:

- the edge is part of the benchmark/tool/task contract rather than an external medical fact;
- examples include `high-risk claim SHOULD_BE_GROUNDED_BY passage` or tool-routing relations;
- correctness is evaluated as system-design truth, not clinical-source truth.

Current count: 7/83.

### Important limitation

`source_verified` is not the same as `clinical-expert-approved`.

Most P0 family manifests are still marked `gold_review_needed`. Therefore the graph currently supports engineering evaluation and evidence tracing, but should not yet be described as clinician-certified medical gold.

## Quality by graph layer

| Layer | Precision confidence | Coverage | Notes |
|---|---|---|---|
| Regulatory/label rules | High locally | Sparse | strongest current clinical truth layer |
| Pharmacology/DDI mechanism | High for included claims | Sparse | official FDA reference tables; not exhaustive |
| PGx | High for included associations | Sparse | FDA table; preserve management vs PK-only distinction |
| Triage | Moderate-high locally | Very sparse | AHA/CDC-backed selected warning-sign modules |
| Clinical reasoning | Moderate | Very sparse | mixed official/recognized clinical reference sources; expert gold review still needed |
| Report interpretation | High internal validity | Sparse | some families are controlled synthetic report truth |
| Trial/guideline temporal reasoning | High internal validity | Sparse | some controlled synthetic snapshots; pharma track adds real regulatory/trial events |
| Pharma intelligence | Moderate-high precision in selected domains | Narrow | strong in selected GLP-1/PD-1/CAR-T/ADC/BTK assets, not clinical pharmacology-complete |

## Overall judgment

### Source quality

Generally **high for the claims that have been included**, because the strongest layers use FDA/DailyMed/official regulatory sources, professional guidance, or explicitly frozen synthetic fixtures.

### Graph correctness

Currently **precision-oriented rather than recall-oriented**. The structure is intentionally conservative and preserves source scope, temporal status and forbidden inference.

### Graph coverage

Still **far from comprehensive medicine**. Major gaps remain in broad DDI, PK/ADME, organ impairment, special populations, toxicology, TDM, pregnancy/lactation, pediatrics, pharmacogenomics breadth and general disease knowledge.

### Recommended description

Use:

> High-provenance, evaluation-oriented medical knowledge graph prototype with strong local truth quality and incomplete domain coverage.

Do not use:

> Comprehensive medical knowledge graph.

## Next quality gates

1. register the six currently warned authoritative hosts;
2. enable strict-host validation;
3. obtain domain/clinical review for P0 gold;
4. add RxNorm normalization coverage metric;
5. add LOINC normalization for lab-heavy families;
6. quantify stale/current-version coverage;
7. measure evidence-backed edge ratio separately for real-world vs synthetic edges;
8. add contradiction and supersession regression tests.
