# GroundSignal Medical — Literature Archive

> Archive index v1.0  
> Date: 2026-09-09  
> Purpose: papers, supplementary materials, source metadata, and reading notes for GroundSignal Medical. This directory is not a dataset release directory.

2026-09-09：已核对附件中的关键方法，见[文献方法与设计取舍](METHODS_TO_DESIGN.md)和[文献补充任务书 v1.3](../docs/taskbooks/patient-evaluation-literature-addendum-v1.3.md)。附件 MedXIAOHE 为 v4。下方清单表示已核验的附件内容，不表示论文二进制已上传。患者评测已完成 v0.3 开发；专业数据来源、许可和首个中文对话接入审计见[数据接入包](../medical/patient-eval/data-sources/v0.1/README.md)。真实模型实验仍未开始。

## Recommended reading order

### Phase 1 — read these four first

1. **Evaluating the robustness and readiness of large frontier models in health AI applications** — Yu Gu et al., *Nature Medicine* (2026).
   - GroundSignal use: adversarial stress tests, robustness, shortcut detection, readiness boundaries.
2. **Towards conversational diagnostic artificial intelligence** — AMIE, *Nature* (2025).
   - GroundSignal use: patient simulator, OSCE scenarios, active questioning, multi-turn dialogue.
3. **HealthBench: Evaluating Large Language Models Towards Improved Human Health** — OpenAI.
   - GroundSignal use: case-specific rubrics, physician evaluation, severe errors, judge calibration.
4. **MedXIAOHE: A Comprehensive Recipe for Building Medical MLLMs** — ByteDance XiaoHe Medical AI (2026).
   - GroundSignal use: public XiaoHe model-development route, medical reasoning, tool-augmented training, evidence grounding, user-preference rubrics and evaluation.

### Phase 2 — patient state, longitudinal reasoning, and medical text

5. **Towards conversational artificial intelligence for disease management** — *Nature* (2026).
   - Longitudinal patient state, follow-up, changing clinical context and disease management.
6. **Domain-Specific Language Model Pretraining for Biomedical Natural Language Processing** — Yu Gu et al.
   - Biomedical NLP, PubMedBERT/BLURB, entities, relations and task-specific evaluation.
7. **MedDialog: Two Large-scale Medical Dialogue Datasets**.
   - Chinese patient language, real-world consultation style and dialogue structure.
8. **Deidentification of free-text medical records using pre-trained bidirectional transformers**.
   - PHI detection, de-identification and clinical-text preprocessing boundaries.

## Inventory from the 2026-09-09 uploaded bundle

| Status | Original file | Canonical title | SHA-256 |
|---|---|---|---|
| ✅ | `s41591-026-04501-8.pdf` | Evaluating the robustness and readiness of large frontier models in health AI applications | `af6904ba666cc165f15be18ae00ced3fe29a32aa4509f947fbd8b80f9cca430c` |
| ✅ | `s41586-025-08866-7.pdf` | Towards conversational diagnostic artificial intelligence | `e2838a045f757bb79420611a9e0b122a9d682d26b6ae3914cedf551e66408cfe` |
| ✅ | `healthbench_paper.pdf` | HealthBench: Evaluating Large Language Models Towards Improved Human Health | `d4897673fef79ae2e13b64228b221b3f6d062798ef9e8d5189c5908b7a9a8f8c` |
| ✅ | `2602.12705.pdf` | MedXIAOHE: A Comprehensive Recipe for Building Medical MLLMs | `abfdecdfa35466992bde4e07470b3d4b13e840395733551b8f0717da6eb79506` |
| ✅ | `s41586-026-10764-5.pdf` | Towards conversational artificial intelligence for disease management | `fb96e88edf731901908f2c31291b8c382421696f6d459e9b8fafe05307b4a186` |
| ✅ | `2007.15779.pdf` | Domain-Specific Language Model Pretraining for Biomedical Natural Language Processing | `8cdc6b2a96ea64ddee4911e12e4c6aafb31a36f269453fd5fd1667ff2dca3ae4` |
| ✅ | `2004.03329.pdf` | MedDialog: Two Large-scale Medical Dialogue Datasets | `47125be01a5e44d7aa7fb7307fcea940e6db565db16c05b52b9033823b8204b7` |
| ✅ | `3368555.3384455.pdf` | Deidentification of free-text medical records using pre-trained bidirectional transformers | `8ef5de0c45079d35898ee6c1708e93763a8a41bf0929cc60f3c23a41409a770c` |
| ⚠️ | `2004.05986.pdf` | CLUE: A Chinese Language Understanding Evaluation Benchmark | `fbfc4f02989802ba306960779befa3797aaab8c2680f12e0e2074796e1e556a5` |

### Duplicate detected

`2602.12705 (1).pdf` and `2602.12705.pdf` are byte-identical. Both have SHA-256:

`abfdecdfa35466992bde4e07470b3d4b13e840395733551b8f0717da6eb79506`

Keep one canonical copy only.

### Important correction

`2004.05986.pdf` is **CLUE**, a general Chinese language-understanding benchmark. It is **not CBLUE**. For GroundSignal's Chinese clinical-text pipeline, additionally acquire:

**CBLUE: A Chinese Biomedical Language Understanding Evaluation Benchmark** — ACL 2022.

## Missing references to acquire next

1. **CBLUE: A Chinese Biomedical Language Understanding Evaluation Benchmark** — Chinese biomedical entity recognition, information extraction, diagnosis normalization, intent and query understanding.
2. **ClinicalBERT: Modeling Clinical Notes and Predicting Hospital Readmission** — clinical-note representation and preprocessing.
3. **Launching into clinical space with medSpaCy: a new clinical text processing toolkit in Python** — clinical context, negation, section detection and terminology mapping.
4. **DeepMed: Building a Medical DeepResearch Agent via Multi-hop Med-Search Data and Turn-Controlled Agentic Training & Inference** — medical tool-use, multi-hop retrieval, excessive tool calls and context rot.
5. **τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains** — dynamic user-agent-tool evaluation and repeatability.
6. **Decision authority in health AI** — Yu Gu & Eric Topol; risk/severity framing according to the model's influence on patient decisions.
7. **PMC-Patients** paper + dataset documentation — patient-summary and patient/article retrieval cases.
8. **MIMIC-IV-Note** documentation/access materials — deidentified real clinical notes; credentialed access required.

## Archive policy

- Do not treat archived papers as training data by default.
- Keep `REAL_CLINICAL`, `REAL_ONLINE_DIALOGUE`, `PUBLISHED_CASE`, `EXPERT_OSCE`, `HUMAN_AUTHORED`, `SYNTHETIC`, and `DERIVED_PERTURBATION` separate in GroundSignal provenance.
- Restricted clinical datasets must not be committed to the public repository.
- Preserve original dataset/article licenses and citations.
- Before a new paper changes a frozen evaluation suite, record the evidence chain from paper claim → method → GroundSignal design change.
- Papers and supplementary materials belong under `reference/`; derived benchmark cases belong under the appropriate controlled data/evaluation paths, not in this archive.
