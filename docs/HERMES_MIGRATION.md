# Hermes 历史模块迁移清单

从 `work/patient-consultation-core-v1` 开始。建议每个 M 任务开子分支并交一个小 PR 到本分支；按文件及依赖闭包迁移，不整分支 cherry-pick 或用旧目录覆盖核心。

**当前执行顺序以 [完整任务清单 H00–H46](taskbooks/clinical-benchmark-hermes-tasks-v0.1.md) 为准：主试点已改为脑卒中。** 本页保留来源与模块复用方法；M00 对应新 H00，原 M01–M03 是 AP07 方法参考，不再作为脑卒中试点的前置任务。临床审核先于 A/B 独立评分的原则继续适用。

## 所有任务共用规则

1. 先读取根 README、项目审查、未关闭问题和本任务卡；确定源提交、准确路径、目标路径与依赖。
2. 以固定提交链接取文件；同一路径有多版本时比较差异，不按更新时间盲选。将 source commit/path/blob、目标路径和修改理由追加到迁移记录。
3. 只复制该任务必要代码、资产与测试；原始运行结果标为历史证据，不能覆盖本次测试结果。
4. 先执行该模块有意义的边界验证，再运行 `python scripts/verify_core.py`；失败保留并修复，不能通过删测试或把未评改成通过来迁移。
5. 更新任务状态、验收命令、实际结果与阻断项，再进入下一个任务。已知问题随模块承接；不代签临床审核或独立评分。

## 任务状态

| ID | 内容 | 状态 |
|---|---|---|
| M00 | 对齐 Hermes 尚未推送的最新材料 | 待执行 |
| M01 | 完成 AP07 下一阶段包与节点审核准备 | 方法参考，按需执行 |
| M02 | 真实节点审核、A/B 独立填写与裁定 | AP07 参考任务；脑卒中按 H15/H21 |
| M03 | 接入获审 Oracle 与受控分支，再做小批量联合试测 | 复用方法；当前主线按 H16–H29 |
| M04 | 逐步迁移旧工作台与统计/裁定能力 | 待执行 |
| M05 | 迁移临床推理归因实验 | 待执行 |
| M06 | 接入可用的真实咨询病例来源 | 待执行 |
| M07 | 按需要恢复证据提取和图谱支撑 | 待执行 |
| M08 | 迁移正式测试隔离、训练导出与回归门禁 | 待执行 |
| M09 | 历史笔记、公司事件、demo 与旧 CI | 待执行 |

## M00：对齐 Hermes 尚未推送的最新材料

**前提**：现在可做；不覆盖本分支已复制文件。

**来源**：本分支 `research/ap07-oracle-draft-v1/` 和 `docs/migration/import-manifest.json`；[benchmark/ap07-oracle-draft-v1/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/e494fa34e6271061c4de8c87864adf1e66fcfc9e/benchmark/ap07-oracle-draft-v1/)。

**动作**：读取 Hermes 自己的 `/home/zehaoli0324/projects/groundsignal-patient-integration`：导出当前分支/提交、git diff 和新增文件清单；寻找 `scripts/build_ap07_review_pack.py` 与 `benchmark/patient-consultation-v1/`。这些名称来自先前本地记录，远端快照没有对应路径，不能直接假定存在或已验收。

**目标**：`docs/migration/LOCAL_RECONCILIATION.md`；确有更新的候选材料放 `research/local-candidates/`，脚本先入待审目录。

**验收**：给每个文件列本地摘要、来源、与远端差异、选择理由；核清 14/16 题版本。若文件不存在，记录缺失与影响；检查是否含本地真实患者数据或凭据，不整目录上传。

## M01：完成 AP07 下一阶段包与节点审核准备

**前提**：依赖 M00 的版本对齐；仅在继续 AP07 时执行，当前最高优先级见新的脑卒中任务清单。

**来源**：[AP07 下一阶段任务说明](AP07_NEXT_TASK.md)；[benchmark/ap07-oracle-draft-v1/NODES.md](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/e494fa34e6271061c4de8c87864adf1e66fcfc9e/benchmark/ap07-oracle-draft-v1/NODES.md)；[benchmark/ap07-oracle-draft-v1/author_only/calibration.json](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/e494fa34e6271061c4de8c87864adf1e66fcfc9e/benchmark/ap07-oracle-draft-v1/author_only/calibration.json)。

**动作**：按任务书修正 C05 样本对齐、拆分 N5/C10、独立生成适用判据、分阶段分发 T-first/T-corrected，补医学适用性审核表和正反边界回答。先保留原始草稿，再生成新版本。

**目标**：`clinical_oracle/ap07-v1/`；构建脚本可放 `scripts/clinical_oracle/`；对应测试与变更说明。

**验收**：构建可重放，作者标签不影响评分行，包中无未来信息。临床审核必须真实完成；无审核者时交付待审包，不代签，不启动正式 A/B。

## M02：真实节点审核、A/B 独立填写与裁定

**前提**：节点及医学适用条件获审后，才能启动 A/B；此步需要实际审核人员。

**来源**：[AP07 下一阶段任务说明 P1–P3](AP07_NEXT_TASK.md)。

**动作**：绑定冻结规则与病例摘要；实际组织节点审核与 A/B 分阶段填写。只接收真实记录，独立保存 A/B、曝光声明、封存摘要及争议裁定。Hermes 可整理和验证材料，不能替人完成独立临床签署。

**目标**：`clinical_oracle/ap07-v1/reviews/` 和 `adjudication/`；公开版按参与者授权处理身份信息。

**验收**：A/B 原始行可溯源，关键争议有状态，未知仍未知。不用作者标签或 A/B 一致率冒充准确率；未执行项明确阻断。

## M03：接入获审 Oracle 与受控分支，再做小批量联合试测

**前提**：依赖 M01/M02；适配器工程壳可先准备，临床语义不能提前认定。

**来源**：[scripts/benchmark_checks/multiturn.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/e494fa34e6271061c4de8c87864adf1e66fcfc9e/scripts/benchmark_checks/multiturn.py)；[scripts/patient_eval/patient.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/e494fa34e6271061c4de8c87864adf1e66fcfc9e/scripts/patient_eval/patient.py)；[scripts/medical_dialogue_bench/runtime.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/e494fa34e6271061c4de8c87864adf1e66fcfc9e/scripts/medical_dialogue_bench/runtime.py)。

**动作**：在现有核心上增加可见状态到判据的适配器；将因子轨道接到批跑，明确模型追问、处置建议、障碍与合理终止的事件条件。保留固定事实和不确定语义待复核。冻结病例、模型设置、预算和停止条件后真实试测。

**目标**：`scripts/clinical_oracle/`、现有 runtime 的小范围增量、`tests/clinical_oracle/`、独立试测报告。

**验收**：跨问法与事实披露路径正确；临床与模拟器失效分开。离线核心不退化，真实试跑分别报告效用、安全、过度分诊、环境无效及争议；公开开发题不算未曝光正式测试。

## M04：逐步迁移旧工作台与统计/裁定能力

**前提**：核心稳定后；一次一个入口，先核对现有 app_pilot 功能。

**来源**：[scripts/patient_eval/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/82e0384c555ac6f3b7bc5413e7e3726be975ab85/scripts/patient_eval/)；[medical/patient-eval/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/82e0384c555ac6f3b7bc5413e7e3726be975ab85/medical/patient-eval/)；[docs/reviews/project-audit-v1/findings.json](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/88ca2ac136d87c02f82f52c7defe9c8007d90f5c/docs/reviews/project-audit-v1/findings.json)。

**动作**：只取确有缺口的操作页面或统计功能，先画出导入闭包；不要把旧 cli/评分/统计整包覆盖到新核心。迁移涉及场景摘要、重复机会、动态失败披露时承接 A1-011、A1-012、A1-016。

**目标**：优先现有 `scripts/patient_eval/` 的明确增量；大界面单独 `tools/review-console/`；模块说明和测试。

**验收**：旧问题有失败复现与修复证据，缺失评审不变零分/通过，别名不会重复计数，现有采集与逐轮评审接口不被旧合同替换。

## M05：迁移临床推理归因实验

**前提**：按试测暴露的真实需求选择，不阻塞当前脑卒中主试点。

**来源**：[docs/taskbooks/clinical-reasoning-attribution-v1.0.md](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/665b8edea3cde907ea03de9bbce174552268f0a3/docs/taskbooks/clinical-reasoning-attribution-v1.0.md)；[scripts/clinical_reasoning/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/665b8edea3cde907ea03de9bbce174552268f0a3/scripts/clinical_reasoning/)；[tests/clinical_reasoning/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/665b8edea3cde907ea03de9bbce174552268f0a3/tests/clinical_reasoning/)；[medical/patient-eval/clinical-reasoning-v1/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/665b8edea3cde907ea03de9bbce174552268f0a3/medical/patient-eval/clinical-reasoning-v1/)。

**动作**：迁入独立实验目录，核清脚本状态与自由文本模型运行差异；模型可见视图和操作员内部轨迹分开。已有演示运行作为历史证据保存，不合并为新模型成绩。

**目标**：`experiments/clinical-reasoning/`；必要包可保留原路径并记录兼容理由。

**验收**：迁移来源和依赖清楚；原模块测试在新路径下通过；报告仍写开发实验，不能把注入故障的演示当作已证实模型根因。

## M06：接入可用的真实咨询病例来源

**前提**：先复核许可、脱敏、事实映射与临床阻断项。

**来源**：[docs/handoffs/2026-09-10-patient-cases-v04-nightly-handoff.md](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/15410abe9f6ffd9afecef15ed4ed7210a5e82e1c/docs/handoffs/2026-09-10-patient-cases-v04-nightly-handoff.md)；[medical/patient-eval/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/15410abe9f6ffd9afecef15ed4ed7210a5e82e1c/medical/patient-eval/)；[medical/patient-eval/data-sources/v0.2/README.md](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/863db9b3048a2007ff32d6bb78a9c1719b92e080/medical/patient-eval/data-sources/v0.2/README.md)。

**动作**：从清单定位候选，不整包复制原始语料。12 个夜间候选仍 blocked；50 条 ReMeDi 候选及其映射统计不能当成已批准题量。逐个恢复来源、适用条件、事实和人工审核。

**目标**：`data-intake/` 元数据与候选索引；审核后的合成/获许可病例再入版本化 benchmark。

**验收**：许可与隐私处理有证据、必要事实映射无遗漏、临床审核完成，blocked/unassessed 不被迁移脚本清零；正文发布范围明确。

## M07：按需要恢复证据提取和图谱支撑

**前提**：明确 Oracle 需要哪些证据后，再逐模块恢复。

**来源**：[docs/reviews/project-audit-v1/findings.json](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/88ca2ac136d87c02f82f52c7defe9c8007d90f5c/docs/reviews/project-audit-v1/findings.json)；[scripts/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/82e0384c555ac6f3b7bc5413e7e3726be975ab85/scripts/)；[medical/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/82e0384c555ac6f3b7bc5413e7e3726be975ab85/medical/)。

**动作**：从来源索引选 S2/S3/S4 文件，追踪运行依赖、数据格式和引文定位。先处理 A1-001 至 A1-007、A1-014、A1-015 中涉及的模块问题。图谱边与来源摘录不能自动升级成临床金判据。

**目标**：`evidence/` 与对应 `scripts/evidence/`，或记录保留原路径的理由；独立合同和测试。

**验收**：拒绝无效输入不写部分状态；来源与证据属性完整，引用端点无悬空，评审与适用范围逐证据保留，域名核验不接受子串伪装。

## M08：迁移正式测试隔离、训练导出与回归门禁

**前提**：评测与数据合同稳定后；历史 S5 默认只引用。

**来源**：[medical/](https://github.com/zehaoli0324-cloud/groundsignal-pharma/tree/3dd4fe0eb367e4bb7c0d912d8ae6a891b68ebbda/medical/)；[scripts/export_training_data_v061.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/82e0384c555ac6f3b7bc5413e7e3726be975ab85/scripts/export_training_data_v061.py)；[scripts/regression_gate.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/82e0384c555ac6f3b7bc5413e7e3726be975ab85/scripts/regression_gate.py)；[scripts/s5_v091_freeze_control.py](https://github.com/zehaoli0324-cloud/groundsignal-pharma/blob/82e0384c555ac6f3b7bc5413e7e3726be975ab85/scripts/s5_v091_freeze_control.py)。

**动作**：根据新任务重新确定开发集、校准集和未曝光集的隔离合同，保留历次 first-fresh FAIL 与开发曝光记录；处理 A1-008、A1-009、A1-010、A1-013 后才接入导出/门禁。

**目标**：`evaluation-controls/`、`exports/` 合同及按需代码；历史结果链接单列。

**验收**：错误 run 不能混入，输出原子化，缺评/重复/失败不能放行；历史失败不因复制改写。训练导出不得反向泄漏正式测试。

## M09：历史笔记、公司事件、demo 与旧 CI

**前提**：仅在有明确用途时取用。

**来源**：[完整文件版本索引](migration/README.md)；[分支与 PR 表](migration/BRANCHES_AND_PRS.md)。

**动作**：在完整来源目录按路径/分支定位；需要展示的资料放参考区，先核对内容版本与历史上下文。旧 CI 不能整批恢复到当前核心。

**目标**：`references/` 或独立实验；没有明确用途就继续保留来源链接。

**验收**：说明与当前目标的关系及入口，避免增加默认依赖、旧检查门禁和重复题库；来源与未审核状态保留。

## 每次交接记录模板

任务 ID / 实施者 / 时间 / 源提交与路径 / 目标路径 / 新增依赖 / 行为变化 / 执行命令与结果 / 未关闭问题 / 临床或独立评审状态 / 下一步。

第一次运行与失败记录必须保留。若医学审核或真实 A/B 尚未进行，写“待审核/待填写”，继续完成已授权的工程准备，不能伪造结果解锁。
