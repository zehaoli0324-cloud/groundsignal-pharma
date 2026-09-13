# M1 Pilot 运行接口就绪度核查

> **文档性质**：接口核查，**未执行任何真实模型调用**（`model_calls=0`）。
> **日期**：2026-09-13
> **依据**：`scripts/ap07_v3_runner.py`（328 行）、`scripts/ap07_v3_packet.py`、`scripts/ap07_rules.py`、`benchmark/patient-consultation-v1/suite.json`

---

## 1. M1 要验证的三个问题（回顾）

| # | 问题 | 对应接口需求 |
|---|---|---|
| 1 | 评分标准是否能稳定裁决 | 需要真实模型回答 + 评分入口 |
| 2 | 是否存在"最终答案正确但过程危险" | 需要逐轮轨迹（非仅最终答案） |
| 3 | 题目是否真能制造有意义的压力 | 需要多前缀变体（severe/barrier/support/opening...） |

---

## 2. 接口就绪度

### 2.1 核心接入点：`run_ap07_offline(client, ...)`

```python
def run_ap07_offline(client, *, stop_after=None, max_turns=MAX_NATURAL_ANSWERS):
    """Drive the real AP07 patient simulator with a *local* client function."""
```

**这是 M1 的唯一接入点**：把 `client` 从 scripted 函数换成真实模型调用函数即可。

**当前状态**：
- `client` 契约已定义（接受消息列表，返回回答）
- 当前传的是 scripted client，明确标注 `SYNTHETIC_TRAJECTORY_LABEL`
- `model_calls=0` 被硬编码并要求保持（`_clean_offline_result` 校验）
- 无 client 时 fail-closed：`status=measurement_invalid`、`ENVIRONMENT_ISSUE`

**docstring 原文**：
> *"The client never contacts a network: in this window it is always a scripted ... labelled SYNTHETIC_TRAJECTORY_LABEL with model_calls == 0"*

### 2.2 组件清单

| 组件 | 路径 | 行数 | 作用 | 状态 |
|---|---|---|---|---|
| 运行器 | `scripts/ap07_v3_runner.py` | 328 | 驱动真实 PatientSimulator，逐轮轨迹 | ✅ |
| 评审包生成 | `scripts/ap07_v3_packet.py` | 102 | 导出评审/模型可见包 | ✅ |
| 规则 | `scripts/ap07_rules.py` | 56 | 披露与节点规则 | ✅ |
| 题包 | `benchmark/patient-consultation-v1/suite.json` | 2203 | AP07 完整定义 | ✅ |
| Oracle | `scripts/ap07_v3_oracle.py` | — | 节点激活，只读 visible prefix | ✅ |
| Verifier | `scripts/ap07_v3_verifier.py` | — | fail-closed 泄露扫描 | ✅ |

### 2.3 前置门状态（M1 启动条件）

| 门 | 状态 | 说明 |
|---|---|---|
| `gold_approved` | 🔴 **false** | Oracle 未经临床审核 |
| A/B 评审 | 🔴 **未提交** | 63+63 行全 unassessed |
| `calibration_ready` | 🔴 false | 评分器未校准 |
| 模型目标与预算 | 🔴 **未指定** | `BLOCKED_MODEL_SELECTION_AND_BUDGET` |
| `stage1_released` | 🔴 false | 未授权发放 |

**结论**：**接口就绪，但不得启动 M1。**

---

## 3. M1 启动的最小前置

M1 可以开始，当且仅当：

1. ✅ AP07 Oracle 达到 `gold_approved`（M0 完成）
2. ✅ A/B 评审提交并完成一致性计算 + 分歧裁决
3. ✅ 模型目标与预算获明确授权
4. ✅ 评分入口在 `gold_approved` Oracle 上验证可运行

**当前：0/4**

---

## 4. M1 执行方式（接口层预案，不执行）

### 4.1 变体覆盖（回答"题目是否有压力"）

`suite.json` 已定义的前缀变体：
- `opening`（首问）
- `severe`（严重疼痛）
- `barrier`（就医障碍）
- `support`（有家人支持）
- `migration`（疼痛位置迁移）
- `action_done`（已采取行动）

**M1 应在全部变体上运行**，而非只跑 base —— 否则无法回答"题目是否制造了有意义的压力"。

### 4.2 逐轮轨迹（回答"过程是否危险"）

`run_ap07_offline` 返回的是**逐轮会话**（非仅最终答案），配合 `ap07_v3_oracle.py` 的节点激活，可以检出：
- 最终答案正确 + 中间轮次出现危险建议 → 问题 2 的场景

### 4.3 相同条件双模型

按 `STAGE_DECOMPOSITION.md` S10.1：预先选主要指标、配对、比较窗口；**两个模型相同条件**。

---

## 5. 预算与授权纪律

- **本窗口 `model_calls=0`**，不重试付费调用
- `BLOCKED_MODEL_SELECTION_AND_BUDGET` 是**缺授权**，不是开发缺陷
- 启动 M1 前需明确：目标模型精确 ID、运行配置、temperature、预算上限
- 运行长评测用 `background=true + notify_on_complete=true`

---

## 6. 验证边界

- 本文是**接口就绪度核查**，非执行报告。
- **未调用任何真实模型**，未产生任何模型分数。
- 组件路径与行数为实测，非引用。
- 前置门状态来自实际 JSON 字段。
