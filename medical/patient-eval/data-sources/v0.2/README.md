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

### 生成公开阻断队列

完成格式适配和官方 `validate-review` 校验后，可以从私有原始包与审阅稿生成只含候选编号、条目编号、枚举阻断类型和聚合分母的公开队列：

```bash
python -m scripts.patient_eval.candidate_blockers \
  --original medical/patient-eval/local/<trusted-original>.json \
  --review medical/patient-eval/local/<validated-review>.json \
  --source-review medical/patient-eval/local/<submitted-review>.json \
  --expected-source-sha256 <sha256> \
  --out medical/patient-eval/local/<public-projection>.json
```

生成器会先重新调用现有官方合同校验器，并核对提交文件的 SHA-256；输入不一致或输出文件已存在时直接拒绝。公开投影不会复制患者文字、来源对话编号、证据片段、审阅理由、审阅者身份或本地路径。`candidate_selection=READY` 只表示可以进入开发候选选择，`dynamic_authoring=READY` 只表示可以编写受控开发脚本；两者都不等于临床可运行。临床关键规则仍须合适人员裁决，`clinical_runnable`、Clinical Gold 和 S6 自动信任保持阻断。

阻断队列通过后，可以冻结一个不读取模型回答的结构多样性开发清单：

```bash
python -m scripts.patient_eval.candidate_selection \
  --original medical/patient-eval/local/<trusted-original>.json \
  --review medical/patient-eval/local/<validated-review>.json \
  --source-review medical/patient-eval/local/<submitted-review>.json \
  --expected-source-sha256 <sha256> \
  --blockers medical/patient-eval/local/<exact-blocker-projection>.json \
  --count 12 \
  --out medical/patient-eval/local/<selection-projection>.json
```

选择器要求阻断队列能由私有审阅稿逐字节等价重建，并只接收至少含一条初始事实和一条问到才披露或定时披露事实的候选。排序依次扩大结构标签覆盖、最大化已选病例间的归一化距离、提高结构复杂度，再用绑定候选包和编号的 SHA-256 打破平局。相似度分组只用于避免同组选入多例；未经校准的词面相似组不能被包装成医学病例家族。

### 生成私有动态病例草稿

冻结清单通过后，使用 `dynamic_case_drafts` 同时生成受控本地草稿和不含患者文字的公开审计：

```bash
python -m scripts.patient_eval.dynamic_case_drafts \
  --original medical/patient-eval/local/<trusted-original>.json \
  --review medical/patient-eval/local/<validated-review>.json \
  --source-review medical/patient-eval/local/<submitted-review>.json \
  --expected-source-sha256 <sha256> \
  --blockers medical/patient-eval/data-sources/v0.2/candidate-blockers-public-v0.1.json \
  --selection medical/patient-eval/data-sources/v0.2/candidate-development-selection-public-v0.1.json \
  --private-out medical/patient-eval/local/<dynamic-case-drafts>.json \
  --public-out medical/patient-eval/data-sources/v0.2/<text-free-audit>.json
```

生成器重新执行官方审阅合同、阻断队列和冻结清单的精确重建，任一输入发生漂移都会拒绝。患者证据片段、自然语言触发草稿、评分锚点和严重错误定义只进入忽略目录中的私有包；公开报告仅保留编号、枚举状态和计数。

当前有限状态机只接收操作员确认的 `OPERATOR_OPEN`、`OPERATOR_CONFIRM:<event>` 和 `OPERATOR_STOP`。未裁决的问询示例或定时条件不会被当作自动匹配规则；问到才披露和定时披露事实不能进入 opening，`never` 事实没有可见转移。评分触发回合、响应回合和结构化截止均保持 `UNRESOLVED`，而不是根据自由文本猜测。

[v0.4 状态机合同](../../schemas/dynamic-case-state-machine-v0.4.json)及[公开聚合审计](dynamic-case-draft-audit-public-v0.1.json)只适用于已暴露开发材料。草稿还需自然语言连贯性复核、触发语义复核、评分机会映射、停止策略、双人独立审阅和合适人员的临床规则裁决；这些完成前 `clinical_runnable`、Clinical Gold、动态场景就绪和 S6 自动信任均保持阻断。

## 下一步的交付条件

两名评审完成原始意见后，先解决错位、否定范围、主体时间、披露与评分分歧，保留初评和裁决版本。随后挑选适合的小批病例，另行编写并测试动态脚本，再进行小荷和通用模型的同条件采集。

50 段来源材料目前不是 50 道正式测试题。代码通过和表格填完均不自动获得临床标准答案、正式 S5（第五阶段：案例准入）资格或模型训练出口。解释与练习见 [算法与工程学习手册](../../../../docs/learning/groundsignal-learning-guide.html)。
