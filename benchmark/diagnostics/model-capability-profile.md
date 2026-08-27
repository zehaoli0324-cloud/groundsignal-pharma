# Model Capability Profile — DeepSeek vs Codex（v0.4 四层诊断）

> 诊断基于：v0.2 六 Case 实跑（Track B frozen-grounded）+ 玛仕度肽 bad case（Track A closed-book）
> 方法：Expert Diagnosis Rubric（A 知识 / B 推理 / C 表达 / D 用户价值，23 维 × 0/1/2）

## 1. 总览（capability profile，非总榜）

| 层 | DeepSeek (deepseek-chat) | Codex (GPT-5-family) |
|----|:---:|:---:|
| A1 Factual Correctness | ✅ 快照内全对 | ✅ 快照内全对 |
| A2 Temporal Freshness | 🔴 **Track A 有真实缺陷**（玛仕度肽 2025 获批 stale） | ✅ 更接近 2026 真实状态 |
| A3 Evidence Sufficiency | ✅ 全达标 | ✅ 全达标 |
| A4 Source Hierarchy | ✅ case-002 Tier 0 决定权处理优秀 | ✅ 同 |
| A5 Claim Scope | ✅ case-004 "best-in-class=Hypothesis" | ✅ 同 |
| B1-B7 Reasoning | ✅ 6 case 全达标（B>A>C 排序、信号≠因果、Top3 压缩） | ✅ 同（侧重不同：DS 交易结构推理 / Codex 资源竞争机制） |
| C1-C6 Expression | ✅ Decision-first + 分层 + 触发条件 | ✅ 同 |
| D1-D5 User Utility | ✅ 6 case 全 10/10 Decision-ready | ✅ 同 |

## 2. 为什么有差异？（专家诊断）

### 差异 1：A2 Temporal Freshness（唯一实测到的模型边界）

**bad case（玛仕度肽，2026-08-27 Track A 无证据）：**

| 模型 | 回答 | 诊断 |
|------|------|------|
| DeepSeek | "III 期、尚未获批；2024 年初提交 NDA" | 🔴 STALE_KNOWLEDGE：训练截止 2024-10，不知道 2025-06-27 NMPA 获批。**原因：内部知识 freshness 无 retrieval 补偿** |
| Codex | "2025 年已获批上市" | ✅ 基本正确（2025-06-27 体重管理 + 2025-09-19 T2D） |

### 差异 2：推理侧重（同判断，不同机制解释）

| Case | DeepSeek | Codex | 判断 |
|------|----------|-------|------|
| 003 BD | "保留权益→联合开发/区域权益结构"（交易结构推理） | "资源竞争/估值压价/交易搁置风险"（portfolio conflict 机制） | 都专业，视角互补 |
| 004 尽调 | "可投但按风险定价，剔除 superiority 溢价" | "给期权价值+明确折价" | 同思路不同表达 |
| 005 安全 | "先验概率 vs 因果确证" | "触发条件驱动分阶段" | 都给出 decision under uncertainty |

## 3. 用户会感受到什么差异？

- **Track B（有证据）**：几乎无差异——两个模型都是 Decision-ready，用户都能带进会议。表达风格略不同（DS 更"结构化表格+交易逻辑"，Codex 更"机制叙事+风险条件"），但都专业。
- **Track A（无证据）**：真实差异——DeepSeek 对 <1 年新事实（监管获批）可能给出过期状态，用户会基于错误前提决策；Codex 新鲜度更好。**在数据产品场景（无 retrieval 兜底）这是致命差异。**

## 4. 优化方向（对应 v0.4 §8）

| 层面 | 干预 | 针对 |
|------|------|------|
| data | 监管状态类训练数据更新周期缩短；时间戳显式化 | DeepSeek A2 |
| SFT / preference | "监管状态"问题要求显式 knowledge cutoff 声明；preferred: 标注不确定 > 给过期状态 | DeepSeek A2 |
| prompt / product | GroundSignal 注入（Track C）时强制带 retrieved_at；无检索时提示"可能过期" | 双模型 |
| retrieval / tool | Track C Live-grounded：实时查 FDA/NMPA/CT.gov 再回答 | 双模型（消除 Track A 差异） |
| regression | case-002 Track A 派生版 + 玛仕度肽状态题，持续回归 freshness | 双模型 |

## 5. 诚实结论

- **在"有证据"的专业任务上，两个前沿模型能力相当（Decision-ready）**——这本身是 benchmark 的有效结果，说明 truth infrastructure 让不同模型都能稳定输出专业判断
- **模型差异的真实来源是"无证据时的内部知识 freshness"**——已被玛仕度肽 bad case 证明，是 Track A 的核心战场
- v0.4 框架（23 维 + 10 failure cluster）已就绪；10 个 cluster 中 9 个待 Track A/C 派生版激活
