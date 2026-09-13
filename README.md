# GroundSignal：患者多轮咨询评测

本分支聚焦一个问题：面对模糊、信息杂糅和高风险决策压力，模型能否帮助患者做出安全、可执行的下一步决定？

当前是可运行的开发框架。患者交互、调用记录、逐轮评审和回放已接入；临床 Oracle 和题目暴露危险错误的有效性仍需独立审核与真实模型试测。最新提案将首个完整参考家族改为急性脑卒中相关患者咨询，AP07 保留为方法参考；脑卒中实现尚待执行。

## 从这里开始

- **让 Hermes 开始出题**：[出题专用清单](docs/taskbooks/question-authoring-hermes-v0.1.md)。按决策节点与交接 → 三层错误假设 → 8 类患者阶段 → 基线场景 → 实验分组 → 压力实例推进，交付五项设计产物。
- **Hermes 当前执行入口**：[完整任务清单 H00–H46](docs/taskbooks/clinical-benchmark-hermes-tasks-v0.1.md)。覆盖脑卒中试点、临床 Oracle、受控实验、压力梯度和测量验证；按依赖先做首轮设计与审核材料。
- **最新设计依据**：[完整临床 Benchmark 提案](docs/proposals/clinical-benchmark-design-v0.1.md)。先审核节点与医学适用条件，再由 A/B 独立填写；原 [AP07 任务说明](docs/AP07_NEXT_TASK.md)作为方法参考。
- **历史模块复用**：[迁移来源与任务卡](docs/HERMES_MIGRATION.md)。与新任务清单配合使用，不再默认要求 AP07 先完成。
- **运行核心**：[快速开始](docs/QUICKSTART.md)；[架构与边界](docs/ARCHITECTURE.md)。
- **了解整理结果**：[项目审查](docs/AUDIT_REPORT.md)、[未关闭问题](docs/KNOWN_ISSUES.md)、[本次验证](docs/VALIDATION.md)。
- **找原来的内容**：[全部分支、PR 与文件来源目录](docs/migration/README.md)。每个来源固定到提交，包含不同分支上的内容版本。

## 目录

| 路径 | 内容 | 当前状态 |
|---|---|---|
| `scripts/patient_eval/` | 固定患者事实、意图匹配、事件、导入与逐轮评审 | 已抽取所需依赖；规则驱动，存在语义覆盖限制 |
| `scripts/medical_dialogue_bench/` | 独立会话、模型适配、日志、回放、评审入口 | 可离线运行；`oracle.py` 是作者执行脚本 |
| `scripts/benchmark_checks/` | 题卡结构、因子变体、动态边界、难度审核 | 工程检查；临床结论单独审核 |
| `benchmark/medical-dialogue-v1/` | 14 张开发题卡、7 个家族 | 公开合成题，未临床批准 |
| `benchmark/multiturn-factors-v1/` | AP07 的 4 个模糊/干扰验收变体 | 单独轨道；尚未接入完整模型批跑 |
| `medical/patient-eval/app-pilot-v1/` | 12 张题卡的人工采集入口 | 兼容已有采集流程，不等于上述 14 题版本 |
| `research/ap07-oracle-draft-v1/` | 最新节点、回答样本、空白 A/B 表与作者材料 | 原样归档的候选草稿；现有 ZIP 不可直接发起正式盲评 |
| `docs/proposals/`、`docs/taskbooks/` | 完整提案、47 项 Hermes 任务和出题专用合同 | 已补 12 节点/8 阶段候选地图与五项出题交付要求；实际题卡、审核和实测仍待执行 |
| `docs/migration/` | 固定版本来源、复制清单、完整路径版本索引 | 供 Hermes 按模块迁移 |

## 最小运行

在仓库根目录使用 Python 3.12；核心离线流程仅用标准库。

```bash
python -m scripts.medical_dialogue_bench validate
python scripts/verify_core.py
```

第二条会运行保留的测试、作者脚本与空操作回放、题目结构和因子轨道检查，不调用付费模型。完整日志写到新的 `runs/core-check-*` 目录。

## 结果解释

工程运行通过、临床判据获审、真实模型表现、题目区分度分别验收。空白表保持 `unassessed`，未知分数保持 `null`；A/B 一致率也不能直接称为评分准确率。

本分支是从旧项目历史中抽取的独立工作分支。整理前全部来源见迁移目录；旧分支与原 PR 仍可继续访问。继承文件中的旧命令、相对链接和历史测试数字属于原版本上下文，当前操作以本 README 和 `docs/QUICKSTART.md` 为准。
