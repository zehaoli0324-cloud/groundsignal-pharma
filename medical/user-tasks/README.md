# Medical User Task Bank

> Purpose: collect realistic user needs before converting them into benchmark items.

GroundSignal does **not** start from isolated exam questions. It starts from a user, a decision, an evidence state and a failure risk.

## 1. User-task record

Each task family should contain:

```yaml
task_id:
user_role: patient | caregiver | general_clinician | specialist | pharmacist | evidence_user
user_goal:
scenario:
primary_question:
context_available:
context_missing:
expected_behavior:
critical_errors:
knowledge_graph_scope:
evidence_requirements:
risk_level: low | medium | high | critical
time_sensitive: true | false
interaction_mode: single_turn | multi_turn | rag | agent | multimodal_ready
```

## 2. Conversion pipeline

```text
Real user need
→ de-identify / synthesize scenario
→ freeze evidence snapshot
→ map graph nodes/edges
→ define ideal behavior
→ define unacceptable behavior
→ create controlled variants
→ create capability probes
→ create safety stress tests
→ expert review
→ release into eval suite
```

## 3. What counts as a good user task?

A good task:

- changes a real user decision or understanding;
- requires more than rote memorization;
- has a defensible evidence boundary;
- allows multiple good phrasings but a stable behavior gold;
- contains at least one meaningful failure mode;
- can be turned into controlled variants;
- is safe to use as a de-identified/synthetic benchmark fixture.

A weak task is merely a textbook recall item with one keyword answer.

## 4. Sources of real user tasks

Preferred sources, with privacy and licensing review before use:

- de-identified clinician workflow interviews;
- patient/caregiver interviews or survey responses;
- public medical QA patterns;
- guideline-defined decision points;
- drug-label contraindication / interaction / monitoring decisions;
- common report/lab interpretation workflows;
- published case reports converted into synthetic, non-identifiable cases;
- real model bad cases observed in controlled testing.

No private patient information should be committed into the public repository.

## 5. Sampling rule

Do not sample only by disease. Sample independently across:

- user role;
- task family;
- evidence sufficiency;
- safety risk;
- temporal sensitivity;
- single-hop vs multi-hop reasoning;
- complete vs incomplete history;
- single-turn vs multi-turn;
- closed-book vs RAG vs Agent.

## 6. Minimum release requirement for a task family

Before a scenario family becomes a benchmark fixture, require:

- [ ] user goal is explicit;
- [ ] graph truth/evidence snapshot is frozen;
- [ ] gold behavior is pre-registered;
- [ ] critical errors are defined;
- [ ] at least 2 controlled variants exist;
- [ ] at least 1 safety/adversarial variant exists when risk is high;
- [ ] case does not contain identifiable patient information;
- [ ] evidence and licensing/provenance are recorded;
- [ ] reviewer status is recorded.
