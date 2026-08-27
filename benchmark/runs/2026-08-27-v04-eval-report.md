# v0.4（updated）评测报告：DeepSeek vs Codex — Visible-only 协议

日期：2026-08-27 · 6 Case · Track B（冻结证据）· **无 Q 提示、无 rubric 泄漏**（模型只见 user question + evidence bundle + output constraint）

## 1. Judgment Value Score（J1-J7，0-14）

| Case | DeepSeek J/14 | Codex J/14 | 关键判断 |
|------|:---:|:---:|---------|
| 001 competitive | 14 | 14 | 两模型都命中"B 比表面更脆弱"（expert must-notice） |
| 002 regulatory | 14 | 14 | 都区分"临床风险下降 vs 执行/准入风险上升"；Codex 给出 PDUFA 日期为最高价值证据 |
| 003 licensing | 14 | 14 | 都选 B>A；最浪费时间=A；Codex 补"防御性占位/竞争情报"动机 |
| 004 investment | 14 | 14 | **Codex 给出 95%CI 计算（n=58/ORR 62% → 49-74%，与 48% 未分离）**——量化非显然洞察；DeepSeek 概念化（概率分布改变） |
| 005 safety | 13 | 14 | **真实差异点：归因排序不同**（见 §3） |
| 006 watchlist | 14 | 14 | 都正确 T1/T2/T3 重估 + Top1=E3 + 二阶 + weak signal |

## 2. 四层 Expert Diagnosis

| 层 | DeepSeek | Codex |
|----|:---:|:---:|
| A Knowledge（A1-A5） | ✅ 全达标 | ✅ 全达标（case-004 额外展示统计素养） |
| B Reasoning（B1-B7） | ✅ 全达标 | ✅ 全达标 |
| C Expression（C1-C6） | ✅ Decision-first + 分层 | ✅ 结构化小节（EJ/Why/Flip/Evidence） |
| D User Utility（D1-D5） | ✅ Decision-ready | ✅ Decision-ready |

## 3. 模型差异诊断（本轮核心发现）

### 差异 1：case-005 因果归因排序（J 分差异，v0.4.1 gold 修订后）

| 模型 | 归因排序 | 与 hidden evaluator 期望 |
|------|---------|------------------------|
| hidden evaluator（v0.4.1 修订） | **必要判断**：target-wide 不能第一、识别 B 为 negative control、shared chemistry 为高优先级 hypothesis、提出区分实验；**软偏好**：platform-first > molecule-first，两者均可 Decision-ready | — |
| Codex | platform/chemistry 强支持 → molecule → target | ✅ 满足 hard requirements + 命中软偏好 |
| DeepSeek | molecule → platform → target | ✅ 满足 hard requirements（识别 B 反证、shared chemistry 高优先级、提出区分证据）；排序为 acceptable alternative（软偏好之外） |

**诊断（v0.4.1）**：DeepSeek molecule-first 不再判为"部分偏离/推理错误"——它满足全部 hard requirements，属于 acceptable ordering。差异保留为**软偏好观察**（Codex 更重视组件共享证据，DeepSeek 更保守归因分子特异性），是否成为 capability gap 需更多 case 验证。**这正是避免重复玛仕度肽错误的关键修正**：evaluator 定义过强会把合理回答判错。

### 差异 2：case-004 统计量化

Codex 主动做 95%CI 计算（62% 的 CI 与 48% 未分离）——这是 B7 Decision Leverage / J2 Non-obvious Insight 的加分行为；DeepSeek 停留在"跨试验不可比"概念层。两者都正确，但 Codex 提供了可直接进投委会的量化论据。

## 4. Failure Taxonomy 状态（v0.4 updated，12 cluster）

| Cluster | 状态 |
|---------|------|
| STALE_KNOWLEDGE | ✅ 已激活（玛仕度肽，Track A） |
| 其余 11 个 | 待激活——v0.4 visible-only 协议下双模型 6 case 仍无重大 failure（Track B 证据充分时前沿模型稳健） |

**观察**：visible-only 协议（无 Q 提示）下，两个模型仍都能自主完成 evidence extraction → structural reasoning → judgment → prioritization → action。说明 Track B 即使不泄露推理骨架，对前沿模型区分度仍有限；**Counterfactual Twins 是下一轮真正的区分战场**（测 Decision Sensitivity / Invariance Discipline，而非静态回答质量）。

## 5. Counterfactual Twins 计划（下一轮）

6 case × 2 twins（C0X-B/C0X-C）已落地（counterfactual-twins.yaml）。下一轮跑法：
- 主 case 回答 + twin 回答对比，算 Decision Sensitivity = correct_direction_updates / expected_updates
- 预期抓：COUNTERFACTUAL_RIGIDITY（条件变了结论不变）/ OVER-SENSITIVITY（小变量大翻转）
- 例如 case-003 twin C03-B（A 的 Phase III 终止 → A 排名应上升）：若模型不改变排序 → COUNTERFACTUAL_RIGIDITY

## 6. 诚实局限

- 每模型每 case 单次采样；J 分由单一 human judge
- Codex exact model ID 未暴露（GPT-5-family）
- twins 尚未跑（下一轮）；Decision Sensitivity 数值待 twins 数据
- 回答字数受 output constraint 限制（400-500 字），信息密度高但深度受限

## 7. 产物

- 回答：runs/2026-08-27-v04-deepseek-case-*.md / v04-codex-case-*.md
- Case 结构：cases/case-*/（case.md visible + hidden-evaluator.yaml + counterfactual-twins.yaml）
- 脚本：scripts/eval_cases_v04.py / gen_cases_v04.py / extract_codex_v04.py
