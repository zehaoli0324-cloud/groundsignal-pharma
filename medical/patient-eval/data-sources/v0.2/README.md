# 真实对话候选审阅 v0.2

**把已取得的 50 段 ReMeDi 对话整理成可复核材料，先解决数据质量，再派生测试病例。** 当前新增的是审阅准备工具，病例、隐私和医学判断均待人工完成。

来源与下载沿用 [v0.1 固定版本](../v0.1/README.md)。本文档是数据接入流程 v0.2；审阅文件另用 `candidate-review/v0.1` 协议，不能与模型回答的 `patient-review/v0.3` 评分包混用。

## 本轮做了什么

| 处理 | 算法的作用 | 工程约束 |
|---|---|---|
| 残余身份信息提示 | 用规则定位联系方式、姓名及地址等线索 | 保留原文字符位置；规则未命中不能证明已经脱敏 |
| 近重复检查 | 对患者发言提取连续三个字符的片段，算 Jaccard 交并比 | 只比较这 50 段，排除医生模板；阈值 0.85 未经校准，不证明同一患者或独立测试 |
| 事实提案 | 保留患者的上游标注及否定、未知、纠正线索 | 医生回复不当患者事实；精确文字位置不等于医学正确 |
| 披露草稿 | 分开最初连续患者消息与后续消息 | 后续才出现的信息不得写成初始可见事实；不自动导出动态患者 |
| 独立审阅 | 为两人分别生成空白事实、完整性及评分规则材料 | 校验原文、候选编号、证据范围；同一审阅者不能充作两人 |
| 分歧整理 | 比较双方已作决定的字段 | 未审阅不计一致；保留分母和分歧，程序不代替医学裁决 |

原文、来源编号、审阅者、修改映射和工作页面只存本地忽略目录。公共仓库只保存代码、方法和[聚合审计](candidate-review-audit.json)。SHA-256（Secure Hash Algorithm 256-bit，256 位安全散列）确认文件身份，不能认证事实或审核者。

## 实际观察

50 段候选包含 642 条患者消息、765 条患者标注提案：745 条文字范围匹配、20 条错位；80 条位于初始信息范围，685 条在后续消息。160 条上游标签属于询问，不能直接当成已经确认的病情。

现有有限规则抽取器产生 1 条观察记录，并记录 842 个未解析句段。**这暴露了规则覆盖不足；没有独立人工真值，不能把它换算为抽取错误率或召回率。** 本轮没有据此修改抽取规则后再把这批数据称为独立测试。

源数据的范围末端是包含式，审阅证据使用 Python Unicode 字符位置的半开区间 `[start, end)`。错位不会通过全文搜索偷偷修复，必须由人工引用实际原文位置。原始连续同角色发言完整保留。

## 怎么运行

已有 v0.1 下载结果时，在仓库根目录运行：

```bash
python -m scripts.patient_eval.candidate_review prepare \
  --source-dir medical/patient-eval/local/source-intake/remedi-base \
  --out medical/patient-eval/local/candidate-review/remedi-v02
```

命令重新核对源数据、许可和原来的确定性 50 段候选清单。输出目录必须不存在，并位于 `medical/patient-eval/local/` 内。每次审阅另开目录，原始包保留不改。

两名评审分别打开各自的本地 HTML，填写真实审阅者编号，逐例检查隐私和完整性，再编写事实与病例评分规则。页面只在内存中编辑，关闭前须下载审阅 JSON（JavaScript Object Notation，结构化数据文本）；下载不会自动表示校验通过。不要先互看对方的意见。

校验和分歧比较的命令如下；将占位文件名替换为本地实际文件：

```bash
python -m scripts.patient_eval.candidate_review validate-review \
  --original medical/patient-eval/local/candidate-review/remedi-v02/original.json \
  --review medical/patient-eval/local/reviewer-a-completed.json \
  --out medical/patient-eval/local/reviewer-a-validation.json

python -m scripts.patient_eval.candidate_review compare-reviews \
  --original medical/patient-eval/local/candidate-review/remedi-v02/original.json \
  --review-a medical/patient-eval/local/reviewer-a-completed.json \
  --review-b medical/patient-eval/local/reviewer-b-completed.json \
  --out medical/patient-eval/local/candidate-review-disagreements.json
```

候选纳入事实须注明主体、时间、肯定/否定/未知/冲突、证据和披露方式；问到才披露的事实还需问询条件。评分规则须写病例特定的 0/1/2 分锚点、适用机会和截止；关键风险项单列严重错误。历史医生回复不能直接成为满分答案。

这轮比较的是**来源与病例编写意见的一致性**。对模型回答的加权科恩一致性系数仍由原 [v0.3 评分流程](../../REVIEW_V0.3.md)计算，两者的评审对象和分母不同。

报告另外列出双方已编写的事实证据、披露条件、评分锚点及隐私片段差异。它们需要人工裁决，不把文字不同直接解释为医学分歧。当前模板固定上游提案；发现漏标事实先记在完整性理由中，后续单独编写，不能将提案数量视为完整真值分母。

## 下一步的交付条件

两名评审完成原始意见后，先解决错位、否定范围、主体时间、披露与评分分歧，保留初评和裁决版本。随后挑选适合的小批病例，另行编写并测试动态脚本，再进行小荷和通用模型的同条件采集。

50 段来源材料目前不是 50 道正式测试题。代码通过和表格填完均不自动获得临床标准答案、正式 S5（第五阶段：案例准入）资格或模型训练出口。解释与练习见 [算法与工程学习手册](../../../../docs/learning/groundsignal-learning-guide.html)。
