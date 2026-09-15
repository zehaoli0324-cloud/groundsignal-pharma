# GroundSignal Pharma

**Failure-driven evaluation for medical AI under changing clinical evidence.**

GroundSignal studies **where, why and under what pressure a medical AI system begins to fail** during patient-facing clinical decision making.

Instead of treating evaluation as a collection of static medical questions, the project starts from the clinical decision process itself. It identifies likely failure points, turns them into controlled experiments, and measures whether those failures appear consistently as information becomes noisier, more incomplete, more conflicting or more urgent.

The repository already contains evidence-routing, semantic-extraction, temporal truth tracking, controlled-case and multi-turn patient-evaluation infrastructure. The current benchmark direction builds a failure-driven experimental layer on top of that foundation.

[Benchmark methodology](docs/BENCHMARK_DESIGN.md) · [Patient-stage decomposition](medical/patient-eval/STAGE_DECOMPOSITION.md) · [Patient evaluation](medical/patient-eval/README.md) · [Current handoff](docs/handoffs/2026-09-09-candidate-review-handoff.md)

## Core idea: build questions from failure mechanisms, not from diseases

A difficult medical question is not automatically a useful benchmark item. If a strong model answers it perfectly but the item never targets a realistic failure mechanism, the question may tell us very little about the model's actual safety boundary.

GroundSignal therefore uses the following authoring chain:

```text
Clinical decision chain
        ↓
Patient stage
        ↓
Failure mechanism
        ↓
Controlled experiment
        ↓
Pressure gradient
        ↓
Observed failure boundary
```

The goal is to move from **“Can the model answer this case?”** to **“At which decision node does the model fail, what kind of failure is it, and how much pressure is required before that failure becomes reproducible?”**

### 1. Start from the clinical decision chain

The first step is to decompose a patient–AI interaction into decision nodes rather than treating the whole conversation as one answer.

Typical nodes include:

- recognizing the problem and the current level of risk;
- extracting symptoms, timing, negative findings and uncertainty correctly;
- deciding what information is still missing;
- asking questions that can actually change the decision;
- distinguishing competing explanations;
- integrating new or conflicting evidence;
- deciding whether the patient can wait, needs follow-up, or needs escalation;
- revising the recommendation after treatment response, deterioration or recurrence.

This matters because a final answer may look correct even when the reasoning path is unsafe. A model may guess the eventual diagnosis too early, miss a critical question, delay escalation for an irrelevant follow-up question, or fail to revise after stronger evidence appears.

Detailed decision-stage definitions are kept in [`medical/patient-eval/STAGE_DECOMPOSITION.md`](medical/patient-eval/STAGE_DECOMPOSITION.md).

### 2. Place the failure in the patient's real journey

The same model error has different consequences depending on when it occurs. GroundSignal therefore organizes scenarios around patient stages such as:

| Patient stage | Example evaluation target |
|---|---|
| Before care | vague symptoms, whether to seek care, unsafe reassurance, missing red flags |
| Triage / first contact | urgency recognition, critical questioning, escalation timing |
| During diagnosis | evidence integration, differential reasoning, uncertainty handling |
| Understanding medical advice | misunderstanding instructions, medication use, follow-up requirements |
| After treatment or medication | treatment response, adverse effects, adherence, when to re-contact care |
| Deterioration or recurrence | recognizing state change, revising the earlier plan, avoiding stale conclusions |

This stage-based view makes the benchmark closer to a real longitudinal patient interaction rather than a disease quiz.

### 3. Convert each suspected failure into a mechanism

A useful item should test a concrete failure hypothesis. GroundSignal separates three levels when the observable evidence allows it:

- **Strategy failure** — the governing decision principle is wrong. Example: the model keeps seeking diagnostic certainty when the safer objective is immediate risk escalation.
- **Algorithm failure** — the overall strategy is reasonable, but ranking, thresholding, evidence weighting, conflict handling or uncertainty estimation is wrong.
- **Engineering failure** — the strategy may be sound, but execution fails because of state loss, context truncation, stale information, field mapping, negation inversion, tool failure or other implementation problems.

Not every black-box failure can be attributed confidently. When the evidence cannot distinguish these causes, GroundSignal keeps the attribution unresolved rather than inventing a mechanism.

The full failure taxonomy and attribution rules are documented in [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md).

### 4. Test the mechanism with controlled experimental groups

Once a failure hypothesis is defined, it is converted into an experiment rather than a single question.

A typical experiment contains a clean control and one or more interventions or counterfactual branches. The clinical core is held fixed while one principal factor changes. Examples include:

- complete information vs. strategically missing information;
- early ambiguous symptoms vs. later high-risk evidence;
- relevant context vs. irrelevant but plausible context;
- consistent evidence vs. conflicting evidence;
- unchanged patient facts expressed with different wording;
- the same early history followed by different later outcomes;
- normal execution vs. state, context or tool degradation.

This makes it possible to ask a causal evaluation question: **did this particular change cause the model's behavior to change?**

The benchmark therefore treats an experiment family—not an isolated prompt—as the basic scientific unit.

### 5. Increase pressure systematically

After a failure mechanism is measurable under controlled conditions, the same capability is tested across a pressure gradient.

The current working scheme is:

- **L0 — clean baseline:** key evidence is explicit and easy to use;
- **L1 — mild pressure:** one small perturbation is introduced while the correct path remains obvious;
- **L2 — integration pressure:** evidence is dispersed, ambiguous, corrected, conflicting or mixed with distractors;
- **L3 — high pressure:** key evidence is sparse, indirect or surrounded by substantial noise, while the task remains clinically answerable.

Pressure is not intended to make questions arbitrarily obscure. Each level should preserve the same underlying clinical capability and change as few variables as possible.

The desired output is a curve rather than a single score:

```text
pressure level
      ↓
failure rate / severity
      ↓
instability threshold
      ↓
capability boundary
```

This allows two models with similar average accuracy to be distinguished by **how early, how often and how dangerously they fail**.

### 6. Score the decision node, not hindsight correctness

GroundSignal does not reward a model for being accidentally correct using information that was not yet available at that point in the conversation.

Each important node can therefore have its own clinical adjudication specification describing:

- what facts are visible and hidden;
- what risks must already be recognized;
- what questions are required, useful or unnecessary;
- what actions are acceptable now;
- what conclusions are still premature;
- what advice would be dangerous;
- what new evidence should force revision later.

The deeper Oracle–Rubric–Verifier architecture is intentionally kept out of the main README. See [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) for the full methodology.

## What GroundSignal is trying to measure

The benchmark is designed to answer questions such as:

- Did the model understand the patient's facts correctly?
- Did it notice uncertainty, negation and correction?
- Did it ask for information that actually changes the decision?
- Did it distinguish evidence strength from mere relevance?
- Did stronger or newer evidence change its judgment appropriately?
- Did it become overconfident before the evidence justified certainty?
- Did a high-risk state trigger the right action at the right time?
- Did its recommendation remain stable under harmless paraphrase but change under clinically meaningful evidence?
- When the model failed, was the failure more consistent with strategy, algorithm or engineering limitations?

The intended end product is a **failure profile and capability boundary**, not only an aggregate accuracy number.

## Current foundation

### Evidence and truth tracking

The repository includes source routing, semantic extraction and temporal truth tracking. Evidence can retain provenance, applicability, version and conflict information instead of treating every retrieved statement as equally reliable.

Implemented entry points include:

- [`scripts/s2_intent_router_v04.py`](scripts/s2_intent_router_v04.py) — source routing;
- [`scripts/s3_semantic_extractor.py`](scripts/s3_semantic_extractor.py) — semantic extraction;
- [`scripts/s4_truth_ledger_v011.py`](scripts/s4_truth_ledger_v011.py) — temporal truth updates;
- [`medical/knowledge-base/`](medical/knowledge-base/) and [`medical/knowledge-graph/`](medical/knowledge-graph/) — evidence and graph assets.

### Controlled cases

The repository contains **12 case families and 60 controlled cases** used as development assets. They include provenance, split-contamination checks and historical-result preservation.

See [`medical/case-families/`](medical/case-families/) and [`medical/stage-evals/`](medical/stage-evals/).

### Multi-turn patient evaluation

The patient-evaluation prototype contains **6 families and 12 synthetic variants** covering ambiguous expression, fact correction, pressure to answer and misunderstanding repair. The interaction layer can disclose information according to the conversation and preserve what was actually shown to the model.

See [`scripts/patient_eval/`](scripts/patient_eval/) and [`medical/patient-eval/`](medical/patient-eval/).

### Real-dialogue review

A review pipeline has processed **1,557 ReMeDi dialogue segments**. Fifty segments have fact/disclosure drafts with source localization, independent review pages and disagreement lists. They have **not** been promoted to physician-approved clinical gold.

See [`medical/patient-eval/data-sources/v0.2/README.md`](medical/patient-eval/data-sources/v0.2/README.md).

## Current validation evidence

These results validate repository components and synthetic workflows. **They are not performance results for a real medical model.**

| Component | Current evidence |
|---|---|
| Source routing v0.3 | Preferred source matched 22/24 controlled held-out queries; two failures were retained for analysis. |
| Temporal truth ledger v0.1.1 | A prior 18/20 failure set reached 20/20 after repair; a newly created 20-trajectory fresh set also passed 20/20. |
| Patient evaluation v0.3 | 161 software tests passed. Disclosure matching on 48 exposed-question expressions improved from 23/48 to 48/48. The 152 criteria in 24 offline sessions remain unscored by human reviewers. |

Reports: [`S2 V0.3`](medical/stage-evals/S2/V0.3_REPORT.md) · [`S4 initial failure`](medical/stage-evals/S4/S4_V0.1_FRESH_FAIL_REPORT.md) · [`S4 fresh pass`](medical/stage-evals/S4/S4_V0.1.1_FRESH_PASS_REPORT.md) · [`patient-eval validation`](medical/patient-eval/VALIDATION_V0.3.md)

## Current benchmark direction

The current benchmark iteration is **failure-driven rather than case-count-driven**.

The working experimental hierarchy is moving toward:

```text
failure hypothesis
    → experiment family
    → control / intervention arms
    → clinical branches
    → clinical instances
    → pressure variants
    → reproducible run plan
```

The immediate objective is to establish several distinct failure families, multiple independent clinical instances per family, reproducible model/configuration bindings and repeated runs. The benchmark will then measure cross-family and cross-instance generalization rather than treating many surface variants of one case as independent evidence.

The first reference scenarios focus on high-risk patient consultation where timing, missing information, evidence update and escalation matter. Real-model capability curves, physician-approved clinical gold and full cross-family validation remain incomplete.

## Quick start

Python 3.11+ is recommended. The existing offline patient-evaluation demo uses the standard library and does not require an API key.

```bash
git clone https://github.com/zehaoli0324-cloud/groundsignal-pharma.git
cd groundsignal-pharma

python -m scripts.patient_eval.pilot_cli validate
python -m scripts.patient_eval.pilot_cli demo --out medical/patient-eval/local/readme-demo
```

The demo generates 24 scripted sessions. `sessions.json` preserves the dialogue, `evaluation/results.json` stores evaluation records, and `evaluation/report.html` provides a browser-readable report.

Instructions for model integration and manual collection are in [`medical/patient-eval/README.md`](medical/patient-eval/README.md).

## Repository map

```text
medical/
  case-families/      controlled development cases
  knowledge-base/     evidence-source assets
  knowledge-graph/    provenance and relation assets
  truth-layer/        truth and evidence-state assets
  patient-eval/       multi-turn patient evaluation
  oracles/            Oracle-related assets
  evaluation/         evaluation assets
  stage-evals/        stage-level validation reports

scripts/
  patient_eval/       patient-evaluation runtime and utilities
  s2_*                source-routing components
  s3_*                semantic-extraction components
  s4_*                temporal truth components

docs/
  BENCHMARK_DESIGN.md benchmark methodology and roadmap
  handoffs/           implementation status and handoff records
  taskbooks/          scoped engineering task specifications
```

## Current limits

As of the current development state:

- no real medical-model performance claim is made from this repository;
- clinical gold approval is incomplete;
- cross-family and multi-instance validation is incomplete;
- L0–L3 pressure levels still require construct validation;
- LLM-based judging, where used, should not be treated as a substitute for physician-validated gold;
- development cases do not establish real-patient benefit or deployment safety;
- this project is not intended to provide patient diagnosis or treatment advice.

These limitations are part of the evaluation record rather than exceptions to it.

## Documentation

- [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) — failure-driven benchmark methodology, experiment design, Oracle–Rubric–Verifier architecture, pressure gradients and roadmap.
- [`medical/patient-eval/STAGE_DECOMPOSITION.md`](medical/patient-eval/STAGE_DECOMPOSITION.md) — patient-evaluation stages, engineering stages and acceptance boundaries.
- [`medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md`](medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md) — source search and evidence verification.
- [`medical/knowledge-graph/HOW_IT_IS_BUILT.md`](medical/knowledge-graph/HOW_IT_IS_BUILT.md) — knowledge-graph construction.
- [`medical/patient-eval/pilot/v0.2/README.md`](medical/patient-eval/pilot/v0.2/README.md) — collection and scoring materials.
- [`docs/handoffs/2026-09-09-candidate-review-handoff.md`](docs/handoffs/2026-09-09-candidate-review-handoff.md) — validated work, evidence boundaries and pending tasks.

## Development note

Problem definition, medical constraints, experimental design and acceptance criteria are human-directed. Implementation and software testing use agent-assisted development. Repository claims are limited to artifacts and validation evidence that can be inspected here.