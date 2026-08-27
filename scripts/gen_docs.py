# -*- coding: utf-8 -*-
"""Generate docs/ for groundsignal-pharma (clinical medicine & advanced pharma)."""
import os

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/docs"

def w(relpath, content):
    path = os.path.join(BASE, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", relpath)

w("01-obsidian-hermes-collaboration.md", """# Hermes × Obsidian 协作方式（通用）

Agent 直接通过文件系统读写 Obsidian vault（无需插件）：

- 读：`read_file`；写：`write_file`（自动建父目录）；改：`patch`；搜：`search_files`
- wikilink 规则：关系一律 `[[文件名]]`；重名用全路径 `[[01-实体/礼来]]`
- wikilink 不放 frontmatter 和代码块（图谱不渲染）
- 文件名避开 `&`/`/`/`?`
- Obsidian URI 打开：`powershell.exe -Command "Start-Process 'obsidian://open?vault=<VaultName>&file=00-总目录'"`
""")

w("02-企业情报数据库-架构与Proposal.md", """# GroundSignal Pharma — 架构与 Proposal（医药版）

## 1. 要解决的问题

临床医学与先进制药行业的信息高度分散：药物管线状态在 ClinicalTrials.gov，获批信息在 FDA/NMPA，商业交易在新闻稿，产能/供应链在年报与行业媒体。传统做法是人工看新闻，缺乏**跨实体、可追溯、随时间更新**的情报能力。

GroundSignal Pharma 把 groundsignal 的 evidence-grounded 情报方法迁移到医药领域：

```text
公开信息（ClinicalTrials.gov / FDA / NMPA / 药企公告 / 行业媒体）
→ Evidence（source_url + 采集时间 + 来源分级）
→ Claim / Relation / Event（管线关系 + 获批/交易事件）
→ Temporal Intelligence Graph（药企 ↔ 药物 ↔ 靶点 ↔ 临床试验 ↔ 产能）
→ Cross-Entity Analysis（共享靶点/适应症/投资人 → 竞争格局）
→ Change Detection（获批/阶段推进/授权/产能变化）
→ Decision-oriented Output（情报卡 · 全景 · Discovery Report · Watchlist）
→ Evaluation（Precision · Recall · Latency · False Alert）
```

## 2. 核心场景

- **管线竞争情报**：谁在同一个靶点/适应症竞争？（如 GLP-1 减重：礼来 vs 诺和诺德 vs 信达）
- **交易情报**：授权/并购/融资事件对哪些已有判断有影响？
- **供应链/产能情报**：GLP-1 API 产能瓶颈、CDMO 产能变化影响谁？
- **监管情报**：FDA/NMPA 获批、安全性信号出现后，哪些 watchlist 需要重新检查？

## 3. 数据模型（V2）

ENTITY（药企/Biotech/CXO/监管）· PRODUCT（药物管线）· TARGET（靶点）· FACILITY（产能/临床中心）· RELATION · CLAIM · EVIDENCE · EVENT

## 4. 与半导体版的关系

同一套 GroundSignal 方法（claim-evidence-event 模型 + 交叉扫描 + 变化检测），不同领域的数据源与对象模型。领域适配点：药物管线的 development_status、靶点关系、临床试验事件类型、产能追踪对象（API 产能 vs 芯片产能）。

## 5. 现状与边界（诚实声明）

已实现：结构化图谱（pharma 52 节点 / demo 32 节点）、单实体看板、双实体全景、交叉扫描、事件流、证据审计。
尚待证明：事件 Recall 覆盖、live 检测延迟、误报率、持续真实用户使用。
""")

w("03-obsidian-usage-guide.md", """# Obsidian 使用指南（通用）

1. 用 Obsidian 打开仓库根目录（`pharma/` 或 `demo/`）作为 vault
2. 图谱视图（Graph View）查看实体关系
3. 每个实体文件 = 一个节点；`[[wikilink]]` = 关系边
4. frontmatter 的 `evidence` 字段是证据等级（VERIFIED/SUPPORTED/INFERRED/UNKNOWN）
5. 变更日志在 `07-变更日志/`；证据审计报告在 `05-证据审计/`（pharma）或 `08-证据审计/`（demo）
6. 生成看板：`python3 scripts/ask.py <vault> "实体名" -o board.html`
""")

w("04-search-methods.md", """# 医药版数据源与检索方法论

## 1. 数据源（按权威度）

| 优先级 | 渠道 | 内容 | 证据等级 |
|--------|------|------|----------|
| P0 | ClinicalTrials.gov v2 API | 临床试验结构化数据（NCT ID/状态/阶段/申办方） | VERIFIED |
| P0 | FDA（Drugs@FDA / 批准公告） | 美国获批记录/批准日期 | VERIFIED |
| P0 | NMPA / CDE（药审中心） | 中国受理/批准 | VERIFIED |
| P0 | WHO / EMA / DrugBank | 国际监管与药物信息 | VERIFIED |
| P1 | 药企官网/年报/公告、FDA 新闻稿 | 一手官方（交易/管线/产能） | SUPPORTED |
| P2 | FiercePharma / Endpoints / Reuters / 丁香园 / 医药魔方 | 权威行业媒体 | SUPPORTED |
| P3 | 360 搜索（data-mdurl 解析） | 线索发现 | INFERRED |

## 2. ClinicalTrials.gov v2 API（P0，免费无需登录）

```bash
# 按干预物/关键词查询
curl "https://clinicaltrials.gov/api/v2/studies?query.term=tirzepatide&pageSize=10&fields=NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName"

# 按 NCT ID 精确查询（关键注册试验用这个）
curl "https://clinicaltrials.gov/api/v2/studies/NCT04184622?fields=NCTId,BriefTitle,OverallStatus,Phase,StartDate,PrimaryCompletionDate"
```

- 每个药物优先登记**关键注册试验**（SURMOUNT/STEP/CARTITUDE/RATIONALE 等），而不是研究者发起的小试验
- 试验状态（COMPLETED/ACTIVE_NOT_RECRUITING/RECRUITING/UNKNOWN）是管线的实时证据
- 国内网络可直连（无需代理），注意 `--noproxy '*'` 绕开失效的本地代理

## 3. 验证纪律（反幻觉）

- 获批日期：以 FDA / NMPA 官方为准（VERIFIED）；报道口径标 SUPPORTED
- 授权交易金额：新闻稿/年报口径，标"报道口径"
- 临床试验状态：以 ClinicalTrials.gov 当前查询为准，不靠记忆
- 关键关系 ≥2 独立来源；事实与预期分离（"预计/可能"标待核实）
- 自查问题：这条的原始出处（URL/NCT ID/批准日期）是什么？给不出就不写

## 4. 常用查询

- 管线阶段：CT.gov `query.term=<药物名>` → OverallStatus/Phase
- 获批：FDA Drugs@FDA / 公司新闻稿
- 交易：公司公告 + Reuters/FiercePharma
- 产能：公司年报/新闻稿（如诺和诺德收购 Catalent、礼来扩产）
""")

w("05-import-guide.md", """# 导入/合并指南（通用）

```bash
python3 scripts/import-helper.py <源库> <目标vault> --check   # 冲突预检
python3 scripts/import-helper.py <源库> <目标vault> --merge   # 执行合并
```

- 同名不同内容 → `企业情报-原名.md` + 内部 wikilink 自动改写
- 同名同内容 → 跳过；用户文件永不覆盖
- 更干净方案：用 ingest.py 的 YAML 在目标 vault 重建
""")

w("06-eval-report.md", """# Eval v1 — 存进去的对不对？（医药版）

## 方法

从 pharma/ 图谱的关系行分层抽样（覆盖 GLP-1 / PD-1 / CAR-T / CXO 板块），按采集期多源验证逐条核对 gold：
- ClinicalTrials.gov 试验状态 = 一手（VERIFIED）
- FDA/NMPA 批准日期 = 一手（VERIFIED）
- 多源报道（Reuters/FiercePharma/公司官网） = SUPPORTED
- 单一自媒体 = INFERRED

## 指标

- Relation Precision / Evidence Precision / Entity Resolution / Temporal Validity / Abstention

## 当前证据打标结果（evidence-audit.py，2026-08-27）

| 库 | VERIFIED | SUPPORTED | INFERRED | UNKNOWN | NA |
|----|----------|-----------|----------|---------|-----|
| pharma/ | 36 | 11 | 0 | 0 | 4 |
| demo/ | 4 | 26 | 0 | 0 | 1 |

UNKNOWN 清零；SUPPORTED 集中在公司官网与行业媒体来源（合规，但 precision 抽样仍待跑 50 条 gold set）。

## 已知短板（诚实）

- 关系行来源引用：核心关系已带（来源: URL），聚合行需补
- 时间信息：部分事件只有年份，需补到日期
- 弱证据混入：授权交易金额为报道口径，未逐条验证
""")

w("07-schema-v2.md", """# Schema V2 — 医药版对象模型

## 七类核心对象（+ 靶点扩展）

| 对象 | 医药版含义 | 示例 |
|------|-----------|------|
| ENTITY | 药企 / Biotech / CXO / 监管机构 | [[礼来]] · [[百济神州]] · [[药明康德]] |
| PRODUCT | 药物管线（含开发状态） | [[替尔泊肽]] · [[西达基奥仑赛]] |
| TARGET | 靶点 | [[GLP-1R]] · [[PD-1]] · [[BCMA]] |
| FACILITY | GMP 工厂 / CDMO 产能 / 临床中心 | 传奇新泽西工厂 · Catalent 灌装厂 |
| RELATION | DEVELOPS / SUPPLIES / LICENSES / COLLABORATES / REGULATES / COMPETES_WITH | 礼来 → DEVELOPS → 替尔泊肽 |
| CLAIM | VERIFIED / SUPPORTED / INFERRED / DISPUTED / STALE / SUPERSEDED | 授权金额（报道口径） |
| EVIDENCE | clinicaltrials.gov / fda.gov / 年报 / 行业媒体 | NCT04184622 |
| EVENT | PHASE_TRANSITION / FDA_APPROVAL / IND_SUBMISSION / LICENSING_DEAL / SAFETY_SIGNAL / CLINICAL_START / M_A | Zepbound 获批（2023-11-08） |

## 字段（值钱字段优先）

- PRODUCT：company / target / indications / development_status / evidence / source_url
- ENTITY：ticker / country / region / industry / evidence / source_url
- EVENT：event_id / event_type / entity / event_date / confidence / impact / evidence / source_url

## 禁止清单

- 不采企业简介/新闻摘要/官网宣传文案（不改变判断的信息）
- 不写没有来源的关系
- 不把"预计/可能"写成事实（标待核实）
- 靶点节点必须有真实药物关联（不建孤立靶点）
""")

w("08-eval-v2.md", """# Eval v2 — 系统有没有用？（医药版）

## 用户价值指标

| Metric | Question | 当前值 |
|--------|----------|--------|
| Relation Recall | 应该知道的关系覆盖多少？ | 待测（gold set 构建中） |
| Event Recall | 重要事件抓到多少？ | **7/12 = 58%**（见下） |
| Detection Latency | 事件发生后多久知道？ | live 待 cron 数据 |
| False Alert Rate | 推送中有多少无意义？ | 待 cron 运行 ≥2 周 |
| Evidence Coverage | 多少 claim 能溯源？ | pharma 100%（0 UNKNOWN） |

## Event Recall 基准集（2024-2026 医药重大事件 12 项）

| # | 事件 | 覆盖 |
|---|------|------|
| 1 | 礼来 Zepbound 获批减重（2023-11） | ✅ |
| 2 | 强生/传奇 Carvykti 二线获批（2024-04） | ✅ |
| 3 | 百济替雷利珠 FDA 获批（2024-03） | ✅ |
| 4 | 诺和诺德 Wegovy 中国获批减重（2024-06） | ✅ |
| 5 | 诺和诺德收购 Catalent（2024-02） | ✅ |
| 6 | 礼来追加 53 亿美元扩产（2024-05） | ✅ |
| 7 | 传奇比利时新工厂（2024-05） | ✅ |
| 8 | 玛仕度肽 NDA 受理（2025-01） | ❌（仅产品节点） |
| 9 | 玛仕度肽 III 期成功（2024-08） | ❌ |
| 10 | 君实特瑞普利 FDA 获批（2023-10） | ✅ |
| 11 | 泽布替尼 CLL/SLL 获批（2023-01） | ❌ |
| 12 | 信达玛仕度肽 III 期 DREAMS-2 达终点 | ❌ |

**未覆盖 4 项 = 采集 backlog**（优先级排序：玛仕度肽 NDA/III 期 → 泽布替尼 CLL）。

## 诚实结论

- precision 高（证据可追溯、0 UNKNOWN），coverage 有限（58%），live latency 与 false-alert 待 cron 证明
- 回溯覆盖 ≠ live 延迟：建库补录事件不能当卖点
""")

w("09-user-validation.md", """# User Validation（用户验证）

## 目标用户

1. 药企 BD / 战略 / 竞争情报团队：管线与交易情报
2. 投资人（医疗 VC/PE）：标的尽调、赛道格局
3. 政策与行业研究：监管动态、产业链变化

## 假设（待验证）

- 用户是否愿意为"管线获批/授权交易/产能变化"的持续监控付费？
- 是否有人持续使用并反馈？（当前为求职作品集 + 方法论验证，无真实付费用户）

## 验证计划

- 收集 3-5 位医药行业从业者的使用反馈
- 跟踪 watchlist 推送的有用率
- 对比人工情报工作流的时间成本

## 状态

**未启动真实用户验证。** 当前证据：方法可行（groundsignal 半导体版已验证技术路线），医药版领域适配合理，但商业价值未证实。
""")

w("10-commercial-validation.md", """# Commercial Validation（商业验证）

## 价值主张

**Evidence-Grounded Biopharma Intelligence**：把分散的管线/获批/交易/产能信息变成可追溯、可比较、可持续更新的决策情报。

## 商业化路径

1. **Service first**：药企/投资人的定制情报报告（管线竞争格局、交易监控）
2. **Subscription second**：watchlist 持续监控订阅（获批/阶段推进/授权/产能）
3. **Data/API third**：结构化医药情报数据接口（ClinicalTrials.gov + FDA + 交易事件的增强数据）

## 与半导体版的协同

同一套 GroundSignal 引擎，多领域部署：AI Compute 供应链 + 生物医药。领域适配成本低（数据源/对象模型替换）。

## 竞争与差异

- 通用数据库（DrugBank/Evaluate）给"事实"，不给"关系 + 变化 + 交叉发现"
- 本系统输出的是 claim + evidence + event + cross-entity discovery

## 风险

- 免费数据源（CT.gov/FDA）是公开的，竞争壁垒在关系模型与持续监控质量
- 医药领域专家知识门槛（领域适配需要 domain knowledge）
- 大厂（IQVIA/Evaluate）已有成熟产品，差异化在 Agent 自动化和证据透明
""")

print("DONE docs")
