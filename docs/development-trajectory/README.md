# Development Trajectory — GroundSignal Pharma（Hermes 会话轨迹）

> 本目录保存 Hermes Agent 从 2026-08-27 12:13 开始的完整开发过程轨迹（会话 `20260827_121356_467dc9`）。
> 从 BioBench 定位讨论开始，覆盖 GroundSignal Pharma 仓库从建库到 counterfactual twins 评测的全流程。

## 数据文件

- `session_20260827_121356_467dc9.jsonl`：结构化轨迹（20 个用户轮 / 304 个决策步 / 366 个工具结果）

## Schema（每行 = 一个 user turn）

```json
{
  "user": "用户消息（截断 800）",
  "steps": [
    {"type": "decision", "text": "assistant 决策文本（截断 500）",
     "tool_calls": [{"name": "terminal", "args_preview": "..."}]}
  ],
  "tool_results": [{"tool_call_id": "xxx", "result": "工具输出（截断 350）"}]
}
```

来源：`~/.hermes/state.db` messages 表（SQLite）。提取脚本：`benchmark/scripts/extract_hermes_session.py`。

## 开发过程里程碑（从轨迹归纳）

| # | 阶段 | 关键动作 | 结果 |
|---|------|---------|------|
| 1 | BioBench 定位评估 | 审阅"数据产品"四层叙事建议 | 给出 reviewer 式意见（评测数据 vs 训练数据、371→65→4 双刃剑） |
| 2 | Google Scholar 验证 | PowerShell 走 Windows 系统代理验证 profile | 确认 URL 有效 + 邮箱未验证建议 |
| 3 | GroundSignal 医药版建库 | clone/结构侦察 → pharma/ v2 库 54 节点 + demo 33 节点（ClinicalTrials.gov 真实数据） | 0 断裂 / 0 UNKNOWN |
| 4 | 可信度修复（外部评审 P0） | scoring protocol 冻结、cross-entity 矢量判断、claim-level audit、用户访谈协议 | 4 项 P0 全部落地 |
| 5 | **玛仕度肽 Gold Audit（关键转折）** | 外部审计发现 2025-06-27 NMPA 获批 → V2 结论反转（Codex 正确、DeepSeek STALE、GroundSignal 自身 stale） | postmortem + 新指标 + 三 Track 设计 |
| 6 | Decision Intelligence 6 Cases v0.2 落地 | U1-U5 评分 + 6 case 目录结构 | 双模型 6/6 Decision-ready |
| 7 | Model Diagnosis v0.4 | 四大评估层 23 维 + failure taxonomy + Optimization Card | STALE_KNOWLEDGE 卡片（唯一激活） |
| 8 | v0.4 updated（visible/hidden 分离） | 无 Q 提示协议 + J-score + Counterfactual Twins | 双模型 J 13-14/14；C05 归因差异 |
| 9 | **v0.4.1 gold 修订** | C05 platform>molecule 改为软偏好（避免 evaluator 偏见） | 防止重复玛仕度肽错误 |
| 10 | Counterfactual Twins 评测 | 24 次独立运行（randomize）→ DS/ID/FC/EC 四指标 | 双模型 11.5/12；COUNTERFACTUAL_RIGIDITY 部分激活 |
| 11 | Trajectory 保存（本轮） | state.db 提取 + 本 README | — |

## 关键决策转折点（result → pivot）

1. **玛仕度肽 gold 反转**：V2 初判"Codex OVERCLAIM"→ 外部审计（经济观察网/36氪/雪球 2025-06-27）→ 反转"Codex 正确、DeepSeek STALE、GroundSignal 自身 stale"→ 新增 Stale Claim Rate / Claim-Evidence Entailment 指标。**教训：先审计 gold 再下模型结论。**
2. **evaluator 偏见修正（v0.4.1）**：C05 把 platform>molecule 从硬 gold 改为"必要判断 + acceptable ordering"——因为 DeepSeek molecule-first 满足全部必要判断，判错会重蹈玛仕度肽覆辙。
3. **Track B ceiling 判断**：静态 6 case 双模型全 Decision-ready → 停止堆静态题 → 转向 Counterfactual Twins（测 Decision Sensitivity 而非静态质量）。
4. **C03-C 共性薄弱点**：双模型都"言语承认 B 应降级但排序未变"→ 形成第一个稳定的跨 case pattern（高敏感 + 高稳定 + 降级保守）→ Capability Gap Hypothesis（COUNTERFACTUAL_RIGIDITY 降级方向部分激活）。

## 工具使用特征（开发过程画像）

- 高频工具：terminal（git/push/python 脚本）、write_file、patch、read_file、browser/powershell（验证外部事实）
- 网络模式：GitHub 直连被阻断时用 Windows 侧 git + Clash 代理（127.0.0.1:7897）经 `\\wsl.localhost\Ubuntu\...` push，token 经 /tmp 临时文件传递
- 事实验证纪律：外部 AI 主张（玛仕度肽获批）先用 360 搜索多源验证再采信

## 关联产物

- 仓库本体：`/home/zehaoli0324/projects/groundsignal-pharma`（GitHub: zehaoli0324-cloud/groundsignal-pharma）
- 评测产物：`benchmark/runs/`、`benchmark/trajectories/`、`benchmark/diagnostics/`
- 版本存档：git tags `benchmark-v0.1` / `v0.2-6cases-eval`
