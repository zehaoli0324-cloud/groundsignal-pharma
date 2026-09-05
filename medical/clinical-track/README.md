# Clinical Track v0.1

## Goal

Extend GroundSignal from drug-development intelligence to clinical model evaluation and development.

This track is deliberately task-centric rather than disease-count-centric. The objective is not to collect many diagnoses; it is to expose clinically meaningful model behaviors and failure modes.

## Initial task families

### C1 — Medical QA
Tests factual medical questions under explicit evidence conditions.

Primary capabilities:
- factual correctness;
- source hierarchy;
- evidence sufficiency;
- uncertainty calibration;
- freshness when guidance changes.

### C2 — Clinical reasoning
Given a de-identified case state, require the model to organize a differential, identify discriminating evidence and explain what would change the ranking.

Primary capabilities:
- symptom/sign integration;
- discriminative reasoning;
- alternative hypotheses;
- avoiding premature closure;
- calibrated uncertainty.

The gold behavior does not always require a single final diagnosis.

### C3 — Medication safety
Given medication list + relevant clinical context, identify medication-related risks and the evidence needed before making a recommendation.

Primary capabilities:
- contraindication / interaction awareness;
- dose/context sensitivity;
- avoiding unsupported medication changes;
- escalation and clarification behavior.

A high-confidence unsafe medication recommendation is a critical error.

### C4 — Report interpretation
Inputs may include laboratory panels, pathology text, imaging reports or other structured/unstructured medical reports.

Primary capabilities:
- extracting abnormalities;
- separating observation from inference;
- recognizing missing context;
- avoiding diagnosis from a single nonspecific finding.

### C5 — Longitudinal reasoning
Cases contain an ordered timeline of symptoms, treatments, tests and state changes.

Primary capabilities:
- temporal consistency;
- recognizing new vs old findings;
- treatment-response interpretation;
- detecting when an earlier claim has become stale or superseded.

### C6 — Multi-turn clarification
The model receives an incomplete initial presentation and must decide whether to answer, ask a clarifying question, retrieve evidence or escalate.

Primary capabilities:
- information value;
- useful abstention;
- conversational state tracking;
- non-repetitive questioning.

### C7 — Medical Agent / tool use
The task requires structured use of one or more tools such as evidence retrieval, calculator, terminology lookup or structured record search.

Primary capabilities:
- tool selection;
- valid arguments;
- using returned evidence rather than prior assumptions;
- stopping when enough evidence is available;
- avoiding unsafe tool-triggered actions.

### C8 — Multimodal-ready task manifest
The v0.1 schema stores image/report references and modality metadata even when images are not yet distributed with the repository.

Primary capabilities to add later:
- image + text evidence integration;
- discordance between report text and visual findings;
- modality-aware uncertainty;
- multimodal hallucination checks.

---

## Clinical case design rules

1. **No hidden patient identity.** Use public/licensed, de-identified or synthetic cases only.
2. **Freeze the evidence state.** Record exactly what information the model receives.
3. **Separate observation from diagnosis.** Labs/reports are evidence, not automatically the gold conclusion.
4. **Pre-register critical errors.** Especially unsafe medication, false reassurance, fabricated findings and unjustified diagnostic certainty.
5. **Gold behavior may be conditional.** Correct behavior can be: ask for data, rank a differential, retrieve a guideline, abstain, or escalate.
6. **Do not reward verbosity.** Decision-relevant correctness and safety dominate answer length.
7. **Use held-out variants.** Demographic wording, distractors, temporal ordering and irrelevant history should vary without changing the underlying capability target.

---

## Minimal case lifecycle

```text
case proposal
→ source / provenance review
→ de-identification / licensing check
→ evidence snapshot freeze
→ gold behavior + critical-error preregistration
→ baseline model run
→ blinded evaluation
→ failure diagnosis
→ intervention
→ held-out regression
```

## v0.1 target

Build 6–12 high-quality cases across C1–C7 before scaling. Each case should have 2–4 controlled variants so the benchmark measures behavior rather than memorized wording.
