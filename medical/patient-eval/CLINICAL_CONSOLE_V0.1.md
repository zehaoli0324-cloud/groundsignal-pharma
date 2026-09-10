# GroundSignal 独立审核工作台 v0.1

这是现有患者审核流程的本地前端，不是患者问诊入口，不是临床签名或准入服务。

## 使用

下载同目录 `console-v0.1.html`，在桌面浏览器打开，无需服务器或联网。

1. 点击“体验合成示例”熟悉界面，或导入已有 `candidate-review/v0.1` 来源包。导入来源时清空所有已有评审意见，保留原始材料；不预填 AI 或另一位评审的结论。
2. 填写自己的评审编号。在“审核范围”中选择全部候选或昨夜冻结的12个开发编号。该选项仅过滤界面，不修改病例冻结、资料包标识或导出行数；没有匹配编号时显示空队列。
3. 逐条填写事实、证据字符片段、隐私与完整性、0/1/2分规则。原文只读。未判断请保持未审阅，不能以未知代替否定。
4. 随时“保存未完成草稿”，以后通过“继续自己的草稿”载入同编号文件；正式交回前使用“导出审核草稿”进行浏览器预检查。浏览器不确认文件下载成功，请检查下载目录。
5. 如填写了未来评分机会或临床背景声明，另在“准入交接”导出交接文件。审核与交接是两份文件，须分别保管、恢复。没有自动保存；关闭页前自行确认两份文件都已下载。
6. 两位独立评审分别完成后，由协调者导入两份审核文件查看逐字段差异。不同编号不证明是不同自然人；同意率、医生资质和临床正确性不由前端推断。协调意见不会自动合并原始审核。

## 与现有流程衔接

审核草稿继续使用原有格式和验证器，不修改 `candidate_review.py`：

```bash
python -m scripts.patient_eval.candidate_review validate-review --original ORIGINAL.json --review REVIEW_A.json --out medical/patient-eval/local/review-a-validation.json
python -m scripts.patient_eval.candidate_review compare-reviews --original ORIGINAL.json --review-a REVIEW_A.json --review-b REVIEW_B.json --out medical/patient-eval/local/review-comparison.json
python -m scripts.patient_eval.clinical_console validate-handoff --original ORIGINAL.json --review REVIEW_A.json --handoff HANDOFF_A.json
```

将大写路径替换为受控本地文件路径。原有验证器拒绝覆盖结果，请每次使用新的输出路径。浏览器的字段比较是便于审阅的字面差异，不替代官方比较报告，也不输出语义一致率。

需要将原始资料直接装入独立离线页面时：

```bash
python -m scripts.patient_eval.clinical_console render --original ORIGINAL.json --out medical/patient-eval/local/console-reviewer-a.html
```

来源含患者文本时，生成器强制输出到被 Git 忽略的 `medical/patient-eval/local/`。生成器会运行官方合同校验、清空既有评审意见，但不能认证自述临床身份或批准病例。

## 第一版具备什么

- 病例队列、范围筛选、按当前导入材料计算的进度；不把夜间聚合数字伪装成实时审核结果。
- 原文、患者主体、时间、否定、纠正、披露方式的逐字段审核。
- 按 Unicode 字符定位的证据片段编辑；不会在载入时修正错误的证据文本。
- 隐私逐轮确认及补充敏感片段；不提供一键全选通过。
- 0/1/2分锚点、严重错误定义、未来机会计划。
- 各自初评的导入导出、协调者逐字段分歧和备注。
- 非授权交接记录及本地验证器。所有临床准入仍为 false，S6 仍为 BLOCKED。

## 明确限制

- **无登录、无后端权限、无数字签名。** 用户可自行进入协调页或更改自述编号；不能宣称技术上强制了双人独立性。协调者必须分别分发材料，收齐初评之前不得交叉共享结果。
- **审核完成不等于批准。** 本版本无正式电子准入收据；只收集需授权负责人核验的材料。临床安全标准仍需合适临床人员裁决。
- **计划不等于观测。** 新交接文件中的机会计划不回填 v0.4 的57条运行机会。未生成真实会话，触发事件和响应规划不冒充已经发生的轮次。
- **无公网部署。** 页面无网络请求、外部资源、浏览器持久存储。内容安全策略禁止连接，但操作系统、浏览器扩展和人工转发等风险不在本工具控制范围内。
- **浏览器不是权威验证器。** 导入的摘要格式检查不是来源认证；最终须将结果与受控原件交给原有 Python 验证器。摘要绑定也不认证审核者身份。
- **未做浏览器端到端操作验收。** 已进行 Python/Node 合成数据测试、生成内容与资源检查；实际浏览器的下载、键盘交互和视觉体验尚需人工试用。
- 若浏览器支持 WebMCP（Web Model Context Protocol，网页向智能体提供结构化操作的接口），仅暴露聚合进度读取，不返回患者文本或允许自动填写审核。此可选接口未在受支持浏览器中验证。

## 验证入口

开发测试需要 Python 3.11+ 和 Node.js 18+；普通评审者打开单文件页面无需安装它们。

```bash
python -m unittest tests.patient_eval.test_clinical_console -v
python -m unittest discover -s tests/patient_eval -q
```

首轮未调用真实平台、付费模型或患者执行器。下一步是人工试用工作台、两人独立审核、临床裁决与正式准入决定；随后才能重新运行 N1–N5。
