# 三 Track 实验设计（Tracks A / B / C）

> 2026-08-27 起生效。玛仕度肽 Gold Audit 后确立：评测不能只给模型一个"当前真相"快照，必须显式区分知识来源与时间维度。

## 设计

| Track | 给模型什么 | 测什么 | Gold 来源 |
|-------|-----------|--------|----------|
| **A. Closed-book** | 不给 Evidence | 模型内部知识、freshness、abstention | 当前官方 truth（2026-08-27） |
| **B. Frozen-grounded** | 固定历史 snapshot（如 2025-01-20） | evidence following、overclaim、reasoning | snapshot 当时的历史 truth |
| **C. Live-grounded** | GroundSignal 当前检索结果 | retrieval + temporal freshness + reasoning | 当前官方 truth |

## 为什么需要拆

V1（全证据）与 V2（无证据）混淆了两个维度：**给不给证据** 与 **证据是不是当前 truth**。
- V1 的 snapshot 被证明是 stale（玛仕度肽仍写 Phase III）→ V1 实际测的是 frozen-grounded（Track B），不是 live
- V2 测的是 closed-book（Track A）
- Track C 才是 GroundSignal 作为 live truth infrastructure 的最终形态

## 测试例：玛仕度肽（黄金 bad case）

### Track A：Closed-book，2026-08-27

> 玛仕度肽目前是否已经在中国获批？

Gold：**是。2025-06-27 体重管理（信尔美®）；2025-09-19 2 型糖尿病。**

预期结果（2026-08-27 实测）：
- Codex ✅（2025 已获批）
- DeepSeek ❌ STALE_KNOWLEDGE（III 期/未获批，训练截止 2024-10）

→ 真正的 model boundary（knowledge freshness）。

### Track B：Frozen snapshot，2025-01-20

> 快照：NDA accepted / 尚未批准（2025-01-20 时点）

Gold：**尚未获批**（NDA 审评中）。

测：模型是否擅自把"NDA 受理"升级成"已获批"（Evidence Sufficiency / Overclaim）。
如果模型此时说"已获批"→ OVERCLAIM（因为在 2025-01-20 时点那是错的）。

### Track C：Live GroundSignal

系统在 2026-08-27 自动读取当前数据库，正确输出应包含 2025-06/09 获批。
如果 GroundSignal 仍输出 Phase III / NDA submitted → **是 GroundSignal 失败（stale truth），不是模型失败**。
指标：Truth Freshness / Stale Claim Rate。

## 新增指标

### Stale Claim Rate（Temporal Truth Validity）

```text
Stale Claim Rate =
  仍标 VALID/VERIFIED 但已被后续 authoritative evidence supersede 的 claim 占比
```

### Claim-Evidence Entailment

```text
这个 URL 真正支持这条 claim 吗？
（≠ 这条 claim 有 URL 吗？）
```

玛仕度肽 bad case：ClinicalTrials.gov 支持"有 III 期试验"，不支持"当前未获批"。

## 执行方式

```bash
# Track A
python3 benchmark/scripts/eval_models.py v2          # 现有 V2 = Track A

# Track B（待实现）：snapshot 参数化
python3 benchmark/scripts/eval_models.py --track B --snapshot 2025-01-20

# Track C（待实现）：先跑 GroundSignal 检索再注入
python3 benchmark/scripts/eval_models.py --track C --live
```
