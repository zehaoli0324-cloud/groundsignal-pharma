# GroundSignal — Knowledge-Graph-Grounded Medical Model Evaluation Platform

> Status: platform architecture v0.1
> Date: 2026-09-05

## 1. Product definition

GroundSignal is evolving into a **knowledge-graph-grounded medical model evaluation and development platform**.

It is not a static medical QA benchmark and not merely a knowledge graph. The platform combines:

1. a versioned medical evidence / knowledge graph;
2. realistic user tasks and clinical cases;
3. reproducible Model / RAG / Agent execution;
4. answer-, retrieval-, trajectory- and safety-level evaluation;
5. failure diagnosis and post-training data generation;
6. held-out regression before a model/system change is accepted.

```text
Real user needs / clinical workflows
            ↓
User Task Bank
            ↓
Clinical Case + Evidence Snapshot
            ↓
Medical Knowledge Graph / Truth Layer
            ↓
Model / RAG / Agent Harness
            ↓
Response + Retrieval + Tool Trajectory
            ↓
Multi-layer Evaluation
            ↓
Failure Taxonomy
            ↓
Intervention Router
            ↓
Prompt / RAG / SFT / Preference / Agent / Judge
            ↓
Candidate model/system
            ↓
Held-out Regression Gate
```

## 2. Why the knowledge graph matters

A medical benchmark without a structured truth layer often has three limitations:

- gold answers become static text and quickly go stale;
- evaluators can score whether wording resembles a reference but not whether the reasoning path is supported;
- retrieval and Agent behavior cannot be evaluated against the same truth used to evaluate the final answer.

GroundSignal therefore treats the graph as a **versioned truth substrate** rather than a visualization feature.

### Core graph objects

```text
PATIENT_CASE
SYMPTOM / SIGN
DISEASE / CONDITION
LAB / VITAL
IMAGING_FINDING
MEDICATION
DRUG_CLASS
INDICATION
CONTRAINDICATION
INTERACTION
GUIDELINE_RECOMMENDATION
LABEL_RECOMMENDATION
TEST / PROCEDURE
DIFFERENTIAL
RISK_FACTOR
EVIDENCE_PASSAGE
DOCUMENT_VERSION
TEMPORAL_EVENT
```

### Core relationships

```text
HAS_SYMPTOM
HAS_FINDING
HAS_LAB
TAKES
INDICATED_FOR
CONTRAINDICATED_IN
INTERACTS_WITH
SUPPORTED_BY
RECOMMENDED_BY
REQUIRES_TEST
RULES_IN / RULES_OUT
HAS_DIFFERENTIAL
PRECEDES / SUPERSEDES
MENTIONS / ENTAILS / CONTRADICTS
```

Every clinically important relation should be traceable to `EVIDENCE_PASSAGE` and a document version/date where applicable.

## 3. Three evaluation layers

### Layer A — Real user tasks

Question: **Can the model help a real user accomplish the task?**

Examples:

- patient asks whether a medication is safe with current renal function;
- physician asks for a differential diagnosis and what information would discriminate alternatives;
- user asks what an abnormal lab/report means and what is urgent vs non-urgent;
- clinician asks for a concise evidence-grounded treatment comparison;
- multi-turn user provides incomplete information and expects the model to ask the right clarification;
- Medical Agent is expected to retrieve a current label/guideline before answering.

Primary outputs:

- task success;
- decision usefulness;
- completeness;
- communication quality;
- calibrated uncertainty;
- safety.

### Layer B — Capability probes

Question: **Why did the model succeed or fail?**

Examples:

- factual correctness;
- evidence sufficiency;
- source hierarchy;
- temporal validity;
- differential reasoning;
- causal vs correlational reasoning;
- claim-scope calibration;
- clarification behavior;
- retrieval selection;
- tool selection;
- cross-turn state tracking.

One realistic user task can generate multiple controlled capability probes.

### Layer C — Safety stress tests

Question: **Which errors must block release even if average quality improves?**

Examples:

- contraindicated medication recommendation;
- unsupported dosing change;
- failure to escalate a red-flag symptom;
- false reassurance;
- inventing missing patient information;
- converting an adverse-event signal into causal certainty;
- using stale/superseded guideline or label information when a current version is available.

Critical safety failures are release-gating events rather than ordinary score deductions.

## 4. Do we need many user questions?

Yes, but the unit of scale should be **user scenario families**, not isolated questions.

A strong case should generate:

```text
1 realistic user scenario
→ 1 primary task
→ 3-8 capability probes
→ 2-5 controlled variants
→ 1-3 safety stress variants
→ optional multi-turn / Agent / RAG variants
```

Therefore 100 high-quality scenario families can produce several hundred to >1,000 meaningful evaluation items without creating 1,000 unrelated exam questions.

## 5. User-task sampling dimensions

Each case should be tagged along independent axes so coverage can be audited.

### User role

- Patient / caregiver
- General clinician
- Specialist clinician
- Pharmacist
- Medical affairs / evidence user

### Task family

- Medical QA / education
- Symptom triage
- Clinical reasoning / differential
- Medication safety
- Drug interaction / contraindication
- Report / laboratory interpretation
- Treatment evidence comparison
- Longitudinal follow-up
- Multi-turn clarification
- Medical Agent / tool use
- Multimodal-ready interpretation

### Difficulty / risk

- low / medium / high reasoning complexity
- low / medium / critical safety risk
- sufficient / incomplete / contradictory evidence
- static / time-sensitive truth
- single-hop / multi-hop graph reasoning

## 6. Graph-grounded evaluation

The graph enables evaluation beyond final-answer similarity.

### Answer metrics

- Factual Correctness
- Evidence Sufficiency
- Claim Scope Accuracy
- Temporal Validity
- Uncertainty Calibration
- Safety
- Task Usefulness
- Communication / Audience Fit

### Retrieval metrics

- Evidence Recall@K
- Evidence Precision@K
- Critical-Passage Recall
- Source-Hierarchy Accuracy
- Freshness / Current-Version Recall

### Graph reasoning metrics

- Required-node coverage
- Required-edge coverage
- Unsupported-edge rate
- Valid reasoning-path rate
- Contradiction detection recall
- Temporal supersession accuracy

### Agent metrics

- Tool Selection Accuracy
- Query Quality
- Retrieval-before-claim compliance for high-risk questions
- Tool-result utilization
- Unnecessary-tool rate
- Step efficiency
- Stop / abstain correctness

### Safety gates

- Critical Unsafe Recommendation Rate
- Contraindication Miss Rate
- Unsupported Dose/Medication Change Rate
- Red-flag Miss Rate
- Fabricated Patient Fact Rate
- Stale Critical Evidence Rate

## 7. Gold is a graph-constrained behavior, not one paragraph

A case should not require exact wording. Gold should describe:

```yaml
must_include_claims: []
must_not_claim: []
required_evidence_passages: []
acceptable_reasoning_paths: []
required_clarifications: []
critical_errors: []
uncertainty_expectation: []
user_action_boundary: []
```

This lets different good answers receive full credit while still rejecting clinically dangerous or unsupported answers.

## 8. Relationship to RAG and Agent evaluation

For the same case, run multiple configurations:

```text
A. Closed-book model
B. Evidence-in-context
C. RAG
D. RAG + reranker
E. Agent with medical tools
```

The same graph truth then allows attribution:

```text
final answer wrong
├─ graph/evidence missing?         → truth/data issue
├─ retriever missed evidence?      → retrieval issue
├─ evidence retrieved but ignored? → generation/reasoning issue
├─ wrong tool chosen?              → Agent issue
└─ answer correct but judge wrong? → judge calibration issue
```

## 9. Dataset split discipline

Do not randomly split near-duplicate cases.

Use scenario-family / evidence-family splits:

- `train`: intervention data;
- `dev`: prompt/router/data development;
- `heldout`: unseen variants and scenario families;
- `safety_regression`: frozen critical cases;
- `temporal_live`: cases whose correct answer can change with evidence updates.

## 10. Target scale

### Stage 1 — platform proof

- 12-20 scenario families
- 60-120 eval items
- 4 major task families
- 2-3 real model configurations

### Stage 2 — useful medical evaluation suite

- 50-100 scenario families
- 300-800 eval items
- all major task families
- multi-turn + RAG + Agent tracks

### Stage 3 — continuously maintained platform

- 200+ scenario families
- 1,000+ evaluation items
- versioned knowledge graph and live evidence updates
- held-out and temporal regression suites
- expert/Judge-calibrated scoring

Scale is not the first objective. **Truth quality, case realism, failure discrimination and repeatable diagnosis come first.**

## 11. Platform success criteria

GroundSignal should eventually answer five questions for every model version:

1. **What real medical tasks can it complete?**
2. **Where does it fail and how severe is the failure?**
3. **Is the failure caused by knowledge, retrieval, reasoning, tool use, calibration, or evaluation?**
4. **Which intervention should be attempted?**
5. **Did the intervention improve held-out performance without introducing a safety regression?**
