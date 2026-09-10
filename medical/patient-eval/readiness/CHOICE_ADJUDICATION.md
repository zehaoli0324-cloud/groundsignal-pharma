# 两份点选答卷的分歧裁决（R13）

本轮完成研究人员使用的裁决处理程序。它识别已有点选答卷，分别列出缺答、待确认、已确认一致和已确认分歧；接收带理由的裁决后，输出可由现有审阅校验器读取的review.json。裁决点选页面尚未搭建。

## 目前可以做什么

- 保留原始两份答卷及其版本、操作记录和身份声明，不用最终意见覆盖初评。
- 只有两边都确认过的分歧允许裁决；缺答和旧答卷缺失确认记录需回到审阅者补充，不能代填。
- 已确认一致项沿用共同意见；尚未处理的分歧保留pending（未完成）。同为“无法判断”也不转换为“通过”。
- 每项裁决记录最终选项、理由和协调者的自报身份，并绑定两份输入和队列的内容摘要。换过答卷后须重新生成队列，旧裁决会被拒绝。
- 派生review.json保留事实配置与评分标准的缺口。支持原文语义不等于事实已纳入，适合考察不等于已有评分规则，裁决也不产生模型回答的评分记录。

原compare-choices命令继续用于比较选项值；本工具额外考虑是否确认，未改变原来的比较输出或四项默认勾选。

## 合成复现

在仓库根目录执行，使用Python现有环境，无新增依赖：

```bash
python -m scripts.patient_eval.choice_adjudication \
  --original medical/patient-eval/readiness/round-13-adjudication/example/original.json \
  --left medical/patient-eval/readiness/round-13-adjudication/example/left.json \
  --right medical/patient-eval/readiness/round-13-adjudication/example/right.json \
  --out /tmp/groundsignal-r13-queue

python -m scripts.patient_eval.choice_adjudication \
  --original medical/patient-eval/readiness/round-13-adjudication/example/original.json \
  --left medical/patient-eval/readiness/round-13-adjudication/example/left.json \
  --right medical/patient-eval/readiness/round-13-adjudication/example/right.json \
  --decisions medical/patient-eval/readiness/round-13-adjudication/example/decisions.json \
  --out /tmp/groundsignal-r13-resolved
```

输出目录必须不存在。第一步生成queue.json与空的decisions-template.json；示例decisions.json已由作者填入一个合成裁决，不能解释为真实人类意见。自己的裁决文件须填写adjudicator_id，并在decisions中列出row_id、answer、reason。row_id来自队列，answer沿用相应板块的选项值，reason写裁决理由。当前需要研究人员编辑文件；后续点选页面会代为生成这些字段。

示例预期：裁决前3项已确认一致、1项分歧、8项缺答；裁决后3项沿用共同意见、1项裁决、8项未解决。review.json通过现有候选审阅结构校验，仍不包含可运行的事实配置或已完成评分规则。

result.json保留逐项原选项、确认状态、最终选项及裁决理由；review.json只供后续审阅工具读取，不能导入点选界面冒充第三份独立答卷。初评比较必须继续使用原来的两份文件，不能用裁决结果计算初评一致性。输出包含原资料副本；使用真实输入时应保存在原定私有工作范围，公开示例只含虚构日期记录。

## 验证与限制

新增9项测试，连同答卷校验、旧版兼容与确认记录共23项通过。覆盖未确认同选项、旧记录未知、部分裁决、旧裁决拒绝、缺答不可裁决、来源改动、重复裁决、非法选项、禁止准入升级及保存防覆盖。合成完整运行结果已保存在本目录。

确认记录和人员身份均为自报，不能证明阅读、独立性或临床资质。临床12条裁决并未完成；真实规则映射仍0/57，真实病例执行和外部模型调用仍为0。

## 还需要搭建什么

| 优先顺序 | 工程缺口 | 已有基础 | 完成标准 |
| --- | --- | --- | --- |
| 1 | 裁决点选页面 | 本轮队列、严格校验、回写程序 | 研究人员导入两份答卷、逐项点选并导出；缺答与待确认单独显示，原始意见可回看 |
| 2 | 真实动态病例适配 | 合成事件映射、批量导入与恢复 | 接收已准入病例版本、明确披露规则与回答边界；提前结束和异常不误触发评分 |
| 3 | 规则映射工作界面 | 57条私有工作清单、合成边界校验 | 展示原文、候选触发与待评回答；无依据留空，人工确认后保留证据与版本 |
| 4 | 真实对照运行记录连接 | 原流程/状态干预配置、调度与故障记录 | 固定病例、模型和评分版本；运行结果、耗时、调用量、缺失用量与实际费用可追溯 |
| 5 | 集成分支进入主分支的交付 | 第19、20号已合并到审阅界面分支 | 单独审查前置改动、主分支差异及运行说明，避免扩大未审查范围 |

浏览器导出/关闭重开/恢复、他人复现、个人独立维护、规则语义和临床裁决属于验收或人工证据缺口，不能靠继续增加模块解决。现阶段不需要另建庞大平台或增加病例数量。
