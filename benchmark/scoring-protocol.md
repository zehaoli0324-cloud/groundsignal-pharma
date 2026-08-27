# Scoring Protocol（评测协议，冻结版）

> 本协议是 benchmark 评测的可信度地基。所有评分必须遵循本协议，禁止临场发挥或手写最终报告。

## 0. 核心原则

- **Pre-registration**：case 的 gold、Critical Error、判分 anchors 在评测前冻结，评测中不可修改
- **盲评**：评分时隐藏模型名（case_id + response_id），避免品牌偏见
- **结构化输出**：评分产出 JSON，报告由脚本渲染，不手写
- **可复现**：每次评测记录完整实验环境（见 §4）

## 1. 评分尺度（冻结）

- 每维 **0 / 1 / 2 三档整数**（禁止 0.5 等中间值）
  - 2 = 达标（完全满足 + 证据支持）
  - 1 = 部分（部分满足，或缺关键限定）
  - 0 = 不可接受（不满足 / 出现 Critical Error）
- 维 1（Factual）/ 4（Competitive reasoning）/ 7（Uncertainty）任一 0 分 → 整体判负
- Critical Error 出现 → 直接判负（无需逐维）

## 2. Case 结构（每个 case 必须包含）

```yaml
case_id:
user_role:
scenario:
evidence_snapshot:   # 快照 ID（LiveEval 有 T1-T4）
questions:           # L1 事实 / L2 关系 / L3 证据充分性 / L4 产品题
gold:                # 每题 pre-registered 正确答案
critical_errors:     # 出现即判负的行为清单
anchors:             # 每维判分锚点（0/1/2 各给 1 个示例行为）
```

## 3. 评分流程

```text
Case → 模型回答（response_id）→ 盲评（按 rubric 逐维）→ score JSON → 脚本渲染 report
```

score JSON 格式：

```json
{
  "case_id": "case-001",
  "response_id": "deepseek-v1",
  "date": "2026-08-27",
  "version": {"case": "v1.1", "rubric": "v2", "protocol": "v1"},
  "scores": {"1_factual": 2, "2_evidence": 2, "3_temporal": 2, "4_competitive": 1, "...": "..."},
  "critical_errors": [],
  "failure_types": ["RELATION_OVERSIMPLIFY(edge)"],
  "notes": ["Q2 断言 direct competitor 但给出机制限定 → anchor 1"],
  "judge": "human-reviewer"
}
```

## 4. 实验环境记录（每个 run 必填）

| 字段 | 说明 |
|------|------|
| provider | deepseek / openai / anthropic / ... |
| model_exact_id | deepseek-chat / gpt-5.x / ... |
| model_version | 有则填 |
| date | 运行日期 |
| temperature | 采样参数 |
| system_prompt_version | v1 / v2 |
| tool_access | none / codex runtime |
| reasoning_mode | hidden / encrypted |
| snapshot_id | T1/T2/T3/T4 或 v1 全证据 |
| case_version | case 文件版本 |
| rubric_version | rubric 文件版本 |
| judge_version | 评分人/自动 judge 版本 |

## 5. 已知判分歧义的处理

- **口径歧义**（如"2023 销售额第一"单药 vs 系列）：gold 必须预先定义口径；模型指出歧义本身是加分行为（证据 grounding 维）
- **claim scope 歧义**（"证明有效"科学 vs 监管语义）：case 必须拆分为子问题（如 Q5a/Q5b），禁止用模糊 gold 评模糊答案
- **模型给出额外限定**：限定属于加分（uncertainty/scope 维），不属于偏离 gold
