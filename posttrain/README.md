# GroundSignal Post-training Interface

> GroundSignal does not need to implement a full distributed trainer. Its responsibility is to transform reviewed medical model failures into provenance-preserving training candidates and to define how improvement will be tested.

## 1. Interface position

```text
Evidence / Knowledge Graph
        ↓
Medical Case
        ↓
Model Run
        ↓
Evaluation
        ↓
Observed Failure
        ↓
Capability Hypothesis
        ↓
Intervention Router
        ↓
Training Example Builder
        ↓
Data Review / Split / Manifest
        ↓
SFT / Preference / Agent / Judge training
        ↓
Candidate checkpoint/system
        ↓
Held-out Regression Gate
```

## 2. Training data types

### SFT

Use when the model lacks a desired response behavior or reasoning structure.

Examples:

- structured differential reasoning;
- clarification before answering;
- evidence-grounded report interpretation;
- uncertain-but-actionable response;
- audience-conditioned communication.

### Preference

Use when the model can produce plausible answers but tends to choose an unsafe/overclaimed/worse behavior.

Examples:

- supported claim vs overclaim;
- calibrated uncertainty vs false certainty;
- safe boundary vs unsupported treatment recommendation;
- decision-first answer vs irrelevant information dump.

### Agent trajectory

Use when the failure is in action selection rather than final prose alone.

Examples:

- retrieve current label before a high-risk medication claim;
- choose the correct medical source/tool;
- formulate a useful query;
- use tool output rather than ignore it;
- stop when evidence is sufficient;
- ask clarification when required.

### Judge / reward labels

Use reviewed dimension scores and critical-error labels to calibrate an evaluator/reward component.

## 3. Intervention routing examples

| Failure | Default candidate intervention | Important alternative |
|---|---|---|
| STALE_KNOWLEDGE | retrieval / knowledge refresh | temporal data refresh |
| KNOWLEDGE_MISSING | SFT or domain data | MidTrain/CPT if broad and systematic |
| REASONING_FAILURE | reasoning SFT | prompt/scaffold first if small |
| OVERCLAIM | preference | evidence-grounded SFT |
| UNSAFE_RECOMMENDATION | safety SFT + preference | retrieval if caused by missing rule |
| FAILURE_TO_CLARIFY | multi-turn SFT | prompt policy |
| PASSIVE_ABSTENTION | uncertain-but-actionable SFT | preference |
| BAD_TOOL_SELECTION | Agent trajectory | tool description / routing fix |
| BAD_QUERY | retrieval trajectory | query-rewrite module |
| RETRIEVAL_MISS | retriever/reranker | do not train generator by default |
| EVIDENCE_MISUSE | preference / grounded SFT | context formatting |
| JUDGE_INCONSISTENCY | judge calibration | deterministic check/human review |

The router produces a **hypothesis**, not a proven causal diagnosis.

## 4. Required provenance

Every training example must preserve:

```text
source case
model/run that produced the failure
failure type
supporting evidence passage IDs
knowledge graph version
review status
builder version
split
intended intervention
regression suite
```

No reviewed provenance → no production training export.

## 5. Data lifecycle

```text
candidate
→ reviewed
→ approved
→ split assigned
→ manifest frozen
→ trainer export
→ intervention run
→ regression result
→ keep / revise / reject
```

## 6. Train/dev/heldout discipline

Do not split near-duplicate variants randomly.

A scenario family used to create training data should not leak its near-identical controlled variants into held-out regression.

Preferred split keys:

- scenario family;
- evidence family;
- drug/guideline decision family when leakage is likely;
- temporal snapshot family.

## 7. Post-training experiment ledger

Each intervention should have a record like:

```yaml
intervention_id: INT-0001
failure_cluster: OVERCLAIM
hypothesis: >
  The model frequently escalates evidence scope in medication-safety answers.
strategy:
  type: preference
  method: external_trainer
training_dataset:
  manifest: posttrain/manifests/overclaim-v1.yaml
  n_examples: 180
baseline:
  model_id: baseline-x
candidate:
  model_id: candidate-x
expected_effect:
  primary_metric: overclaim_rate
  direction: decrease
regression_suites:
  - medication-safety-heldout
  - evidence-sufficiency-heldout
  - core-clinical-safety
status: proposed
```

## 8. Trainer boundary

GroundSignal exports standard files that can be consumed by external training stacks such as a team's internal trainer or common open-source stacks.

The platform's differentiating responsibilities are:

- why the data exists;
- what failure it targets;
- what evidence supports the preferred behavior;
- whether expert/reviewer approval exists;
- where leakage boundaries are;
- what regression must improve after training.

## 9. Success definition

A post-training experiment is not considered successful because training loss decreases.

It is successful only when:

```text
target held-out failure improves
AND critical safety regressions = 0
AND unrelated core capability does not materially regress
```
