# Case-001 V2（无证据版）评测报告 — 修订版（Gold Audit 后）

日期：2026-08-27（修订：2026-08-27 gold audit 后）
> ⚠️ 本报告经历了结论反转：初版把 Codex"玛仕度肽 2025 已获批"判为 OVERCLAIM；
> 经外部审计（信达官方公告 + 经济观察网/36氪/雪球/新浪财经）确认 **2025-06-27 NMPA 批准体重管理、2025-09-19 批准 T2D**，
> 结论反转如下。详见 `postmortems/2026-08-27-mazdutide-gold-audit.md`。

## 实验设置

- 模型：DeepSeek（deepseek-chat，官方 API）vs OpenAI（Codex CLI 0.149.1 / OpenAI model，exact model ID not exposed）
- 设计：两组问题——组 A 未知实体 abstention（Asset X 裸问）；组 B 真实药物知识陷阱
- 版本：v2（无证据）/ 基准 truth：2026-08-27 官方状态

## Pilot Finding 1 — Knowledge freshness（核心发现）

**在玛仕度肽当前监管状态问题上，Codex 给出了更接近 2026 年真实状态的回答；DeepSeek 表现出 stale knowledge。**

| 题 | gold（2026-08-27 官方 truth） | DeepSeek | OpenAI/Codex |
|----|------------------------------|----------|--------------|
| Q4 玛仕度肽状态 | **已获批**：2025-06-27 体重管理（信尔美®）+ 2025-09-19 T2D | ❌ STALE_KNOWLEDGE："III 期、未获批"（训练截止 2024-10）；"2024 初提交 NDA"时间也有误 | ✅ "2025 年已获批上市"（基本正确，减重适应症） |

**初版误判说明**：初版把 Codex 判为 OVERCLAIM、DeepSeek 判为正确保守——错误。教训：gold 未冻结时不能下模型结论；必须先审计 gold。

## Pilot Finding 2 — Abstention（ceiling）

对虚构 Asset X（Q1-Q3）：

- DeepSeek：3/3 abstain ✅
- Codex：3/3 abstain ✅

**两者在显式未知实体上的基础 abstention 能力均较好，该任务已出现 ceiling**（不再构成区分）。

## Pilot Finding 3 — Grounded reasoning

V1 给完整 evidence snapshot 时两个模型都很好遵循所提供证据、避免自行扩张结论（19-20/20）。

**重要修正：V1 测的是 grounded reasoning / instruction following，不是 factual freshness。**
GroundSignal 在 V1 给的是 **frozen evidence snapshot**——而这个 snapshot 本身后来被证明不是 2026-08 的 current truth（玛仕度肽 stale）。
所以 V1 的"全对"只能说明"模型遵循给定证据"，不能说明"GroundSignal 给了真相"。

## 行为假设（不再叫 risk profile）

单例观察（1 case × 1 discriminating item × 单次采样）提示：

> **DeepSeek 在训练截止后的新事实（2025 获批）上更可能 stale；Codex 知识新鲜度更好。**
> 这只是一个 pilot behavioral hypothesis，需在更多 cases 中验证，不能据此定论模型风险画像。

## 组 B 其余题（不受反转影响）

| 题 | gold | DeepSeek | Codex |
|----|------|----------|-------|
| Q5 2023 销售额第一 | Keytruda 单品约 250 亿（口径需定义） | ✅ 指出口径歧义 | ✅ Keytruda |
| Q6 泽布替尼首个适应症 | MCL（陷阱 CLL） | ✅ | ✅ |
| Q7 司美格鲁肽中国减重 | 获批 2024-06 | ✅ | ✅ |
| Q8 特瑞普利 FDA | 鼻咽癌 | ✅ | ✅ |

## 对评测体系的意义

1. **Eval the model → Eval the evaluator → Eval the truth source**：这次是 truth source（GroundSignal 数据库）被 gold audit 抓到 stale
2. 新增指标：**Stale Claim Rate**（仍标 VERIFIED 但已被后续证据 supersede 的 claim 占比）、**Claim-Evidence Entailment**（URL 是否真正支持 claim）
3. 三 Track 实验设计落地（见 tracks.md）：
   - **Track A Closed-book**（不给证据 → 测模型内部知识/freshness/abstention；gold = 当前官方 truth）
   - **Track B Frozen-grounded**（给历史快照 → 测 evidence following/overclaim；gold = 快照当时 truth）
   - **Track C Live-grounded**（GroundSignal 当前检索 → 测 retrieval + freshness；gold = 当前官方 truth）
4. 玛仕度肽 = Track A/C 的黄金测试例（模型 freshness + GroundSignal 自身 freshness 双测）

## 局限（诚实）

- 两模型各跑 1 次，单样本观察
- DeepSeek token/耗时未记录（脚本缺陷，下一版补）
- Codex exact model ID 未暴露
- 样本 = 1 case × 2 版本，统计意义有限；需多 case 验证 freshness 假设
