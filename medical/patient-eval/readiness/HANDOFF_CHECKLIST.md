# 合成工程统一交接清单（T07，待他人验收）

目的：让另一人在自己的环境中，按文档复现已有工程结果，并交回卡点；不是新增模型评测，也不代替李泽豪的独立学习或临床裁决。

## 1. 固定版本与环境

本清单只覆盖截至R6的已提交功能。代码与输入冻结在 `b45ed12b3d0a01fb4dbc921a7c41bd74bd49ed21`，文件树为 `73b9a931239fa0a3e0407300293f0038905dcdba`。后续会话导入或规则清单增量不在本次复现口径内。

需要 Git、Python 3.11或更新版本和本地浏览器；这组演练仅用Python标准库，不需要安装数据库服务、第三方包、付费密钥或真实患者材料。本次文档入口核验环境是Python 3.12.14/Linux；其他系统尚待使用者验证。Node.js不是执行以下演练的前提。

在一个不存在的目录中开始，逐条执行，不把整段报错忽略后继续：

```bash
git clone --branch work/social-hire-readiness-20260910 https://github.com/zehaoli0324-cloud/groundsignal-pharma.git groundsignal-handoff
cd groundsignal-handoff
git switch --detach b45ed12b3d0a01fb4dbc921a7c41bd74bd49ed21
git rev-parse HEAD
git status --short
python --version
```

`HEAD`应等于上述冻结提交，工作树应干净。如果版本不存在或已有改动，保留输出并停止，不重置原仓库。Windows如果没有`python`，可将后续命令统一替换为`py -3`并记录实际版本。克隆需要网络；下面所有演练均为本地合成响应。

## 2. 运行入口与对照结果

首次只做A；成功后再按时间做B—F。每项单独记录“未做/成功/失败/待解释”，不能用一项成功代替全部验收。下列路径都位于已忽略的本地结果目录；不要把结果自动提交GitHub。

### A. 最小正常运行与可解释异常（必做）

```bash
python -m scripts.patient_eval.readiness_drill --out medical/patient-eval/local/handoff-a
```

查看`handoff-a/report.json`：`passed=true`、9/9检查。正常保存2条会话；故意中断保留1/2；超时/空响应属于`target_error`（目标接口失败），适配器格式错误属于`measurement_invalid`（测量无效）。异常由脚本故意制造，不是实际模型失败率。

这是R0历史运行器：新目录重跑会重复全部任务，不是断点续跑。详见[最小交接包](README.md)。

### B. 新格式中断后恢复

```bash
python -m scripts.patient_eval.resumable_drill --out medical/patient-eval/local/handoff-b
```

查看`handoff-b/report.json`：`passed=true`、8/8检查；中断保留1/2，恢复只增加剩余会话调用，原会话字节不变，最后2/2。不要手工删除锁或更改摘要使检查通过；未落盘请求仍可能重放，不承诺绝对只调用一次。详见[恢复合同](RECOVERY_CONTRACT.md)。

### C. 统计与分母

```bash
python -m scripts.patient_eval.readiness_statistics --input medical/patient-eval/readiness/statistics-fixture-v0.1.json --db medical/patient-eval/local/handoff-c.sqlite --report medical/patient-eval/local/handoff-c-report.json
```

查看报告：3病例、7会话、1重复；5完成、1目标失败、1测量无效；服务完成率5/6；7条计划评分机会中仅1条双方均给分。数据库执行了3条查询，查询正文在`statistics-queries-v0.1.sql`。详见[统计练习](STATISTICS_REVIEW.md)。这里的两位评审只是作者构造的标签，不是两人独立评分。

### D. 失败归因证据

```bash
python -m scripts.patient_eval.readiness_diagnosis --out medical/patient-eval/local/handoff-d.json
```

预期`passed=true`、15/15检查，3个既有合成用例的状态规则从失败到通过，6类证据不足情形拒绝确认内部原因；临床规则保持未评。恢复的是既有故障注入，不是新发现的生产缺陷。详见[失败归因说明](FAILURE_ANALYSIS_REVIEW.md)。先完成A以创建父目录；若仅做D，需自行建立新的输出父目录。

### E. 三条评分规则的结构检查

```bash
python -m scripts.patient_eval.readiness_rules
```

预期3条合成规则、9个作者分档示例通过结构核验；这不判断自然语言分数是否正确。详见[规则审阅说明](SCORING_RULES_REVIEW.md)。另两名评审的独立评分和歧义裁决仍未完成；不要拿附作者答案的教材计算独立一致性。

### F. 合成界面保存与恢复（需要真实使用者）

```bash
python -m scripts.patient_eval.clinical_console render --out medical/patient-eval/local/handoff-console.html
```

不加`--original`，只生成空白入口与内置合成示例；不要导入私有材料。若文件已存在，先换新文件名，生成器不提供与演练相同的防覆盖承诺。

用本地浏览器打开，点“体验合成示例”，记录浏览器版本与评审席位，然后：

1. 一题只查看预选，不确认；另一题直接确认预选。
2. 另选一题改选并确认，再改选一次，观察其确认是否清除；保留至少一题未答或跳过。
3. 保存答卷，确认下载确实完成；记录已选/已确认数量，关闭页面。
4. 重新打开同一HTML，选择同一评审席位，通过“继续自己的答卷”恢复文件；核对答案、未答项、确认记录及两个数量。

四项默认答案保持：“原文支持这条信息。”“未发现患者身份信息”“适合考察，具体评分标准待补充”“足够理解本段情况。”旧版缺失的界面和确认来源必须保留未知。详见[操作记录说明](INTERACTION_RECORDS_REVIEW.md)。实际浏览器体验和预选是否影响判断质量，均不能由本清单或已有脚本测试判定完成。

## 3. 失败时怎么做

- 找不到`scripts`：核对是否位于仓库根目录及冻结提交，不先修改程序。
- 输出已存在：保留首次目录和终端输出，换新的尝试编号；不要删除失败文件制造“首次通过”。
- 检查为false、意外异常或恢复锁冲突：停止该步骤，保留完整报错、命令和结果，不自行修改病例标签、清单或锁绕过检查。
- 结果数字不同：先核对输入版本与配置；时间戳和会话摘要可能随运行改变，应比较结构和检查结果，不要求整个JSON逐字一致。
- 意外出现真实材料、模型密钥或联网采集要求：停止该步骤，不在公开反馈中附原文、密钥或身份信息。

## 4. 请使用者交回这些内容

复制以下字段到自己的记录中；未发生或不知道就如实写，不能由助手预填成功。

| 字段 | 使用者填写 |
| --- | --- |
| 使用者代号、日期、是否独立首次操作 | 待填（不要求公开真实姓名） |
| 冻结提交、实际提交、工作树状态 | 待填 |
| 系统、Python版本；F另填浏览器版本 | 待填 |
| A—F各项状态、命令、输出文件位置 | 待填；未做项写未做 |
| 首次失败原始报错、卡住步骤 | 待填；没有失败写未观察到 |
| 李泽豪提供了什么帮助、之后改了什么 | 待填；记录是否有提示，不能全部算独立 |
| 重试版本与结果、尚未解释的问题 | 待填；不覆盖首次记录 |
| 对结果的解释 | 用自己的话说明一次异常、一个分母或一次确认来源 |

最小回交是A的`report.json`、命令/版本/首次输出及本人解释；B—F按实际完成情况另附报告或合成答卷。由李泽豪安排真实使用者并处理反馈，助手不发邀请、不代写其解释。不要上传患者原文或整份私人下载目录。

验收仍为“待他人验收”。T01个人修改、T03独立评分、T05手算、T06独立归因与T08临床准入分别记账；本包不能证明已达到某公司的社招级别。
