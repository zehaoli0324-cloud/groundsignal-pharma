# Interview-derived Medical Question Candidates v0.1

This directory contains **questions only** derived from two user-supplied interview documents. It is a quarantine area, not a benchmark release or medical knowledge source.

## Why this exists

The documents contain useful medical-product, safety, policy, workflow and model-evaluation scenarios, but their answers contain unsupported facts, invented metrics and potentially unsafe clinical guidance. GroundSignal therefore preserves the question value without inheriting answer authority.

## Trust boundary

- Trust status: `UNVERIFIED_INTERVIEW_MATERIAL`
- Raw DOCX files: not committed
- Source answers: not committed
- Eligible for trust root: no
- Eligible for medical knowledge graph: no
- Eligible for training export: no
- Eligible for held-out/regression assignment: no

Every retained question still requires premise verification, authoritative evidence, behavior-gold authoring, critical-error definition and expert review before it can become a benchmark case.

## Files

- `source-manifest.json` — source filenames, SHA-256 digests and boundary flags.
- `all-question-inventory.jsonl` — all 148 extracted questions, including 26 interview-only exclusions.
- `user-question-candidates.jsonl` — 122 retained question candidates.
- `evaluation-seeds.jsonl` — one unvalidated evaluation seed per retained candidate.
- `unsafe-answer-risk-seeds.jsonl` — five paraphrased unsafe-answer patterns; no source answer text.
- `priority-review-queue.jsonl` — 16 high-value candidates selected for premise and evidence review first.

## Rebuild locally

```bash
python scripts/import_unverified_interview_corpus.py \
  --product-manager-docx /path/to/医疗大数据产品经理面试逐字稿125题.docx \
  --hot-topics-docx /path/to/医疗结构化面试热点23题.docx

python scripts/validate_unverified_interview_corpus.py
```

Rebuilding is deterministic for the same input bytes. A changed source digest must be treated as a different source version and reviewed again.

## Promotion path

```text
quarantined question
→ premise check
→ authoritative source retrieval
→ evidence snapshot freeze
→ behavior gold + critical errors
→ controlled variants
→ expert review
→ separately approved benchmark suite
```

No promotion occurs automatically.

The first controlled-use checkpoint is documented in
`../../promotion-pilots/interview-pilot-v0.1/`. It defines S2 source routes for three priority
questions while keeping S3 evidence, S4 knowledge-graph ingestion, S5 Gold/split assignment and all
training/downstream use blocked.
