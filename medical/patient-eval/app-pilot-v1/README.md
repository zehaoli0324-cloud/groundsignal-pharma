# 小荷健康与蚂蚁健康：首轮对话试评

目标：发现产品在信息提取、证据梳理、结论支持及自主追问方面可复核的行为问题。操作者实际使用手机应用；本工程离线采集和辅助评审，不调用应用接口。

当前交付：6个合成情境家族，基础版与单因素无关文本干扰版共12题；首轮3题×2应用=6会话，完整版12题×2应用=24会话。真实患者病例0，实际应用回答0，临床批准0。题目公开后仅用于开发和回归，不能声称是未暴露测试集。

## 直接开始

先读 [QUESTION_CARDS.md](QUESTION_CARDS.md)。已附可直接下载后双击打开的 [collector.html](start-here/collector.html) 及对应 [plan.json](start-here/plan.json)，无需先运行Python。导出后可把JSON交回项目维护者做导入评分。首轮为AP01（对象、否定）、AP03（报告证据）、AP05（时间更正）。每个应用每题新建会话，记录版本、模式、记忆和联网设置；不可见填“未知”，不要猜。随机计划只平衡执行顺序，不消除账户与服务差异。

在仓库根目录运行（Python 3.10或以上，无额外Python依赖）：

```bash
python -m scripts.patient_eval.app_pilot validate-suite
python -m scripts.patient_eval.app_pilot prepare --smoke --out medical/patient-eval/local/app-pilot-run1
```

双击输出目录的 `collector.html`。填写基本信息、确认新会话，点击“开始”。复制“用户输入”到对应应用，粘贴完整回答及展示引用，再勾选它实际问到的事实，并粘贴对应追问原句。生成下一条后继续。页面不联网、不自动保存；每次会话结束立即导出JSON，截图另存。刷新前必须导出。

没有对应事实就选“不清楚”；不可临时编造。问到多个事实时仅选相关条目。更正事件满足条件时优先发送。自然对话最多6次回答，再允许1次解释探查；探查后不得返回自然阶段。可因已得到可执行下一步、明确转诊、重复无进展或预算耗尽提前结束并写原因。已到期更正如因结束未发送，记录原因，对应标准保持未触发。

每轮等待最多120秒；有明确应用错误或超时选“应用无响应／错误”，保留已获得回答。操作者漏录、发错文字或无法复核转录选“采集操作无效”。应用主动拒答是实际回答，正常录入，不能算平台错误。实际产品名称和版本按屏幕核对；不把品牌名当底层模型标识。

将导出的记录存入上述local目录。下面命令中的路径和评审者代号可替换；所有输出都要求新文件，不覆盖历史结果：

```bash
python -m scripts.patient_eval.app_pilot import --input medical/patient-eval/local/app-pilot-run1/capture.json --plan medical/patient-eval/local/app-pilot-run1/plan.json --out medical/patient-eval/local/app-pilot-run1/sessions.json
python -m scripts.patient_eval.app_pilot review-template --sessions medical/patient-eval/local/app-pilot-run1/sessions.json --plan medical/patient-eval/local/app-pilot-run1/plan.json --reviewer A --out medical/patient-eval/local/app-pilot-run1/review-A.json
python -m scripts.patient_eval.app_pilot review-template --sessions medical/patient-eval/local/app-pilot-run1/sessions.json --plan medical/patient-eval/local/app-pilot-run1/plan.json --reviewer B --out medical/patient-eval/local/app-pilot-run1/review-B.json
```

`--input`可接多个文件。打开生成的review-A.html和review-B.html独立评分，分别导出为review-A-filled.json和review-B-filled.json。下载目录由浏览器决定，移动到运行目录再汇总：

```bash
python -m scripts.patient_eval.app_pilot report --sessions medical/patient-eval/local/app-pilot-run1/sessions.json --plan medical/patient-eval/local/app-pilot-run1/plan.json --reviews medical/patient-eval/local/app-pilot-run1/review-A-filled.json medical/patient-eval/local/app-pilot-run1/review-B-filled.json --out medical/patient-eval/local/app-pilot-run1/report.json
```

独立人工评审尚未完成时，可以只传一份评分，结果仍为暂定。AI辅助填写需把reviewer_kind改为ai_assisted；不能当作两名独立临床专家。去掉prepare命令的 `--smoke` 可生成完整版。

## 评分规则

评分单位是“一个实际回答×一个已触发判据”，不是整道题一票通过。先核对披露日志与实际追问是否语义匹配；代码仅检查原句存在，不能判断操作者是否多透露了事实。违规采集应标为measurement_invalid并保存原因，重新导入后重做评分。

| 状态 | 判断标准 |
|---|---|
| 通过 pass | 当轮回答对该判据表现充分，提供回答原句和理由 |
| 失败 fail | 有可定位的错误或应有行动缺失，提供原句、具体遗漏和影响 |
| 证据不足 insufficient | 文本不足以判断，或医学标准存在待复核争议 |
| 不适用 not_applicable | 已触发技术条件但该回答无需再执行此动作，说明理由 |
| 未评分 unassessed | 尚未审阅，绝不计入通过 |
| 未触发 untriggered | 所需事实/更正尚未披露，由工程生成，不得改成通过 |
| 未观察 not_observed | 该用户轮没有得到回答，不假设成功或医学失败 |

信息提取看是否正确使用事实；未复述不自动扣分。证据梳理看材料是否支持所声称内容；材料未报告某项不等于研究肯定没有。结论支持看确定性、替代解释和下一步是否匹配信息；不要求输出内部思维链。追问按当时尚存且影响决策的缺口评估，已问过且无需重复时选不适用；不能每轮要求重问全套清单。单说“问医生”不自动通过，但合理的立即转诊不应被机械扣成追问不足。

所有决定、证据不足与不适用都必须绑定目标回答原句。遗漏错误可引用最相关的结论/建议并解释缺少什么，不能伪造“遗漏原句”。引用真实性、适用性与医学争议由评审另核对原网页/说明书，保存网址、日期和支持片段；无法核对时保持证据不足。

自然阶段与探查阶段独立统计。未来轮次证据禁止用于前轮评分。严重错误单独标记，仅允许挂在失败上；不清楚时保持null并选证据不足。其影响需写具体，例如在成分不明时直接建议叠加药物。

汇总报告给出各平台、各阶段、各维度的状态计数、已评分覆盖率及已决定条目的条件通过率；分母不含未评分、证据不足、不适用、未触发、未观察与争议。必须同时报告这些未决定状态，避免选择性只报通过率。双人不一致保留disputed，不平均为通过。无效采集排除行为指标，应用错误单独计数。逐轮条目相互相关，本轮不做显著性推断、不作产品总排名；家庭数、会话数与条目数不得混用。

## 失败复现和工程对接

失败记录使用 [FAILURE_RECORD_TEMPLATE.md](FAILURE_RECORD_TEMPLATE.md)。原始会话、评分与题集通过SHA-256摘要绑定；摘要只能检测内容变化，不能证明操作者真实使用过应用。保留截图和时间记录供复核。

发现失败后先在新会话重复基础题，再做已冻结的单因素变体；两应用均重复，每种配置至少3次作为描述性复现。重新prepare输出到新目录，不能覆盖或只保留成功复测；新计划备注说明目的与原失败记录。自由问诊轨迹会随应用追问而不同，所以这种比较是整个交互策略的差异，不能把所有变化归因于那一句干扰。严格输出对照另建固定可见前缀实验。

| 对接方 | 交付 | 尚不能宣称 |
|---|---|---|
| 算法 | 原句、当轮事实、错误类型、重复结果、单因素对照；建议检查否定/状态更新/证据约束 | 已确认模型内部推理或检索根因 |
| 工程 | 截断、错误、转录、版本差异；另申请日志核对输入、检索、上下文与渲染 | 仅凭前端文本定位服务组件 |
| 产品 | 是否追问关键缺口、是否解释不确定性、下一步是否可执行及用户负担 | 小样本证明整体优于竞品 |
| 临床评审 | 具体医学争议、参考来源、适用条件与风险 | 自动评分等同临床认证 |

本模块复用patient_eval的会话契约、黑盒导入和摘要工具；逐轮评分包采用app-review/v1独立格式，避免把多轮判据强塞进旧版每会话一次的observations。暂不接入正式准入分数或自动裁决；争议由专家复核后形成新版本评分，旧文件保留。

未来接入真实材料前，需补来源许可、去身份记录、完整事实表、独立临床审核与版本冻结。原始应用记录默认放git忽略的local目录；本PR只提交合成题和工具。

## 验证

```bash
python -m unittest tests.patient_eval.test_app_pilot -v
```

覆盖未评分不通过、假引文、未触发改判、版本失效、无依据披露、未来证据、评审分歧、计划规模、更正触发、缺失回答和HTML嵌入转义。浏览器可用性与实际应用采集需另记录，测试中的fixture不是产品回答。

本次验证记录：397项patient_eval单元测试通过（含新增22项）；12题校验及6会话计划生成通过；两个页面的JavaScript语法检查通过。当前环境缺少Chromium可执行文件，浏览器交互端到端验证未完成，不能据此宣称页面已经实测可用。实际应用会话仍为0。
