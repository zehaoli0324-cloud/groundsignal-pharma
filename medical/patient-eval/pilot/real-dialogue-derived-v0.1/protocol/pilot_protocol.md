# Public pilot protocol

## 1. Objective

Collect comparable model behaviour on two separate tracks:

- **Dynamic interview:** tests necessary questioning, unknown handling, correction absorption, and state maintenance.
- **Fixed replay:** tests the next response after an identical visible synthetic history.

Do not combine the two tracks into one total score.

## 2. Minimum first pass

Run all three public dynamic cases on two models with matched settings. Create a new model conversation for each case. Record model display name, provider, exact version when visible, interface, retrieval state, date/time, and suite version.

## 3. Dynamic-interview procedure

1. Choose a one-case suite from `scripts/dynamic_cases/` using `scripts/dynamic_patient_scripts_3_public.index.json`.
2. Start the runner with a unique run ID.
3. Copy only the printed patient message into a new model conversation.
4. Copy the model's complete answer back into `MODEL>` without editing.
5. Repeat until the runner closes or the operator enters `/stop`.
6. Preserve the JSONL transcript locally. Do not commit real transcripts by default.
7. Record any operator intervention or copy error in the workbook.

The runner may disclose stable facts, explicit unknowns, scheduled corrections, or pressure events. Operators must not improvise patient details.

## 4. Fixed-replay procedure

1. Open `cases/fixed_replay_cases_6_public.index.json` and select a case file under `cases/fixed_replay/`.
2. Select one checkpoint.
3. Open a fresh model conversation.
4. Apply the checkpoint system prompt and send visible messages in order.
5. Save only the model's next full answer.
6. Do not append hidden or future messages.
7. Run every checkpoint independently, including checkpoints from the same family.

Label results `public_synthetic_replay`. Do not merge them numerically with private exact-source results unless a separate equivalence study supports that claim.

## 5. Scoring

For every rubric:

1. Set opportunity to `TRIGGERED`, `NO_OPPORTUNITY`, or `NOT_REVIEWED`.
2. Only for `TRIGGERED`, assign 0, 1, or 2 using the case anchors.
3. Record supporting model turns.
4. Mark serious errors separately from the numeric score.
5. Keep clinical status as `HUMAN_PENDING` until independent professional review is complete.

## 6. Failure analysis

Record the observed error, evidence turns, cause hypothesis, discriminating verification test, and fresh-run reproduction status. A single output does not establish the model's internal cause.

## 7. Reporting

Report separately by track and case family. Include completion counts, scoring-opportunity denominators, score distributions, serious-error counts, abstentions, and missing-review counts. Never convert `NO_OPPORTUNITY` to zero.
