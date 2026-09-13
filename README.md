# GroundSignal Pharma

**Failure-driven evaluation for medical AI under changing clinical evidence.**

GroundSignal studies where medical AI systems fail during evidence-dependent clinical decision making. Instead of treating evaluation as a collection of static medical questions, the project records how evidence is retrieved, interpreted, updated and passed through a patient–AI interaction, then uses controlled cases to localize failures.

The repository already contains evidence-routing, semantic-extraction, temporal truth tracking, controlled-case and multi-turn patient-evaluation infrastructure. A new failure-driven benchmark design is now being built on top of that foundation. Its clinical Oracle, standardized pressure gradients and model-level capability-boundary results are **not yet validated benchmark results**.

[Benchmark design](docs/BENCHMARK_DESIGN.md) · [Patient evaluation](medical/patient-eval/README.md) · [Stage decomposition](medical/patient-eval/STAGE_DECOMPOSITION.md) · [Current handoff](docs/handoffs/2026-09-09-candidate-review-handoff.md)

## What GroundSignal is trying to measure

A final medical answer can be correct even when the path to that answer is unreliable. GroundSignal therefore treats the clinical decision process itself as the object of evaluation.

The current design follows this chain:

```text
Clinical decision chain
        ↓
Failure hypothesis
        ↓
Controlled experiment / counterfactual
        ↓
Standardized pressure gradient
        ↓
Node-specific Oracle
        ↓
Rubric + modular Verifier
        ↓
Repeated runs
        ↓
Failure profile / capability boundary
```

The target questions are concrete: Did the model extract the patient's facts correctly? Did it distinguish a patient's belief from an objective test? Did it ask for information that changes the decision? Did stronger or newer evidence change its judgment? Did it become overconfident before the evidence justified certainty? Did a high-risk state trigger the right action at the right time?

The full methodology, including Oracle, Rubric, Verifier, pressure gradients, measurement validity and the M0–M5 roadmap, is kept in [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md). The design document intentionally separates planned methods from implemented claims.

## Current foundation

### Evidence and truth tracking

The repository includes source routing, semantic extraction and temporal truth tracking. Evidence is stored with provenance and can retain applicability, version and conflict information rather than treating every statement as equally reliable.

Implemented entry points include:

- [`scripts/s2_intent_router_v04.py`](scripts/s2_intent_router_v04.py) — source routing;
- [`scripts/s3_semantic_extractor.py`](scripts/s3_semantic_extractor.py) — semantic extraction;
- [`scripts/s4_truth_ledger_v011.py`](scripts/s4_truth_ledger_v011.py) — temporal truth updates;
- [`medical/knowledge-base/`](medical/knowledge-base/) and [`medical/knowledge-graph/`](medical/knowledge-graph/) — evidence and graph assets.

This evidence layer is intended to support later evaluation of evidence source, evidence weighting, conflict handling and evidence update.

### Controlled cases

The current repository contains **12 case families and 60 controlled cases**. They vary clinically relevant conditions and are accompanied by provenance, split-contamination checks and historical-result preservation. These are development assets rather than a finished clinical benchmark.

See [`medical/case-families/`](medical/case-families/) and [`medical/stage-evals/`](medical/stage-evals/).

### Multi-turn patient evaluation

The patient-evaluation prototype contains **6 families and 12 synthetic variants** covering ambiguous expression, fact correction, pressure to answer and misunderstanding repair. The interaction layer can disclose information according to the conversation and retain what was actually sent to the model.

The current implementation also separates quality/safety observations from scoring opportunities and supports paired baseline/state-enhanced comparisons.

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

## Benchmark under construction

The next benchmark iteration is **failure-driven rather than case-count-driven**. The first planned reference family is acute stroke-related patient consultation. It is intended to test time-sensitive symptom recognition, critical questioning, evidence update, risk escalation and delay-sensitive decisions.

The proposed pilot will use a deterministic patient script plus finite-state machine, node-specific acceptable-action Oracles, decision-chain Rubrics, modular Verifier checkers, controlled counterfactuals and reproducible L0–L3 pressure levels. The goal is to determine not only whether a model fails, but **which decision stage fails first and under what pressure**.

This paragraph describes the current design target. The stroke reference family, pressure-scale construct validation, physician-approved Oracle and real-model failure curves are not yet complete.

## Quick start

Python 3.11+ is recommended. The existing offline patient-evaluation demo uses the standard library and does not require an API key.

```bash
git clone https://github.com/zehaoli0324-cloud/groundsignal-pharma.git
cd groundsignal-pharma

python -m scripts.patient_eval.pilot_cli validate
python -m scripts.patient_eval.pilot_cli demo --out medical/patient-eval/local/readme-demo
```

The demo generates 24 scripted sessions. `sessions.json` preserves the dialogue, `evaluation/results.json` stores evaluation records, and `evaluation/report.html` provides a browser-readable report. Use a new output directory for a repeated run.

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
- the new failure-driven stroke reference family has not completed its M0/M1 validation loop;
- L0–L3 pressure levels are a design specification and still require construct validation;
- LLM-based judging, where used in the pilot, should not be treated as a substitute for physician-validated gold;
- development cases do not establish real-patient benefit or deployment safety;
- this project is not intended to provide patient diagnosis or treatment advice.

These limitations are part of the evaluation record rather than exceptions to it.

## Documentation

- [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) — failure-driven benchmark methodology, Oracle–Rubric–Verifier architecture, pressure gradients and roadmap.
- [`medical/patient-eval/STAGE_DECOMPOSITION.md`](medical/patient-eval/STAGE_DECOMPOSITION.md) — ten-stage decomposition and acceptance boundaries.
- [`medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md`](medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md) — source search and evidence verification.
- [`medical/knowledge-graph/HOW_IT_IS_BUILT.md`](medical/knowledge-graph/HOW_IT_IS_BUILT.md) — knowledge-graph construction.
- [`medical/patient-eval/pilot/v0.2/README.md`](medical/patient-eval/pilot/v0.2/README.md) — collection and scoring materials.
- [`docs/handoffs/2026-09-09-candidate-review-handoff.md`](docs/handoffs/2026-09-09-candidate-review-handoff.md) — validated work, evidence boundaries and pending tasks.

## Development note

Problem definition, medical constraints, experimental design and acceptance criteria are human-directed. Implementation and software testing use agent-assisted development. Repository claims are limited to artifacts and validation evidence that can be inspected here.