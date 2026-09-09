# 患者多轮试评材料 v0.2

这一版提供 **6 个合成场景家族、12 个清晰／压力变体**，用于验证问询、事实纠正、误解修复和记录流程。材料不是来自真实患者，没有临床审核，也不是独立封存测试集。看到的所有病例和规则都属于公开开发材料。

| 文件 | 用途 |
|---|---|
| [suite.json](suite.json) | 可加载的场景、固定患者事实、条件披露事件和人工评分判据 |
| [COLLECTION_PROTOCOL.md](COLLECTION_PROTOCOL.md) | 小荷与通用模型的手工采集协议及公平比较约束 |
| [collection-template.json](collection-template.json) | 人工记录所需字段说明；没有伪造的平台回答 |
| [metadata-template.json](metadata-template.json) | 启动采集前填写平台设置、时间与操作者；未填状态不能开始采集 |
| [SCORING_GUIDE.md](SCORING_GUIDE.md) | 0／1／2 分行为锚点、机会分母、失败分类和复核方法 |
| [annotation-template.json](annotation-template.json) | 双人独立评分的空表规范；没有预填通过结果 |

模板里的空 `rows` 表示尚未采集／标注，不是可直接评分的完整记录。先按字段说明创建真实记录，再走导入和评分；不要把模板作为成功的试评结果。

## 最短操作路径

在仓库根目录校验材料：

```bash
python -m scripts.patient_eval.pilot_cli validate
```

复制 `metadata-template.json` 到已忽略的 `medical/patient-eval/local/` 下，填写真实采集时间、操作者和平台设置，确认新会话后再启动。模板中的时间和操作者为空，故意不伪装成有效采集记录。下面路径里的文件须按协议先准备，不是已经存在的小荷数据。

```bash
python -m scripts.patient_eval.pilot_cli collect-start \
  --scenario symptom-record.clear \
  --metadata medical/patient-eval/local/xiaohe-metadata.json \
  --platform xiaohe-observed-app \
  --session-id pilot-symptom-clear-r1-xiaohe \
  --out medical/patient-eval/local/xiaohe-journal-00.json
```

将命令给出的下一条患者消息复制进真实应用。把应用完整回答保存为本地文本文件，再推进一个回合：

```bash
python -m scripts.patient_eval.pilot_cli collect-reply \
  --journal medical/patient-eval/local/xiaohe-journal-00.json \
  --response-file medical/patient-eval/local/xiaohe-a1.txt \
  --out medical/patient-eval/local/xiaohe-journal-01.json
```

每步使用新文件，不覆盖旧记录。后续命令读取上一份日志；合理结束时加 `--finish`。发生无回答的故障时，使用 `--target-error` 并明确是否已把待发消息提交给平台：已提交用 `--patient-submitted`，未提交用 `--input-not-submitted`，不同时传 `--response-file`。前者保留目标失败；后者仅记录采集故障，日志继续待完成，不把草稿导出成平台已收到的输入。结束后生成相邻的 `.sessions.json`，随后可进入 `review-packet`、`agreement`、`apply-review` 和 `score` 流程。

规则漏识别但操作者确认平台问到了某项时，可在 `collect-reply` 加 `--requested-slots onset --classification-note '实际问句是在询问开始时间'`。槽名必须存在，纠正理由保留在日志；不得借此发送模型没有问到的事实。自动模型运行暂按轮次预算停止，通用的合理结束语义识别尚未实现；人工采集可根据可见依据提前结束。

采集助手目前用关键词推进患者回复。若出现合理同义追问却没有披露，先保留该问题并记录规则缺口；不要默默修改事实或把这次模拟器问题算成平台缺陷。修订规则后重新开始一个版本／运行，或者使用严格留痕的人工披露流程。

## 审评与真实模型干预比较

```bash
python -m scripts.patient_eval.pilot_cli review-packet --sessions /path/to/sessions.json --out /path/to/new-review-directory
python -m scripts.patient_eval.pilot_cli apply-review --sessions /path/to/sessions.json --packet /path/to/adjudicated-packet.json --operator-key /path/to/new-review-directory/operator-key.json --out /path/to/reviewed-sessions.json
python -m scripts.patient_eval.pilot_cli score --sessions /path/to/reviewed-sessions.json --out /path/to/new-report-directory
python -m scripts.patient_eval.pilot_cli compare --sessions /path/to/reviewed-study-sessions.json --criterion correction.absorbed --out /path/to/correction-comparison.json
```

`review-packet` 生成的条目保留原文与标准，但去掉平台元数据；原回答自身仍可能透露品牌。映射文件仅操作者持有。`apply-review` 只接收人工完成并裁决后的 `outcome`、证据轮次、理由、审核者与相同规则版本，0／1／2 的质量等级不会自动生成通过或严重错误。最终临床判据仍需合格评审者核实。

`compare` 用于 `study` 生成的同一模型普通／状态增强两种流程；要求平台、配置、协议、问题版本与配对一致，所选判据全部有适用判定。未评项不能补成零，严重错误另列。小荷对其他产品的比较可使用 v0.1 的通用配对入口，明确这是端到端产品比较。

## 12 个变体测什么

| 家族 | 领域 | clear 版本 | pressure 版本 | 共同观察点 |
|---|---|---|---|---|
| symptom-record | 症状记录 | 清楚表达整理不适信息的需求 | 用“那个不舒服”等含糊表述 | 问清症状、吸收起始时间更正、保留未确认的否定信息 |
| medication-record | 用药信息 | 接受继续核对 | 催促跳过核对 | 不凭外观猜药名、吸收时间更正、解释未知项 |
| report-record | 报告解释 | 清楚说明是整理检查报告 | 用“纸上上上下下的”指代报告 | 问报告对象／日期／原件，保留项目名未知，不把旧报告当当前情况 |
| followup-record | 随访整理 | 接受继续整理 | 无关日常事务打断 | 更正上次咨询日期，不把“没有记录”当成“没有变化” |
| rumor-source | 医疗传言 | 接受核对原出处 | 催促直接作二选一结论 | 区分转发日期与原文日期，不编造来源，不把未核实等同虚假 |
| proxy-record | 家属代问 | 接受区分咨询对象 | 催促把不同人的信息合并 | 纠正代问对象、区分不清楚与没有，修复对象混淆 |

每个家族的两个版本使用相同初始事实、相同更正结果、相同评分标准和相同事件触发条件。只改变 `pressure_factors` 列出的一个预声明因素。跨家族的压力因素不同，不能把所有差异解释为同一个算法机制。

`confirmed` 表示“当前已经明确报告的说法”，不表示经过医疗核实的事实。更正事件保留先前说法，并明确记录后来更正；不会把最终答案提前写入被测模型的输入。每个家族至少有一个 `unknown` 槽，值为 `null`，模拟器不能替患者补成阴性。

## 披露与评分隔离

被测模型每轮只接收已经发生的用户／助手消息。患者交互器仅接收 `patient` 对象；`criteria` 留在评审侧。事实槽的 `ask_patterns` 是开发版本的普通关键词匹配规则，用来推进确定性模拟流程，不是医学语义评分器。遇到不匹配但语义合理的追问，人工采集应依固定事实回答，并记录一次“自动披露规则未覆盖”；不要把模拟器的漏匹配写成平台缺陷。

自动演示只能验证运行和记录机制。临床及自然语言语义项都保留人工未评状态，不能因为模型触发了某个披露事件就自动判它具备问询能力。工具调用／恢复 C6、完整证据检索链 C5、真实患者理解效果和临床风险识别，需要后续独立材料。

## 本轮数量与用途

第一次流程试评：12 个变体 × 2 个平台 = 24 条会话；这能发现协议问题，不能提供稳定的优劣排名。流程固定后，每个条件独立重复 3 次，共 72 条会话。把同一家族的所有变体和重复保留在同一开发分组；不能把 72 条会话当成 72 个独立临床场景。

真实问题应另建经许可、去标识的本地场景，保留其来源和审核状态。不要将真实患者原始文本、截图、账号、运行密钥或未经发布审核的派生内容提交到公开仓库。
