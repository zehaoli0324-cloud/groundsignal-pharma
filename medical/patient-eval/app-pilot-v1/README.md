# 小荷健康与蚂蚁健康：首轮对话评测

这批测试用于发现应用在**信息提取、证据梳理、结论支持和主动追问**上的可见问题。先采集真实应用的回答，再分析具体错误。不会自动判断临床正确性，也不会仅凭聊天记录证明底层算法根因。

当前交付：**6个合成场景家族、12张题卡、24项完整试评计划；第一步只做6段会话。真实患者病例0、实际应用回答0、临床批准0。**公开题目属于开发材料，不是未公开测试集。

## 你现在怎么开始

1. 下载 [START_HERE.html](START_HERE.html)，用电脑浏览器打开。文件可离线使用，不需要配置Python；GitHub文件预览页不会运行页面。
2. 页面选好的计划任务说明要测哪个应用、哪道题。填写匿名操作者代号、应用模式和设备，打开应用中的新会话。
3. 复制“患者消息”框的首问，到对应应用发送；在页面点击“我已在应用发送这条消息”。
4. 将应用完整回答粘贴回来，保存该轮。被问到什么，才勾选对应事实；粘贴应用问句作为依据。页面生成固定回复，其他问题回答“不清楚”。更正到期会提示优先发送。
5. 正常结束或出错时写明原因，导出JSON。下一项任务重新打开页面。保留每个计划槽的一份原始记录，不挑选最好答案；诊断重复另建计划。
6. 将这6份JSON交回分析。无需你手工编辑字段，也不需要现在填写医学评分表。

页面不自动保存。可以下载“进行中备份”；备份不是完成会话，当前不提供自动恢复按钮，可据备份人工恢复记录后检查。未发送的草稿不会进入实际对话。只有点击已发送后，才能录入该输入对应的应用回答。

先做AP01、AP03、AP05的基础版，各应用一次。完整题目与固定患者回答见 [QUESTION_CARDS.md](QUESTION_CARDS.md)。首批没有真实患者记录；“真实”指实际使用产品采集其原始输出。

## 题目测什么

| 家族 | 场景 | 主要检查 |
|---|---|---|
| AP01 | 代问家人血糖异常 | 对象、否定症状、报告名称与实际采样条件 |
| AP02 | 复方感冒药后考虑加药 | 成分未知、重复成分、建议是否越过证据 |
| AP03 | 两家机构报告箭头不同 | 数值与单位、参考区间、是否过度解释改善 |
| AP04 | 两项血糖证据不一致 | 冲突保留、确认检测、确定性表达 |
| AP05 | 保健品与头痛时间线更正 | 新信息更新、因果推断撤回与保留 |
| AP06 | 研究指标下降是否证明个人疗效 | 材料来源、研究设计、临床结局与适用范围 |

每题只有首问被自动准备。事实表、评分标准、事件编号和参考资料留在操作者侧。基础版和干扰版只相差首问末尾一段无关文字；程序逐字段核对其余内容相同。不同应用的实际追问路径可以不同，不伪造相同的助手历史。

## 工程人员如何运行

环境：Python 3.10及以上，标准库；从仓库根目录执行。以下路径都在已被Git忽略的本地目录中。输出默认不覆盖旧文件。

```bash
# 校验题卡、来源编号及单因素对照
python -m scripts.patient_eval.app_pilot validate-suite

# 生成全部24项任务的随机顺序与独立采集页面
python -m scripts.patient_eval.app_pilot prepare \
  --out medical/patient-eval/local/app-full-01

# 若使用现成START_HERE.html，导入时用其对应的smoke-plan.json
# 将下面文件名换成实际下载文件；可以一次传入多份
python -m scripts.patient_eval.app_pilot import \
  --input medical/patient-eval/local/capture-01.json \
          medical/patient-eval/local/capture-02.json \
  --plan medical/patient-eval/app-pilot-v1/smoke-plan.json \
  --out medical/patient-eval/local/app-sessions-01.json

# 为两位评审者分别生成JSON及可填写的HTML；默认全部未评
python -m scripts.patient_eval.app_pilot review-template \
  --sessions medical/patient-eval/local/app-sessions-01.json \
  --plan medical/patient-eval/app-pilot-v1/smoke-plan.json \
  --reviewer reviewer-A --out medical/patient-eval/local/reviewer-A.json
python -m scripts.patient_eval.app_pilot review-template \
  --sessions medical/patient-eval/local/app-sessions-01.json \
  --plan medical/patient-eval/app-pilot-v1/smoke-plan.json \
  --reviewer reviewer-B --out medical/patient-eval/local/reviewer-B.json

# 在生成的HTML中填写并下载；把下载文件放到下述位置后汇总
python -m scripts.patient_eval.app_pilot report \
  --sessions medical/patient-eval/local/app-sessions-01.json \
  --plan medical/patient-eval/app-pilot-v1/smoke-plan.json \
  --reviews medical/patient-eval/local/review-reviewer-A.json \
            medical/patient-eval/local/review-reviewer-B.json \
  --out medical/patient-eval/local/app-report-01.json

python -m unittest tests.patient_eval.test_app_pilot tests.patient_eval.test_import_batch -v
```

只有一份评审时也可生成暂定报告，但必须保留单人评审状态。两人有分歧的行不平均、不投票通过，另列裁决。界面保留平台名称，本版不是盲评；双人评审也不自动证明彼此独立或具备临床资质。AI辅助评分应将`reviewer_kind`明确改为`ai_assisted`，不能冒称医生签字。

## 数据与现有平台如何连接

复用现有 `contracts.load_suite`、`import_batch.validate_batch`、`scenario_digest` 和排他写入函数。输出会话遵循原有外部应用记录格式，`trace=[]`，不填内部日志。增加披露日志、冻结计划身份和阶段，原始会话 `observations=[]`，不在导入时补分。

逐轮评审另用 `app-review/v1`，同时绑定题卡文件摘要、完整规范化会话摘要、评分版本与具体回答边界。修改任何对话文本或元数据都需生成新评审，不能沿用旧评分。摘要用于版本一致性，不证明来源真实或独立批准。

这条评审路径暂不写入共享回归发布脚本，也不提升S5准入。已有审计PR #23的16项发现仍单独保留；本次没有宣称修复它们。与复杂临床取证PR #24并行，未依赖其动态动作环境。

严格导入会拒绝漏贴、错贴、协议不符、未知版本或非法日志。被拒的原文件需保留到采集失败台账，不删除或悄悄修成成功。`measurement_invalid`只接纳结构及披露记录仍可核对、但有独立采集失效原因的记录；完全破坏格式的记录在导入前就被拒绝。计划中缺失的槽仍需在批次结案时逐一说明，当前报告不自动补齐未导入的计划槽。

## 报告可以支持什么结论

报告保留会话状态、自然/探查阶段、能力分类、通过与失败、未评、未触发、未采到回答、证据不足、分歧和严重错误未知状态。`overall_pass=null`，`clinical_approval=false`，`root_cause_proven=false`。

通过率分母仅为实际已判通过或失败的判据，同时展示覆盖率；不适用和证据不足仍留在观测覆盖分母中。逐回答计数会受到对话长度影响，不能作为独立样本数或直接给应用总排名。优先展示病例级失败原句、是否可复现和对照差异；不能将24会话说成24个独立场景。

临床参考链接及核对日期已放进题卡和`suite.json`，只支持特定评分原则，没有冻结完整网页，也没有成为独立临床金标准。复杂剂量、诊断争议和转诊时机需要有资格的临床评审；没有依据时应选择证据不足。

## 继续迭代

先采完6会话 → 核查披露是否准确 → 复核评分标准是否有歧义 → 两人分别评分 → 对最清楚的1—2个错误复测 → 形成缺陷卡。协议修订启用新版本，旧结果保留；再开展24项完整开发试评。后续真实来源病例经独立准入后进入另一套材料，不修改这里的合成来源标签。

详细评分与复测工程见 [DESIGN.md](DESIGN.md)，本次验证范围见 [VALIDATION.md](VALIDATION.md)。
