# GroundSignal Medical — 10-Stage System Lifecycle

> Version: v0.1  
> Date: 2026-09-05

GroundSignal Medical is organized as a **10-stage model-development lifecycle**. The stages separate user-need discovery, medical truth construction, model execution, evaluation, post-training, and regression so that a failure can be traced end to end.

```text
S1  User Need / Workflow Discovery
 ↓
S2  Knowledge Search & Source Routing
 ↓
S3  Evidence Verification & Temporal Truth
 ↓
S4  Medical Knowledge Graph Construction / Update
 ↓
S5  Controlled Case / Benchmark Factory
 ↓
S6  Model / RAG / Agent Execution Harness
 ↓
S7  Multi-layer Evaluation & Safety Gate
 ↓
S8  Failure Diagnosis & Capability Hypothesis
 ↓
S9  Intervention / Post-training Data Generation
 ↓
S10 Candidate Model/System + Held-out Regression
  └──────────────────────────────→ back to S2/S4/S5/S8 as needed
```

---

## S1 — User Need / Workflow Discovery

Question:

> What do real users actually need the medical model to do?

Inputs:

- patient/caregiver questions;
- clinician/pharmacist workflows;
- medical-agent tasks;
- real bad-case patterns;
- user interviews / questionnaires;
- product logs when legally/ethically available and de-identified.

Outputs:

- user-task taxonomy;
- scenario families;
- frequency / severity / AI-value prioritization;
- high-risk task list.

Current assets:

- `medical/user-tasks/SEED_TASK_BANK.md`
- `medical/user-tasks/HIGH_RISK_USER_QUESTION_MATRIX.md`
- user-research plan.

---

## S2 — Knowledge Search & Source Routing

Question:

> Which source should be searched for this exact type of claim?

Examples:

```text
drug identity              → RxNorm
current US dose/warning     → DailyMed / Drugs@FDA
CYP/transporter role        → FDA DDI resources
PGx                         → FDA PGx + current label
trial state                 → ClinicalTrials.gov
lab identity                → LOINC
China regulatory truth      → NMPA/CDE
clinical guideline          → current professional/national guideline
postmarketing signal        → FAERS, signal only
```

Outputs:

- candidate source documents;
- source IDs;
- versions/dates/jurisdiction;
- retrieval trace.

Current assets:

- `medical/knowledge-base/SOURCE_REGISTRY.json`
- `medical/knowledge-base/SOURCE_REGISTRY_SUPPLEMENT.json`
- `medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md`

---

## S3 — Evidence Verification & Temporal Truth

Question:

> Does this exact source passage support this exact claim at this exact time?

Process:

```text
source
→ document version
→ locator / passage
→ atomic claim
→ claim scope
→ evidence role
→ temporal status
→ contradiction / supersession check
→ review status
```

Review lifecycle:

```text
DISCOVERED
→ MACHINE_PARSED
→ SOURCE_VERIFIED
→ DOMAIN_REVIEWED
→ GOLD_APPROVED
```

Key rule:

> Source quality is not the same as evidence strength.

Outputs:

- evidence manifests;
- current/superseded claims;
- verified passage IDs;
- contradictions.

---

## S4 — Medical Knowledge Graph Construction / Update

Question:

> How should verified claims be represented as nodes, edges and temporal relations?

Graph layers:

1. case-local clinical graphs;
2. reusable pharmacology/safety backbone;
3. pharma temporal evidence track;
4. canonical merged medical graph.

Current graph sources:

- `medical/case-families/*/graph.json`
- `medical/knowledge-base/PHARMACOLOGY_BACKBONE_V0.1.json`
- `medical/knowledge-base/ORGAN_SPECIAL_POP_SAFETY_BACKBONE_V0.1.json`

Builder:

- `scripts/build_medical_knowledge_graph.py`

Important semantics:

```text
mechanism ≠ clinical effect ≠ management recommendation
association ≠ causality
warning ≠ diagnosis
risk factor ≠ event
trial registration ≠ efficacy
new study ≠ updated guideline
```

Outputs:

- canonical KG snapshot;
- provenance-preserving nodes/edges;
- temporal graph state;
- affected-case map for future updates.

---

## S5 — Controlled Case / Benchmark Factory

Question:

> How do we turn a real user need and verified truth into a diagnostic experiment?

One family typically contains:

```text
base
+ controlled variant
+ controlled variant
+ adversarial/regression variant
+ held-out variant
```

Each case pre-registers:

- patient/context state;
- evidence snapshot;
- required nodes/edges;
- forbidden claims/edges;
- expected reasoning path;
- critical safety errors;
- split.

Current P0:

- 12 scenario families;
- 60 controlled cases.

Outputs:

- frozen eval cases;
- held-out suites;
- regression suites.

---

## S6 — Model / RAG / Agent Execution Harness

Question:

> Under exactly what model/system configuration was this answer produced?

Record:

```text
model/provider/version
prompt version
closed-book vs evidence/RAG
retriever/reranker version
top-K
tools
Agent trajectory
temperature
snapshot ID
latency/usage
run ID
```

Current implementation:

- `scripts/model_harness.py`

Outputs:

- reproducible run records;
- responses;
- retrieval traces;
- tool trajectories.

---

## S7 — Multi-layer Evaluation & Safety Gate

Question:

> Was the whole system correct and safe, not just the final prose?

Four evaluation layers:

### E1 Answer

- factuality;
- evidence sufficiency;
- temporal validity;
- clinical reasoning;
- uncertainty;
- usefulness;
- communication;
- safety.

### E2 Knowledge-graph grounding

- required-node recall;
- required-edge recall;
- unsupported-edge rate;
- valid reasoning path;
- contradiction/supersession handling.

### E3 RAG

- Evidence Recall@K;
- Critical Passage Recall@K;
- source hierarchy;
- current-version recall.

### E4 Agent

- tool selection;
- query quality;
- result utilization;
- stop correctness;
- clarification;
- trajectory safety.

Hard rule:

> A new critical medical-safety error can block release even when average score improves.

Outputs:

- score records;
- critical errors;
- failure observations.

---

## S8 — Failure Diagnosis & Capability Hypothesis

Question:

> Why did the model/system fail?

Examples:

```text
STALE_KNOWLEDGE
RETRIEVAL_MISS
SOURCE_HIERARCHY
EVIDENCE_MISUSE
OVERCLAIM
THRESHOLD_BLUR
PREMATURE_CLOSURE
FAILURE_TO_CLARIFY
PASSIVE_ABSTENTION
BAD_TOOL_SELECTION
BAD_QUERY
TOOL_RESULT_IGNORED
OVERSEARCH
JUDGE_INCONSISTENCY
```

Discipline:

```text
Observed failure
≠
Capability gap
≠
Proven root cause
```

Outputs:

- failure taxonomy;
- capability profile;
- intervention hypothesis.

---

## S9 — Intervention / Post-training Data Generation

Question:

> What is the smallest appropriate intervention for this failure?

Routing examples:

```text
stale knowledge       → retrieval / temporal refresh
retrieval miss        → index/query/reranker
reasoning failure     → reasoning SFT
unsupported overclaim → preference data
unsafe recommendation → safety SFT + preference + gate
failure to clarify    → multi-turn SFT
bad tool selection    → Agent trajectory
judge inconsistency   → judge calibration
```

Data outputs:

- SFT;
- preference pairs;
- Agent trajectories;
- judge/reward labels;
- prompt/RAG changes.

Current assets:

- `scripts/intervention_router.py`
- `scripts/export_training_data.py`
- `posttrain/`

Rule:

> Eval failures do not automatically become training data; approved provenance is required.

---

## S10 — Candidate Model/System + Held-out Regression

Question:

> Did the intervention actually improve the intended capability without breaking something else?

Compare:

```text
baseline
vs
candidate
```

on frozen held-out/regression suites.

Check:

- target capability improvement;
- safety errors;
- factuality;
- overclaim rate;
- abstention preservation;
- RAG/Agent behavior;
- unrelated capability regressions.

Current implementation:

- `scripts/regression_gate.py`
- CI release-gate pattern.

If the candidate fails, the loop returns to the relevant stage rather than blindly adding more training data.

---

# Stage ownership view

For team collaboration, the 10 stages roughly map to:

```text
Product / User Research     S1
Data / Retrieval / Medical  S2–S4
Eval / Benchmark            S5–S8
Post-training / Algorithm   S9
Model Release / Eval        S10
```

The key value of GroundSignal is that it connects these roles with shared provenance rather than treating evaluation as the final downstream step.
