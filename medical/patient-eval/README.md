# 患者多轮评测子系统

这是 GroundSignal 的开发子系统：把会话证据、评分、受控故障与修复回放连起来，并允许导入小荷等只能观察回答的平台记录。当前是 Python 3.11 标准库实现的命令行核心，不是患者咨询产品。

- [统一任务书 v1.2](../../docs/taskbooks/patient-evaluation-master-taskbook-v1.2.md)
- [十阶段职责与验收拆分](STAGE_DECOMPOSITION.md)
- [动态试评 v0.2 场景、采集与评分材料](pilot/v0.2/README.md)
- [v0.3 独立评分操作](REVIEW_V0.3.md) · [本轮验证](VALIDATION_V0.3.md) · [问询校准](calibration/v0.3/README.md)
- [专业数据接入](data-sources/v0.1/README.md)：现有材料审计、八个候选来源、首个中文医患对话集的实际接入与质量检查。
- [原任务书全文](../../docs/taskbooks/patient-multiturn-evaluation-taskbook-v1.0.md) · [Word 原件](../../docs/taskbooks/patient-multiturn-evaluation-taskbook-v1.0.docx)
- [现有项目适配方案、黑盒研究协议和学习路线](ADAPTATION_PLAN.md)
- [数据合同与评分约定](schemas/README.md)

## 当前动态试评：v0.2 场景与 v0.3 评分

新建审评包默认使用 v0.3，独立记录质量、安全和评分机会；旧格式需显式加 `--review-version legacy`。下列目录名只是输出位置，实际版本以记录中的字段为准。操作步骤与部分评分示例见 [v0.3 说明](REVIEW_V0.3.md)。

六个合成家族各有清晰和压力变体，共十二场景。患者只在模型问到或预先规定的事件触发时披露信息；未知、纠正、催促和错误复述都有操作员侧记录。规则问句识别可能漏掉口语表达，人工采集支持带理由的识别纠正；这种模拟器误差必须与被测模型不足分开评估。

```bash
python -m scripts.patient_eval.pilot_cli validate
python -m scripts.patient_eval.pilot_cli demo --out /tmp/patient-pilot-v02
python -m scripts.patient_eval.pilot_cli review-packet --sessions /tmp/patient-pilot-v02/sessions.json --out /tmp/patient-review-v02
```

`demo` 的目标是离线问询夹具，不调用真实模型，不产生临床成绩。它执行两种流程、共二十四条动态会话，验证问询分支、记录、评分入口和审评包。全部临床项等待人工判定。

真实模型对照命令如下，须替换服务地址和模型，并在环境中配置密钥：

```bash
python -m scripts.patient_eval.pilot_cli study --base-url https://YOUR_PROVIDER/v1 --model YOUR_MODEL --key-env PATIENT_MODEL_API_KEY --out medical/patient-eval/local/study-v02 --repeats 1 --seed 7
```

两种流程均保留完整对话与相同输出预算。候选流程仅增加从可见用户原话抽取的事实记录，实验考察“抽取、状态与提示”的组合干预；额外输入开销据实记录，不能声称隔离了模型训练算法。每条会话完成即落盘，输出目录存在会拒绝，防止静默覆盖或重复调用。本版不自动续跑。

小荷应用由人工操作，`collect-start`／`collect-reply` 逐步给出应复制的患者文本并记录模型原文；`review-packet` 隔离平台元数据与操作员映射，`apply-review` 将裁决后的证据判定写回会话，`agreement` 计算两名评审者的一致性。具体命令与模板见 [采集协议](pilot/v0.2/COLLECTION_PROTOCOL.md) 和 [评分细则](pilot/v0.2/SCORING_GUIDE.md)。有序质量等级、严重错误和判据是否通过分别保存，不由分数自动推断临床真值。

## 保留的 v0.1 专项机制

| 核心 | 实际用途 | 本版边界 |
| --- | --- | --- |
| 可见事实状态机 | 明确处理未知、冲突、来源和纠正；拒绝没有来源引用的覆盖 | 输入是人工或上游结构化事件，尚未自动理解患者口语 |
| Best Matching 25（BM25，词项相关性检索） | 中文双字词元与拉丁词元排序，日期和人群硬过滤 | 合成段落验证；尚未接入原项目真实证据库 |
| 固定多轮前缀回放 | 同一个合法历史下测试最后回答；保存状态和输出 | 历史助手消息预先写定，不是动态患者模拟器 |
| 故障注入与修复 | 实际丢弃一次纠正事件，观察输出错误，再恢复事件投递 | 仅一次最终轮纠正故障；任务书十类故障尚未完整实现 |
| 黑盒人工导入 | 校验平台条件、完整轮次、来源声明及评分证据 | 不登录小荷、不自动采集、不根据回答猜内部架构 |
| 应用程序接口（Application Programming Interface，API）适配器 | 向兼容聊天补全接口发送合法文本前缀，记录响应和有界重试 | 仅显式运行；默认演示不联网；本次未调用真实模型 |
| 评分与诊断 | 未评、服务失败和测量无效分开；严重错误单列；归因附证据等级 | 临床项需人工审核，不能由自动标签宣布医疗安全 |
| 对照报告 | 原文、分母、证据、未评项及家族配对自助重采样区间 | 小样本开发结果，不生成商业模型排名或临床放行 |

八能力模块共用一个框架。本版合成自动检查覆盖 C3 事实更新和 C5 检索机制；C4 风险边界与 C7 患者解释预留人工评分。其余能力以及完整八模块临床评价仍按任务书建设。

## 离线运行

在仓库根目录运行，无需安装第三方包或配置密钥：

```bash
python -m unittest discover -s tests/patient_eval -v
python -m scripts.patient_eval demo --out /tmp/patient-eval-demo
```

输出目录包含 `sessions.json`、`results.json` 和可直接打开的 `report.html`。四个合成家族各有清晰/压力两个变体；每变体运行故障臂和恢复臂，共十六条记录。演示检验故意设置的工程机制，不能把这个差值描述为某个医疗模型的提升。

报告中的临床安全和解释项保持未评。没有已发现严重错误，与已经证明没有严重错误，是两个不同状态。

## 手工导入小荷或其他平台

先用明确标记为合成、并非来自小荷的 [示例记录](development/manual-transcript.example.json) 跑通：

```bash
python -m scripts.patient_eval import --input medical/patient-eval/development/manual-transcript.example.json --out /tmp/patient-imported.json
python -m scripts.patient_eval evaluate --sessions /tmp/patient-imported.json --out /tmp/patient-manual-report
```

实际研究时复制结构到 `medical/patient-eval/local/`，替换为经许可且去标识的问题与完整记录，并创建相应开发场景。该目录及 `runs/` 已被 Git 忽略；任何真实会话原文、截图、账号或身份映射都不应放进公开仓库。去标识和使用许可标志只是操作员声明，不能替代复核或研究审核。

同一患者任务分成两条研究轨：

- `free_dialogue`：由平台自主问询，人工按冻结患者事实与披露规则作答，记录完整路径。比较完整任务结果。
- `fixed_prefix`：比较同一角色结构、同一历史内容后的一个回答。若小荷界面只能粘贴一段历史文本，它实际收到的是用户引用文本，应另建协议与场景；不能伪装成收到了 API 的结构化历史。

评分与比较拒绝混合两种协议。平台版本、模式、记忆/联网条件、采集时区、是否新会话、输入方式和重复编号必须留痕。产品之间的差异不能自动解释成底层模型差异。

`observations` 中的每个判定指向实际 `turn_id`。人工标注还要填写 `reviewer_id` 和 `rubric_version`；实际临床审核资格和分歧裁决属于研究流程，程序不会认证一个填入的名字。未标注的临床项目自动保持 `unassessed`。

## 接入通用模型

先在运行环境中设置所选密钥变量，再显式执行：

```bash
python -m scripts.patient_eval run-api --base-url https://YOUR_PROVIDER/v1 --model YOUR_MODEL --key-env PATIENT_MODEL_API_KEY --out medical/patient-eval/local/api-run
```

该命令会调用外部服务，可能计费。地址和模型名需要替换；密钥只从环境变量读取。每个场景发出一次固定前缀请求，传输错误最多重试一次；完成的每条记录立即写出。超时、空回答和响应结构错误保留为目标失败。本版不自动续跑，重跑命令会重新调用整个套件，应使用新输出目录记录重复实验。

只发送 `role` 和 `content`；结构化事实、隐藏材料、评分答案与故障标签不进入模型消息。发送给目标的临床文本仍需使用者事先核实授权和去标识状态。API 返回后没有自动临床评分，需按统一规则盲评。

## 统计与证据等级

`compare` 接收预先确定指标的逐会话记录数组：

```json
{"family_id":"family-01","scenario_id":"case-01","variant":"pressure","platform":"platform-A","repeat_id":1,"score":0.0,"comparison_lane":"free_dialogue","protocol_id":"study-v1"}
```

每个配对键要同时有基线和候选记录；目标失败计入指标，不能删除后只比成功样本。重复、缺对、跨轨道或跨协议会拒绝汇总。

```bash
python -m scripts.patient_eval compare --rows /path/to/paired-rows.json --baseline platform-A --candidate platform-B --out /path/to/comparison.json
```

先算家族内部平均差值，再给家族等权重并按家族自助重采样。家族少于两个不输出区间；少量合成家族的区间只用于验证程序。严重错误和临床覆盖率必须与数值差值一起报告。

诊断器区分行为证据、候选原因和受控验证。有内部轨迹且实际故障、修复、输入、状态和最终输出匹配时，才在该实验范围内确认组件原因。黑盒输出不能据此确认内部算法、截断方式、检索器或服务器根因。

人工采集到同条件的一项输入干预后，可以用 `evaluate --controls /path/to/controls.json` 提交对照。该文件以基线 `session_id` 为键、控制记录数组为值；黑盒记录使用 `kind="blackbox_behavior_probe"`，并提供 `control_id`、`criterion_id`、`factor`、`changed_turn_id` 和完整 `controlled_session`。本版接受 `correction_restated`、`ambiguity_clarified`、`evidence_supplied`、`pressure_removed` 四种探针。除一个指定用户消息外，历史必须相同；平台、版本、模式、协议也必须匹配且新建会话。符合条件的失败转通过只支持行为敏感性假设，仍不能确认内部根因，也不证明干预已提前注册或具有总体有效性。

现有案例准入、独立测试污染检查、临床审核和训练导出机制保持独立；本子系统只接受开发分区，持续集成成功不能放行真实患者服务。
