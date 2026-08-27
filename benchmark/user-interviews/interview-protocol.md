# 用户任务访谈协议（P0-4）

> **状态：待真人执行。** 本协议已冻结；访谈 3-5 位药企 BD / 医疗 VC / 行业研究从业者后，把"我认为 BD 需要什么"升级为"4/5 BD 用户把竞争资产优先级列为核心任务"这类可引用证据。

## 目标

验证 Decision Benchmark 的用户任务假设（User → Job-to-be-done → Decision Question → Ideal Output → Unacceptable Failure → Metric），并把结果写回 `docs/09-user-validation.md` 与 Benchmark README。

## 对象（3-5 人）

| 角色 | 目标数 | 典型问题 |
|------|--------|---------|
| 药企 BD / 战略 / 竞争情报 | 2 | 找合作方、判断竞争格局、跟踪变化 |
| 医疗 VC / PE | 2 | 赛道拥挤度、投前尽调、价值拐点 |
| 行业研究 / 临床开发 | 1 | 解释行业事件、评估邻近管线 |

## 访谈脚本（15-20 分钟，半结构化）

### 开场（2 分钟）
说明目的：了解你在医药信息上的真实工作流程，不是推销产品。

### 任务挖掘（8 分钟）
1. 上周你花最多时间查的医药信息是什么？为了做什么决策？
2. 查这些信息时，你最常看的来源是哪些？为什么信它们？
3. 你做过最"贵"的一个判断是什么？（花了很多时间/影响大）
4. 如果有一个工具能帮你自动回答一个问题，你希望是什么？
5. 现在信息工作里最让你烦的是什么？（新闻太多/找不到可靠来源/不知道信谁）

### 具体任务验证（5 分钟，逐项确认 Benchmark 假设）
对每个候选任务问：
- 这个任务你实际做过吗？频率？
- 对你来说"好的答案"长什么样？
- 什么输出会让你觉得"这工具没用"？

候选任务清单：
- A. 竞争资产优先级（新资产进来，先看谁）
- B. 找潜在合作/授权对象
- C. 判断赛道拥挤度
- D. 投前尽调（公司声称 vs 公开证据）
- E. 解释行业事件影响（FDA 获批/III 期/BD 交易 → 影响谁）
- F. Watchlist：今天哪 5 条值得看

### 打分（3 分钟）
对每个任务：重要性 1-5 / 频率（每周/每月/几乎不）/ 现有工具满意度 1-5。

### 收尾（2 分钟）
- 愿意再看一轮 demo 吗？（构建候选用户池）
- 可以介绍同行吗？

## 数据采集模板（每场访谈一份）

```yaml
interview_id: INT-001
role: BD / VC / IR / ClinicalDev
date:
duration_min:
user_tasks:
  - job_to_be_done: "找海外合作伙伴"
    decision_question: "我的资产最可能和谁产生 licensing 机会？"
    ideal_output: "候选公司 + 资产重叠 + 机制互补 + 历史交易 + 证据"
    unacceptable_failure: "虚构合作关系；猜测当事实"
    metric: [Precision, Evidence Coverage, Actionability]
    importance_1to5:
    frequency: weekly|monthly|rarely
    satisfaction_1to5:
pain_points: [新闻过多, 来源不可靠, 不知道信谁, 变化跟踪不及时]
quotes: ["<原话引用>"]
```

## 输出

- `benchmark/user-interviews/INT-001.md` 等逐场记录
- 汇总：任务频率表 + 痛点频次 + 优先级排序
- 更新 `docs/09-user-validation.md`（假设 → evidence）
- 新增/调整 Decision Benchmark case（用户任务优先级决定 case 顺序）

## 纪律

- 不引导（不先说"我们认为你需要 X"，先听）
- 引用要忠实记录原话
- 访谈对象知情同意（用途：研究 + 求职作品展示，可匿名）
