# 复杂临床推理与主动取证：开发入口

主计划：[`clinical-reasoning-attribution-v1.0.md`](../../../docs/taskbooks/clinical-reasoning-attribution-v1.0.md)。归属 S8，连接 S5/S6/S7/S9/S10。

本目录是新增合成开发资产，不是原60题的临床批准版。首批交付病例标准初审、肾功能与贫血两个草稿、肾功能干扰配对、模型可见输入投影、最小结构化动作环境与工具投递失败轨迹。临床评分和因果验证器尚未实现。

在仓库根目录运行（Python 3.11+，仅标准库）：

```bash
python -m unittest discover -s tests/clinical_reasoning -v
python -m scripts.clinical_reasoning.demo
```

演练输出两家族各一组正常/投递失败脚本会话，共4条。它展示工具原始返回与实际投递的差异，所有临床质量、安全和任务成绩保持未评；模型调用为0。演练输出包含操作者轨迹，不能整体作为模型输入。

`DevelopmentSession.model_view()` 是目标可见投影；`operator_trace()` 仅供操作者。动作接口是结构化主题精确匹配，不能当成自由中文问询理解已经完成。所有现有查询主题可在开发病例中检查；正式模型调用不得把完整主题列表、病例ID、评分标准或故障标签混进题干。

`validate_distractor_pair()` 只接受 `opening.context_extra` 改动和不同病例编号，其他临床事实、评分草稿、家族等均须相同。机械配对通过不证明干扰内容临床无关，该判断待人工审核。

`CLINICAL_REVIEW.md` 记录来源可访问范围与标准疑点；`PROGRESS.json` 是下一轮入口。开始实现新评分/归因功能前先读主计划的 A1 审计依赖。

当前限制：无自由口语适配、无真实模型调用、无临床金标准、无完整过程评分、无根因证明、无真实患者验证。本轮没有修改旧S5冻结或旧评分器。
