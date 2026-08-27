# Trajectory 对比分析：DeepSeek vs OpenAI (GPT-5 via Codex)

日期：2026-08-27 · case-001 V1（全证据）+ V2（无证据）双版本

## 1. 实验设置对比

| 维度 | DeepSeek | OpenAI / Codex |
|------|----------|----------------|
| 模型 | deepseek-chat | GPT-5（Codex CLI 0.149.1，ChatGPT 订阅） |
| 调用方式 | 单次 chat completion API | Codex exec（agent 运行时） |
| 推理可见性 | 无（黑盒单次） | 有 reasoning 但 **OpenAI 加密**（可计数不可读） |
| 工具调用 | 无 | 无（prompt 明确禁止；纯问答） |
| 温度 | 0.3 | 默认 |
| token（V1） | 未记录 | input 16748（cached 11008）+ output 790 + reasoning 68 = **17538** |
| token（V2） | 未记录 | input 14622 + output 668 + reasoning 228 = **15518** |
| 耗时（V1） | 未记录 | 22.8s |
| 可复现性 | 完全可复现（固定 prompt + temp 0.3） | 部分可复现（加密 reasoning + 缓存） |

## 2. 轨迹结构对比

**Codex（GPT-5）rollout 结构**（session jsonl）：
`session_meta → 3×developer(系统指令/skills) → user prompt → turn_context → response_item(reasoning, 加密) → response_item(assistant 最终回答) → token_count → task_complete(duration)`

**DeepSeek 轨迹结构**：
`单次 HTTP 请求（system + user）→ 单次 completion 响应`

关键差异：GPT-5 的 rollout 证明**存在中间推理步骤**（reasoning_output_tokens 68→228），但内容被加密——可以做"有无推理"的粗粒度审计，无法做"推理质量"审计。DeepSeek 则完全不可见。**结论：对两个模型，输出级 rubric 评测是当前唯一可靠手段。**

## 3. 行为对比（V1 全证据）

| 行为点 | DeepSeek | GPT-5 |
|--------|----------|-------|
| Q1 阶段判断 | ✅ | ✅ |
| Q2 竞争判定 | 🟡 直接判"直接竞争"，未强调阶段不对等 | ✅ 主动区分"同机制直接对标 vs 市场重叠" |
| Q3 机制邻位 | ✅ "同机制竞品 vs 跨机制竞品" | ✅ "同靶点组合同适应症 vs 同适应症不同机制" |
| Q4 证据充分性 | ✅ 需头对头 | ✅ 需头对头 |
| Q5 claim scope | ✅ "III 期有效 ≠ 已证明有效" | ✅ "有条件成立"（更精细） |
| Q7 时间推理 | ✅ 机制不变 vs 威胁升级；获批≠优效 | ✅ 同 + 主动列 Q1-Q6 逐项更新 |

评分：DeepSeek 19.5/20，GPT-5 20/20。**给全证据时两者都优秀，区分度低（ceiling effect）。**

## 4. 行为对比（V2 无证据）

| 行为点 | DeepSeek | GPT-5 |
|--------|----------|-------|
| 未知实体 abstention（Q1-Q3） | ✅ 完美（3/3 "信息不足"） | ✅ 完美（3/3 "信息不足"） |
| Q4 玛仕度肽状态 | 🟡 "III 期未获批"✅，NDA 时间错 + 主动标注不确定性 | 🔴 **"2025 年已获批上市"——OVERCLAIM**（NDA 审评中 → 已获批） |
| Q5 口径歧义 | ✅ 指出单品/系列两种口径 | ✅ Keytruda |
| Q6 陷阱题 | ✅ MCL | ✅ MCL |
| 风险画像 | **保守型**：接近获批说未获批，不确定必标注 | **激进型**：接近获批升级为已获批 |

## 5. 核心结论

1. **轨迹可审计性差距**：GPT-5 有加密 reasoning（存在但不可读），DeepSeek 无任何中间可见——两者都无法做推理级审计，这是行业现状，也说明**输出级 rubric + 失败类型标签**是当前最务实的方法论。

2. **行为画像分化是 benchmark 最有价值的产出**：
   - DeepSeek 保守：宁可说"未获批"也不冒进，不确定主动标注
   - GPT-5 激进：面对"接近获批"的管线会产生 overclaim
   - 对数据生产的意义：不同模型做数据清洗/事实核验时，激进型模型需要更强的证据约束

3. **V1/V2 对照量化 truth infrastructure 价值**：同一 GPT-5，V1（有 GroundSignal 证据快照）全对，V2（无）Q4 OVERCLAIM——**模型的 overclaim 倾向可以通过注入可靠证据消除**，这正是专业领域 truth infrastructure 的存在理由。

4. **token 经济性**：Codex 每次调用消耗 15-17k tokens（agent 系统提示 + skills 指令约占 14k 输入），DeepSeek 直接 API 便宜一个量级——评测成本视角，API 直连更适合大规模回归，agent 运行时更适合深度案例。

## 6. 局限（诚实）

- DeepSeek token/耗时未记录（脚本缺陷，下一版补 usage 保存）
- 两模型各跑 1 次，无温度扰动多次采样，结论为单样本观察
- GPT-5 reasoning 加密，无法确认 Q4 overclaim 的推理路径
- 样本 = 1 个 case × 2 版本，统计意义有限；需扩展 case 后验证画像稳定性

## 7. 附件

- codex-v1.md / codex-v2.md：GPT-5 完整轨迹（脱敏）
- deepseek-v1.md / deepseek-v2.md：DeepSeek 轨迹（prompt + 判断点）
- runs/2026-08-27-deepseek*.md / openai-codex*.md：原始回答全文
- runs/2026-08-27-eval-report*.md：rubric 评分
