# 从合成会话到可追溯统计（R12）

现有R10流程可以直接生成R4数据库输入。没有评分也能出统计报告；不会为了计算一致性而补造评审记录。

## 如何复现

在仓库根目录，使用现有Python环境，无需新增依赖：

```bash
python -m scripts.patient_eval.pipeline_statistics \
  --suite medical/patient-eval/readiness/round-10-pipeline/suite.json \
  --sessions medical/patient-eval/readiness/round-10-pipeline/imported.json \
  --plan medical/patient-eval/readiness/round-10-pipeline/plan.json \
  --out /tmp/groundsignal-r12-before

python -m scripts.patient_eval.pipeline_statistics \
  --suite medical/patient-eval/readiness/round-10-pipeline/suite.json \
  --sessions medical/patient-eval/readiness/round-10-pipeline/mock-reviewed-sessions.json \
  --plan medical/patient-eval/readiness/round-10-pipeline/plan.json \
  --out /tmp/groundsignal-r12-after
```

输出目录必须不存在；重跑请换新目录。每个目录包含统计输入bundle.json、证据索引evidence-links.json、单文件数据库statistics.sqlite和报告report.json。已保存报告位于round-12-statistics/before、after；数据库可以用以上命令重建。

## 应该看到什么

| 指标 | 评分前 | 加入作者模拟评分后 |
| --- | --- | --- |
| 病例 / 会话 | 3 / 7 | 3 / 7 |
| 有效会话 / 测量无效 | 6 / 1 | 6 / 1 |
| 计划评分项 | 7 | 7 |
| 候选回答已定位 | 3 | 3 |
| 有正式格式机会判断“已发生” | 0 | 3 |
| 质量评分记录 | 0 | 3 |
| 行为通过 / 失败 / 未评 | 0 / 0 / 7 | 2 / 1 / 4 |
| 双人均有质量评分 | 0 | 0 |
| 一致性系数 | 无法计算 | 无法计算 |

这里的“正式格式”只指字段结构，三条仍全部为作者预制模拟记录。实际独立评审人数为0。第二位评审只是空席位，没有生成任何评分行。

已定位候选不等于已确认评分机会。没有评审记录时，即使事件记录完整，也不把“候选未到达”填入正式机会判断。会话完成率5/6描述采集/运行状态，不能解释为模型质量通过率。

## 怎样追查一个数字

先看report.json中的statistics.denominators；quality_trace来自数据库实际评分行，并连接原评分器的结果。failure_queue保留失败项的item_id、session_id、criterion_id和evidence_turn_ids。

用item_id到evidence-links.json查找该项，再用session_id定位输入会话。observation_index是该会话observations数组中的位置（从0开始），review_evidence_turn_ids定位原回答。review_sha256与transcript_sha256用于发现记录变化；它们不证明来源可信或临床准入。证据索引还绑定原输入文件和统计输入摘要。

行为判断与0/1/2质量分独立。只有行为失败、质量仍未评的项目会进入失败清单，质量分保持空值。失败清单只描述可见行为，不认证模型内部根因。

## 适用范围与剩余工作

本转换器只接收显式R10合成材料与原有模拟作者/评分版本。真实来源病例、独立评审声明及其他版本会被拒绝，不能作为真实双人答卷导入器。原一致性工具仍保留其非空输入要求；零评分由统计入口返回agreement=null和no_reviewer_rows。

数据库中的baseline仅用来归组合成材料，repeat_id按同病例会话编号排序生成；这些字段不证明做过原流程/状态干预对照或重复运行。终止原因只复述已有状态，不推测具体接口故障。真实模型实验的分组、重复编号与费用仍须另行绑定。

本轮新增9项测试；相关33项、完整患者评测362项通过。评分前后各5项贯通检查通过，首次零评分失败原样留档。助手自测不能代替他人复现或个人能力验收。

目前是合成工程贯通验证、真实评测准入前准备。57条真实规则映射仍0/57、12条临床裁决待完成；真实动态适配、点选裁决回写、浏览器实际操作和真实对照仍未完成。真实模型调用与真实病例执行均为0。
