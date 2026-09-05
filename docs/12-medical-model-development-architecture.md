# GroundSignal — Evidence-Grounded Medical Model Development Architecture

> Status: architecture v0.1
> Date: 2026-09-05

## 1. Repositioning

GroundSignal Pharma is evolving from a **Pharma Intelligence System** into an **Evidence-Grounded Medical Model Development System**.

The existing `pharma/` graph is preserved as the first mature evidence domain. The new system adds a clinical/model-development layer around it:

```text
Medical / Pharma Sources
        ↓
Evidence & Temporal Truth Layer
        ↓
Medical Task Factory
        ↓
Model / RAG / Agent Harness
        ↓
Evaluation & Safety Gates
        ↓
Failure Diagnosis
        ↓
Intervention Router
        ↓
Retrieval / Prompt / SFT / Preference / Agent-trajectory / Judge changes
        ↓
New Model Version
        ↓
Regression Gate
        └────────────────────────────→ loop
```

The project is **not** claiming to train a medical foundation model. Its role is to build the evidence, evaluation, diagnosis, training-data and regression infrastructure that can drive model iteration.

---

## 2. Full development loop

```text
┌──────────────────────────────────────────────────────────────┐
│                     SOURCE / EVIDENCE                        │
│ Guidelines · Drug labels · Regulatory docs · PubMed          │
│ ClinicalTrials · case materials · reports · pharma sources   │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│              EVIDENCE & TEMPORAL TRUTH LAYER                 │
│ passage_id · source · section · claim · valid_time            │
│ evidence role · hierarchy · contradiction · supersession      │
│ OBSERVED / DERIVED / HYPOTHESIS                              │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│                    MEDICAL TASK FACTORY                      │
│ medical QA · clinical reasoning · medication safety          │
│ report interpretation · evidence sufficiency · longitudinal  │
│ multi-turn · tool use · multimodal-ready task schemas         │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│                  MODEL / RAG / AGENT HARNESS                 │
│ model_id · provider · version · prompt_version                │
│ RAG on/off · tools · temperature · snapshot_id · run_id       │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│                 EVALUATION & SAFETY GATES                    │
│ deterministic checks · expert rubric · calibrated judge       │
│ factuality · evidence sufficiency · temporal validity         │
│ reasoning · uncertainty · medication/clinical safety          │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│                    FAILURE DIAGNOSIS                         │
│ stale knowledge · missing knowledge · reasoning failure       │
│ overclaim · bad tool use · retrieval failure · judge drift    │
│ unsafe recommendation · audience mismatch · expression        │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
                     INTERVENTION ROUTER
             ┌─────────────────┼──────────────────────┐
             ↓                 ↓                      ↓
         Retrieval           Prompt              Data / Training
      index/query/rank     policy/template      MidTrain/SFT/Pref
             │                 │                      │
             └─────────────────┼──────────────────────┘
                               ↓
                       NEW SYSTEM VERSION
                               ↓
┌──────────────────────────────────────────────────────────────┐
│                       REGRESSION GATE                        │
│ capability delta · safety delta · factuality delta            │
│ critical-error count · abstention calibration · no-regress    │
└──────────────────────────────┬───────────────────────────────┘
                               └────────────────────────→ loop
```

---

## 3. Two domain tracks

### Track P — Pharma / drug-development intelligence

Existing assets remain useful for:

- regulatory-state freshness;
- trial and approval temporal truth;
- source hierarchy;
- claim-evidence alignment;
- pipeline / target / indication reasoning;
- medical evidence overclaim and contradiction tests.

The existing `pharma/` directory is therefore retained as a **real-world temporal evidence track**, not deprecated.

### Track C — Clinical model development

The new `medical/` directory expands the model-development surface to:

1. medical QA;
2. differential/clinical reasoning tasks;
3. medication safety;
4. laboratory and report interpretation;
5. longitudinal disease-course reasoning;
6. multi-turn clarification and uncertainty management;
7. medical Agent/tool-use tasks;
8. multimodal-ready task manifests (image bytes are not required for the first schema version).

The clinical track must use de-identified, public, synthetic, licensed or otherwise appropriately usable data. It must not store identifiable patient information.

---

## 4. Truth is passage-level, not URL-level

Old prototype:

```text
claim → source_url
```

Target architecture:

```text
claim
  → evidence_passage_id
      → source_id
      → document version/date
      → section / paragraph / table
      → quoted span or normalized proposition
      → evidence role
      → valid_from / valid_to
      → source hierarchy
      → contradiction / supersession links
```

This matters because "there is a URL" does not prove that the cited document entails the claim.

### Evidence roles

- `DIRECT_SUPPORT`
- `PARTIAL_SUPPORT`
- `CONTRADICTS`
- `CONTEXT_ONLY`
- `DOES_NOT_SUPPORT`
- `SUPERSEDES`

### Source roles

- guideline / consensus;
- drug label / regulator;
- clinical trial registry;
- peer-reviewed study;
- systematic review / meta-analysis;
- company disclosure;
- media / discovery lead.

`source_quality != evidence_strength` remains a hard rule.

---

## 5. Clinical task object

Every clinical case should separate patient state, evidence available to the model, expected behavior and safety boundaries.

```yaml
case_id: clinical-xxx
task_type: medical_qa | clinical_reasoning | medication_safety | report_interpretation | longitudinal | agent
patient_context:
  demographics: deidentified
  chief_complaint: ...
  history: ...
  medications: ...
  examination: ...
  labs: []
  imaging_reports: []
  longitudinal_events: []
evidence_snapshot:
  allowed_passage_ids: []
interaction:
  mode: single_turn | multi_turn
  prior_turns: []
expected_behavior:
  must_include: []
  must_not_claim: []
  uncertainty_behavior: ...
  escalation_or_clarification: ...
safety:
  critical_errors: []
scoring:
  rubric_version: ...
```

For diagnostic tasks, the gold should not always be a single disease string. Depending on the task, correct behavior can be a ranked differential, an information-gathering action, explicit uncertainty, or escalation.

---

## 6. Harness contract

A model run must be reproducible:

```yaml
run_id: ...
case_id: ...
model_id: ...
provider: ...
model_version: ...
prompt_version: ...
rag:
  enabled: true
  retriever_version: ...
  top_k: 8
tools:
  enabled: []
temperature: 0
snapshot_id: ...
response: ...
latency_ms: ...
```

The harness must support at least:

- closed-book model;
- evidence-in-context model;
- RAG-enabled model;
- tool/Agent mode;
- multiple providers through adapters.

---

## 7. Intervention Router

A failure is an observation. An intervention is a hypothesis. The router must preserve this distinction.

| Failure cluster | First intervention candidates | Regression target |
|---|---|---|
| STALE_KNOWLEDGE | retrieval / temporal truth | freshness, stale-claim rate |
| KNOWLEDGE_MISSING | retrieval first; data/MidTrain if systematic | factual coverage |
| RETRIEVAL_MISS | index/query/reranker | evidence recall@k |
| SOURCE_HIERARCHY | source-aware retrieval / hard negatives / SFT | hierarchy accuracy |
| REASONING_FAILURE | SFT / reasoning exemplars / task decomposition | held-out reasoning |
| OVERCLAIM | preferred-rejected pairs / uncertainty policy | claim-scope, calibration |
| UNSAFE_MEDICATION | safety data + hard gate + expert review | critical safety errors |
| BAD_TOOL_CALL | Agent trajectory data / tool schema / policy | tool success, unsafe-call rate |
| PASSIVE_ABSTENTION | uncertain-but-actionable preference data | useful abstention |
| JUDGE_INCONSISTENCY | judge calibration / anchors / human adjudication | judge-human agreement |

The router must allow multiple candidate interventions and should not silently equate every failure with "add training data".

---

## 8. Training-data export

Evaluation artifacts can be transformed into post-training candidates only after review.

### SFT candidate

```json
{
  "instruction": "...",
  "context": {"evidence": ["passage-id"]},
  "ideal_response": "...",
  "failure_type": "REASONING_FAILURE",
  "source_case_id": "...",
  "review_status": "approved"
}
```

### Preference candidate

```json
{
  "prompt": "...",
  "chosen": "calibrated, evidence-grounded response",
  "rejected": "overclaimed response",
  "failure_type": "OVERCLAIM",
  "source_case_id": "...",
  "review_status": "approved"
}
```

Data provenance must preserve the originating case, evidence snapshot, reviewer and rubric version.

---

## 9. Regression gate

Each candidate model/system version is compared against a frozen baseline.

Minimum gates:

- no increase in critical clinical/medication safety errors;
- factuality does not regress beyond tolerance;
- evidence sufficiency / claim scope does not regress;
- temporal validity does not regress;
- calibrated abstention is not destroyed while improving answer rate;
- target capability for the intervention improves on held-out cases.

Example decision:

```text
candidate capability +4.1 pp       PASS
factuality          +1.2 pp       PASS
critical safety      0 → 0        PASS
useful abstention   -0.3 pp       PASS (within tolerance)
held-out target     +5.8 pp       PASS
---------------------------------------
release gate                      PASS
```

A model that improves average score while introducing a new critical safety error must fail the release gate.

---

## 10. Repository target structure

```text
pharma/                         # existing real-world pharma evidence track
benchmark/                      # existing decision/model diagnosis benchmark
medical/
  README.md
  clinical-track/
  truth-layer/
  schemas/
  configs/
  examples/
scripts/
  model_harness.py
  intervention_router.py
  export_training_data.py
  regression_gate.py
docs/
  12-medical-model-development-architecture.md
  13-medical-model-development-roadmap.md
```

---

## 11. Definition of done for v0.1

Architecture v0.1 is not "done" because folders exist. It is done when one end-to-end case can execute:

```text
paragraph-level evidence
→ clinical case
→ two model configurations
→ structured eval result
→ failure diagnosis
→ intervention recommendation
→ training-data candidate
→ baseline vs candidate regression report
```

The first milestone should therefore optimize for **one fully traceable vertical slice**, not for maximum numbers of diseases, drugs or cases.
