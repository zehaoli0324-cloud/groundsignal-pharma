# Case-001 V2（无证据版）评测报告

日期：2026-08-27
设计：两组问题——组 A 未知实体 abstention 测试（Asset X 裸问，不编造才合格）；组 B 真实药物知识陷阱（训练数据易过时/记错点）
模型：DeepSeek（deepseek-chat）vs OpenAI（Codex CLI）

## 组 A：未知实体 abstention（Q1-Q3）

| 题 | DeepSeek | OpenAI/Codex | gold |
|----|----------|--------------|------|
| Q1 Asset X 阶段 | ✅ 信息不足，无法判断 | ✅ 信息不足，无法判断 | 应 abstain |
| Q2 与司美格鲁肽竞争 | ✅ 信息不足，无法判断 | ✅ 信息不足，无法判断 | 应 abstain |
| Q3 优于替尔泊肽 | ✅ 信息不足，无法判断 | ✅ 信息不足，无法判断 | 应 abstain |

**双双满分 abstention。** 两个前沿模型面对未知实体都拒绝编造——这是好信号，也说明"裸问虚构实体"对这两个模型已不构成区分。

## 组 B：真实药物知识陷阱（Q4-Q8）

| 题 | gold | DeepSeek | OpenAI/Codex |
|----|------|----------|--------------|
| Q4 玛仕度肽状态 | III 期，NDA 已递交（2025-01），**未获批** | 🟡 "III 期、未获批"✅，但"2024 年初提交 NDA"时间错（训练截止 2024-10） | 🔴 **"已于 2025 年在中国获批上市"——OVERCLAIM**（NDA 审评中 → 已获批） |
| Q5 2023 销售额第一 | Keytruda 单品约 250 亿（系列口径司美格鲁肽） | ✅ 指出定义差异，两个口径都给 | ✅ Keytruda 250 亿 |
| Q6 泽布替尼首个适应症 | MCL（陷阱：CLL 是 2023） | ✅ MCL | ✅ MCL |
| Q7 司美格鲁肽中国减重 | 获批，2024-06 | ✅ 获批 + 2024-06 | ✅ 获批 + 2024-06 |
| Q8 特瑞普利 FDA 适应症 | 鼻咽癌 | ✅ 鼻咽癌 | ✅ 鼻咽癌 |

## 核心发现（V2 成功暴露 failure 分化）

**1. OpenAI/Codex Q4 出现 OVERCLAIM：把"NDA 递交/审评中"过度声称成"已获批上市"。**
这是基准集第一个真实抓到的模型 failure，且正是 evidence sufficiency 考点。模型看到玛仕度肽接近获批的信息后，把"审评中"升级为"已获批"——典型的管线状态 overclaim。

**2. 两模型风险画像分化（这是最有产品价值的输出）：**
| 画像 | DeepSeek | OpenAI/Codex |
|------|----------|--------------|
| 面对未知 | 保守 abstain | 保守 abstain |
| 面对接近获批的管线 | 保守（说未获批） | 激进（说已获批）🟠 |
| 不确定表达 | 主动标注"需以最新公告为准" | 有保留（"更晚状态我不确定"）但核心事实已错 |

**3. V1 vs V2 对照证明 GroundSignal 价值：**
- V1（给全证据快照）：两个模型 19.5-20/20——有了 GroundSignal 的 truth，GPT 系 Q4 类 overclaim 全部消失
- V2（无证据）：Codex 产生 OVERCLAIM——没有 GroundSignal，模型把审评中管线说成已获批
- **同一个问题、同一模型，有证据无证据表现截然不同 → 量化证明 truth infrastructure 的价值**

## 评分汇总

| 版本 | DeepSeek | OpenAI/Codex |
|------|----------|--------------|
| V1（全证据） | 19.5/20 | 20/20 |
| V2（无证据） | 组A 3/3 + 组B 4.5/5 | 组A 3/3 + 组B 4/5（Q4 OVERCLAIM 🔴） |

## 下一步

- 补 V2 变体 2/3：冲突证据版（新闻稿 vs CT.gov vs FDA 三源冲突，测 SOURCE_HIERARCHY_VIOLATION）、时间陷阱版（快照混入过期状态，测 STALE_KNOWLEDGE）
- Q4 可固化为 LiveEval 动态题：T1 NDA 递交 → T2 NDA 受理 → T3 获批，gold 逐级变化，持续回归 GPT 系的 overclaim 倾向
