# GroundSignal：GPT多轮医学对话评测 v1

一次启动，逐题建立独立会话；每题最多6次自然回答，按GPT实际追问披露事实，结束后切换下一题。可另加1次解释探查。当前12张公开合成题卡来自6个基础情境及各自的无关文本干扰版，不是12个独立真实病例，也不是未暴露测试集。

## 交付内容

| 文件/模块 | 用途 |
|---|---|
| QUESTION_CARDS.md / suite.json | 首问、事实、纠正事件、逐题判据及来源 |
| patient-patterns.json | 患者追问与固定事实的对应规则 |
| oracle-policy.json / scripts/medical_dialogue_bench/oracle.py | 作者参考对话策略；包括noop、naive、stale失败对照 |
| RUBRIC.md | 评分依据、证据规则、未知状态、严重性与统计分母 |
| scripts/medical_dialogue_bench/runtime.py | 顺序调度、逐题上下文重置、预算和请求日志 |
| scripts/medical_dialogue_bench/verifier.py | 重放披露、拒绝缺题/篡改/越界，绑定逐轮评分 |
| scripts/medical_dialogue_bench/client.py | OpenAI Responses接口，保存实际返回型号和用量 |
| scripts/medical_dialogue_bench/judge.py | 可选模型辅助评分，逐行只提供截至当轮的信息 |
| Dockerfile / benchmark.toml | 容器入口及任务配置说明 |

六类能力情境：代问对象与否定、复方药成分未知、跨机构报告、相互不一致的检测证据、时间更正与因果判断、摘要支持范围与个人疗效。实际覆盖见题卡；不宣称覆盖全部医学能力。

## 先跑离线参考解法

仓库根目录，Python 3.10或以上；无额外Python依赖：

```bash
python -m scripts.medical_dialogue_bench validate
python -m scripts.medical_dialogue_bench run --backend oracle --out medical/patient-eval/local/bench-oracle
python -m scripts.medical_dialogue_bench verify --run medical/patient-eval/local/bench-oracle --out medical/patient-eval/local/oracle-report.json
python -m scripts.medical_dialogue_bench run --backend noop --out medical/patient-eval/local/bench-noop
python -m scripts.medical_dialogue_bench run --backend naive --out medical/patient-eval/local/bench-naive
python -m scripts.medical_dialogue_bench run --backend stale --out medical/patient-eval/local/bench-stale
```

- oracle：按公开首问识别情境并提问，给出作者参考回答，只证明存在可执行路径。它预先为题库编写，成绩不能和真实模型作公平比较。
- noop：始终只说“请咨询医生”。
- naive：无依据宣称恢复正常。
- stale：在时间更正情境仍沿用旧时间。

这些对照的记录都可能通过工程完整性检查，因为记录可以完整地显示错误。`engineering_integrity=PASS`绝不是临床通过。无评分时`clinical_score=null`、`readiness=NEEDS_SEMANTIC_REVIEW`；不存在空白答卷reward=1。

## 调用实际GPT

将密钥在运行机器的环境变量`OPENAI_API_KEY`中配置好，不写进题目、脚本、仓库或聊天。先核对账户中实际可用的模型标识，明确传给`--model`。不硬编码或自动替换用户所选GPT型号。

```bash
python -m scripts.medical_dialogue_bench run --backend openai --model YOUR_ACTUAL_MODEL_ID --max-calls 72 --max-output-tokens 2048 --out medical/patient-eval/local/gpt-run1
```

上面的`YOUR_ACTUAL_MODEL_ID`必须替换为真实型号。首批12题自然阶段最多72次被测调用；若开启`--probe`，将`--max-calls`至少设为84。`--repeats 3`的自然阶段上限为216次。启动时校验最坏情况预算，不够则不发送请求。追加评分调用另算。

每次请求只包含固定的简短助手角色说明与本题截至当轮的用户/助手文本。题名、事实编号、答案、判据和其他题不发给GPT。不同题不复用会话标识。固定角色说明不提示具体待测错误。

接口使用`store=false`与完整可见消息历史，不发送`previous_response_id`、模型不可见的推理内容或工具。它定义的是“仅可见文本历史”的多轮配置，不与保留其他服务端状态的配置混同。保存provider_model和返回token用量；输出被截断记录为output_incomplete，不作为完整答卷评分。没有自动重试；超时可能已产生费用，未知用量不补0。输出上限包含接口可能使用的推理token；2048仅为起步配置，可能导致不完整结果，调整需新建批次。

接口依据：2026-09-12核对[OpenAI Responses创建接口](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)。模型可用性、支持参数和实际费用需按使用账户核对；本次未进行真实API调用。

## 生成评审表与校验评分

```bash
python -m scripts.medical_dialogue_bench review --run medical/patient-eval/local/gpt-run1 --reviewer A --out medical/patient-eval/local/review-A.json
```

会同时生成可离线打开的review-A.html。人工填写后导出新文件review-A-filled.json。第二名评审以不同代号重复生成，独立完成；不要拿AI的两次评分冒充双人临床审核。

```bash
python -m scripts.medical_dialogue_bench verify --run medical/patient-eval/local/gpt-run1 --reviews medical/patient-eval/local/review-A-filled.json medical/patient-eval/local/review-B-filled.json --out medical/patient-eval/local/gpt-report.json
```

可选自动评分草稿，需要额外模型调用：

```bash
python -m scripts.medical_dialogue_bench judge --run medical/patient-eval/local/gpt-run1 --model YOUR_JUDGE_MODEL_ID --reviewer model-draft-A --max-calls 200 --out medical/patient-eval/local/model-review.json
```

judge按实际已触发的“回答×判据”逐条调用；超过预算时不调用。最多完整自然6轮的12题约300行，含探查可更多，实际数量在`review`输出中查看，再自行设置预算。每条judge只见该回答及此前历史、当前判据和参考来源简介，不见未来信息、隐藏事实表或oracle。judge没有浏览工具，不能自行核实引用来源；医学存疑必须保留insufficient并人工核对。格式错误、假引文等无法通过校验的结果保持未评。模型辅助标签始终暂定，不提供临床认证；应记录与被测模型是否同源。

所有报告和评审文件放在run目录外。run目录只保存plan.json、12个会话JSON及逐请求日志；额外或缺失会话会被verifier拒绝。

## 信息披露与停止规则

复用PatientSimulator的有限状态规则。先检查到期更正，再按实际直接追问匹配事实；否定要求、转述和引用示例不触发披露。更正后同一事实再次被问及，使用更新后的回复。题卡中的“未知”是明确的患者知识状态；整块复合回复只是作者定义的披露粒度，不表示内部每个字段都已经确定。

题库尚未覆盖的追问无法可靠自动匹配时，停为measurement_invalid，等待映射复核，不扣为模型医学错误。无可识别后续追问时结束，记录no_supported_followup；这是有限规则的停止判断，不是模型明确声明任务已完成，间接追问可能漏识别，首次真实运行必须人工抽查。自然轮次耗尽记录turn_budget，不自动通过。探查单列，不能反补自然阶段。

## 日志、恢复和可信边界

每个请求发出前写入并刷盘journal；收到结果后再写返回记录。每题结束原子保存会话JSON。`--resume`只允许同一配置和实现版本，跳过已经保存的题；发现未完成journal则停止，防止不知情重复调用。进程被强制结束可能留下.lock，确认没有活跃进程、核对日志与服务端调用记录后才能人工处理。第一版不实现逐轮自动恢复未确认请求。

verifier使用实际回答重新运行患者规则，逐条比较披露、请求上下文、停止原因和日志。文件摘要用于版本与完整性，不证明会话来源真实，更不替代外部临床信任根。拥有写权限的人仍可能伪造整套日志；需要更强真实性时应接入外部只追加存储和服务端请求证据。

API被测模型只有文本通道，无文件或代码工具；Docker包是可信评测方环境，内部含公开oracle和题库。不能把此容器的shell直接交给被测智能体并声称答案隔离。若以后评测有代码/文件权限的智能体，需要单独目标容器与消息代理。

## Docker

以下命令面向Linux、macOS或Windows的WSL终端；从仓库根目录构建：

```bash
docker build -f benchmark/medical-dialogue-v1/Dockerfile -t groundsignal-medical:v1 .
docker run --rm --network none groundsignal-medical:v1 validate
mkdir -p medical/patient-eval/local/docker-results
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" -v "$PWD/medical/patient-eval/local/docker-results:/output" groundsignal-medical:v1 run --backend oracle --out /output/oracle
```

实际模型运行需允许容器联网，并通过`-e OPENAI_API_KEY`传入宿主环境中的密钥。不要把密钥值直接写在命令参数或镜像构建参数里：

```bash
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" -e OPENAI_API_KEY -v "$PWD/medical/patient-eval/local/docker-results:/output" groundsignal-medical:v1 run --backend openai --model YOUR_ACTUAL_MODEL_ID --out /output/gpt
```

容器校验用`--network none`，实际API运行需要外部网络。镜像不安装外部Python包；基础镜像默认python:3.12-slim，标签会更新，发布冻结时用`--build-arg PYTHON_IMAGE=已核验的镜像摘要`固定镜像。当前开发环境没有Docker/Podman，本地容器构建未验证；已提供GitHub CI执行构建与离线oracle/noop检查，必须查看其实际结果，不能把配置存在当成构建通过。

## 测试与下一阶段

```bash
python -m unittest discover -s tests/medical_dialogue_bench -v
python -m unittest discover -s tests/patient_eval -q
```

测试涵盖12题独立会话、更正、未评分不通过、假引文、未来信息、缺题与日志篡改、调用预算、超时、无密钥、API响应解析及judge输入边界。详见VALIDATION.md。

下一阶段：真实GPT试跑→复核患者映射和停止行为→独立医学评分→从错误出发补充独立病例→受控修复与冻结回归。当前只有6个独立情境，不能对全部医学能力作普遍结论。
