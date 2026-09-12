# 本批验证范围（2026-09-12）

基线：`82e0384c555ac6f3b7bc5413e7e3726be975ab85`。本文件记录本地实际执行结果，不代表远端持续集成已通过。

| 检查 | 结果 | 边界 |
|---|---|---|
| 题卡校验 | 12张、6个家族；每对仅追加首问无关文字 | 全部合成开发题，非真实患者病例 |
| 新增后端测试 | 22项通过 | 版本/计划错配、重复运行、披露错误、更正更新、阶段边界、评分引用、未知状态、分歧 |
| 现有严格导入回归 | 10项通过 | 新增模块复用的导入边界 |
| 患者评测目录测试 | 397项通过 | `tests/patient_eval`，不是整个仓库审计 |
| 命令行完整演练 | 1条合成会话导入成功；11条逐轮判据均未评 | 原始回答为测试夹具，不是蚂蚁或小荷实测 |
| 页面事件检查 | 通过 | 最小文档对象模型模拟：更正、探查、导出→Python导入、空白评审导出、未提交与已提交超时区分 |
| 实际浏览器渲染与手工交互 | 未完成 | 运行环境没有浏览器；下载浏览器超时，未将模拟测试当作真实浏览器测试 |
| 临床评审、实际应用运行、第三方交接复现 | 均未完成 | 需要首轮实际采集和独立复核 |

复现命令：

```bash
python -m scripts.patient_eval.app_pilot validate-suite
python -m unittest tests.patient_eval.test_app_pilot tests.patient_eval.test_import_batch -v
python -m unittest discover -s tests/patient_eval -q
node tests/patient_eval/app_pilot_pages.cjs
```

页面测试只需Node.js 20及以上，无外部依赖；脚本使用最小文档对象模型模拟，不替代浏览器。合成导出放在已被Git忽略的`medical/patient-eval/local/app-ui-test`。测试失败时修复的是本批采集/评分工程，不会改动原始病例或把临床未知改为通过。

生成器入口为`python -m scripts.build_app_pilot_suite`，同步题卡、套件、两个兼容采集入口和计划。公开入口内仅含合成题卡，没有真实应用回答、账户凭证或患者原文。完整病例难度、评分者一致性和实际产品表现仍待实测。
