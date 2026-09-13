# 本次精简分支验证

执行日期：2026-09-13。实际运行环境：Python 3.12.14。未调用付费模型，未执行临床评审或 A/B 填写。

## 最终执行结果

命令：`python scripts/verify_core.py --out runs/reorg-20260913-fixed`。

| 检查 | 实际结果 | 解释 |
|---|---|---|
| static | PASS，1,961 条检查通过 | 结构、版本与引擎合同 |
| autoreview | PASS，2,033 条通过、2 条 NOT_RUN | 规则审查；医学真值与模型辅助审查未执行 |
| track-static | PASS，1 条通过 | 独立因子轨道合同 |
| track-validation | PASS，14 条通过 | 多轮状态、模糊/干扰与边界验收 |
| difficulty-review | NEEDS_REVIEW，3 条 NOT_RUN | 尚无难度语义认可，不转为临床通过 |
| validation | PASS，149 条通过 | 其中 115 条测试结果，其余包括 14 题作者脚本与 14 题空操作回放、事件覆盖及空白评分保持未知 |

[执行摘要](validation/verified/summary.json)、[115 项测试及回放逐条记录](validation/verified/validation/report.json)、[执行日志](validation/verified/validation.log)、[输入文件摘要](validation/verified/input-fingerprints.json)、[多轮轨道记录](validation/verified/track-validation/report.json)、[难度待审记录](validation/verified/difficulty-review/report.json)。

测试来自本次保留的核心目录，不引用原完整仓库的历史测试总数。日志中个别主动注入的错误输出属于验证检测器能否拒绝坏输入的测试；最终状态以逐条测试结果为准。

## 首次失败与修复

首次运行 `runs/reorg-20260913` 有 1 条 ERROR：`test_workflow_aggregate_rejects_missing_or_failed_required_jobs` 找不到 `.github/workflows/medical-dialogue-benchmark-ci.yml`。该测试验证必要 CI 任务失败、跳过或取消时不能整体放行。

修复方式：从同一固定基线原样补回这个主题相关的工作流及来源记录；没有删除、跳过或放宽测试。复测 115 项测试全部通过。原有 PR 完整质量检查工作流继续保留；新分支另外使用 push 触发的离线核心检查。

[首次摘要](validation/first-attempt/summary.json)、[首次逐条记录](validation/first-attempt/validation/report.json)、[首次执行日志](validation/first-attempt/validation.log)均保留。

## 来源与内容核对

- 88 个来源文件与复制清单 SHA-256 一致，源提交中的 blob SHA 全部可解析；25 个核心源代码文件未改动。
- 来源索引覆盖 1,546 个唯一路径、1,674 个路径内容版本，69 个路径存在多版本差异；逐个核对源提交与 blob。
- AP07 候选包的 20 个清单成员摘要全部一致，清单本身随原始候选包复制，共 21 个文件；这些校验不代表临床批准。
- 本次新写的入口、审查和任务文档的本地链接及固定提交路径已核对。继承文档保留原版本上下文，可能含原项目的相对路径和旧操作命令，应通过来源清单查看原始上下文。

底层检查报告中的 `commit` 是执行时 checkout 的父提交 `e494fa34e6271061c4de8c87864adf1e66fcfc9e`，不能当作精简内容已经提交的证明；本次运行发生在新分支内容待提交时，实际输入由文件摘要绑定，最终发布使用同一批核心文件。源 CI 文件另由复制清单绑定。

## 未验证范围

本地未构建 Docker，未重跑被留在历史来源中的旧模块，未进行全项目安全认证、独立医学审核、真实模型有效性试测或排行榜评估。GitHub Actions 的实际远端状态以发布后的运行记录为准，不能用本地结果代替远端成功。

`clinical_approval=false`、`clinical_score=null`；下一步按 [Hermes 任务清单](HERMES_MIGRATION.md) 和 [AP07 任务说明](AP07_NEXT_TASK.md)推进。
