# 核心快速开始

所有命令从仓库根目录运行。建议 Python 3.12；此处离线命令使用标准库，不需要安装第三方包。

## 1. 完整离线验收

```bash
python scripts/verify_core.py
```

保留所有子步骤日志及 JSON。`difficulty-review` 的 `NEEDS_REVIEW` 是待审核，不会改写成临床通过。此命令无真实模型请求；`validation` 内含当前保留测试、14 题作者脚本和 14 题空操作回放。

## 2. 看一次咨询记录与回放

首次使用以下路径；重复执行时换一个新目录，避免混合不同运行。

```bash
python -m scripts.medical_dialogue_bench validate
python -m scripts.medical_dialogue_bench run --backend oracle --out runs/first-oracle
python -m scripts.medical_dialogue_bench verify --run runs/first-oracle --out runs/first-oracle-integrity.json
python -m scripts.medical_dialogue_bench review --run runs/first-oracle --reviewer A --out runs/first-oracle-review-A.json
```

这证明链路能运行、记录、回放，并能生成待填评审表；不能证明作者回答是医学金答案。这里生成的通用运行评审表也不等同于 AP07 临床校准专用包。

## 3. 查看模糊与混合信息轨道

```bash
python -m scripts.benchmark_checks track-static --out runs/first-track-static
python -m scripts.benchmark_checks track-validation --out runs/first-track-validation
python -m scripts.benchmark_checks difficulty-review --out runs/first-difficulty-review
```

这是独立的 AP07 因子验收轨道；不能据此宣称 14 题的真实模型批跑都已支持该轨道。

## 4. 真实模型联合试测前

出题准备先按 [出题专用清单](taskbooks/question-authoring-hermes-v0.1.md) 交付错误地图、阶段覆盖、场景卡、分组和压力记录，并在 H24 分别核对全范围地图与首批实验链；现有题量及工程通过不能替代这项验收。

新主线按 [完整任务清单](taskbooks/clinical-benchmark-hermes-tasks-v0.1.md) 完成脑卒中临床与评审门槛，再按 H26 冻结题库、分支、判据、停止条件、模型配置与调用预算。现有模型调用入口仍面向当前 14 题开发底座，可用 `python -m scripts.medical_dialogue_bench run --help` 检查参数；脑卒中资产与接入尚待建设，不能把现有命令当成已完成的新试点。

第一次真实试测分别报告模拟器有效性、常规咨询表现、高风险错误、过度分诊、评分争议与未评数量。每题独立会话，同一比较条件使用一致的模型设置和预算。无需先做排行榜或单一总分。

AP07 原草稿 ZIP 已公开包含作者开发样本，且同包存在前后时序材料。应按新任务书重建分阶段包、记录评审者曝光情况后再组织独立填写。
