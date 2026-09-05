# GroundSignal Medical Track

This directory is the clinical/model-development extension of GroundSignal.

The existing `pharma/` directory remains the real-world biopharma evidence track. `medical/` adds the layers required to turn evidence into model-development assets:

```text
Clinical / guideline / label evidence
→ paragraph-level truth objects
→ clinical cases
→ model harness runs
→ evaluation
→ failure taxonomy
→ intervention routing
→ SFT / preference / Agent-trajectory candidates
→ regression gate
```

## Modules

- `clinical-track/` — patient-case task design: medical QA, clinical reasoning, medication safety, report interpretation, longitudinal reasoning, multi-turn and Agent tasks.
- `truth-layer/` — paragraph-level guideline / label / regulator / literature evidence with temporal validity and contradiction handling.
- `schemas/` — machine-readable schemas for cases, evidence passages and run records.
- `configs/` — model-matrix and intervention configuration examples.
- `examples/` — de-identified/synthetic vertical-slice fixtures.

## Safety and data boundary

This repository is a research/evaluation system, not a patient-facing clinical decision system.

Do not commit identifiable patient information. Clinical fixtures must be public, licensed, de-identified or synthetic. A benchmark answer is not a substitute for clinical care. High-risk medication, diagnosis and escalation errors should be represented as explicit `critical_errors` and used as release-gate blockers.

## First vertical-slice milestone

The first v0.1 milestone is one fully traceable case:

1. paragraph-level truth;
2. clinical task;
3. baseline and candidate model runs;
4. structured evaluation;
5. failure diagnosis;
6. intervention recommendation;
7. post-training data candidate;
8. regression gate decision.

See `docs/12-medical-model-development-architecture.md` and `docs/13-medical-model-development-roadmap.md`.
