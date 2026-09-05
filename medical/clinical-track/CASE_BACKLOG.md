# Clinical Track — Case Backlog v0.1

> Build by capability and failure mode, not by disease popularity.

## Selection rules

Every candidate case must answer four questions before construction:

1. What model capability is being isolated?
2. What clinically meaningful failure would a user notice?
3. What evidence can freeze a defensible gold behavior?
4. What controlled variant can falsify a superficial shortcut?

Priority order favors patient safety, evidence calibration and model-development usefulness.

---

## C01 — Medication safety: renal-function threshold

**Status:** fixture implemented.

- Task: medication safety.
- Capability: label grounding + threshold reasoning + scope calibration.
- Failure: ignores explicit contraindication / invents replacement regimen.
- Truth: current drug label paragraph-level evidence.
- Variants:
  - threshold below 30;
  - just above 30;
  - 30–45 initiation vs already-taking distinction;
  - missing eGFR;
  - older/superseded label snapshot.
- Intervention candidates: retrieval, source hierarchy, preference overclaim pairs.

---

## C02 — Clinical reasoning: premature closure

**Status:** design next.

- Task: differential/clinical reasoning.
- Capability: integrate symptoms + exam + tests; preserve plausible alternatives.
- Failure: anchors on one salient finding and declares a diagnosis before discriminating evidence.
- Data target: public/de-identified or synthetic case derived from authoritative educational material.
- Gold behavior: ranked differential + discriminating next information, not necessarily one diagnosis.
- Controlled variant: swap one high-information finding while keeping narrative wording similar.
- Main metrics: differential coverage, ranking quality, evidence use, uncertainty.

---

## C03 — Medical QA: guideline version conflict

**Status:** design next.

- Task: medical QA / evidence grounding.
- Capability: source hierarchy + guideline version/freshness.
- Failure: cites an older recommendation as current or merges recommendations across versions.
- Truth: two versioned guideline passages with explicit valid dates.
- Controlled variant: evaluate once at T1 and again at T2 using the same wording.
- Main metrics: temporal validity, source selection, stale-claim rate.

---

## C04 — Report interpretation: observation vs inference

**Status:** planned.

- Task: laboratory/pathology/imaging-report interpretation.
- Capability: extract abnormal/important findings without turning a nonspecific observation into a definitive diagnosis.
- Failure: report text → unsupported disease conclusion.
- Data target: de-identified/public report text or synthetic report generated from a reviewed structured template.
- Gold behavior: observed finding, bounded interpretation, required clinical context.
- Controlled variant: preserve the same finding but alter one context variable that changes interpretation.
- Main metrics: observation accuracy, overclaim rate, missing-context recognition.

---

## C05 — Longitudinal reasoning: superseded patient state

**Status:** planned.

- Task: longitudinal clinical reasoning.
- Capability: track new vs historical state and treatment response.
- Failure: treats an old test/medication/state as current after a later event supersedes it.
- Truth: ordered timeline with explicit event timestamps.
- Controlled variant: shuffle irrelevant events while preserving causal order of the key state change.
- Main metrics: temporal consistency, stale-state rate, changed-claim detection.

---

## C06 — Multi-turn: useful clarification vs passive abstention

**Status:** planned.

- Task: multi-turn clinical conversation.
- Capability: ask the highest-value missing question rather than giving a premature answer or saying only “insufficient information.”
- Failure: passive abstention, low-value repetitive questions, or confident answer without key information.
- Gold behavior: a small set of acceptable high-information clarifications.
- Controlled variant: provide the requested missing information on turn 2 and test whether the model updates.
- Main metrics: clarification value, state tracking, useful abstention, update consistency.

---

## C07 — Medical Agent: evidence retrieval decision

**Status:** planned after harness tool adapter.

- Task: tool-use Agent.
- Capability: decide when to retrieve a label/guideline, formulate a query, use returned evidence and stop.
- Failure: answers from memory when freshness matters; calls irrelevant tools; ignores tool result; fabricates a source.
- Tools: evidence search + passage fetch only for the first version.
- Controlled variant: one question answerable from supplied context vs one requiring current retrieval.
- Main metrics: tool selection, argument validity, evidence recall, answer grounding, unnecessary-call rate.

---

## C08 — Multimodal-ready: image/report discordance

**Status:** schema/planning only; do not implement until rights/de-identification path is ready.

- Task: image + report integration.
- Capability: distinguish what is visually observed from what is stated in accompanying text and handle discordance.
- Failure: hallucinates a visual finding, blindly copies report text, or ignores modality uncertainty.
- Data requirement: appropriately licensed/de-identified images with expert review.
- Controlled variant: same report with image pair altered, or same image with intentionally conflicting report fixture.
- Main metrics: visual observation, cross-modal consistency, hallucinated-finding rate, uncertainty.

---

# Build order

```text
C01 medication safety       IMPLEMENTED AS FIXTURE
C02 premature closure       NEXT
C03 guideline conflict      NEXT
C04 report interpretation   after C02/C03
C05 longitudinal            after temporal truth tooling
C06 multi-turn              after replay support
C07 Agent                   after tool executor adapter
C08 multimodal              after data-rights + image pipeline
```

## Scale rule

Do not add the 50th case before the first 8 cases have:

- frozen evidence;
- gold review;
- controlled variants;
- at least two real-model runs;
- failure analysis;
- held-out lineage;
- regression usability.
