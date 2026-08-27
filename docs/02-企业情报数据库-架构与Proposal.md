# GroundSignal Pharma — 架构与 Proposal（医药版）

## 1. 要解决的问题

临床医学与先进制药行业的信息高度分散：药物管线状态在 ClinicalTrials.gov，获批信息在 FDA/NMPA，商业交易在新闻稿，产能/供应链在年报与行业媒体。传统做法是人工看新闻，缺乏**跨实体、可追溯、随时间更新**的情报能力。

GroundSignal Pharma 把 groundsignal 的 evidence-grounded 情报方法迁移到医药领域：

```text
公开信息（ClinicalTrials.gov / FDA / NMPA / 药企公告 / 行业媒体）
→ Evidence（source_url + 采集时间 + 来源分级）
→ Claim / Relation / Event（管线关系 + 获批/交易事件）
→ Temporal Intelligence Graph（药企 ↔ 药物 ↔ 靶点 ↔ 临床试验 ↔ 产能）
→ Cross-Entity Analysis（共享靶点/适应症/投资人 → 竞争格局）
→ Change Detection（获批/阶段推进/授权/产能变化）
→ Decision-oriented Output（情报卡 · 全景 · Discovery Report · Watchlist）
→ Evaluation（Precision · Recall · Latency · False Alert）
```

## 2. 核心场景

- **管线竞争情报**：谁在同一个靶点/适应症竞争？（如 GLP-1 减重：礼来 vs 诺和诺德 vs 信达）
- **交易情报**：授权/并购/融资事件对哪些已有判断有影响？
- **供应链/产能情报**：GLP-1 API 产能瓶颈、CDMO 产能变化影响谁？
- **监管情报**：FDA/NMPA 获批、安全性信号出现后，哪些 watchlist 需要重新检查？

## 3. 数据模型（V2）

ENTITY（药企/Biotech/CXO/监管）· PRODUCT（药物管线）· TARGET（靶点）· FACILITY（产能/临床中心）· RELATION · CLAIM · EVIDENCE · EVENT

## 4. 与半导体版的关系

同一套 GroundSignal 方法（claim-evidence-event 模型 + 交叉扫描 + 变化检测），不同领域的数据源与对象模型。领域适配点：药物管线的 development_status、靶点关系、临床试验事件类型、产能追踪对象（API 产能 vs 芯片产能）。

## 5. 现状与边界（诚实声明）

已实现：结构化图谱（pharma 52 节点 / demo 32 节点）、单实体看板、双实体全景、交叉扫描、事件流、证据审计。
尚待证明：事件 Recall 覆盖、live 检测延迟、误报率、持续真实用户使用。
