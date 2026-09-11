# A1第五批：动态草稿、状态与页面边界

2026-09-11，输入远端 `331e12fccb0db7fec9cf74441d4b9e7e6762c23f`，本地 `6843f91`，共同树 `243852b1e1555b991bd2ed4ac29f70976874258a`。本批新增1项OPEN，累计16项未修复；生产实现没有修改。

8项新检查中6项符合预期、2项失败，两个反例归并为A1-016。另有14项既有动态草稿/裁决页面文件互通测试通过。原始退出码分别2和0；不将两组混成项目通过率。

## A1-016：合成披露器先改状态后报错

缺少opening.evidence_fragments时，open已把状态由NOT_OPENED改为ACTIVE、记录初始事实披露，再抛KeyError。缺少event.response.evidence_fragments时，confirm已记录事实和事件触发，再抛KeyError。后续重试分别被“只能打开一次”或“事件已触发”拒绝。

根因是构造器没有预先验证完整输出结构，操作又在准备返回内容前修改state/disclosed/fired/trace。修复应先验证与构建输出，再统一提交状态，异常时保持原快照。本问题为P2，仅影响合成合同执行器；不能扩大为真实患者执行器出错，也没有发生真实披露。其模式与A1-001类似，但不是同一实现。

## 本轮确认的边界与限度

- 动态草稿精确重算来源审阅、阻断清单与结构选择；病例保持BLOCKED，具体评分回合仍UNRESOLVED，不自动开启语言触发或评分。
- 静态准备报告将未运行、未映射和未评分分开；只有合成fixture进入小型执行器，真实来源模式被拒绝。对完整草稿的篡改在精确重算时被拒绝。
- 公开报告不复制原文片段和评分草稿；既有合成哨兵测试保留。没有加载真实患者文件。
- 私有输出路径helper在静态状态下拒绝目录外路径和指向目录外的父级链接。测试把路径根设为临时合成目录，不修改真实路径/认证常量；没有验证检查之后的并发链接替换，不能据此宣布不存在路径竞态。
- 两个审阅页面生成器对含关闭script标签、脚本及图片事件属性的标记完成转义，JSON解析后原样恢复；原始标记未形成页面标签。这是字符串与解析器验证，没有打开浏览器，也不能代替完整的脚本注入审查。
- 裁决页将原文通过textContent呈现，嵌入JSON转义，明确禁止网络连接；既有4项页面测试在Node中验证保存/恢复文件与后端接纳，缺失和未确认项目不自动补齐。

裁决页包含原文，生成的正式文件仍须留在原私有范围。四项默认勾选未修改。本轮没有绕过此前浏览器访问限制，也没有发布网站。

## 证据与复现

- [首次观察](first-run/observations.json)、[首次命令与摘要](first-run/run-manifest.json)、[原始退出输出](first-execution.txt)。
- [14项既有测试](existing-tests.txt)及[运行清单](existing-tests-manifest.json)。
- [覆盖矩阵](coverage.json)、[累计发现](../findings.json)、[总进度](../PROGRESS.md)。

输出须是新目录；审计基线预期退出2：

```bash
python scripts/audit_dynamic_boundaries.py --out /tmp/groundsignal-a1-dynamic-new
python -m unittest tests.patient_eval.test_dynamic_case_offline tests.patient_eval.test_adjudication_page -v
```

目前仍是A1逐模块审查，A2修复与A3固定版本集中复测尚未开始。下一批优先底层谱系/重复判定算法、其余共享脚本与凭据/工作流检查，再依据覆盖矩阵补接口、页面和路径竞态。所有真实准入、人工临床判断和个人能力验收继续独立保留。模型调用、真实患者读取/执行、真实回执及训练行创建0；定时任务保持暂停，main不变，PR23继续草稿。
