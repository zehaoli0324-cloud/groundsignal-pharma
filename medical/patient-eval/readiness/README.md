# 最小合成工程交接包

本包让另一人在干净环境中复现：一次正常运行、几类失败、中断保留与独立重跑。所有响应由本地脚本产生，不调用真实模型，不需要密钥或患者材料。

## 运行

需要 Git 和 Python 3.11或更新版本；本演练使用Python标准库，无需安装第三方依赖。Windows若没有 `python` 命令，可尝试 `py -3` 并确认版本。

```bash
git clone --branch work/social-hire-readiness-20260910 https://github.com/zehaoli0324-cloud/groundsignal-pharma.git groundsignal-readiness
cd groundsignal-readiness
python --version
git rev-parse HEAD
python -m scripts.patient_eval.readiness_drill --out medical/patient-eval/local/my-first-readiness-drill
```

先记录实际提交号。需复现首轮冻结版本时，使用 `docs/handoffs/social-hire-readiness-ledger.md` 的“R0实现提交”或代码所在提交，不把分支未来更新当成同一版本。

正常结果：终端输出 `passed=true`、`checks_passed=9`、`checks_total=9`，目录内有 `report.json`。若已有同名输出目录，换一个新目录名；不要删除旧结果来冒充首次成功。

## 怎样读结果

| 结果 | 含义 |
| --- | --- |
| `normal_sessions_persisted` | 两种流程的合成会话都已保存，不能据此判断模型质量 |
| `timeout_classified` / `empty_classified` | 超时、空回答分别被记为被测接口侧失败 |
| `invalid_adapter_classified` | 采集适配器返回格式错误，属于测量无效 |
| `interruption_preserves_checkpoint` | 计划2条会话，故意中断后保留已完成的1条 |
| `same_config_directory_reuse_rejected` / `changed_config_directory_reuse_rejected` | 无论配置相同或改变，现有目录都在调用前被拒绝复用；它还不是按哈希核验的续跑功能 |
| `new_directory_replay` | 新目录重新执行全部任务，保留旧结果；是独立重跑，不是跳过已完成会话的断点续跑 |
| `resume_limitation_explicit` | 当前运行器明确声明不支持断点续跑 |

意外中断后，旧清单仍可能显示 `running`，不能据此认定任务仍活着。这个缺口已记录，后续应单独设计恢复与存活状态处理。

`external_model_calls=0`、`model_quality_assessed=false`。工程检查通过不代表质量、临床安全或求职能力验收通过。文件时间戳与检查点摘要会随运行变化，不应逐字比较整份报告来判断成功。

## 常见问题

- `No module named scripts`：先进入包含 `scripts` 目录的仓库根目录。
- `FileExistsError`：输出目录已存在，使用新的输出名；演练内部故意制造的复用失败会被捕获，不应中止正常演练。
- 未知命令或找不到 `readiness_drill`：确认检出的是上述分支及包含首轮代码的提交。
- 任何检查为false或出现意外异常：保留原目录与终端报错，记录Python版本和提交号，交给李泽豪排查。

另一位使用者应交回：提交号、Python版本、执行命令、`report.json`、卡住的步骤及李泽豪如何解决。未完成实际复现前，状态保持“待他人验收”。

## 评分规则草稿

`correction-opportunity-v0.1.json` 给出一条“明确纠正后使用新信息”的合成规则，包含触发、响应、截止、分档示例和未评状态。它尚未经过独立双人试评分，也没有接入自动自然语言评分器，更没有回填真实来源的57条机会。


## R1：三条规则包

现已补齐纠正、未知、提问三条合成规则。阅读 [规则审阅说明](SCORING_RULES_REVIEW.md)，运行 `python -m scripts.patient_eval.readiness_rules` 核验结构。结果记录在 `round-1-rule-validation.json`。三条均为待人工审阅草稿，不能称为真实57条机会已映射。

## R2：只读恢复前检查

阅读 [恢复合同](RECOVERY_CONTRACT.md)，运行 `python -m scripts.patient_eval.recovery --drill-out medical/patient-eval/local/recovery-first`。本轮能指出输入、配置、调度、检查点或目录残留的不一致，不修改原结果。即使内部一致性通过，仍明确禁止续跑：旧格式缺少可信会话摘要、排他锁和恢复执行器。不会改变上述R0演练的历史含义。

## R3：新格式最小显式续跑

运行 `python -m scripts.patient_eval.resumable_drill --out medical/patient-eval/local/resume-first`。新v0.3格式绑定输入、配置、调度、相关代码摘要和每条会话文件摘要，并使用排他锁。固定合成演练8/8通过：中断保存1/2，恢复只调用剩余会话，旧会话字节不变。未落盘请求仍可能重放，不能声称绝对只调用一次；真实平台和真实病例均未验证。
