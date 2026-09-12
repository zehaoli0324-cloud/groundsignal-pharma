# GroundSignal Pharma

**GPT自动试评：**[12题多轮医学Benchmark](benchmark/medical-dialogue-v1/README.md)——逐题独立会话、参考解法、评分细则、重放校验器与Docker。公开合成开发版，实际GPT与临床审核结果待补。
**医疗大模型评测工具：记录证据、检索和对话过程，定位错误并验证修复。**

[运行示例](#快速运行) · [进度与交接](docs/handoffs/2026-09-09-candidate-review-handoff.md) · [任务书](docs/taskbooks/patient-evaluation-master-taskbook-v1.2.md)

**新增：**[小荷健康与蚂蚁健康首轮对话评测](medical/patient-eval/app-pilot-v1/README.md)——12张合成题卡、可直接打开的采集页面、逐轮评审和分歧汇总。先采6段实际应用对话；当前尚无应用实测结果。

项目围绕三个问题开发：模型用了什么证据？错误发生在哪一步？修改后是否解决了问题？目前已实现证据处理、受控案例检查和患者多轮评测原型。

我负责问题定义、医学约束、实验设计与迭代验收；代码实现和测试使用智能体辅助开发。

## 已完成的工作

- **独立审核工作台 v0.1（本分支新增）。** 下载[离线页面](medical/patient-eval/console-v0.1.html)，导入原有资料包，逐项审阅事实、证据、隐私、评分规则与机会计划；支持草稿续填和分歧交接。[使用与限制](medical/patient-eval/CLINICAL_CONSOLE_V0.1.md)。无登录或临床签名，不自动准入；只有合成示例，未嵌入患者原文。
- **证据处理。** 根据问题选择医学来源，抽取带出处的主张，用知识图谱记录适用条件、版本和冲突。实现了[来源路由](scripts/s2_intent_router_v04.py)、[语义抽取](scripts/s3_semantic_extractor.py)和[图谱更新](scripts/s4_truth_ledger_v011.py)。
- **受控案例。** 建立 12 个家族、60 个案例，改变关键条件来检查模型行为；另有来源追踪、分区污染检测和历史结果保留。[案例目录](medical/case-families/) · [阶段评测](medical/stage-evals/)
- **患者对话评测。** 6 个家族、12 个合成变体，覆盖含糊表达、事实纠正、催促和误解修复。交互器按问询披露信息；质量、安全和评分机会分别记录，配套双人评分及同一模型的状态增强对照。[代码](scripts/patient_eval/) · [评分操作](medical/patient-eval/REVIEW_V0.3.md)
- **真实数据审阅。** 核验 1,557 段 ReMeDi 对话，为其中 50 段生成带原文定位的事实与披露草稿、独立审阅页面和分歧清单；尚未形成医学标准答案。[接入与审阅](medical/patient-eval/data-sources/v0.2/README.md)

## 已有结果

以下是组件和合成场景验证，尚无真实医疗模型的性能结果。

| 对象 | 观察结果 | 记录 |
|---|---|---|
| 来源路由 v0.3 | 24 条受控留出查询中，首选来源命中 22 条；保留两条失败 | [报告](medical/stage-evals/S2/V0.3_REPORT.md) |
| 时间知识图谱 v0.1.1 | 修复“晚到旧事实覆盖当前争议”：原失败集从 18/20 到 20/20，随后新建的 20 条轨迹全部通过 | [首次失败](medical/stage-evals/S4/S4_V0.1_FRESH_FAIL_REPORT.md) · [修复与新集](medical/stage-evals/S4/S4_V0.1.1_FRESH_PASS_REPORT.md) |
| 患者评测 v0.3 | 161 项软件测试通过；48 条已暴露问询表达的披露匹配从 23/48 到 48/48；24 条离线会话的 152 个判据仍待人工评分 | [验证与限制](medical/patient-eval/VALIDATION_V0.3.md) |

例如，在受控演示中，用户先说“症状开始时间是昨天”，后说“更正，症状开始时间是前天”。系统记录更正消息、抽取后的事实、实际传给模型的上下文和后续回答。自建流程可据此排查抽取、状态更新或消息传递；对只能看到回答的平台，只记录行为缺陷与待验证原因。

## 快速运行

需要 Python 3.11 或以上版本。以下演示使用标准库和离线脚本，无需密钥：

```bash
git clone https://github.com/zehaoli0324-cloud/groundsignal-pharma.git
cd groundsignal-pharma

python -m scripts.patient_eval.pilot_cli validate
python -m scripts.patient_eval.pilot_cli demo --out medical/patient-eval/local/readme-demo
```

演示生成 24 条脚本会话。输出目录中的 `sessions.json` 保存原文，`evaluation/results.json` 保存评测记录，`evaluation/report.html` 可在浏览器打开。再次运行须换一个新输出目录。

接入真实模型或人工采集小荷健康回答，见[患者评测使用说明](medical/patient-eval/README.md)。

## 当前范围

截至 2026-09-09，已补齐披露校准、独立评分和真实对话审阅工具。真实平台采集、独立口语校准、临床审核及真实模型改进实验均未完成；开发样本结果不能代表真实患者效果。下一步见[交接文档](docs/handoffs/2026-09-09-candidate-review-handoff.md)。

现有案例属于开发资产；案例准入阶段的历史冻结检查已修复，正式研究准入仍未通过。本项目不用于向患者提供诊疗建议。

## 文档

- [十阶段任务拆分](medical/patient-eval/STAGE_DECOMPOSITION.md)：每阶段的输入、输出和验收。
- [文献设计补充](docs/taskbooks/patient-evaluation-literature-addendum-v1.3.md)：论文方法对应的算法、工程任务及实施进度。
- [知识来源与核验](medical/knowledge-base/SEARCH_AND_VERIFICATION_PROTOCOL.md) · [图谱构建](medical/knowledge-graph/HOW_IT_IS_BUILT.md)。
- [采集与评分材料](medical/patient-eval/pilot/v0.2/README.md)：披露规则、采集模板与人工评分细则。
- [算法与工程学习手册（HTML）](docs/learning/groundsignal-learning-guide.html)：术语、代码用途、基础练习与模型训练的关系；下载后用浏览器打开。
- [进度与交接](docs/handoffs/2026-09-09-candidate-review-handoff.md)：本轮交付、证据边界和下一步。
