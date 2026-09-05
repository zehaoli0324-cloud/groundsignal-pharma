# Real Medical User Problem Collection Plan

> Goal: make the benchmark reflect real user needs rather than designer imagination.

## 1. Why user research is required

A technically difficult case is not automatically a valuable medical-model task. The platform needs evidence that users actually ask the question, struggle with the decision, or encounter the workflow.

The user-research layer should answer:

- who asks this question;
- what decision/understanding they need;
- what information they usually have or omit;
- what a useful answer looks like;
- which model errors destroy trust or create risk;
- which follow-up questions are natural;
- whether tool/retrieval use is expected.

## 2. Target participant groups

Initial qualitative sample:

- 5-8 general clinicians / trainees;
- 3-5 pharmacists or medication-safety users;
- 5-8 patients/caregivers for non-identifying workflow questions;
- 3-5 users who regularly interpret medical reports/labs;
- optional specialist interviews for high-complexity tracks.

The goal of the first round is task discovery, not population prevalence estimation.

## 3. Interview prompts

Ask participants for workflows, not private identifiable cases.

### Core prompts

1. What are the most common medical questions you would realistically ask an AI assistant?
2. Which questions are easy to search but hard to make a decision from?
3. When would you expect the AI to ask you a follow-up question instead of answering immediately?
4. Which information do users commonly forget to provide?
5. What answer would sound convincing but actually be dangerous or misleading?
6. Which mistakes would make you immediately stop trusting the system?
7. Which questions require up-to-date guideline/label information rather than general medical knowledge?
8. In what situations should the AI retrieve a source or use a tool before answering?
9. Which reports/laboratory results are commonly misunderstood?
10. Which clinical decisions depend on comparing several pieces of evidence rather than one fact?
11. When is uncertainty acceptable, and when is a vague 'consult a doctor' response useless?
12. What would make an AI answer genuinely useful in your workflow?
13. What follow-up question would you naturally ask after the first response?
14. Are there tasks where a concise answer is better than exhaustive explanation?
15. Which tasks should never be fully automated by the model?

## 4. Task capture template

For every discovered task:

```yaml
raw_task_id:
participant_role:
user_goal:
example_question_redacted:
decision_or_action:
information_normally_available:
information_often_missing:
expected_followups:
requires_current_evidence: true | false
requires_tool_use: true | false
risk_if_wrong: low | medium | high | critical
common_bad_answer:
what_good_looks_like:
frequency_signal: rare | occasional | common | unknown
notes:
```

Do not save identifying patient details.

## 5. From interview to benchmark

A raw user statement is not directly committed as a benchmark question.

```text
raw user workflow
→ redact / abstract
→ synthesize non-identifiable scenario
→ map to capability and risk tags
→ locate authoritative evidence
→ build case-local graph
→ pre-register gold behavior and critical errors
→ create controlled variants
→ expert review
→ benchmark release
```

## 6. Quantitative validation after discovery

After 30-50 candidate task families have been discovered, run a lightweight survey to rank:

- frequency;
- importance;
- difficulty;
- risk if wrong;
- usefulness of AI assistance;
- need for current evidence;
- need for multi-turn interaction;
- need for tools/RAG.

Use these scores to prioritize benchmark coverage rather than treating every possible task equally.

## 7. Coverage dashboard

Track the benchmark along at least these axes:

```text
user role × task family × risk × evidence state × interaction mode
```

Warning signs:

- >50% of cases are textbook QA;
- medication safety has no critical-error cases;
- all cases contain complete information;
- all tasks are single-turn;
- no cases require temporal/current evidence;
- no retrieval/tool-use attribution cases;
- one disease area dominates simply because data was easy to collect.

## 8. Initial validation target

For P1:

- discover 30+ raw task families;
- retain 12-20 after evidence/feasibility screening;
- obtain at least one domain-review pass for high-risk case families;
- convert 12 families into the first controlled benchmark suite.

The existing `SEED_TASK_BANK.md` is a designer-generated hypothesis bank. User research should confirm, modify, reject or add to it.
