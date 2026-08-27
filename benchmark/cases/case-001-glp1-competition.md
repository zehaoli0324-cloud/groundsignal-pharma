# Case 001 — GLP-1 新资产竞争分析

```yaml
case_id: case-001-glp1-competition
user_role: 药企战略 / Competitive Intelligence
scenario: 某公司新加入一个 GLP-1/GIP 双激动剂减重资产（III 期阶段），希望判断竞争格局
evidence_snapshot: T2（III 期 topline positive）
```

## 用户任务

> 一家 GLP-1 创新药公司准备判断其双激动剂减重资产的竞争格局。基于现有管线、靶点、适应症、临床阶段和竞争证据，这个资产真正和哪些药物构成竞争？应该优先监控谁？

## 证据快照（供模型回答时引用）

- Asset X：GLP-1R/GIPR 双激动剂，III 期减重试验达到主要终点（体重降幅 vs 安慰剂显著）
- [[替尔泊肽]]：GLP-1R/GIPR 双激动剂，已上市（Mounjaro 2022-05 糖尿病 / Zepbound 2023-11-08 减重，FDA）
- [[司美格鲁肽]]：GLP-1R 单激动剂，已上市（Ozempic 2017 / Wegovy 2021-06 减重，FDA；中国减重 2024-06 获批）
- [[玛仕度肽]]：GLP-1R/GCGR 双激动剂，III 期（中国 NDA 已递交，未获批）
- 靶点节点：[[GLP-1R]] · [[GIPR]] · [[GCGR]]

## 问题（四层派生）

### L1 事实题（Fact / Temporal Grounding）

**Q1. 基于当前证据，Asset X 处于什么临床阶段？**

gold：III 期已完成、主要终点阳性；**未获批、未提交 NDA（在给定快照下）**。
不可接受：把"III 期阳性"写成"已批准上市"（OVERCLAIM）。
测试：factuality、temporal grounding、overclaim。

### L2 关系题（Relation Reasoning）

**Q2. Asset X 与司美格鲁肽是否构成直接竞争？**

gold：**部分竞争，但不是完全对等**。共享适应症（肥胖）与 GLP-1R 靶点，但机制不同（双激动 vs 单激动）、阶段不同（III 期 vs 已上市）、临床证据成熟度不同。直接竞争判定需要叠加：靶点 + 适应症 + modality + 阶段 + 定位。
不可接受："都做肥胖，所以直接竞争"（RELATION_OVERSIMPLIFY）；或"靶点不同完全不竞争"。
测试：relation reasoning、shared target ≠ direct competitor 纪律。

**Q3. Asset X 与替尔泊肽的关系和与司美格鲁肽的关系有什么本质区别？**

gold：Asset X 与替尔泊肽**共享双靶点机制**（GLP-1R/GIPR），是最接近的机制邻位（mechanistic neighbor），竞争关系比司美格鲁肽更直接；与司美格鲁肽共享 GLP-1R 但不共享 GIPR。机制邻近 ≠ 直接竞争，但提示更高的临床头对头风险。
测试：mechanism-level reasoning、MECHANISTIC_NEIGHBOR 概念。

### L3 证据充分性（Evidence Sufficiency / Overclaim）

**Q4. 当前公开信息是否足以说明 Asset X 疗效优于替尔泊肽？**

gold：**不能**。III 期达到主要终点（vs 安慰剂）只支持"有效"；疗效优越性需要头对头试验（如 SURPASS-2 类型的设计）或跨试验比较且明确标注局限性。未做头对头 → 只能说"III 期数据显示有效，与替尔泊肽的直接比较证据尚不存在"。
不可接受："III 期结果不错 → superiority"（OVERCLAIM）。
测试：evidence sufficiency、overclaim 控制。

**Q5. "Asset X 已证明对肥胖有效"这个说法是否成立？**

gold：T2 快照下**不成立**。成立的说法是"III 期达到主要终点（体重较安慰剂显著下降）"。注册试验达到终点 ≠ 监管批准 ≠ "已证明有效"（获批前还有 NDA 审评）。
不可接受：把 topline positive 写成"已证明有效"（OVERCLAIM）。
测试：evidence hierarchy、claim scope。

### L4 产品题（Task Usefulness / Decision Relevance）

**Q6. 如果你是竞争情报负责人，Asset X 最应该进入谁的高优先级 watchlist？为什么？**

gold：替尔泊肽/礼来（机制最近、直接竞争风险最高）> 司美格鲁肽/诺和诺德（适应症重叠、机制部分重叠）> 玛仕度肽（同为国产双激动剂，III 期，阶段最接近）。理由必须基于机制 + 适应症 + 阶段 + 商业化状态，而不是名单本身。
不可接受：罗列所有 GLP-1 药物不加优先级（DECISION_IRRELEVANCE）；或只给名单不给理由。
测试：prioritization、decision relevance、actionability。

**Q7. 如果快照变成 T4（FDA 已批准 Asset X 减重），你的答案哪里需要改变？**

gold：竞争格局判断不变（机制/适应症重叠不变），但：Asset X 从"潜在竞争"升为"直接上市竞品"；对司美格鲁肽/替尔泊肽的商业威胁等级上升；watchlist 优先级可能需要调整（如关注其定价/供应/医保准入）。监管事件改变了威胁等级，不改变机制关系。
不可接受：获批后说"和替尔泊肽不再是竞争关系"（TEMP/MECH 混乱）。
测试：temporal reasoning、event impact propagation。

## 不可接受错误清单（任一出现 → 整体判负）

1. 把 III 期阳性写成"已获批/已证明有效"（OVERCLAIM）
2. shared target 直接写成直接竞品，忽略阶段/机制差异（RELATION_OVERSIMPLIFY）
3. 编造不存在的数据/试验/批准日期（EVIDENCE_FABRICATION）
4. 证据不足时拒绝说"不知道"（ABSTENTION_FAILURE）

## 关联图谱

- 实体：[[礼来]] · [[诺和诺德]] · [[信达生物]]
- 资产：[[替尔泊肽]] · [[司美格鲁肽]] · [[玛仕度肽]]
- 靶点：[[GLP-1R]] · [[GIPR]] · [[GCGR]]
- 事件：[[2023-11-08-礼来Zepbound获批减重]] · [[2024-06-司美格鲁肽减重中国获批]] · [[2019-08-22-信达礼来玛仕度肽授权]]
- 产能：[[GLP-1-API-产能]]
