# 数据合同与评分约定 v0.1

执行合同以 [`contracts.py`](../../../scripts/patient_eval/contracts.py) 为准；黑盒采集补充校验在 [`importers.py`](../../../scripts/patient_eval/importers.py)，评分入口在 [`scoring.py`](../../../scripts/patient_eval/scoring.py)。使用标准库显式校验，不声称使用了尚未运行的 JSON Schema 校验器。

## 场景与家族

套件：`schema_version="patient-eval/v0.1"`、`scope="development_only"`、非空 `scenarios` 数组。场景含 `scenario_id`、`family_id`、`variant`、`protocol_id`、`split="development"`、`source`、`prefix`、`criteria`。正式独立测试准入尚未实现，标记 `gold_approved=true` 不能绕过开发分区限制。

`source` 为 `synthetic` 或 `deidentified_real`；后一类需操作员明确声明 `use_authorized=true` 和 `deidentification_confirmed=true`。这些声明不是审批结果。真实来源场景只应存于受控研究目录。

`prefix` 为交替的用户/助手消息，用户开头并结尾。每条有唯一 `turn_id`、`role`、`content`；`answer` 保留给被测响应。模型输入仅从这些消息中取角色与正文。`visible_updates` 是按用户轮次索引的结构化可见事实标注，不发给真实目标，也不等于自然语言理解结果。

事实更新包含 `key`、`value`、`status`（`confirmed`、`unknown`、`conflict`）。修正必须用 `supersedes` 引用该字段当前的来源轮次，保留旧事实历史。合成故障夹具仅允许一次最后用户轮的纠正投递干预。

## 会话

会话记录标识场景、家族、变体、平台、观测等级和状态。`completed` 以助手消息结束；`target_error` 可以停在用户消息。`measurement_invalid` 需 `invalid_reason` 与 `invalid_component`，后者仅限 `simulator`、`evaluator`、`collector`。目标模型或平台超时不能标成测量无效。

`observability="black_box"` 不允许内部 `trace`。API 模型也属于黑盒，即使自建调用器能记录网络耗时。`instrumented` 只适用于实际具有组件轨迹的自建实验；字符串标记本身不能证明日志可信或临床放行。

黑盒 `metadata` 必须记录带时区的 `collected_at`、`app_version`、`platform_mode`、布尔值 `conversation_reset`、`input_mode`、`comparison_lane`、`question_source`、两个来源声明、`session_protocol_id`、`operator`。可在同一对象补充账号研究编号、设备、网络、引用、逐轮时间、批次和 `repeat_id`；不保存身份映射。

## 评分项和标注

判据含唯一 `id`、`module`（C1–C8）、`kind`（`mechanical` 或 `clinical`）、布尔值 `critical`、`required`、行为描述。工程夹具另支持 `state_value` 和 `selected_evidence` 检查；前者检查显式结构化输出，后者只检查合成段落排序，不能替代医学理解判断。

标注包含 `criterion_id`、`outcome`、`evidence_turn_ids`、`reason`、`source`。`outcome` 为 `pass`、`fail`、`not_applicable` 或 `unassessed`。已决定的判据要引用存在的轮次；人工标注需 `reviewer_id` 和 `rubric_version`。临床项仅人工来源可以作出判定，自动来源保持未评。

必要步骤因目标失败而没有发生，计操作性未完成。真正的临床严重错误需其独立判定，不能把超时自动当成危险医学建议；也不能把没有评估严重错误记成安全。独立测量无效单列并退出目标质量分母。

输出同时保留有证据的评分覆盖率、操作性未完成数、未评数、严重错误未知数和各自分母。人审姓名、结果标签和事件声明均不能单独证明判定正确；正式研究仍需标注校准、裁决与原始证据复核。

## v0.4 动态病例草稿状态机

真实来源开发病例的作者态合同见 [`dynamic-case-state-machine-v0.4.json`](dynamic-case-state-machine-v0.4.json)。它不是 `patient-eval/v0.1` 的正式可运行场景协议：只有 `NOT_OPENED`、`ACTIVE`、`CLOSED` 三态，所有动态披露都要求操作员明确确认，自动自然语言匹配固定关闭。

opening 只能引用 `initial` 事实；`on_question` 与 `scheduled` 事实各有一次性确认事件；`never` 事实没有可见转移。合同不把审阅稿中的问询例句、定时条件或评分机会自由文本解释为结构化触发回合、响应回合或截止点。所有私有病例草稿保持 `dynamic_scenario_ready=false` 和 `clinical_runnable=BLOCKED`，完成独立审阅、临床裁决、自然语言渲染及离线泄漏测试后才可另走准入流程。
