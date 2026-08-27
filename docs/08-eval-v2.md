# Eval v2 — 系统有没有用？（医药版）

## 用户价值指标

| Metric | Question | 当前值 |
|--------|----------|--------|
| Relation Recall | 应该知道的关系覆盖多少？ | 待测（gold set 构建中） |
| Event Recall | 重要事件抓到多少？ | **8/12 = 67%**（见下） |
| Detection Latency | 事件发生后多久知道？ | live 待 cron 数据 |
| False Alert Rate | 推送中有多少无意义？ | 待 cron 运行 ≥2 周 |
| Evidence Coverage | 多少节点能溯源到来源域名？ | 节点级 100%（0 UNKNOWN）；claim 级审计待实施 |

## Event Recall 基准集（2024-2026 医药重大事件 12 项）

| # | 事件 | 覆盖 |
|---|------|------|
| 1 | 礼来 Zepbound 获批减重（2023-11） | ✅ |
| 2 | 强生/传奇 Carvykti 二线获批（2024-04） | ✅ |
| 3 | 百济替雷利珠 FDA 获批（2024-03） | ✅ |
| 4 | 诺和诺德 Wegovy 中国获批减重（2024-06） | ✅ |
| 5 | 诺和诺德收购 Catalent（2024-02） | ✅ |
| 6 | 礼来追加 53 亿美元扩产（2024-05） | ✅ |
| 7 | 传奇比利时新工厂（2024-05） | ✅ |
| 8 | 玛仕度肽 NDA 受理（2025-01） | ❌（仅产品节点） |
| 9 | 玛仕度肽 III 期成功（2024-08） | ❌ |
| 10 | 君实特瑞普利 FDA 获批（2023-10） | ✅ |
| 11 | 泽布替尼 CLL/SLL 获批（2023-01） | ❌ |
| 12 | 信达玛仕度肽 III 期 DREAMS-2 达终点 | ❌ |

**覆盖 8 项 / 12 项 = 67%**。未覆盖 4 项 = 采集 backlog（优先级排序：玛仕度肽 NDA/III 期 → 泽布替尼 CLL）。

## 诚实结论

- precision 高（证据可追溯、0 UNKNOWN 节点），coverage 有限（67%），live latency 与 false-alert 待 cron 证明
- 回溯覆盖 ≠ live 延迟：建库补录事件不能当卖点
- **注意：Evidence Coverage 分两层——节点级（source_url 域名可溯源）与 claim 级（原子 claim 逐条审计）。** 2026-08-27 起 claim-level audit 已实施（`scripts/claim-audit.py`）：pharma 102 条原子 claim 全部可溯源（70 VERIFIED / 32 SUPPORTED / 0 UNSUPPORTED）。demo 库关系行未带来源标注（v1 格式），claim 级支持率 0%，是已知短板。
