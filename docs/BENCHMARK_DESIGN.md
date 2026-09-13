# GroundSignal Pharma — Benchmark Design

> **Status:** methodology specification. This document separates planned benchmark design from functionality already implemented in the repository.

## 1. Goal

GroundSignal is moving from static medical-question evaluation toward a failure-driven benchmark for evidence-dependent clinical decision making. The benchmark is intended to measure **where a medical AI system begins to fail**, not only whether its final answer matches a reference.

The central design is:

**Clinical decision chain → failure hypothesis → controlled experiment → pressure gradient → node-specific Oracle → Rubric → modular Verifier → repeated runs → failure profile / capability boundary**

## 2. Clinical decision chain

A patient–AI interaction is decomposed into observable stages: problem recognition, fact extraction, negation/uncertainty handling, evidence-source recognition, evidence weighting, missing-information detection, question selection, competing explanations, evidence update, risk assessment, action selection, escalation, and longitudinal revision.

Failure hypotheses should be attached to a stage in this chain whenever possible. This avoids building a taxonomy from ad-hoc error labels.

## 3. Experimental unit

The benchmark unit is not a single question. The hierarchy is:

**decision stage → failure type → failure hypothesis → experiment family → controlled variants → query → dialogue nodes → repeated runs**

A failure hypothesis should be tested with several controlled variants. For example, premature diagnostic certainty can be tested with complete information, incomplete information, counterfactual branches sharing the same early history, irrelevant-information variants, and paraphrases that preserve clinical facts.

Two forms of repetition are distinct:

- **Experimental replication:** multiple cases or variants test whether a failure generalizes.
- **Run replication:** the same instance is run repeatedly to measure stochastic reliability. The pilot can begin with approximately three independent runs per instance and adjust later based on observed variance.

Severe safety failures must be reported separately rather than averaged away.

## 4. Patient simulator

The first benchmark version uses a **deterministic script plus finite-state machine (FSM)** rather than a freely generating patient model.

1. A case truth store fixes symptoms, timing, tests, negative findings, history, medication and what the patient knows.
2. The FSM controls the current node, what may be disclosed, and what must remain hidden.
3. Deterministic language templates express permitted facts.

A language model may later paraphrase permitted facts, but it must not add, remove or change clinical facts.

## 5. Shortcut and temporal validity

Final-answer correctness is insufficient evidence of valid reasoning. A model that predicts a later diagnosis before the available evidence supports that certainty should not receive retrospective credit simply because the diagnosis later becomes true.

The benchmark therefore uses:

- node-truncated scoring;
- counterfactual branches;
- surface-form perturbations with clinical facts held fixed;
- evidence-timing consistency.

Core principle: **do not reward hindsight correctness; reward decisions justified by the evidence available at that time.**

## 6. Strategy, algorithm and engineering failures

Failures are separated when evidence permits:

- **Strategy:** the governing decision principle is inappropriate.
- **Algorithm:** the computation implementing a reasonable strategy is wrong, e.g. ranking, thresholding, evidence weighting, conflict resolution or uncertainty estimation.
- **Engineering:** a sound strategy/algorithm is not executed correctly, e.g. state loss, field mapping errors, negation inversion, stale scores, context truncation or tool failures.

Attribution must allow `UNRESOLVED` when observable evidence cannot distinguish these causes.

## 7. Pressure gradients

Stress testing is not synonymous with making a case maximally difficult. Each pressure axis should have reproducible operational levels and change one principal variable at a time.

Initial axes include information loss, language noise, irrelevant information, conflicting evidence, dialogue length, patient corrections, paraphrase variation, multitask load and tool/engineering degradation.

A provisional four-level scheme is:

- **L0:** clean baseline;
- **L1:** one mild perturbation while key evidence remains directly available;
- **L2:** evidence becomes dispersed, ambiguous or competitively framed and requires active integration;
- **L3:** key evidence is sparse, indirect or surrounded by substantial noise, while the task remains clinically answerable.

L3 must not become an impossible or underdetermined question. Pressure levels require later construct validation.

The important output is not merely error under stress, but the relationship:

**pressure level → failure rate/severity → instability threshold → capability boundary**.

## 8. Oracle

The Oracle is a node-specific clinical adjudication specification, not a single canonical answer. It should define:

- facts visible and hidden at the node;
- risks that must be recognized;
- required and optional questions;
- actions that may be given immediately;
- acceptable action sets;
- conclusions not yet justified;
- prohibited/dangerous actions;
- action deadlines;
- evidence that should force later revision.

Oracle uncertainty must be represented rather than hidden. Multiple clinical actions may be acceptable.

## 9. Rubric

The pilot Rubric follows the clinical decision chain rather than generic dimensions such as fluency. Initial dimensions include fact extraction, negation/uncertainty, critical questions, evidence source, evidence weighting, evidence conflict, evidence update, temporal consistency, risk assessment, action selection and certainty calibration.

Scoring has two layers:

1. **Safety gate / blocker:** predefined severe failures are recorded separately and cannot be averaged away.
2. **Capability profile:** remaining dimensions are scored after the safety state is preserved.

The pilot may use deterministic rules plus constrained LLM judges. LLM judges are automation aids, not clinical gold. They should answer narrow questions and return `PASS | FAIL | UNCERTAIN` with an evidence span and reason rather than an unconstrained overall score.

## 10. Verifier

The target architecture is a **unified Verifier engine with modular capability checkers**.

Reusable checkers may include information-boundary, negation, temporal-consistency, deadline, state-consistency and safety-blocker checks. Capability-specific checkers may include critical-question, overconfidence, evidence-source, evidence-weight, evidence-conflict, evidence-update, risk-escalation, counterfactual-consistency and robustness checks.

Experiment families and checkers form a many-to-many relation: an experiment can call several checkers, and a checker can be reused across diseases and patient stages.

A structured failure record should preserve at least case, experiment family, pressure axis/level, run, node, decision-chain stage, failure type, rubric item, checker, verdict, severity, blocker status, evidence span, reason and Oracle version.

## 11. Measurement validity

The benchmark itself must be tested. For every claimed capability effect, competing explanations should be considered. For example, an irrelevant-information experiment may need length-matched relevant and neutral controls to distinguish noise from simple context-length effects.

Future validation should address construct validity, content validity, discriminant validity, test–retest reliability, judge/human agreement, item discrimination, ceiling/floor effects, calibration and measurement invariance across diseases, populations and models.

The benchmark should also be attacked deliberately: always-escalate strategies, blanket refusal, excessively long answers, judge-style gaming, benchmark recognition and post-hoc reasoning should be tested as potential shortcuts.

## 12. M0–M5 roadmap

- **M0:** complete one reference-family Oracle and adjudication chain.
- **M1:** run real models and test whether the measurement system can expose meaningful failures.
- **M2:** freeze the Benchmark Contract: schemas, disclosure rules, Rubric, Verifier interfaces, blockers, splits and repetition rules.
- **M3:** transfer the experimental skeleton to additional scenarios.
- **M4:** run a frozen multi-model pilot and produce decision-stage/failure/pressure analyses.
- **M5:** scale only after validity, reproducibility and discrimination have been demonstrated.

The proposed first reference family is **acute stroke-related patient consultation**, selected to test symptom recognition, time-sensitive evidence, critical questioning, risk escalation, evidence update and delay-sensitive decisions. This reference family is a design target, not yet a validated benchmark result.

## 13. Long-term direction

The longer-term trajectory is:

**Medical Benchmark → Medical AI Evaluation Engine → Medical AI Validation Infrastructure → high-risk AI measurement infrastructure.**

The desired product of evaluation is a capability boundary that can inform a deployment boundary: what can be automated, what requires human review, and what should remain outside autonomous operation.

This is a research roadmap. Current repository claims must remain limited to implemented and validated assets documented in the main README.