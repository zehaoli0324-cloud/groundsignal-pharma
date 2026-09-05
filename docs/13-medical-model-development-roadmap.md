# GroundSignal Medical Model Development Roadmap

> Date: 2026-09-05
> Principle: prove one end-to-end vertical slice before scaling breadth.

## Current checkpoint

### Implemented as architecture/code scaffold

- [x] Reposition repository around evidence-grounded medical model development.
- [x] Preserve `pharma/` as a real-world temporal evidence track.
- [x] Define Clinical Track task families.
- [x] Add paragraph-level evidence-passage schema.
- [x] Add clinical-case schema.
- [x] Add reproducible model-run schema.
- [x] Add multi-model harness v0.1 (`fixture` + OpenAI-compatible adapter).
- [x] Add deterministic Intervention Router v0.1.
- [x] Add reviewed SFT/preference exporter v0.1.
- [x] Add policy-driven Regression Gate v0.1.
- [x] Add first medication-safety vertical-slice fixture.
- [x] Add CI workflow that exercises the vertical-slice pipeline.

### Not yet validated as a model-improvement result

- [ ] Real multi-provider model run on the clinical track.
- [ ] Clinician/expert review of clinical gold and safety gates.
- [ ] Production guideline / label ingestion pipeline.
- [ ] Real retriever / reranker and evidence Recall@K measurement.
- [ ] Calibrated LLM-as-Judge vs expert agreement.
- [ ] Real SFT or preference intervention.
- [ ] Held-out regression proving the intervention improves a model/system version.
- [ ] Medical Agent tool execution benchmark.
- [ ] Multimodal image benchmark.

This distinction is intentional: **implemented infrastructure is not the same as demonstrated model improvement.**

---

# P0 — Make the first vertical slice real

## Goal

Turn the current fixture into one actual model-development experiment.

## Tasks

1. Run at least 2 real model configurations on `clinical-medication-safety-001` and controlled variants:
   - closed-book;
   - evidence-in-context / RAG-style.
2. Add 3–5 controlled variants:
   - eGFR just above/below the threshold;
   - irrelevant distractor history;
   - incomplete renal-function information;
   - conflicting/older evidence snapshot;
   - multi-turn version that requires clarification.
3. Blind-score the outputs with the frozen rubric.
4. Confirm whether the expected failure actually appears.
5. Route the failure to an intervention hypothesis.
6. Apply one small intervention (prompt/RAG preferred for the first proof; SFT/preference after the data contract is stable).
7. Re-run on held-out variants.
8. Record a regression report.

## Definition of done

A report can show:

```text
baseline configuration
→ observed bad case
→ failure diagnosis
→ chosen intervention + rationale
→ candidate configuration
→ held-out improvement
→ no new critical safety regression
```

---

# P1 — Clinical Track: 6–12 expert-quality cases

Do not scale to hundreds of cases yet.

Build 1–2 cases in each high-value family:

| Family | Initial target | Primary risk/capability |
|---|---:|---|
| Medical QA | 1–2 | factuality / evidence hierarchy |
| Clinical reasoning | 2 | premature closure / differential reasoning |
| Medication safety | 2 | critical unsafe recommendation |
| Report interpretation | 1–2 | observation vs inference |
| Longitudinal reasoning | 1 | stale/superseded patient state |
| Multi-turn | 1 | useful clarification / abstention |
| Agent/tool use | 1 | tool selection / tool-grounded answer |

Each case should produce controlled variants, so 8 base cases can yield ~24–40 evaluation items without superficial breadth.

## Required quality checks

- provenance / license status;
- de-identification;
- evidence snapshot frozen;
- gold behavior reviewed;
- critical errors preregistered;
- counterfactual or distractor variants;
- leakage check;
- held-out split.

---

# P2 — Guideline / Label Truth ingestion

## Goal

Move from hand-authored evidence fixtures to a reproducible evidence pipeline.

## Sources to support first

1. drug labels / regulatory prescribing information;
2. professional guidelines / consensus with version dates;
3. ClinicalTrials registry fields;
4. PubMed / peer-reviewed literature metadata and scoped propositions.

## Pipeline

```text
source registry
→ fetch/version
→ section segmentation
→ proposition extraction
→ claim-scope normalization
→ paragraph locator
→ evidence-role classification
→ temporal validity
→ reviewer approval
→ evidence JSONL/index
```

## Metrics

- passage provenance coverage;
- claim-passage entailment precision;
- version/date coverage;
- contradiction/supersession recall;
- reviewer agreement.

Do not measure success by number of downloaded documents.

---

# P3 — Harness v0.2: real experimental matrix

Add adapters and experiment controls:

- provider-specific model name separate from experiment alias;
- retry / timeout / rate-limit logging;
- deterministic seed when provider supports it;
- system-prompt registry;
- RAG retriever adapter;
- tool executor adapter;
- multi-turn replay;
- response caching keyed by model+prompt+snapshot;
- cost/token accounting;
- run manifest and dataset hash.

Target experiment matrix:

```text
Model A closed-book
Model A + evidence
Model A + RAG
Model A + RAG + medical tool
Model B closed-book
Model B + evidence
...
```

This allows attribution: model problem vs retrieval problem vs orchestration problem.

---

# P4 — Evaluation / Judge calibration

## Human-first seed

For the first 50–100 clinical responses:

- freeze rubric;
- blind model identity;
- use at least one domain-competent reviewer for safety-critical dimensions;
- collect disagreement rather than forcing consensus silently.

## Judge metrics

- exact/weighted agreement;
- dimension-level correlation;
- critical-error sensitivity/specificity;
- calibration by task family;
- judge drift across prompt/rubric versions.

Only automate dimensions that show acceptable human agreement.

`JUDGE_INCONSISTENCY` routes to judge calibration, not model training.

---

# P5 — Intervention experiments

Run controlled experiments by failure class.

### Experiment A — stale knowledge

```text
closed-book
vs
frozen temporal retrieval
```

Primary endpoint: temporal validity / stale-claim rate.

### Experiment B — overclaim

```text
baseline prompt/model
vs
preference examples or explicit claim-scope policy
```

Primary endpoint: overclaim rate; guardrail: useful answer rate does not collapse.

### Experiment C — reasoning failure

```text
baseline
vs
small reviewed reasoning-SFT set
```

Primary endpoint: held-out reasoning; guardrail: factuality and safety.

### Experiment D — bad tool use

```text
baseline Agent policy
vs
reviewed trajectory examples / tool-schema changes
```

Primary endpoint: tool success; guardrail: unsafe call rate.

Do not mix multiple interventions in the first causal experiment unless necessary.

---

# P6 — Post-training data factory

Only after P0–P4 data contracts stabilize.

For every exported sample preserve:

- source case;
- evidence snapshot;
- failure cluster;
- rejected/base response;
- ideal/chosen response;
- reviewer;
- rubric version;
- intervention experiment ID;
- train/held-out lineage.

Hard rule:

> A case used to create training data cannot be reused as the sole evidence of improvement.

Maintain separate regression/held-out variants.

---

# P7 — Regression as release engineering

Move `regression_gate.py` from fixture CI to real model/system comparisons.

Release gate should eventually report:

```text
Core capability
  factuality
  evidence sufficiency
  clinical reasoning
  report interpretation

Safety
  medication critical errors
  false reassurance
  unsupported high-confidence diagnosis
  unsafe tool calls

Calibration
  uncertainty
  useful abstention

Grounding
  evidence recall@k
  citation entailment
  temporal validity

Target intervention capability
  metric tied to the experiment
```

No candidate releases if a new preregistered critical medical error appears.

---

# P8 — Medical Agent and multimodal extension

Only after the text/evidence loop is stable.

## Agent

Add tasks requiring:

- evidence search;
- calculator / structured-data lookup;
- choosing between tools;
- deciding when not to call a tool;
- trajectory-level evaluation;
- recovery from tool failure;
- stopping criteria.

## Multimodal

Add image-bearing cases with explicit modality provenance and rights/de-identification review.

Evaluate separately:

- image observation;
- image-text integration;
- report-image contradiction;
- uncertainty under low-quality/partial images;
- hallucinated visual findings.

---

# Near-term order of work

```text
NOW
1. Architecture + schemas + executable skeleton          DONE
2. First evidence-grounded medication-safety slice       DONE as fixture
3. Run real models + create controlled variants          NEXT
4. Human/expert scoring                                  NEXT
5. First intervention + held-out regression              NEXT
6. Expand to 6–12 clinical cases
7. Automate guideline/label ingestion
8. Calibrate judge
9. Small post-training experiment
10. Agent + multimodal tracks
```

The repository should optimize for **traceability and causal learning**, not headline case count.
