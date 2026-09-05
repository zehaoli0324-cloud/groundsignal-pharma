# GroundSignal Medical Track

This directory is the clinical/model-development extension of GroundSignal and the core of the **Knowledge-Graph-Grounded Medical Model Evaluation Platform**.

The existing `pharma/` directory remains the real-world biopharma evidence track. `medical/` adds the layers required to turn evidence and realistic user needs into model-development assets:

```text
Real user needs
→ de-identified / synthetic clinical scenarios
→ paragraph-level medical truth
→ case-local medical knowledge graph
→ Model / RAG / Agent harness runs
→ answer + retrieval + trajectory evaluation
→ failure taxonomy
→ intervention routing
→ SFT / preference / Agent-trajectory / Judge candidates
→ held-out regression gate
```

## Modules

- `clinical-track/` — patient-case task design: medical QA, clinical reasoning, medication safety, report interpretation, longitudinal reasoning, multi-turn and Agent tasks.
- `user-tasks/` — realistic user-problem discovery, 48 initial designer-generated task hypotheses, and user-research validation plan.
- `truth-layer/` — paragraph-level guideline / label / regulator / literature evidence with temporal validity and contradiction handling.
- `knowledge-graph/` — task-oriented clinical evidence graph: patient state, medical rules, evidence passages, temporal supersession and graph-grounded evaluation paths.
- `evaluation/` — answer-, graph-, retrieval-, Agent- and safety-level evaluation protocol.
- `schemas/` — machine-readable schemas for cases, evidence passages and run records.
- `configs/` — model-matrix and intervention configuration examples.
- `examples/` — de-identified/synthetic vertical-slice fixtures.

Post-training interfaces live in top-level `posttrain/` and preserve case/evidence/failure provenance for SFT, preference, Agent trajectory and Judge data.

## Platform evaluation philosophy

The platform uses three layers:

```text
Layer A — Real User Tasks
Can the model actually help with a realistic medical task?

Layer B — Capability Probes
Why did it succeed or fail: knowledge, evidence, reasoning, retrieval, tool use, uncertainty?

Layer C — Safety Stress Tests
Which failures must block release even when the average score improves?
```

One high-quality scenario family should generate a base case, controlled variants, safety/adversarial variants and optional multi-turn/RAG/Agent variants rather than becoming one isolated QA item.

## Knowledge graph role

The graph is not a decorative visualization and is not intended to become a complete medical ontology before evaluation can start.

It acts as a versioned **truth substrate** for:

- required and forbidden clinical relations;
- paragraph-level provenance;
- temporal guideline/label changes;
- retrieval ground truth;
- acceptable reasoning paths;
- unsupported-edge detection;
- post-training data provenance;
- LiveEval triggers when evidence changes.

See `medical/knowledge-graph/README.md` and `docs/14-kg-grounded-medical-eval-platform.md`.

## Real user task strategy

The current `SEED_TASK_BANK.md` contains 48 task hypotheses spanning medication safety, triage, clinical reasoning, report interpretation, evidence comparison, multi-turn, Agent and multimodal-ready scenarios.

These are **not claimed to be validated real-user tasks**. They are hypotheses to be confirmed, modified or rejected through interviews/surveys and workflow research. The first production-quality suite should prioritize 12-20 scenario families and create controlled variants rather than scaling immediately to hundreds of loosely designed questions.

## Safety and data boundary

This repository is a research/evaluation system, not a patient-facing clinical decision system.

Do not commit identifiable patient information. Clinical fixtures must be public, licensed, de-identified or synthetic. A benchmark answer is not a substitute for clinical care. High-risk medication, diagnosis and escalation errors should be represented as explicit `critical_errors` and used as release-gate blockers.

## Current vertical-slice milestone

The v0.1 pipeline already demonstrates the software/data contract for one fully traceable medication-safety fixture:

1. paragraph-level truth;
2. clinical task;
3. baseline and candidate harness runs;
4. structured evaluation;
5. failure diagnosis;
6. intervention recommendation;
7. post-training data candidate;
8. regression gate decision.

The fixture is not evidence that a real model has already been improved through post-training. The next milestone is to run real model configurations and validate a real intervention on held-out variants.

See:

- `docs/12-medical-model-development-architecture.md`
- `docs/13-medical-model-development-roadmap.md`
- `docs/14-kg-grounded-medical-eval-platform.md`
- `medical/user-tasks/SEED_TASK_BANK.md`
- `medical/user-tasks/USER_RESEARCH_PLAN.md`
- `medical/evaluation/README.md`
- `posttrain/README.md`
