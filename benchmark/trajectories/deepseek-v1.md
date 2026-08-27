# deepseek-v1 — DeepSeek trajectory

## 调用配置

- 模型：deepseek-chat（DeepSeek 官方 API，https://api.deepseek.com）
- 调用方式：单次 chat completion（temperature 0.3, max_tokens 3000）
- 推理可见性：**无**（deepseek-chat 不输出 reasoning；本次未使用 deepseek-reasoner）
- 工具调用：无（纯问答）
- token usage：未记录（评测脚本当时未保存 usage 字段）

## Prompt 结构

1. SYSTEM：医药行业竞争情报分析师（BD/战略视角）+ 证据纪律（"基于快照回答，证据不足说不知道，不编造"）
2. EVIDENCE：GroundSignal 证据快照（Asset X III 期阳性 / 替尔泊肽已上市 / 司美格鲁肽已上市 / 玛仕度肽 III 期 NDA 递交）
3. QUESTIONS：7 题（L1 事实 → L2 关系 → L3 证据充分性 → L4 产品题）

## 逐题关键判断点

| 题 | 行为 | 判定 |
|----|------|------|
| Q1 阶段 | "III 期达到主要终点，尚未提交上市申请" | ✅ 正确 |
| Q2 与司美格鲁肽竞争 | 直接判"是直接竞争"，但给出机制差异（双 vs 单激动） | 🟡 未强调阶段不对等 |
| Q3 与替尔泊肽区别 | "同机制竞品 vs 跨机制竞品" | ✅ 优秀 |
| Q4 优于替尔泊肽 | "不足以说明，需头对头" | ✅ 正确 |
| Q5 "已证明有效" | "不成立；只能说 III 期显示有效" | ✅ 正确 |
| Q6 watchlist | 替尔泊肽/礼来高优先级 + 理由 + 次级 watchlist | ✅ 优秀 |
| Q7 获批后变化 | 逐题更新；"获批≠优于替尔泊肽" | ✅ 优秀 |

## 输出全文

见 `runs/2026-08-27-deepseek.md`。
