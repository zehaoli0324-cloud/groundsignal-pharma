# 患者评测开发与 S5 历史冻结检查的衔接

核对日期：2026-09-09。核对主线：`e1843c310530472e635d96d054d9bb0baad2d0b2`。

本次修复的是持续集成（Continuous Integration，代码变更后的自动检查）错误地重新生成历史冻结收据的问题。它使已有冻结证据能够随着主线前进继续被正确验证，没有新建冻结、提高案例可信等级或开放训练数据。

## 1. 原检查为什么失败

[先前失败运行](https://github.com/zehaoli0324-cloud/groundsignal-pharma/actions/runs/34301603091)对应工作流的“已有收据”分支执行了 `materialize_s5_v091_freeze_receipt.py`，试图重新生成 `cdc89298693aa9c5222f15ed9bd62a57e140fbc6` 的收据。

这个生成器要求冻结提交必须是当时 `origin/main` 的最新提交。这是创建新冻结时的必要约束。主线前进之后，旧冻结仍然属于合法历史，但不再是最新提交，于是生成器正确返回：

```text
receipt_created: false
FREEZE_COMMIT_NOT_CANONICAL_MAIN_TIP
```

本轮在补齐完整 Git 历史后重新执行原命令，重现了上述唯一错误。患者评测代码没有改变冻结字节；“重新生成收据”的操作选错了。

## 2. 使用已经发布的历史对象

新增 `scripts/verify_s5_v091_historical_receipt.py`，只验证已有收据。

| 已有对象 | 固定身份与核对依据 |
|---|---|
| 冻结提交 | `cdc89298693aa9c5222f15ed9bd62a57e140fbc6`，已有第 7 号合并请求的冻结提交 |
| 收据发布提交 | `31c94deded224d54a7e2f0e977ebe458e9b6c16e`，已有收据发布对象，其唯一父提交就是上面的冻结提交 |
| 收据 Git 文件对象摘要 | `9fb59ab6205b8b37a1574988d386980c953a0839`，直接读取该发布提交中的原收据字节计算，不从当前案例的自述取得 |

核对来源为仓库已有 [收据发布提交](https://github.com/zehaoli0324-cloud/groundsignal-pharma/commit/31c94deded224d54a7e2f0e977ebe458e9b6c16e)及其 [父冻结提交](https://github.com/zehaoli0324-cloud/groundsignal-pharma/commit/cdc89298693aa9c5222f15ed9bd62a57e140fbc6)。新验证器使用这些已存在的身份，不生成新审批引用。

验证器要求：

1. 完整 Git 历史可用；浅克隆或缺少历史对象明确失败，不能把“查不到”当作“已通过”。
2. 收据发布提交同时属于当前分支和 `origin/main` 的祖先；不能仅在任意分支放置一个同名文件。
3. 发布提交的父提交、收据文件摘要以及当前收据字节完全匹配既有对象；发布时尚无下一轮全新评测资产。
4. 调用**未修改**的冻结收据验证函数，继续检查冻结树、24 项实现文件、8 项控制面文件、冻结前收据不存在及各项发布限制。

工作流把原来的“重新生成并比较”替换成上述只读验证。新建冻结时仍由原生成器要求“当前主线最新提交”，不能通过这个新入口创建或授权冻结。

## 3. 本轮验证结果

| 检查 | 本地实测结果 |
|---|---|
| 新增历史收据测试 | 14 项通过，另含两个非祖先子用例；覆盖主线前进、浅历史、缺对象、错误发布父提交、收据字节漂移、冻结树和文件漂移、擅自提高可信等级 |
| 当前真实仓库历史收据验证 | 通过 |
| 原冻结生成器对旧冻结再次生成 | 按预期拒绝，未创建收据 |
| 原下一轮作者准入检查 | 输出与 `next-fresh-admission-after-freeze-v0.10.json` 逐字节相同 |
| 既有冻结准备、控制面准备及已暴露回归 | 7 个脚本全部成功，输出与 7 份既有固定结果逐字节相同 |

可以从仓库根目录复现核心检查：

```bash
python scripts/test_s5_v091_historical_receipt.py
python scripts/verify_s5_v091_historical_receipt.py --out /tmp/s5-historical-receipt-check.json
python scripts/check_s5_v10_fresh_admission.py --out /tmp/s5-authoring-admission.json
cmp /tmp/s5-authoring-admission.json medical/stage-evals/S5/next-fresh-admission-after-freeze-v0.10.json
```

远端自动检查以本次实际推送提交的工作流结果为准。上述本地检查不表示已完成新患者场景的临床审核。

## 4. 哪些边界继续有效

- `gold_approved=false`：案例没有获得专家确认的标准答案资格。
- `s6_automatic_trust=BLOCKED`：不会因为代码检查成功而允许第六阶段自动信任或导出训练数据。
- 已有下一轮“可开始创作”的准入结果不等于“新鲜测试通过”，更不等于临床产品上线资格。
- 本轮新增患者场景属于公开的合成开发材料；不能重命名或修改字段后当作未暴露测试。
- 原冻结收据、8 项冻结控制面脚本、固定清单、既有首次观测结果保持原字节。

本次代码合并应依据开发检查、历史证据验证及代码审查结果处理；案例纳入正式独立测试、专家标准确认及训练数据开放继续遵循原来的各自流程。
