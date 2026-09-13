# M1 启动前置条件清单（逐条：缺什么 / 谁提供 / 可否离线推进）

> **文档性质**：前置条件矩阵，非执行报告。**未调用任何真实模型**（`model_calls=0`）。
> **日期**：2026-09-13
> **关联**：`MILESTONES_M0-M5.md`（验证链）、`M1_PILOT_INTERFACE_READINESS.md`（接口实测）

---

## 0. 结论先行

**M1 的 4 个前置门当前 0/4 通过。其中 3 个必须医生参与，1 个必须用户授权。**

| 前置门 | 状态 | 阻塞方 | 可否离线推进 |
|---|---|---|---|
| `gold_approved` Oracle | 🔴 false | **医生**（填 63+63 行 + 16 临床字段） | ❌ 不可 |
| A/B 一致性 + 分歧裁决 | 🔴 未提交 | **医生 ×2 + 裁决人** | ❌ 不可 |
| 模型目标与预算授权 | 🔴 未指定 | **用户** | ❌ 不可（需付费授权） |
| 评分入口在 gold 上可运行 | 🟡 接口已验证，未在 gold 上跑 | Hermes（受 1 阻塞） | ✅ 接口层已做 |

---

## 1. 逐条拆解

### 门 1：`gold_approved` Oracle 🔴 阻塞于医生

**缺什么**：

| 缺口 | 载体 | 当前值 |
|---|---|---|
| A 医生 63 行判定 | `draft_stage1/A/review.json` | 63/63 `unassessed` |
| B 医生 63 行判定 | `draft_stage1/B/review.json` | 63/63 `unassessed` |
| 16 个临床字段 | `CLINICAL_REVIEW.json` | 16/16 `pending`、`conclusion: null` |
| 医生身份与资质 | 同上 + review.json 顶部 | 全 `null` |
| `clinical_approval` | `CLINICAL_REVIEW.json` | `false`（**AI 不得代置 true**） |

**谁提供**：持有执业资质的临床医生 ≥2 名（A/B 独立）+ 1 名裁决人（若分歧）。

**能否离线推进**：❌ **不能**。这是硬边界 —— 任何由 AI 填写的 clinical judgment 都是伪造 gold。

**能提前做的**（已完成）：
- ✅ 评审包干净可分发放（`build_clinician_packet.py`，已自检 + 独立复核）
- ✅ 填写指南（`CLINICIAN_GUIDE.md`）
- ✅ 泄漏防护与验证（`leak_scan.py`，PASS + 3 注入全抓）
- ✅ 一致性计算入口（`ab_agreement.py`，配对 63/63 验证通过）

---

### 门 2：A/B 一致性 + 分歧裁决 🔴 阻塞于医生

**缺什么**：
- A/B 双方提交后的一致性计算（工具已就绪，待数据）
- 若不一致：第三方裁决记录（`adjudication.schema.json` 已定义，`clinical_approval` 硬约束 false）

**谁提供**：医生 ×2 提交；不一致时第三人裁决。

**能否离线推进**：❌ 不能（无数据）。**但工具链已 100% 就绪并实测**：注入 63 行模拟评分，kappa 计算正确（完全一致=1.0 / 完全分歧=0.0 / 60-3 混合 simple=0.9524）。

---

### 门 3：模型目标与预算授权 🔴 阻塞于用户

**缺什么**（须明确到可复现）：
1. 目标模型精确 ID（如 `deepseek-v4-flash`）
2. provider / endpoint 配置
3. temperature、max_tokens
4. **预算上限**（调用次数或金额）
5. 是否两模型同条件对比（S10.1）

**谁提供**：**用户**（这是授权，不是开发缺陷）。

**能否离线推进**：❌ 不能（`BLOCKED_MODEL_SELECTION_AND_BUDGET`）。

**纪律**：预算未授权前 `model_calls=0`，不试探性付费调用。

---

### 门 4：评分入口在 gold 上可运行 🟡 接口已验证

**已做（本轮实测）**：

| 验证项 | 方法 | 结果 |
|---|---|---|
| 接入点存在 | `run_ap07_offline(client, ...)` | ✅ |
| 正常 client 跑通 | scripted client | ✅ `completed`，4 turn |
| 逐轮轨迹可用 | `session["turns"]` + `disclosure_log` | ✅ 记录 F2/F3 披露 |
| fail-closed | client=None / 坏 schema | ✅ `measurement_invalid` |
| 元数据位置 | `session["metadata"]`（非顶层） | ✅ 已实测并写入文档 |

**本轮修复**：client 失败原被误标 `invalid_component="simulator"`，已改为 `"collector"`。

**缺什么**：在 `gold_approved` Oracle 上跑一次验证（受门 1 阻塞）。

---

## 2. 医生到位后的启动序列（预计 < 1 天）

```text
1. 发包含 → 医生 A（reviewer_A.zip）+ 医生 B（reviewer_B.zip）     [5 min]
2. 医生各自填 63 行 + 顶部身份声明                                  [医生侧]
3. 收回两包，运行 ab_agreement.py 算一致性                          [5 min]
4. 若分歧 → 第三方裁决（adjudication.schema.json）                  [视分歧数]
5. 医生填 CLINICAL_REVIEW.json 的 16 行临床字段                     [医生侧]
6. 医生显式置 clinical_approval=true（AI 不代置）                   [医生侧]
7. Oracle 标记 gold_approved → M1 可启动                            [即时]
```

**Hermes 侧已 100% 就绪，医生侧一到即可跑。**

---

## 3. 仍需协调人确认的开放项

| # | 开放项 | 影响 | 建议 |
|---|---|---|---|
| 1 | `NODES.md` 是否纳入评审包 | 医生可能缺节点级定义 | 若纳入需确认不含作者预期 |
| 2 | 判据范围 C01–C09（无 C10）是否正确 | 指南已按实际记录 | 确认 C10 是刻意排除 |
| 3 | 是否需第二家族并行（母版验证前） | 验证链建议**不要** | 按 M0–M5 保持单家族 |

---

## 4. 验证边界

- 本文为**前置条件矩阵**，非执行报告。
- **未调用任何真实模型**，未产生任何模型分数，`clinical_approval` 保持 `false`。
- 所有接口状态为实测（实际运行 Python 代码），非引用文档。
- 未创建 cron、未启动付费调用、未伪造任何临床判断或签名。
