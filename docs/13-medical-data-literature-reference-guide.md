# GroundSignal Medical — 数据、病例、医疗文本与评测文献 Reference Guide

> Status: reference guide v1.0  
> Date: 2026-09-09  
> Scope: GroundSignal Pharma 患者多轮复杂评测、小荷 AI 医生公开技术路线、医疗文本处理与真实病例建设  
> Relation: complements [`12-medical-model-development-architecture.md`](./12-medical-model-development-architecture.md)

---

## 0. 这份文档解决什么问题

GroundSignal 当前已经具备较明确的评测目标：不只判断医疗大模型“最后答得对不对”，而是希望在真实患者式、多轮、信息不完整、用户纠正、工具失败、证据冲突和催促压力下，测量模型是否能够：

1. 理解患者真实表达与歧义；
2. 主动追问会改变后续判断的关键信息；
3. 在多轮对话中维护并更新患者事实；
4. 识别风险、控制建议边界；
5. 检索并正确使用适用证据；
6. 正确调用工具，并在故障后恢复或降级；
7. 向普通患者做清楚、准确、不过度的解释；
8. 在长对话、焦虑、催促、错误复述和话题切换下保持稳定。

但评测框架本身不能替代数据基础。下一阶段必须补齐一条完整的数据与文本处理链：

```text
真实/公开/标准化病例与患者语言
        ↓
来源、许可、隐私与独立性审查
        ↓
医疗文本处理
        ↓
患者状态结构化
        ↓
多轮患者场景与披露策略
        ↓
干净对照 + 压力扰动
        ↓
模型 / RAG / Agent 运行
        ↓
评分、诊断、受控替换
        ↓
defect → algorithm / engineering / data / judge
```

本 Reference Guide 的目的不是把所有医疗 AI 论文列成 bibliography，而是回答三个实际问题：

- **哪些数据和病例值得下载？**
- **每篇文章具体帮助 GroundSignal 的哪一层？**
- **资料下载后应该如何使用，而不是简单塞进 RAG 或训练集？**

---

# Part I. 先建立正确的数据分层

## 1. 不同“医疗数据”不能混称真实患者数据

GroundSignal 后续必须为每个案例保留 `source_type`。建议至少区分：

| 类型 | 含义 | 可以支持什么结论 | 不能支持什么结论 |
|---|---|---|---|
| `REAL_CLINICAL` | 医院真实临床记录，如脱敏电子病历 | 临床文本、真实医疗过程与记录结构研究 | 不自动代表患者口语 |
| `REAL_ONLINE_DIALOGUE` | 真实或历史在线医患咨询语料 | 患者自然表达、追问方式、互联网问诊语言 | 不自动等于线下诊疗质量标准 |
| `PUBLISHED_CASE` | 公开论文中的病例报告 | 医学事实、疾病表现、病例相似性与文献证据 | 不等于真实在线用户交互 |
| `EXPERT_OSCE` | 专家设计的标准化临床考试病例 | 可控隐藏事实、问诊目标、评分标准 | 不是自然产生的真实患者日志 |
| `HUMAN_AUTHORED_EVAL` | 人工专门设计的评测案例 | 对抗性、难度、专家 rubric | 不等同临床分布 |
| `SYNTHETIC` | 模型或规则合成 | 规模扩展、受控变量、故障测试 | 不可声称来源于真实患者 |
| `DERIVED_PERTURBATION` | 从原案例派生出的歧义、纠正、噪声、长对话版本 | 鲁棒性、因果对照、压力测试 | 变体不能当成独立新病例 |

**原则：数据真实性、临床真实性、患者语言真实性和评测有效性是四件不同的事。**

---

# Part II. 病例与数据资源：先下载什么、分别怎么用

## 2. AMIE 2025：标准化多轮问诊与患者模拟器的第一参考

**Paper**  
*Towards conversational diagnostic artificial intelligence*  
Nature, 2025  
https://www.nature.com/articles/s41586-025-08866-7

**AMIE** = Articulate Medical Intelligence Explorer，对话式医疗人工智能研究系统。

### 2.1 它提供什么

该研究使用 159 个病例场景，通过类似 **OSCE（Objective Structured Clinical Examination，客观结构化临床考试）** 的方式，让患者扮演者与医生或 AMIE 进行文本问诊。评估覆盖：

- history-taking：病史采集；
- diagnostic reasoning：诊断推理；
- management：处理与下一步；
- communication：沟通；
- empathy：同理与患者体验。

AMIE 的训练方法还使用 patient agent、doctor agent、自我反馈和模拟对话来扩展多轮数据。

### 2.2 GroundSignal 应该学什么

重点不是复制 AMIE 的最终分数，而是拆它的病例结构：

```text
hidden patient facts
      ↓
initial complaint
      ↓
model asks question
      ↓
patient discloses only allowed information
      ↓
new state
      ↓
next question / action
      ↓
final assessment
```

对应 GroundSignal：

- C1 语义与澄清；
- C2 主动问询；
- C3 多轮事实更新；
- C4 风险边界；
- C7 患者解释；
- C8 压力稳定。

### 2.3 下载与使用

优先下载：

1. Nature 正文 PDF；
2. Supplementary Information；
3. 可公开获得的 scenario / rubric 补充材料。

**用途：**学习如何写标准化患者场景、隐藏事实、披露规则和医生/患者双侧 rubric。  
**不要：**把 OSCE case 称为真实患者日志。

---

## 3. AMIE 2026：多次就诊、疾病变化和长期状态

**Paper**  
*Towards conversational artificial intelligence for disease management*  
Nature, 2026  
https://www.nature.com/articles/s41586-026-10764-5

### 3.1 为什么比单次问诊更接近 GroundSignal 下一阶段

这项研究把问题扩展到 multivisit disease management（多次就诊疾病管理），覆盖：

- disease progression：疾病进展；
- therapeutic response：治疗反应；
- investigation：检查与复查；
- medication reasoning：药物决策；
- clinical guideline grounding：临床指南证据约束。

正式评测使用 100 个多次就诊病例场景，并与 21 名初级保健医生比较；论文还构建了 RxQA 药物推理评测。

### 3.2 GroundSignal 应该学什么

重点映射：

- C3：旧事实、新事实、纠正和时间状态；
- C4：患者风险随时间发生变化；
- C5：证据版本、适用性和指南时效；
- 用药信息；
- 既有问题随访；
- 12–16 轮长程压力场景。

### 3.3 下载与使用

下载正文和全部 supplementary material。优先分析每个多访视场景中：

- 哪些事实属于时间点 T1 / T2 / T3；
- 哪些条件出现后必须改变行动；
- 哪些信息必须查指南或药品资料；
- 哪些错误属于“继续使用旧状态”。

---

## 4. MedDialog-CN：中文患者真实表达研究主语料

**Paper**  
*MedDialog: Two Large-scale Medical Dialogue Datasets*  
2020  
https://arxiv.org/abs/2004.03329

**Project repository**  
https://github.com/UCSD-AI4H/Medical-Dialogue-System

### 4.1 数据价值

论文报告 MedDialog-CN 含约：

- 1.1 million 中文医患咨询；
- 约 4 million utterances（发言）；
- 覆盖大量专科；
- 来源为历史在线医疗咨询数据。

这类数据最重要的价值不是“标准答案”，而是学习患者怎么说：

- 口语化症状；
- 信息缺失；
- 同一事实多种表达；
- 用户连续补充；
- 药品简称、俗称；
- 代替家属咨询；
- 不完整病史；
- 用户希望医生解决的问题。

### 4.2 GroundSignal 应该怎么用

优先用于构建：

1. **Patient Language Corpus**：患者语言语料；
2. C1 语义/歧义 taxonomy；
3. C2 真实高价值追问模式；
4. C7 通俗表达与患者理解；
5. C8 催促、重复、断裂表达与长程噪声。

### 4.3 重要限制

公开论文/研究仓库可用于研究，不等于可以无条件把所有历史医患文本重新公开到 GroundSignal GitHub。

在重新分发、公开派生数据或训练数据前，必须重新核验：

- repository license；
- 原始数据来源条款；
- 个人信息与可识别性风险；
- 是否只允许研究使用；
- 是否需要进一步脱敏或只发布统计/派生模板。

**初期建议：本地分析，不把原始语料直接 commit 到仓库。**

---

## 5. MIMIC-IV-Note：真实临床文本和患者底层事实

**Dataset**  
*MIMIC-IV-Note: Deidentified free-text clinical notes*  
PhysioNet v2.2  
https://physionet.org/content/mimic-iv-note/2.2/

### 5.1 数据价值

MIMIC-IV-Note 是脱敏真实临床自由文本数据，包含大规模：

- discharge summaries：出院小结；
- radiology reports：放射报告。

它可以和 MIMIC 的结构化住院、检查、实验室、用药和时间信息关联。

### 5.2 GroundSignal 的正确用途

它更适合做：

> **clinical ground state / patient fact backbone**

而不是患者口语。

可以从一个临床过程建立：

```text
症状
→ 既往史
→ 当前用药
→ 检验
→ 影像/报告
→ 病情变化
→ 最终诊断
→ 出院计划
```

然后再生成受控患者披露版本。

对应：C3、C4、C5、报告解读、随访、时间更新。

### 5.3 访问限制

MIMIC 属于 credentialed access（认证访问）数据。应按 PhysioNet 的当前要求完成：

- 账户认证；
- 相关培训；
- Data Use Agreement（数据使用协议）。

**禁止：**把原始受限数据上传到公开 GroundSignal 仓库。

---

## 6. PMC-Patients：公开病例报告与病例—文献关联

**Paper**  
*A large-scale dataset of patient summaries for retrieval-based clinical decision support systems*  
Scientific Data, 2023  
https://www.nature.com/articles/s41597-023-02814-8

**Repository**  
https://github.com/pmc-patients/pmc-patients

**Dataset**  
可通过 Figshare / Hugging Face 下载，仓库 README 提供入口。

### 6.1 数据规模与结构

公开仓库说明包含约：

- 167k patient summaries；
- 3.1M patient–article relevance relations；
- 293k patient–patient similarity relations。

### 6.2 GroundSignal 用途

它非常适合训练和测试：

- C5 证据与适用性；
- patient-to-article retrieval；
- patient-to-patient retrieval；
- 相似病例是否真的适用；
- RAG 找到“相关”内容后是否能判断“支持什么 / 不支持什么”。

### 6.3 License

项目仓库声明数据集采用 **CC BY-NC-SA 4.0**。

使用时保存：

- source PMID；
- patient UID；
- 原文章信息；
- dataset license；
- 派生案例 lineage。

---

## 7. HealthBench：现实型评测对话与病例特异 rubric

**OpenAI project**  
https://openai.com/index/healthbench/

**Dataset**  
https://huggingface.co/datasets/openai/healthbench

### 7.1 数据性质必须准确描述

HealthBench 包含 5,000 个医疗对话场景和大量医生编写的 case-specific rubrics（病例特异评分规则）。

这些对话来自：

- synthetic generation：合成生成；
- human adversarial testing：人工对抗测试。

因此它是：

> 高质量、现实型医疗评测数据

但不是：

> 5,000 条真实患者临床日志。

### 7.2 GroundSignal 应该学什么

1. **case-specific rubric**，而不是只有固定“准确性 1–5 分”；
2. 必须包含/禁止包含的内容；
3. underspecified queries（信息不足问题）的追问；
4. worst-case reliability（最差情况可靠性）；
5. 严重错误不能被平均分抵消；
6. benchmark 应保持 unsaturated（不饱和）。

对应 GroundSignal W05、C1–C8、严重错误率和评分器校准。

---

## 8. CBLUE：中文医疗文本理解的结构化任务集合

**Paper**  
*CBLUE: A Chinese Biomedical Language Understanding Evaluation Benchmark*  
ACL 2022  
https://aclanthology.org/2022.acl-long.544/

**Repository**  
https://github.com/CBLUEbenchmark/CBLUE

### 8.1 为什么重要

CBLUE 把中文医疗语言理解拆成多个可诊断任务，包括：

- Named Entity Recognition（NER，命名实体识别）；
- information / relation extraction（信息/关系抽取）；
- clinical diagnosis normalization（临床诊断标准化）；
- single-sentence / sentence-pair classification（句子分类）；
- patient query intent / query relation 等任务。

### 8.2 GroundSignal 应该怎么用

它帮助我们把 C1/C3 从“模型整体答错”拆成更底层的失败：

```text
患者原话
  ↓
实体识别失败？
  ↓
否定/人物/时间错误？
  ↓
标准医学概念映射失败？
  ↓
关系错误？
  ↓
患者状态写错？
  ↓
最终回答错误
```

CBLUE 项目仓库标注 Apache-2.0 license；具体子任务数据如有额外条款，使用前仍应逐项核验。

---

## 9. CURE-Bench：用药与治疗决策的后期扩展数据

**Project**  
https://curebench.ai/

**NeurIPS 2025**  
https://neurips.cc/virtual/2025/competition/127720

**Starter repository**  
https://github.com/mims-harvard/CUREBench

### 9.1 它测什么

CURE-Bench 不是普通医学 QA，而聚焦 patient–disease–drug 的复杂治疗决策，包括：

- treatment recommendation；
- adverse events；
- warnings / contraindications；
- dosage / administration；
- special populations；
- pharmacology；
- clinical studies；
- patient-focused medication information；
- agentic tool-augmented reasoning。

### 9.2 GroundSignal 什么时候用

不要在第一阶段把它当核心患者数据。

当“用药信息”从说明书查询升级到：

> 患者状态 + 多药 + 相互作用 + 禁忌 + 特殊人群 + 证据工具

再重点接入。

对应 C4、C5、C6 和 pharma evidence layer。

---

# Part III. 医疗文本处理：不能把原始文本直接扔给 RAG

## 10. 医疗文本处理最少要保留的语义

医学文本中“词出现了”不代表“患者当前有这个事实”。

例：

- “无糖尿病史” → `diabetes` 存在，但 `negated = true`；
- “父亲有肺癌” → `lung cancer` 存在，但 `experiencer = family`；
- “三年前服用华法林，目前已停” → medication 存在，但 `status = stopped`、`time = past`；
- “考虑感染，尚未证实” → concept 存在，但 `certainty != confirmed`。

GroundSignal clinical state 至少需要处理：

1. **Entity**：医学实体；
2. **Negation**：否定；
3. **Temporality**：时间；
4. **Uncertainty**：不确定性；
5. **Experiencer**：患者本人还是家属；
6. **Relation**：实体之间关系；
7. **Normalization**：标准化到统一医学概念；
8. **Section**：病历章节；
9. **Source / turn**：事实来自哪一轮/哪一份文件；
10. **Correction / supersession**：后续事实是否纠正旧事实。

建议患者状态对象逐步演进到：

```yaml
concept: metformin
concept_type: medication
subject: patient
status: active
negated: false
certainty: confirmed
time: current
dose: unknown
source_turn: 4
corrected_by: null
source_document: null
```

---

## 11. 顾禹：PubMedBERT / BLURB

**Paper**  
*Domain-Specific Language Model Pretraining for Biomedical Natural Language Processing*  
Yu Gu et al., 2020  
Microsoft Research / ACL-era biomedical NLP work  
https://www.microsoft.com/en-us/research/publication/domain-specific-language-model-pretraining-for-biomedical-natural-language-processing/

### 11.1 重点不是“以后一定要训练 BERT”

这篇文章的重要性在于建立 biomedical NLP 的任务地图，并提出 **BLURB（Biomedical Language Understanding & Reasoning Benchmark，生物医学语言理解与推理基准）**。

相关能力包括：

- NER；
- relation extraction；
- question answering；
- sentence similarity；
- document classification。

### 11.2 对 GroundSignal 的意义

它帮助回答：

> 医疗文本理解到底有哪些底层能力，而不是把所有错误都归为“LLM 推理差”。

这也是顾禹后续 robustness / benchmark 工作的早期技术背景之一。

---

## 12. ClinicalBERT：临床文本和生物医学论文不是同一个语言域

**Paper**  
*ClinicalBERT: Modeling Clinical Notes and Predicting Hospital Readmission*  
2019  
https://arxiv.org/abs/1904.05342

### 12.1 应学什么

Clinical note 中包含大量结构化实验室表格看不到的信息，因此：

- biomedical literature；
- clinical note；
- patient-generated text

必须视为三个不同 domain（语言域）。

GroundSignal 不应该使用“医学文本”一个标签把它们混在一起。

---

## 13. medSpaCy：最适合学习工程化 Clinical NLP pipeline

**Paper**  
*Launching into clinical space with medspaCy: a new clinical text processing toolkit in Python*  
https://pmc.ncbi.nlm.nih.gov/articles/PMC8861690/

### 13.1 重点模块

medSpaCy 展示了一个完整临床 NLP pipeline 可以怎样组织：

- sentence segmentation；
- section detection；
- concept extraction；
- context analysis；
- negation；
- standard terminology mapping。

### 13.2 GroundSignal 的直接用途

它最适合帮助我们实现：

> raw text → structured patient state

而不是把全文原样长期堆在 conversation context 里。

未来 W03 patient state、C1、C3 和缺陷归因都可以参考这种组件化思想。

---

## 14. 医疗文本脱敏：真实材料进入系统前的前置门

**Paper**  
*Deidentification of free-text medical records using pre-trained bidirectional transformers*  
2020  
https://pmc.ncbi.nlm.nih.gov/articles/PMC8330601/

### 14.1 关注什么

**PHI（Protected Health Information，受保护健康信息）**包括姓名、联系方式、日期、机构、地址和其他可能识别个体的信息。

GroundSignal 如果未来获得医院、医生或真实用户材料，必须先有：

```text
raw material
→ authorization / legal scope
→ de-identification
→ residual re-identification audit
→ content processing
→ case derivation
```

不能把“模型自动打码”当成已经完成隐私合规。

---

# Part IV. 多轮医疗大模型与 Agent 评测：怎么测真正的缺陷

## 15. 顾禹 2026 Nature Medicine：GroundSignal 压力测试的第一核心论文

**Paper**  
*Evaluating the robustness and readiness of large frontier models in health AI applications*  
Nature Medicine, 2026  
https://www.nature.com/articles/s41591-026-04501-8

**Associated public release**  
论文 Data Availability 提供公开可分享部分和 Zenodo release：  
https://doi.org/10.5281/zenodo.20047288

### 15.1 核心问题

不是问：

> 模型 benchmark 分数有多高？

而是问：

> 高分究竟是否来自正确能力？模型在输入扰动后是否仍保持可靠？现有 benchmark 到底测到了什么？

研究使用 adversarial stress tests（对抗压力测试）暴露：

- 关键输入被移除仍可能猜对；
- 很小 prompt 改动会导致失败；
- reasoning trace 可能流畅但错误；
- benchmark score 与 application readiness 之间存在明显距离。

### 15.2 GroundSignal 应该吸收的五个原则

1. 原始 clean case 必须和 perturbation 配对；
2. 改变输入但尽量保持核心医学真值；
3. 一个总分不能代替 failure mode；
4. 必须检验模型是否依赖 shortcut；
5. 结论强度不能超过实际 stress test 证据。

对应 GroundSignal D0–D3、C1–C8 pressure slices 和 F01–F10 fault tests。

---

## 16. HealthBench：如何用医生 rubric 把自由回答变成可复测缺陷

详见第 7 节。

重点阅读：

- conversation-specific rubric；
- physician weighting；
- hard cases；
- meta-evaluation / grader reliability；
- necessary context seeking；
- worst-case behavior。

GroundSignal 不应该只复制 HealthBench 评分，而应把其思想转成：

```text
criterion
+ applicability
+ deadline
+ evidence requirement
+ forbidden action
+ severity
+ exact failure span
```

---

## 17. τ-bench：用户—Agent—工具动态交互

**Paper**  
*τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*  
2024  
https://arxiv.org/abs/2406.12045

### 17.1 为什么非医疗论文仍然重要

它测试：

```text
User ↔ Agent ↔ Tools / API / Policy
```

并提出 `pass^k` 来衡量同一任务重复运行时的稳定性。

### 17.2 GroundSignal 对应

- C6 工具与恢复；
- C8 重复运行稳定性；
- W02 patient simulator；
- W03 conversation runner；
- W04 tool gateway。

医疗正确终态仍需独立临床标准，不能直接借用其他领域 task state。

---

## 18. LLM-as-a-Judge：评分器本身也必须被评测

**Paper**  
*Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*  
2023  
https://arxiv.org/abs/2306.05685

**LLM-as-a-Judge** = 用大语言模型作为自动评分器。

### 18.1 需要专门防的偏差

- position bias：位置偏差；
- verbosity bias：长度偏差；
- self-enhancement bias：偏爱自身/相似模型输出；
- reasoning limitation：评分模型自身推理限制。

### 18.2 GroundSignal 对应

这直接支持：

- F10 等价内容改顺序/长度/措辞的 judge stress test；
- W05 自动评分与专家盲审校准；
- 严重错误标签不能因文风变化翻转。

---

# Part V. 小荷 / ByteDance 公开技术路线：理解“未来要测什么”

## 19. MedXIAOHE：小荷公开的医疗多模态模型技术路线

**Paper**  
*MedXIAOHE: A Comprehensive Recipe for Building Medical MLLMs*  
2026  
https://arxiv.org/abs/2602.12705

**MLLM** = Multimodal Large Language Model，多模态大语言模型。

### 19.1 公开技术主题

论文介绍：

- entity-aware continual pretraining；
- heterogeneous medical corpora；
- long-tail / rare disease coverage；
- reinforcement learning；
- medical reasoning patterns；
- tool-augmented agentic training；
- evidence-grounded reasoning；
- user-preference rubrics；
- hallucination reduction；
- long-form medical report generation。

### 19.2 GroundSignal 应怎样使用这篇论文

不是复制训练 recipe，而是建立：

> **defect → possible intervention family**

例如：

| GroundSignal 缺陷 | 可能需要进一步排查的模型/系统方向 |
|---|---|
| 长尾疾病知识缺失 | continual pretraining / data coverage |
| 工具找到证据但回答没用 | reasoning / agentic training |
| 引用证据但结论过强 | evidence-grounded reasoning / rubric / post-training |
| 医学内容正确但患者无法理解 | preference / communication training |
| 图片与文本联合推理失败 | multimodal training / fusion / eval |

注意：公开论文证明技术路线存在，**不能据此推断小荷生产系统内部一定采用完全相同架构。**

---

## 20. DeepMed：检索成功不等于医学推理成功

**Paper**  
*DeepMed: Building a Medical DeepResearch Agent via Multi-hop Med-Search Data and Turn-Controlled Agentic Training & Inference*  
ACL Findings 2026  
https://aclanthology.org/2026.findings-acl.904/

### 20.1 关键思想

医疗 DeepResearch 系统的一个核心失败是：

> **find it but fail to use it**

即工具/检索找到了信息，但模型不会在临床上下文中正确解释和应用。

### 20.2 GroundSignal 应新增的缺陷类型

不能只测 `retrieval_hit = true/false`，还要区分：

```text
retrieval failed
retrieval succeeded but wrong evidence selected
correct evidence selected but applicability wrong
correct evidence available but ignored
correct evidence used but conclusion overclaimed
excessive tool use introduced noise
```

这直接对应 C5、C6、W04 和受控证据替换实验。

---

## 21. CURE-Bench / CureFlow：复杂用药决策的未来深水区

CURE-Bench 见第 9 节。

ByteDance 团队公开页面还列出：

**CureFlow: An AI Engine for Complex Medication Decision-Making**

现阶段把它作为“用药决策 Agent”方向参考即可。GroundSignal 第一阶段仍应先保证：

- 药名/剂型识别；
- 说明书适用性；
- 禁忌/特殊人群；
- 证据版本；
- 工具失败；
- 患者解释。

随后再进入复杂多药和治疗规划。

---

## 22. Decision Authority：严重程度不能只看“医学错误大小”

**Paper / Comment**  
Yu Gu, Eric J. Topol  
*Decision authority in health AI*  
Nature Health, 2026  
https://www.nature.com/articles/s44360-026-00185-z

### 22.1 对 GroundSignal severity 的意义

医疗 AI 风险应进一步考虑：

> AI 输出对用户现实健康决策拥有多大的影响力？

因此错误严重程度未来不能只有“事实错 / 事实对”，还应考虑 actionability（可行动性）和 decision authority（决策影响力）：

```text
低：知识解释
↓
中：风险解释 / 就医建议
↓
高：治疗选择 / 用药建议
↓
更高：自动触发或改变医疗行动
```

这可以成为 C4 严重错误体系未来升级的重要理论来源。

---

# Part VI. 小荷 AI 医生公开产品材料：研究真实产品任务，不推断内部架构

## 23. 小荷 AI 医生功能用户使用须知

**Public product document**  
*AI健康咨询用户使用须知 / 小荷AI医生功能 用户使用须知*  
更新日期：2026-02-13  
https://lf26-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/xiaohe/37328621-f943-47b8-b832-58dcd8905f94.html

### 23.1 公开列出的产品任务

公开说明涉及：

- AI 健康咨询；
- AI 诊室 / 深度健康咨询；
- 诊前信息收集；
- 分诊导诊；
- 门诊帮手；
- 报告解读；
- 拍患处；
- 拍药品 / AI 用药助手；
- 就医推荐 / 找医生找医院；
- 历史报告带入；
- 会话内容用于医生后续咨询的诊前信息。

### 23.2 GroundSignal 用途

它是**业务需求与真实产品交互边界参考**，不是小荷内部模型架构说明。

GroundSignal 六条患者业务轨可以持续与这些公开能力做 coverage mapping：

- 症状咨询；
- 用药信息；
- 报告解读；
- 既有问题随访；
- 医学信息辨析；
- 家属代问。

---

## 24. 小荷医疗大模型处方质量及效果评价项目

**Public informed-consent document**  
*“医疗大模型处方质量及效果评价项目”知情同意书*  
版本 1.0，2025-04-25  
https://lf3-cdn-tos.draftstatic.com/obj/ies-hotsoon-draft/xiaohe/7cf023fa-f140-4167-83a6-750a99470195.html

研究机构公开写明包括海南省人民医院和海南小荷健康网络技术有限公司。

### 24.1 为什么对 GroundSignal 很重要

公开流程展示了一条真实 downstream workflow：

```text
用户需求识别
→ AI 线上预问诊
→ 初步诊断 / 用药建议
→ 医生审核与追问
→ 正式处方
→ 处方审核
→ 药品配送
→ 医生反馈回流
```

这提示 GroundSignal 的远期评测不应永远停留在：

> 最终回答文本是否正确

而应该研究：

> 模型输出是否导致正确、可审核、可恢复的下游医疗工作流。

这是 M4 真实使用研究和 human-in-the-loop（人在回路）评测的重要业务参照。

---

# Part VII. 阅读顺序：不要一次读完所有论文

## 25. Phase A — 先解决“病例和患者到底长什么样”

顺序：

1. **AMIE 2025** — 多轮问诊和 OSCE case；
2. **AMIE 2026** — longitudinal / multivisit；
3. **MedDialog-CN** — 中文患者表达；
4. **MIMIC-IV-Note** — 真实临床文本；
5. **PMC-Patients** — 公开病例与病例—文献关系；
6. **HealthBench** — 现实型对抗评测案例。

目标产物：

- patient scenario schema；
- patient language taxonomy；
- source type registry；
- case lineage policy。

---

## 26. Phase B — 再解决“医疗文本怎么变成可靠状态”

顺序：

1. **CBLUE**；
2. **PubMedBERT / BLURB**；
3. **ClinicalBERT**；
4. **medSpaCy**；
5. **De-identification paper**。

目标产物：

```text
raw text
→ section
→ entity
→ context
→ negation
→ uncertainty
→ temporality
→ experiencer
→ normalization
→ relation
→ patient state
```

---

## 27. Phase C — 再解决“怎么把模型真正难住”

顺序：

1. **Gu et al. Nature Medicine 2026**；
2. **HealthBench scoring**；
3. **τ-bench**；
4. **LLM-as-a-Judge**。

目标产物：

- Stress Test Taxonomy；
- clean–perturbation pairing；
- repeat-run reliability；
- judge calibration suite；
- failure → evidence → attribution pipeline。

---

## 28. Phase D — 最后研究“小荷公开模型能力如何对应缺陷修复”

顺序：

1. **MedXIAOHE**；
2. **DeepMed**；
3. **CURE-Bench / CureFlow**；
4. **Decision Authority**；
5. 小荷公开产品使用须知；
6. 小荷处方评价项目公开材料。

目标产物：

> `GroundSignal defect → possible algorithm / engineering intervention map`

---

# Part VIII. 下载后怎么放：资料管理指南

## 29. 不要把所有下载文件直接 commit 到 GitHub

建议本地资料目录：

```text
external_reference/
├── papers/
│   ├── dialogue_and_patient_simulation/
│   ├── clinical_nlp/
│   ├── medical_eval/
│   ├── agent_and_tool_use/
│   └── xiaohe_bytedance/
├── datasets/
│   ├── open/
│   ├── credentialed/
│   └── restricted_review/
├── supplementary/
├── licenses/
└── manifests/
```

**公开仓库建议只保存：**

- 数据源说明；
- URL；
- DOI；
- license；
- checksum；
- schema；
- derivation code；
- 允许公开的派生统计/示例；
- split / lineage manifest。

**默认不要公开：**

- MIMIC 原始数据；
- 未重新核验许可的 MedDialog 原文；
- 真实患者可识别材料；
- 第三方版权受限 clinical case；
- held-out 隐藏测试答案。

---

## 30. 每一个数据源必须建立 Source Card

建议字段：

```yaml
source_id:
title:
source_type:
provider:
url:
doi:
version:
download_date:
license:
access_level: open | credentialed | restricted
contains_real_patient_data:
language:
medical_domain:
contains_dialogue:
contains_longitudinal_state:
contains_labels:
contains_rubric:
redistribution_allowed:
derivative_use_allowed:
privacy_review_status:
intended_groundsignal_use:
forbidden_use:
checksum:
notes:
```

没有 Source Card 的数据，不直接进入研究版 case factory。

---

# Part IX. 下载后怎么分析：不是“先全量导入”

## 31. 第一阶段只抽小样本做数据审计

每个大型数据源先抽取少量样本，例如 50–200 个 case / dialogue，先回答：

1. 文本真实长什么样？
2. 每条数据有哪些字段？
3. 有没有重复？
4. 有没有隐私/许可问题？
5. 患者、医生、报告、时间能否区分？
6. 能否恢复 chronology（时间顺序）？
7. 是否有 diagnosis / action / evidence 可作真值？
8. 哪些字段适合 C1–C8？
9. 哪些内容只能用于开发，不能用于 held-out？
10. 能否生成 clean–perturbation pair？

通过审计后才扩大处理规模。

---

## 32. 数据进入 GroundSignal 的标准转换链

```text
SOURCE
  ↓
license/privacy validation
  ↓
raw snapshot
  ↓
normalization
  ↓
clinical NLP extraction
  ↓
patient state
  ↓
expert / rule validation
  ↓
scenario family
  ↓
clean reference
  ↓
controlled perturbations
  ↓
development / calibration / held-out split
```

**禁止顺序：**

```text
下载数据
→ 直接扔给 LLM 改写
→ 当成 1000 个“真实患者案例”
→ 直接做排行榜
```

---

# Part X. 数据源与 GroundSignal C1–C8 对应关系

## 33. Capability mapping

| Source | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | 核心用途 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MedDialog-CN | ★★★ | ★★★ | ★★ | ★ | ★ |  | ★★★ | ★★★ | 中文患者语言和真实交互模式 |
| AMIE 2025 | ★★★ | ★★★ | ★★ | ★★★ | ★ |  | ★★★ | ★★ | 多轮问诊、OSCE、patient simulator |
| AMIE 2026 | ★★ | ★★★ | ★★★ | ★★★ | ★★★ | ★ | ★★ | ★★★ | 长期状态、疾病管理、用药 |
| MIMIC-IV-Note | ★ | ★ | ★★★ | ★★★ | ★★★ |  | ★ | ★ | 临床事实、时间线、报告 |
| PMC-Patients | ★ |  | ★ | ★ | ★★★ | ★ | ★ |  | 病例—证据检索与适用性 |
| HealthBench | ★★★ | ★★★ | ★★ | ★★★ | ★★ | ★ | ★★★ | ★★★ | rubric、adversarial eval |
| CBLUE | ★★★ | ★ | ★★★ | ★ | ★ |  | ★ |  | 中文医学文本底层能力 |
| CURE-Bench | ★ | ★ | ★★ | ★★★ | ★★★ | ★★★ | ★★ | ★★ | 用药/治疗 Agent |

★ 仅表示优先使用价值，不是数据集官方能力评分。

---

# Part XI. 当前 GroundSignal 最应该形成的四个新资产

## 34. Asset A — Patient Language Corpus

来源优先：MedDialog-CN + 后续合法真实用户材料。

目标不是训练聊天机器人，而是建立：

- 口语症状；
- 省略；
- 否定；
- 指代；
- 家属代问；
- 时间模糊；
- 药名模糊；
- 用户纠正；
- 催促；
- 错误复述；
- 情绪表达；
- 不知道 / 无法提供信息。

---

## 35. Asset B — Clinical Patient State Schema

来源优先：CBLUE + medSpaCy + MIMIC + ClinicalBERT literature。

目标：让每一轮对话都能回答：

> 当前我们真正知道什么？不知道什么？什么被纠正了？这个事实属于谁？什么时间？可信度多少？

这是 C3、诊断回放和工程/算法归因的基础。

---

## 36. Asset C — Medical Scenario Family

来源优先：AMIE OSCE + PMC-Patients + 经审核的公开病例。

一个 family 内含：

```text
same medical truth
+ clean version
+ ambiguity version
+ missing-info version
+ correction version
+ pressure version
+ tool-failure version
+ stale-evidence version
```

所有变体必须在同一个 split。

---

## 37. Asset D — Stress / Fault Library

来源优先：Gu 2026 + HealthBench + τ-bench + GroundSignal F01–F10。

区分：

### Input perturbation
患者表达和输入变化。

### Environment fault
工具、RAG、版本、解析、上下文故障。

### Controlled response fault
预先指定错误回答，验证 grader 能否识别。

这三类不能混在一个“困难样本”标签里。

---

# Part XII. 最终要形成的研究闭环

## 38. GroundSignal 的目标不是积累最多医疗数据

最终目标应该是：

```text
真实/可信来源
        ↓
可解释的 patient state
        ↓
可控患者互动
        ↓
模型失败
        ↓
具体 failure evidence
        ↓
algorithm / engineering / data / judge hypothesis
        ↓
单因素修复
        ↓
新 held-out regression
```

数据量只有在它增加：

- failure diversity；
- clinical coverage；
- patient-language realism；
- evidence quality；
- diagnostic power

时才有价值。

---

# Part XIII. 当前下载优先级摘要

## P0 — 立即下载 / 阅读

1. AMIE 2025 — paper + supplementary；
2. AMIE 2026 — paper + supplementary；
3. MedDialog paper + repository/data availability；
4. CBLUE paper + dataset/repository；
5. PubMedBERT paper；
6. medSpaCy paper；
7. Gu et al. Nature Medicine 2026 + public release；
8. HealthBench paper/data。

## P1 — 数据建设随后下载

9. PMC-Patients；
10. MIMIC-IV-Note（先完成 credential / DUA）；
11. ClinicalBERT paper；
12. de-identification paper。

## P2 — Agent / 评分方法

13. τ-bench；
14. LLM-as-a-Judge；
15. DeepMed。

## P3 — 小荷能力扩展与用药深水区

16. MedXIAOHE；
17. CURE-Bench + starter kit；
18. CureFlow materials；
19. Decision Authority；
20. 小荷 AI 医生使用须知；
21. 小荷医疗大模型处方质量及效果评价公开材料。

---

# Part XIV. 下载完成后下一步怎么做

当资料下载完成后，不立即开始全量训练或构造大规模 benchmark。下一步按以下顺序执行：

1. 建立 `source_inventory`；
2. 做 license / privacy / access audit；
3. 每个数据源抽取小样本；
4. 分析字段、语言和真实案例结构；
5. 建立 patient language taxonomy；
6. 建立 clinical patient state schema；
7. 从 AMIE / PMC / MIMIC 等来源各做少量 scenario conversion；
8. 建 clean–perturbation pairs；
9. 用 GroundSignal C1–C8 试评分；
10. 只在数据和评测器稳定后扩大规模。

---

# Glossary / 术语表

- **AI** — Artificial Intelligence，人工智能。
- **LLM** — Large Language Model，大语言模型。
- **MLLM** — Multimodal Large Language Model，多模态大语言模型。
- **NLP** — Natural Language Processing，自然语言处理。
- **Clinical NLP / cNLP** — Clinical Natural Language Processing，临床自然语言处理。
- **OSCE** — Objective Structured Clinical Examination，客观结构化临床考试。
- **RAG** — Retrieval-Augmented Generation，检索增强生成。
- **NER** — Named Entity Recognition，命名实体识别。
- **PHI** — Protected Health Information，受保护健康信息。
- **DUA** — Data Use Agreement，数据使用协议。
- **Rubric** — 评分规则；规定回答必须满足/避免的具体标准。
- **Held-out** — 留出测试；未参与当前算法选择的数据。
- **Perturbation** — 扰动；在尽量保持核心真值的前提下修改输入或环境。
- **Patient state** — 患者状态；对当前已知、未知、冲突、时间和来源事实的结构化表示。
- **Decision authority** — 决策影响力；AI 输出实际能够改变用户健康决策和行动的程度。

---

## Maintenance rule

本文件是**动态 Reference Guide**，不是静态 bibliography。以后每增加一个重要来源，应补充：

1. 来源类型；
2. 可访问性；
3. license；
4. GroundSignal 对应能力；
5. 下载路径；
6. 使用限制；
7. 是否已经转化为实际 case / state / perturbation / rubric。

只有“读过论文”不算完成；必须最终落到 GroundSignal 的数据资产、评测设计或缺陷诊断能力上。
