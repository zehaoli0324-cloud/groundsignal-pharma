# v0.2 六 Case 评测报告：DeepSeek vs Codex

日期：2026-08-27 · 6 个 Decision Intelligence Case（控制变量式冻结快照）
模型：DeepSeek（deepseek-chat，官方 API）vs Codex（CLI 0.149.1 / GPT-5-family，OpenAI model exact ID not exposed）

## 1. 评分总表

| Case | DeepSeek (U/10) | Codex (U/10) | DeepSeek (bench/20) | Codex (bench/20) | 核心考点 |
|------|:---:|:---:|:---:|:---:|---------|
| 001 competitive-impact | 10 | 10 | 20 | 20 | 竞争层级 + 排序 |
| 002 regulatory-conflict | 10 | 10 | 20 | 20 | source hierarchy + 冲突 |
| 003 licensing-bd | 10 | 10 | 20 | 20 | partner 排序 + 不编造意图 |
| 004 due-diligence | 10 | 10 | 20 | 20 | claim 拆解 + 跨试验不可比 |
| 005 safety-signal | 10 | 10 | 20 | 20 | 信号≠因果≠类别效应 |
| 006 temporal-watchlist | 10 | 10 | 20 | 20 | Top3 + 去重 + changed claim |

**双模型 6/6 case 全部 Decision-ready（U 10/10，bench 20/20），无 Critical Error。**

## 2. 逐 case 判断点（两模型与 gold 的一致性）

| Case | gold 关键判断 | DeepSeek | Codex |
|------|-------------|----------|-------|
| 001 | A>B>C：同机制已上市/市场竞争者/机制不同 III 期 | ✅ 全对 + 监控频率/触发条件 | ✅ 全对 + 升级/降级条件 |
| 002 | under review 不能标已获批；Tier 0 决定权 | ✅ 全对 + 给内部标准表述 | ✅ 全对 + 事实/预期分离 |
| 003 | B>A>C；A 有 portfolio conflict；outreach≠成交概率 | ✅ 全对 + 保留权益→联合开发结构推理 | ✅ 全对 + 资源竞争/估值压价/交易搁置 |
| 004 | best-in-class=HYPOTHESIS；跨试验不可比 | ✅ 全对 + "可投但按风险定价，剔除 superiority 溢价" | ✅ 全对 + "期权价值+明确折价" |
| 005 | 不定类别效应但升 P0；B 无警告=反证 | ✅ 全对 + 先验概率 vs 因果确证 | ✅ 全对 + 触发条件驱动分阶段 |
| 006 | E1/E3/E5；E2/E4 去重；E9 降级 | ✅ 全对 + 管理层 vs 医学事务视角 | ✅ 全对 + 主要不确定性定位 |

## 3. Trajectory 分析（Codex rollout，从 session jsonl 提取）

| Case | input tok | output tok | reasoning tok | total | duration |
|------|----------:|----------:|----------:|------:|------:|
| 001 | 16910 | 2482 | 87 | 19392 | 62.6s |
| 002 | 15205 | 1216 | 0 | 16421 | 35.0s |
| 003 | 15268 | 2197 | 20 | 17465 | 59.6s |
| 004 | 15248 | 2308 | 21 | 17556 | 58.3s |
| 005 | 15254 | 2574 | 23 | 17828 | 74.6s |
| 006 | 15446 | 1311 | 0 | 16757 | 34.1s |

要点：
- **reasoning 加密不可读**（OpenAI 限制），仅能计数：复杂推理 case（001 竞争/005 安全）reasoning tokens 多，简单事实类（002 监管状态/006 watchlist）为 0——reasoning 量与任务复杂度正相关
- **agent runtime 开销显著**：每次调用 ~15-17k input tokens（系统提示 + skills 指令占大头），总耗时 34-75s
- DeepSeek 侧（case-001 实测 usage）：prompt 650 + completion 2734 = 3384 tokens——**API 直连比 agent runtime 轻一个量级**（但成本口径不同：订阅 vs API，不能直接断言"便宜"）

## 4. 模型能力判断

### 4.1 在"冻结快照 + 明确用户任务"条件下（Track B）

**两个前沿模型都能达到 Decision-ready：12 能力全覆盖，无显著差异。**

| 能力 | DeepSeek | Codex |
|------|:---:|:---:|
| Factual / Evidence / Temporal / Source hierarchy / Relation / Sufficiency / Abstention / Prioritization / Actionability / Falsification / Impact / User-specific | 全部达标 | 全部达标 |

结论：**"快照跟随 + 用户任务理解"是前沿模型的共同强项**。v0.2 的 case 设计（控制变量 + 冻结快照 + 明确决策任务）让好模型都答好——这是 benchmark 应有的行为，但也意味着 Track B 对这两个模型区分度低。

### 4.2 模型差异的真实来源（已有证据）

1. **Knowledge freshness（Track A / closed-book）**：玛仕度肽 bad case（gold audit）证明——DeepSeek 训练截止 2024-10 后新事实（2025-06 NMPA 获批）stale；Codex 知识更新。**这是目前唯一实测到的模型边界。**
2. **表达风格**：同一判断的呈现方式不同（DeepSeek"按风险定价剔除溢价" vs Codex"期权价值+折价"；DeepSeek 更强调交易结构推理，Codex 更强调资源竞争/风险机制）——但都达到专业标准。
3. **推理可见性**：Codex 有加密 reasoning（量随复杂度变化），DeepSeek 完全黑盒——两者都无法做推理级审计。

### 4.3 对数据生产/评测体系的意义

- v0.2 证明：**给定高质量 evidence snapshot，两个前沿模型都能把知识转成决策 Intelligence**——truth infrastructure 的价值不在于"防止模型犯错"，而在于"让不同模型都能稳定输出专业判断"
- 真正的区分度战场在 Track A（closed-book freshness）和 Track C（live retrieval + 冲突环境）——v0.1 的玛仕度肽 bad case 已证明 Track A 能抓到真实边界
- 下一步 benchmark 优先级：**把 v0.2 的 6 case 各派生 Track A（无快照）版本 + 实现 Track C（GroundSignal 实时检索注入）**，预计能暴露 freshness 与 retrieval 差异

## 5. 诚实局限

- 每模型每 case 单次采样（无温度扰动）；评分由单一 human judge（盲评未做二次校验）
- DeepSeek usage 仅 case-001 记录（脚本本次已补 usage 保存）
- Codex exact model ID 未暴露；reasoning 加密无法审计推理路径
- 冻结快照是控制变量设计，不代表真实世界当前状态

## 6. 产物索引

- 回答全文：runs/2026-08-27-v02-deepseek-case-*.md / runs/2026-08-27-v02-codex-case-*.md
- 评分：cases/case-*/scores/（benchmark-scores.json + user-utility-scores.json）
- trajectory：trajectories/v02-codex-rollout-summary.json
- 评测脚本：scripts/eval_cases_v02.py / extract_codex_v02.py / extract_codex_v02_trajectory.py
