# 未关闭问题与迁移阻断

## 本次确认的当前建设缺口

| ID | 缺口 | 后续任务 |
|---|---|---|
| FOCUS-01 | AP07 C05 定义与部分作者期望不一致 | M01 |
| FOCUS-02 | N5/C10 与终止/测量合同混合 | M01 |
| FOCUS-03 | AP07 同包暴露前后时序，阶段一可能看到未来 | M01/M02 |
| FOCUS-04 | 适用评分行须独立于作者期望推导 | M01/M03 |
| FOCUS-05 | 因子轨道未接完整模型批跑；规则患者语义覆盖有限 | M03 |
| FOCUS-06 | 临床节点、严重性和医学适用条件未获独立批准；A/B 空表未填写 | M01/M02 |
| FOCUS-07 | Hermes 本地 builder/16 题等更改未在本次远端快照出现 | M00 |
| FOCUS-08 | 尚未证明题目对强模型的危险错误区分度 | M03 联合试测 |

本次原样复制候选材料是为了保留进展与可追溯性，不能解释为上述问题已修复。

## 承接旧审计的 16 项 OPEN

原始证据：[docs/reviews/project-audit-v1/findings.json](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/88ca2ac136d87c02f82f52c7defe9c8007d90f5c/docs/reviews/project-audit-v1/findings.json)。原审计声明 project_audit_complete=false、project_tests_complete=false；本次没有重跑这些历史复现，也没有声称这些缺陷已经修复。

下列报告指向的文件没有纳入当前 25 个核心源文件。重新引入相关模块时，必须复现并处理对应问题；当前核心通过不代表这些历史问题关闭。

| ID | 严重性 | 原问题 | 原路径 | 状态 |
|---|---|---|---|---|
| A1-001 | P1 | 缺少事件编号时先写状态再抛错 | `scripts/s4_truth_ledger_v011.py` | OPEN，待模块迁移时处理 |
| A1-002 | P1 | 同编号边合并丢失证据属性差异 | `scripts/build_medical_knowledge_graph.py` | OPEN，待模块迁移时处理 |
| A1-003 | P2 | 图谱输出未检查悬空端点 | `scripts/build_medical_knowledge_graph.py` | OPEN，待模块迁移时处理 |
| A1-004 | P2 | 运行时校验未落实已声明的类型合同 | `scripts/s3_semantic_extractor.py` | OPEN，待模块迁移时处理 |
| A1-005 | P1 | 检索评分未绑定运行身份且重复行静默覆盖 | `scripts/eval_s2_live_retrieval.py` | OPEN，待模块迁移时处理 |
| A1-006 | P2 | 空输入与缺失目录可被成功验证 | `scripts/validate_medical_knowledge_sources.py` | OPEN，待模块迁移时处理 |
| A1-007 | P2 | 错误适配器绕过逐项异常记录 | `scripts/s2_live_retrieval.py` | OPEN，待模块迁移时处理 |
| A1-008 | P1 | 导出前关联运行记录时可串接错误回答 | `scripts/export_training_data_v061.py` | OPEN，待模块迁移时处理 |
| A1-009 | P1 | 输出可被覆盖，失败可能留下部分新内容 | `scripts/export_training_data_v061.py` | OPEN，待模块迁移时处理 |
| A1-010 | P2 | 冻结检查失败与允许编写标志可同时出现 | `scripts/s5_v091_freeze_control.py` | OPEN，待模块迁移时处理 |
| A1-011 | P1 | 通用评分入口未核对已有病例摘要，旧结果可用于新标准 | `scripts/patient_eval/cli.py` | OPEN，待模块迁移时处理 |
| A1-012 | P2 | 统计输入只按外部编号查重，同一评分机会可重复计数 | `scripts/patient_eval/readiness_statistics.py` | OPEN，待模块迁移时处理 |
| A1-013 | P1 | 共享回归发布检查接纳缺失评审与重复病例 | `scripts/regression_gate.py` | OPEN，待模块迁移时处理 |
| A1-014 | P1 | 知识库合并的冲突重命名和附件复制可覆盖旧文件 | `scripts/import-helper.py` | OPEN，待模块迁移时处理 |
| A1-015 | P2 | 来源分级用整段网址子串匹配，非官方地址可标成官方 | `scripts/evidence-audit.py` | OPEN，待模块迁移时处理 |
| A1-016 | P2 | 合成披露器输出失败后仍记录已披露且阻止重试 | `scripts/patient_eval/dynamic_case_offline.py` | OPEN，待模块迁移时处理 |

原记录的 trigger、actual、repair_plan 与 validation 链接保留在固定提交中；迁移后的修复记录应引用 finding_id 并附新证据，不能只改本表状态。
