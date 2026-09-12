# 每次改题后，自动检查哪里出了问题

这套检查用于 GroundSignal 的 14 张公开合成医学对话题卡。提交拉取请求（Pull Request，简称 PR）后，GitHub Actions 自动检查结构、评分规则和执行环境，结果显示在 PR 的 Checks 页与 Actions 的运行摘要中。可下载完整 JSON 报告，每条缺陷含规则编号、题号、文件、JSON 路径和说明。

它是题目质量检查，和给被测 GPT 回答打分是两套不同的评审。绿色状态表示明确列出的检查通过，不代表临床正确、所有缺陷已排除或真实模型已经答过题。

## 你现在怎么用

1. 打开本次 PR，选择 **Checks → Automated Checks → Details**。在运行摘要查看三项结果，展开具体 job 查看失败注释。运行结束后的 Artifacts 提供完整报告与离线对话。
2. 修改题卡、评分规则或代码，提交到同一个 PR；新提交会重新检查，过期运行会取消。报告记录 PR 提交与实际检出提交（PR 检查通常是测试合并提交），避免拿旧结果代表新版本。
3. 某项失败时，先看 `scenario_id`（题号）和 `pointer`（JSON 路径）。例如 `/scenarios/0/criteria/0/requires` 是第 1 道题、第 1 个评分点的披露前提。索引从 0 开始。
4. 修复后再提交。不要为了变绿删除测试；若规范确实需要改，应同时解释原因、更新对应样本并审阅分数可比性。

本分支依赖题卡包 PR #27。合并顺序沿现有依赖链进行，不直接合并到错误的基线。工作流尚未进入默认分支时，手动运行按钮可能不可用；PR 自动检查仍可运行。

## 页面中每个名字是什么意思

| 名称 | 谁执行、检查什么 | 如何解释通过 |
|---|---|---|
| Static checks（静态检查） | Python 检查字段、编号、引用、轮次、配对和清单摘要，再加载现有引擎 | 题目符合当前代码明确规定的结构；来源链接有记录，不等于原文支持已核验 |
| Autoreview (rules)（规则自动审阅） | 重跑结构检查，并检查事件前提、更正实际更新、评分要求与失败示例 | 规则之间未出现已编码的这些矛盾；没有假装调用评审模型 |
| Validation（执行验证） | 缺陷样本、已有边界测试、参考对话和空操作回放、Docker 构建与容器执行 | 工程能运行，已覆盖的异常能被识别；临床评分仍未知 |
| Model-assisted review（模型辅助评审） | 手动启用后，每个基础题调用一次指定模型，核对逐字引用 | 仅辅助意见；`insufficient` 保留为证据不足，模型也可能漏报或误报 |
| Automated Checks（汇总） | 汇总前三项的真实 job 结论 | 三项均 success 才通过；失败、跳过、取消都不能替代 success |

本版本没有相似题检测、自动分配审稿人或机器人评论功能。已有 PR Checks 和运行摘要承担展示，不伪称 “Reviewers are already assigned”。代码不申请仓库写权限，不使用 `pull_request_target` 运行提交方代码。

## 本地先练习，不花模型费用

安装 Python 3.12，在仓库根目录执行。输出目录必须是新目录，避免混入旧报告。

```bash
python -m scripts.benchmark_checks static --out medical/patient-eval/local/quality-static-001
python -m scripts.benchmark_checks autoreview --out medical/patient-eval/local/quality-review-001
python -m scripts.benchmark_checks validation --out medical/patient-eval/local/quality-validation-001
```

本地 `validation` 执行 Python 测试与回放；Docker 是 Actions 中单独的后续步骤。本地通过不能冒充 Docker 已通过。

做一个最小练习：

```bash
python -m scripts.benchmark_checks.demo --out medical/patient-eval/local/quality-demo-001
```

它复制题库，把 AP01 的一个评分前提改为不存在的 `F999`。打开输出目录的 `summary.md`，会看到两个版本的明确失败位置；原题库不变。演示程序退出 0 表示成功抓到了预设错误，里面的检查报告仍然是 FAIL。

## 规范写在哪，怎样继续扩充

- `scripts/benchmark_checks/__main__.py`：`inspect_suite` 是结构和规则检查，`validation` 是运行检查，`MODEL_RULES` 是模型辅助审阅的五个问题，`write_report` 统一生成报告。
- `tests/benchmark_checks/mutations.json`：14 个预先标注的缺陷。每个只做一次指定修改，并声明应该被哪条规则抓到。
- `tests/benchmark_checks/test_checks.py`：合格题库应通过；每个缺陷必须触发对应规则；检查模型伪造引用、请求失败、预算不足和证据不足处理。子测试失败也必须进入报告。
- `.github/workflows/medical-dialogue-benchmark-ci.yml`：决定什么时候运行、如何并行，以及哪些结果组成汇总。

例如要加入“患者体温必须注明单位”的规则，先明确适用哪些结构化字段，再写合格样本、缺单位样本以及无需单位的非数值回答；最后写检查函数。不要靠全局搜索一个“℃”就判整道题通过。每次修复实际漏检，都把最小复现保留下来。

当前缺陷集验证的是已编码机械规则，不是临床正确性标注集，也不是模型评审器精确率／召回率的校准集。后续应另外准备独立标注的合格与不合格题卡，评估模型评审的误报和漏报。

新项目可复用工作流、报告格式、缺陷样本方法和汇总逻辑；`inspect_suite` 的字段以及动态回放适配器必须按新题型重写。这里的静态配对规则只适用于基础版＋无关后缀版，不能直接用于任意多因素实验。

## 模型辅助评审怎么开启

工作流进入默认分支后，在仓库 Actions → **Benchmark Quality → Run workflow**，启用 `model_review`，填写账户实际可用的模型 ID。仓库需要配置 `OPENAI_API_KEY` Secret；不要将密钥填在模型名称、题卡或提交记录里。当前版本默认关闭，PR 不发起模型请求。

本地等价命令（密钥由环境提供）：

```bash
python -m scripts.benchmark_checks model-review --model YOUR_AVAILABLE_MODEL_ID --max-review-calls 10 --out medical/patient-eval/local/quality-model-001
```

当前 7 个家族最多调用 7 次，每次最多输出 4096 token，默认调用预算上限 10；题库增加超过预算会在发请求前停止。没有自动重试。逐次日志记录开始、结果、模型返回名称与用量；中断后先检查已发生的请求，再决定是否另开输出目录运行。

辅助模型只读题卡与来源摘要，无浏览或执行工具，所以无法代替来源原文核验、Docker 实测或临床专家。现有 7 道基础题的审阅也不能代表它已独立审阅全部干扰版本；干扰版本的一致性由配对检查覆盖。

## 怎样真正限制合并

工作流提供失败状态；只有仓库 Rulesets／分支保护将 **Automated Checks** 设置为 required status check（必需状态检查），才能在规则覆盖范围内阻止未通过的合并。建议同时要求分支与目标分支同步，并审阅检查代码与工作流自身的修改，避免题目作者同时放宽标准而不被发现。

该设置属于仓库管理配置，本次代码提交不表示已经启用。已有连接不提供管理设置写接口，需仓库管理员在 Settings → Rules → Rulesets 配置；这不影响先运行和查看检查。自动检查也不能阻止管理员按仓库配置使用绕过权限。

## 参考与适配边界

借鉴 Terminal-Bench Science 的分层检查方式，未照搬其要求研究级终端计算任务的整套 rubric。医学多轮问答允许多种合理回答，不能把确定性终端任务的唯一数值答案要求直接套用过来。

- [上游题目评审工作流](https://github.com/harbor-framework/terminal-bench-science/blob/main/.github/workflows/review.yml)
- [上游验证示例：Docker、Oracle、Nop](https://github.com/harbor-framework/terminal-bench-science/pull/1263#issuecomment-5307299708)
- [GitHub 必需状态检查与规则配置](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub 手动运行工作流](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

当前版本规范号：`benchmark-checks/v1`。报告绑定规范号、检查代码摘要、题库摘要、清单摘要和提交号；规则变化需要更新规范号并说明兼容性。容器基础镜像仍使用现有 Python 标签，尚非固定镜像摘要，因此不宣称未来任意时间环境字节级可复现。
