# How GroundSignal Medical Knowledge Graph Is Built

> Date: 2026-09-05
> Scope: construction method, source provenance, quality tiers, and known limitations.

GroundSignal currently has **two generations of graph representation** and a new canonical merge layer.

## 1. Generation 1 — Pharma / Obsidian intelligence graph

The original `pharma/` track is file-based rather than a graph database.

```text
Markdown node
+ YAML/frontmatter metadata
+ wikilink relations
+ source_url / evidence status
```

`scripts/ingest.py` can create nodes from YAML/JSON and write bidirectional wikilinks between entities. Typical entities are company, product/drug, target and event. This layer is useful for human-readable intelligence navigation and temporal pharma tracking.

### Strengths

- transparent and easy to inspect;
- real-world regulatory/trial/company sources;
- useful for pharma entity relations and temporal events;
- already supports provenance and evidence-audit workflows.

### Limitations

- many older relations are document/node-oriented rather than fully atomic claim objects;
- free-text entity naming is weaker than formal clinical terminology normalization;
- not designed originally for patient-level medication safety, PK/PD or DDI reasoning;
- wikilink relation semantics are less strict than the newer medical graph schema.

Therefore the pharma graph is retained as a specialist evidence track, not treated as the entire medical knowledge graph.

---

## 2. Generation 2 — Case-local medical evaluation graphs

Each P0 clinical family contains:

```text
manifest.json
  → family definition / split / capabilities

evidence.json
  → source documents / claims / passage IDs / locators

graph.json
  → nodes / edges / statuses / source passage IDs

cases/*.json
  → patient state / interaction / graph-eval contract
```

A case can pre-register:

```text
required nodes
required edges
forbidden claims/edges
acceptable reasoning paths
```

The graph is therefore not only for retrieval. It is part of the scoring contract.

Example:

```text
case:eGFR_27
  HAS_LAB → eGFR=27
  TAKES → metformin

metformin
  CONTRAINDICATED_IN → eGFR<30 rule
      SUPPORTED_BY → current label passage
```

A model may phrase the answer differently, but an unsupported edge such as:

```text
eGFR<30 → REQUIRES insulin
```

can still be detected as graph-level overclaim.

---

## 3. Generation 3 — Pharmacology / safety backbone

`medical/knowledge-base/PHARMACOLOGY_BACKBONE_V0.1.json` adds reusable cross-case knowledge modules for:

- CYP3A;
- CYP2D6;
- CYP2C19;
- OCT2/MATE;
- OATP/BCRP;
- pharmacogenomics;
- CNS depressant safety;
- QT risk;
- anticoagulation/bleeding.

These modules deliberately separate:

```text
mechanistic relation
≠ exposure consequence
≠ clinical outcome
≠ management recommendation
```

For example:

```text
Drug A INHIBITS CYP3A
Drug B SUBSTRATE_OF CYP3A
```

does **not** automatically create:

```text
Drug A + Drug B CONTRAINDICATED
```

A patient-specific management edge requires direct drug-label/guideline support.

---

## 4. Canonical graph build

`scripts/build_medical_knowledge_graph.py` merges:

```text
all medical/case-families/*/graph.json
+
PHARMACOLOGY_BACKBONE_V0.1.json
```

into a single evaluation-oriented snapshot:

```text
medical/knowledge-graph/generated/medical-kg-v0.1.json
```

The canonical graph preserves:

- original node/edge IDs;
- family/module contexts;
- source passage IDs;
- source IDs;
- review status;
- evidence scope;
- forbidden-inference notes.

Duplicate IDs are merged only when semantics are compatible; incompatible collisions fail the build instead of silently overwriting truth.

The canonical graph is intended to support:

```text
RAG / graph retrieval
edge-level answer scoring
failure attribution
case impact analysis after source updates
post-training data provenance
held-out regression selection
```

It is still a JSON graph snapshot, not yet a production graph database.

---

# Evidence provenance model

## Evidence chain

```text
Source document
→ document version / date / jurisdiction
→ section / paragraph / table locator
→ normalized claim
→ evidence role / claim scope
→ graph node / edge
→ case / evaluation contract
```

A source URL alone is not sufficient.

## Review states

```text
DISCOVERED
→ MACHINE_PARSED
→ SOURCE_VERIFIED
→ DOMAIN_REVIEWED
→ GOLD_APPROVED
```

`SOURCE_VERIFIED` means the cited source/locator was checked for support. It does **not** mean a clinician has approved the claim as final benchmark gold.

---

# Source quality tiers

## Tier A — strongest production truth for the relevant claim

Examples:

- FDA / DailyMed current prescribing information;
- Drugs@FDA approval records;
- FDA clinical pharmacology/DDI resources;
- FDA pharmacogenomics resources;
- EMA product information;
- NMPA/CDE regulatory information;
- applicable current professional/national guidelines.

These are high-quality sources when used **within their correct scope**.

## Tier B — authoritative structured reference / registry

Examples:

- RxNorm for drug identity;
- LOINC for lab/observation identity;
- ClinicalTrials.gov for trial registration metadata;
- NIH LiverTox for DILI background.

These are high quality for their domain but are not interchangeable with prescribing recommendations.

## Tier C — signal/discovery sources

Examples:

- FAERS/openFDA;
- PubMed search/indexing;
- high-quality secondary summaries.

These can discover signals or studies but generally require additional verification before becoming a clinical management edge.

## Synthetic controlled truth

Some benchmark families intentionally use synthetic evidence snapshots to isolate capabilities such as cross-trial comparability or temporal supersession.

Synthetic truth is:

- high internal validity for the controlled experiment;
- not a real-world medical fact;
- clearly marked and never merged into the graph as if it were external clinical truth.

---

# Quality assessment of the current graph

## Strong today

- source provenance discipline;
- temporal/version reasoning;
- controlled evaluation contracts;
- selected medication-safety rules;
- selected triage, clinical reasoning and report-grounding modules;
- selected pharma regulatory/trial events;
- explicit observed/derived/hypothesis/superseded semantics.

## Partial

- drug identity normalization;
- drug-label breadth;
- DDI breadth;
- PK/ADME;
- organ-function dose rules;
- guideline coverage;
- high-risk user scenarios.

## Sparse / missing

- comprehensive pharmacology;
- systematic CYP/UGT/transporter coverage across common drugs;
- special populations;
- pediatric/geriatric dosing;
- pregnancy/lactation;
- pharmacogenomics breadth;
- TDM;
- toxicology/overdose;
- multimodal medical knowledge.

The graph should therefore be described as:

> **a high-provenance, evaluation-oriented medical knowledge graph prototype with strong local truth quality but intentionally incomplete domain coverage.**

It should **not** be described as a comprehensive medical knowledge graph.

---

# Quality metrics to track

For each release:

```text
evidence-backed edge ratio
source-verified edge ratio
domain-reviewed edge ratio
current-version coverage
stale active-edge rate
unresolved contradiction count
entity-normalization coverage
orphan node rate
case required-path coverage
forbidden-edge false-positive rate
```

Coverage and correctness are separate metrics: a small graph can have high precision but poor recall.
