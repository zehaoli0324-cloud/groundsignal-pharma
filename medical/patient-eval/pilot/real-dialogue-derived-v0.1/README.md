# GroundSignal public patient-evaluation pilot v0.1

This directory publishes a **deidentified, synthetic derivative** of the GroundSignal patient-evaluation pilot. It contains runnable interaction logic, public case cards, collection templates, and evaluation instructions. It does **not** contain original patient conversations or completed review packets.

## Included

- 12 public case cards: 6 dynamic-interview families and 6 fixed-replay families.
- 3 runnable dynamic patient scripts, stored one case per JSON file.
- 6 synthetic fixed-replay cases with 10 independent checkpoints, stored one case per JSON file.
- A local command-line runner, collection workbook, scoring protocol, operation guide, and fail-closed release validator.

## Intentionally excluded

- Original dialogue text and source dialogue identifiers.
- Candidate-review JSON/HTML files, reviewer drafts, evidence spans, original turn numbers, redaction maps, and direct or quasi-identifiers.
- Exact-source replay contexts, real model transcripts, local run logs, screenshots, or clinical adjudication records.
- Any claim of formal approval, clinical-gold status, or verified reviewer credentials.

See [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md).

## Validate before use

```bash
python scripts/validate_public_release.py .
```

## Run a dynamic case

Each dynamic case file is a complete one-case suite. Example:

```bash
python scripts/pilot_runner.py \
  --suite scripts/dynamic_cases/GS-PUB-DYN-001.json \
  --case GS-PUB-DYN-001 \
  --run-id example-GS-PUB-DYN-001-001 \
  --output-jsonl runs/example-GS-PUB-DYN-001-001.jsonl
```

The index is `scripts/dynamic_patient_scripts_3_public.index.json`.

## Fixed replay

Open `cases/fixed_replay_cases_6_public.index.json`, select a case file under `cases/fixed_replay/`, and run every listed checkpoint in a fresh model conversation. Public replay contexts are synthetic derivatives and must not be reported as exact-source replay results.

## Scoring boundary

Dynamic-interview and fixed-replay results measure different capabilities and must be reported separately. Score only when a rubric opportunity was triggered. `NO_OPPORTUNITY` is not a zero score.

## Status

- `formal_approval=false`
- `clinical_gold=false`
- No real model results are included.
