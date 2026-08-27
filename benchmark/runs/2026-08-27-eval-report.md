# Case-001 模型评测报告（v0.1 首次实测）

日期：2026-08-27
评测方法：BD Answer Rubric 10 维 × 每题 gold 对照
模型：DeepSeek（deepseek-chat，官方 API）vs OpenAI（Codex CLI gpt 系，ChatGPT 订阅）

## 分维评分（0-2 分）

| # | 维度 | DeepSeek | OpenAI/Codex | 说明 |
|---|------|----------|--------------|------|
| 1 | Factual correctness | 2 | 2 | 无事实错误 |
| 2 | Evidence grounding | 2 | 2 | 全部基于快照，无编造 |
| 3 | Temporal validity | 2 | 2 | 用最新状态 |
| 4 | Competitive reasoning | 1.5 | 2 | DS Q2 直接判"直接竞争"，未强调 III 期 vs 已上市阶段不对等；Codex 主动区分"同机制对标 vs 市场重叠" |
| 5 | Decision relevance | 2 | 2 | 回答用户任务 |
| 6 | Prioritization | 2 | 2 | 都给出主/次级 watchlist 优先级 |
| 7 | Uncertainty | 2 | 2 | Q4/Q5 证据不足明确表达 |
| 8 | Actionability | 2 | 2 | 下一步可执行 |
| 9 | Information density | 2 | 2 | 判断驱动，非堆新闻 |
| 10 | Expression quality | 2 | 2 | 结构化、专业 |
| | **总分** | **19.5/20** | **20/20** | |

## 失败类型标签

| 模型 | 标签 | 位置 | 说明 |
|------|------|------|------|
| DeepSeek | RELATION_OVERSIMPLIFY（边缘 🟡） | Q2 | "是直接竞争"——共享适应症+GLP-1 机制但未充分强调阶段不对等（III 期 vs 已上市）；Q3 的机制区分（同机制竞品 vs 跨机制竞品）实际弥补了 Q2 |
| OpenAI/Codex | 无 | — | 全程合规 |

## 逐题亮点

- Q5（"已证明对肥胖有效"是否成立）：两个模型都给出"有条件成立"——"III 期证明减重疗效"成立，"已获批"不成立。这是 evidence sufficiency 核心考点，双双通过 ✅
- Q7（获批后答案如何变）：两个模型都正确区分"机制关系不变 vs 威胁等级变化"，且都指出"获批 ≠ 优于替尔泊肽"（Q4 不因获批改变）——这是最专业的考点，双双通过 ✅
- Q3（机制邻位区分）：两个模型都正确识别 Asset X 与替尔泊肽的同靶点关系比与司美格鲁肽更直接 ✅

## 关键发现（重要）

**1. Ceiling effect：给全证据快照时，两个前沿模型区分度不足。**
case-001 在"GroundSignal 输出完整证据快照"的条件下，gpt 系和 deepseek-chat 都拿到 19.5-20/20。这本身是 benchmark 设计的有效信号：**对前沿模型，需要提升难度或改变证据暴露方式**。

**2. 三个难度升级方向（下一版必做）：**

| 变体 | 做法 | 测什么 |
|------|------|--------|
| V2 无证据版 | 不给快照裸问（模拟无 GroundSignal 场景） | 内在知识 + 幻觉倾向（EVIDENCE_FABRICATION 高风险区） |
| V2 冲突证据版 | 公司新闻稿 vs CT.gov vs FDA 三源冲突 | SOURCE_HIERARCHY_VIOLATION |
| V2 时间陷阱版 | 快照里混入过期信息（如 2022 年状态） | STALE_KNOWLEDGE / TEMPORAL_CONFUSION |

**3. 无证据版预计暴露真实差距：** 没有 GroundSignal 时，模型依赖训练数据里的过时/错误信息（如把玛仕度肽写成已获批、把替尔泊肽 2023 年销售额写成第一）——这正好反证 GroundSignal 作为 truth infrastructure 的价值。

## 结论

- case-001（L1-L4 四层派生）验证了 benchmark 管线可用：问题生成 → 模型调用 → rubric 评分 → 失败类型输出 全链路跑通
- 前沿模型在"全证据"条件下表现优秀，说明 **LiveEval 的核心价值不在静态 case，而在动态证据快照 + 无证据/冲突证据变体**
- 下一步：做 case-001 的 V2 无证据版 + 冲突证据版，跑同两个模型，预期出现可量化的 failure 分化
