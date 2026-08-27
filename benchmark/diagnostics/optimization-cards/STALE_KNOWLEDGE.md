# Optimization Card — STALE_KNOWLEDGE

> 状态：已激活（唯一有真实案例的 cluster，2026-08-27）

```yaml
failure_cluster: STALE_KNOWLEDGE

observed_behavior:
  - deepseek_v2_q4: "玛仕度肽 III 期、尚未获批"（2026-08-27 时点错误，实际 2025-06-27 NMPA 已获批体重管理、2025-09-19 获批 T2D）
  - deepseek_v2_q4: "2024 年初提交 NDA"（实际 2025-01 受理）
  - groundsignal_self: 数据库玛仕度肽.md 曾标 VERIFIED / last_verified_at=2026-08-27 但 development_status 为过期 NDA 状态（truth source 自身 stale）

user_experience:
  - 用户基于错误前提做监管/竞争判断
  - 对系统的信任流失（"连状态都是错的"）
  - 风险：在决策场景（BD/投资）直接造成错误行动

capability_gap_hypothesis:
  - 模型训练截止后的新事实（<1 年）freshness 不足，且无 retrieval 补偿
  - 真相源（GroundSignal 数据库）缺少"权威来源 supersede 旧 claim"的时序更新机制（Temporal Intelligence Graph 未实现）

intervention_candidates:
  - data: 监管状态类训练数据更新周期缩短；claim 带 valid_from/valid_until/superseded_by
  - sft_preference: "监管状态"问题要求显式 knowledge cutoff 声明；preferred 回答标注"我训练截止于 X，最新状态需查证" > 给出过期状态
  - prompt_product: Track C 注入时强制带 retrieved_at；无检索时提示"此状态可能已过期"
  - retrieval_tool: 实现 GroundSignal Temporal Intelligence Graph（SUPERSEDED claim 保留 + 指向新 claim）——这是 Track C 的地基

success_metrics:
  - Stale Claim Rate（仍标 VERIFIED 但被 supersede 的 claim 占比）
  - Track A Freshness accuracy（玛仕度肽状态题答对率）
  - Temporal Validity（claim 是否带时间边界）

regression_cases:
  - case-002-regulatory-conflict（Track A 派生版：无快照问玛仕度肽/监管状态）
  - 玛仕度肽状态题（2026-08-27 实测：DeepSeek ❌ / Codex ✅ → 优化后应双 ✅）
```
