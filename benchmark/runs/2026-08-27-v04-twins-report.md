# Counterfactual Twins 评测报告：DeepSeek vs Codex

日期：2026-08-27 · 12 个 Twin 变体（6 case × 2）× 2 模型 = 24 次独立运行（randomize 顺序，无反事实泄漏）
协议：Base + Twin 分开独立提问，模型不知道互为 twin；评分阶段才配对

## 1. Pair 表（应变化方向 × 双模型）

| Pair | 关键变量变化 | 应变化 | DeepSeek | Codex |
|------|-------------|--------|:---:|:---:|
| C01-B | X 低价 30% + payer 接近 + 供应充足 | B threat ↑ | ↑ ✅ | ↑ ✅ |
| C01-C | X 疗效好但供应受限 + coverage 差 | commercial threat ↓ | ↓ ✅（B 缓冲、C 管线价值受压） | ↓ ✅（同） |
| C02-B | review 延期 6 个月 | time-to-market ↓ | ↓ ✅（时间线后移+情景预算） | ↓ ✅（同+竞争窗口扩大） |
| C02-C | 获批但 label 明显窄 | 监管成功 vs 商业上行分离 | ✅（审批风险→标签风险） | ✅（重校产能防过剩） |
| C03-B | A 内部 Phase III futility 终止 | A priority ↑ | ↑ ✅（渴求度上升） | ↑ ✅（明确"排名应明显上升"） |
| C03-C | B in-license 同靶点 ADC | B priority ↓ | ⚠️ 部分（Top2 未变，未降 B） | ⚠️ 部分（言语"优先级应下调"但排序 B>A 未变） |
| C04-B | ORR 58% 但 DOR 显著更长成熟 | DOR 差异化 ↑ | ✅（从 ORR 追赶者升级为 DOR 差异化者） | ✅（DOR 更接近患者获益与换药意愿） |
| C04-C | biomarker subgroup 大队列复现 | positioning ↑（非 best-in-class） | ✅（+10-20% 而非翻倍） | ✅（可小幅提高差异化 conviction） |
| C05-B | B 也出现一致肝毒性 | target hypothesis ↑ | ✅（molecule→target 明确翻转） | ✅（多 modality 一致性=关键证据，但保留"非已证实 class effect"） |
| C05-C | A warning 来自 off-target metabolite | platform ↓ / molecule ↑ | ✅（molecule 第一 + A 证据解析） | ✅（molecule > platform > target） |
| C06-B | E3 终止原因非 efficacy | dev path ↓ 但非 efficacy failure | ✅（战略不确定性资产，非疗效失败） | ✅（"必须撤回疗效失败的推断"+ Top1 调整为 Q 获批） |
| C06-C | E5 区域很小无开发权 | T3 update 幅度 ↓ | ✅（国际化叙事失效→降级） | ✅（小幅下调，更新幅度小于原版） |

## 2. 四指标

### DS — Decision Sensitivity（该变的变了多少）
- **DeepSeek：11.5/12**（C03-C 部分：言语承认 B 优先级应下调，排序未变）
- **Codex：11.5/12**（C03-C 同）
- 两个模型都能在关键变量变化时正确改变判断方向——Decision Sensitivity 高

### ID — Invariance Discipline（不该变的稳不稳）
- C01-B：B threat ↑ 的同时保留"A 有先发/支付壁垒缓冲"✅ 双模型
- C05-B：target hypothesis ↑ 的同时都声明"不应宣布已证实 class effect"✅ 双模型
- C02-B：延期 → 下调时间线，但都声明"延期 ≠ 疗效论点被推翻"✅ 双模型
- **ID 满分：没有出现"改一个变量推翻整套判断"的 over-sensitivity**

### FC — Flip Calibration（何时真翻转 vs 只调 confidence）
- C05-B 是"该翻转时敢翻"：DeepSeek（molecule→target）、Codex（转向 target-level）都正确翻转 ✅
- C03-C 是"证据足够但没翻"：两个模型都停留在"言语下调 + 排序不变"——**FC 部分失分**（过度保守，可能套用 BASE 排序模板）
- 总体：翻转纪律好（无过度翻转），但 C03-C 显示**降级方向的 flip 偏保守**

### EC — Explanation Consistency（变化是否有因果解释）
- DeepSeek C05-B："因为 B（不同 modality）也出现一致肝毒性 → 打破 molecule/modality 特异性 → target 上调"✅
- Codex C03-B："因为 A 内部项目 futility 终止 → 内部冲突下降 → 排名应明显上升"✅
- 大多数变化都有明确的"新增证据 → 中间变量 → 结论"因果链；C03-C 的"言语下调但排序未变"正是 EC 最弱处

## 3. 模型画像（twins 行为）

| 维度 | DeepSeek | Codex |
|------|----------|-------|
| Decision Sensitivity | 11.5/12 | 11.5/12 |
| Invariance Discipline | ✅ 满分 | ✅ 满分 |
| Flip Calibration | 翻转敢做（C05-B），降级偏保守（C03-C） | 同 |
| Explanation Consistency | 强（显式因果链） | 强 |
| 显著差异 | 无——两模型 twins 行为高度一致 | 无 |

**Observed pattern（比 v0.4 静态更稳的结论）**：
> 两个前沿模型在 counterfactual 环境下都表现出一致的**高 Decision Sensitivity + 高 Invariance Discipline**；唯一共性薄弱点是**降级方向 flip 保守**（C03-C：证据足以降 B 优先级但排序未变）。

**Capability Gap Hypothesis**（不是单例结论）：
> 模型可能在"关键变量削弱某选项吸引力"时，因锚定 BASE 排序而更新不足——COUNTERFACTUAL_RIGIDITY（降级方向）部分激活。需更多"削弱型 twin"验证（当前 12 个 twin 中仅 C03-C 是纯削弱型）。

## 4. Failure Taxonomy 激活状态

| Cluster | 状态 |
|---------|------|
| STALE_KNOWLEDGE | ✅ 已激活（玛仕度肽 Track A） |
| COUNTERFACTUAL_RIGIDITY（降级方向） | 🟡 部分激活（C03-C 双模型） |
| 其余 10 个 | 未激活 |

## 5. 优化方向

针对 COUNTERFACTUAL_RIGIDITY（降级 flip 保守）：
- data：构造更多"削弱型 twin"（选项吸引力下降）——当前 12 twin 中 11 个是"增强型"
- preference：奖励"优先级下调"的显式重排（不仅言语承认）
- prompt：输出约束要求"若排序变化请给出新旧排序对比"
- regression：C03-C 类 twin 固定为回归集

## 6. 诚实局限

- 每 twin 单次采样；评分由单一 human judge
- randomize 顺序但两模型 prompt 完全相同（Codex 有 agent 系统提示差异）
- C03-C 的"排序未变"是否真 failure 需专家确认（B 仍可能是合理 Top2——因为 C 太弱，降 B 后 A/C 顶不上）
- twins 回答未做 Base-vs-Twin 差异的定量 diff（人工判断方向）

## 7. 产物

- 回答：runs/twins/2026-08-27-v04-deepseek-*/codex-*.md（36 个文件）
- 脚本：scripts/eval_twins_v04.py / extract_codex_twins.py / extract_twins_summary.py
