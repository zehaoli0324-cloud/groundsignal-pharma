# GroundSignal Pharma

### Evidence-Grounded Biopharma Intelligence（临床医学 + 先进制药情报）

> **从公开信号到决策情报：药物管线、获批、授权交易、产能变化，全部可追溯。**

**把分散的公开医药信息变成可追溯、可比较、可持续更新的管线与企业情报。**

> 软件是生产机器，数据是资产，**Intelligence 才是商品**。
> 商业路径：Service first → Subscription second → Data/API third。

GroundSignal Pharma 不是"搜索药物信息"的 Agent，也不是静态知识图谱。它建立一条完整的医药情报链路：

```text
公开信息（ClinicalTrials.gov / FDA / NMPA / 药企公告 / 行业媒体）
→ Evidence
→ Claim / Relation / Event
→ Temporal Intelligence Graph
→ Cross-Entity Analysis
→ Change Detection
→ Decision-oriented Output
→ Evaluation
```

目标不是回答"GLP-1 有哪些药？"，而是继续回答：

> 这条管线关系由什么证据支持？它是什么时候获批的？现在还成立吗？
> 新加入一款 GLP-1 减重药后，它和已有礼来 / 诺和诺德 / 信达有什么竞争或合作交集？
> 一个 FDA 获批、授权交易或产能变化出现后，哪些已有判断可能需要更新？
> 系统漏掉了多少重要事件？发现得够不够快？误报多不多？

---

## Why this exists

医药情报真正困难的部分不是"找到一条新闻"，而是把长期分散的信息连接起来：

```text
礼来 → develops → 替尔泊肽 → targets → GLP-1R → competes with → 司美格鲁肽 → develops → 诺和诺德
```

某一天出现"FDA 批准 Zepbound 用于减重"，真正有价值的问题不是"礼来获批了"，而是：

> 这对司美格鲁肽 / 玛仕度肽 / 整个 GLP-1 减重格局意味着什么？哪些 CDMO、原料药供应商、临床试验中心与这个变化有关？哪些已有 watchlist 应该被重新检查？

**核心思想：新信息不是被存入数据库，而是被放进已有知识网络中重新解释。**

---

## System Logic

```text
1. Research Target (Drug/Company/Indication/Target/Watchlist)
        ↓
2. Multi-source Retrieval (ClinicalTrials.gov API/FDA/NMPA/annual reports/media)
        ↓
3. Evidence Extraction (source URL · NCT ID · publication time · source tier)
        ↓
4. Structured Intelligence (Company·Drug·Target·Facility·Relation·Claim·Evidence·Event)
        ↓
5. Intelligence Graph (company ↔ drug ↔ target ↔ trial ↔ facility, investor ↔ company, event ↔ affected)
        ↓
   Cross-Entity Scan              Change Detection
   (shared target/indication/     (approval/phase transition/
    investor/competition)          licensing/capacity)
        ↓
6. Intelligence Output (Company Card · Panorama · Discovery Report · Watchlist · Evidence Audit)
        ↓
7. Evaluation (Precision · Recall · Evidence Coverage · Detection Latency · False Alert Rate)
```

---

## What happens when a new drug enters the system?

加入"玛仕度肽"，系统不会只创建 `玛仕度肽.md`，而是执行一次 **Cross-Entity Intelligence Scan**：

```text
玛仕度肽 → 读取靶点/公司/适应症/已知关系
        → 与已有实体逐一比较 → neighbors(new) ∩ neighbors(existing)
        → 识别共享节点和直接关系 → 分类
```

当前 prototype 支持发现：`DIRECT_COMPETITOR / PRODUCT_OVERLAP / SHARED_TARGET / SHARED_INDICATION / SHARED_INVESTOR / COLLABORATION_LINK / COMMON_ECOSYSTEM`

```text
OBSERVED    已有直接关系或证据支持的事实
DERIVED     由共享靶点/适应症/合作结构计算出的分析
HYPOTHESIS  只有行业或生态重叠，需要进一步检索验证
```

```bash
python3 scripts/cross-entity-scan.py pharma 玛仕度肽 --report
# → 08-智能发现/2026-08-27-玛仕度肽-交叉关系发现.md
```

---

## From search to evidence

| Tier | Source | Typical use |
|------|--------|-------------|
| Tier 1 | ClinicalTrials.gov（NCT 编号）、FDA 批准记录、NMPA/CDE、WHO/EMA | 事实验证 |
| Tier 2 | 药企官网/年报/公告、Reuters/FiercePharma/Endpoints/丁香园 | 强支持证据 |
| Tier 3 | 搜索结果、公众号、论坛、自媒体 | 线索发现 |

核心原则：**一手优先（CT.gov/FDA/NMPA）、多源交叉、事实与预期分离、获批日期以监管为准、授权金额标报道口径、弱来源只作为 lead。**

系统保存的不只是"礼来 → 替尔泊肽"，而是 claim + evidence：

```yaml
claim:
  subject: 礼来
  predicate: DEVELOPS
  object: 替尔泊肽
  status: VERIFIED
  valid_from: 2022-05-13
  last_verified_at: 2026-08-27
evidence:
  source_type: fda_approval
  source_url: https://www.fda.gov
  nct_id: NCT04184622
```

---

## Data Model

V2 intelligence model：ENTITY / PRODUCT / TARGET / FACILITY / RELATION / CLAIM / EVIDENCE / EVENT

- **ENTITY**：谁？（礼来 / 诺和诺德 / 百济神州 / 药明康德）
- **PRODUCT**：哪个药物管线？（司美格鲁肽 / 替尔泊肽 / 西达基奥仑赛）
- **TARGET**：哪个靶点？（GLP-1R / PD-1 / BCMA / CD19 / HER2）
- **FACILITY**：哪个产能/临床节点？（GLP-1 API 产能 / CAR-T 制备工厂）
- **RELATION**：DEVELOPS / SUPPLIES / LICENSES / COLLABORATES / REGULATES / COMPETES_WITH
- **CLAIM**：VERIFIED / SUPPORTED / INFERRED / DISPUTED / STALE / SUPERSEDED / UNKNOWN
- **EVIDENCE**：clinicaltrials.gov / fda.gov / annual report / industry media
- **EVENT**：PHASE_TRANSITION / FDA_APPROVAL / IND_SUBMISSION / LICENSING_DEAL / SAFETY_SIGNAL / CLINICAL_START / M_A / FUNDING

---

## Information Integration

### 1. Single-Entity Intelligence

```bash
python3 scripts/ask.py pharma "礼来的客户是谁" -o board.html
```
聚合公司画像 + 药物管线 + 靶点 + 竞品 + 交易 + 证据 + 关联实体 → 单实体 Intelligence Card。

### 2. Pairwise Intelligence

```bash
python3 scripts/panorama.py pharma 礼来 诺和诺德 -o panorama.html
```
比较 A-only / B-only / shared nodes / common ecosystem，理解两个药企的关系结构（GLP-1 双寡头格局）。

### 3. Cross-Entity Intelligence

```bash
python3 scripts/cross-entity-scan.py pharma 玛仕度肽 --report
```
新药物/新公司进入数据库后自动与已有知识比较 → Discovery Report。

### 4. Temporal / Event Intelligence

```bash
python3 scripts/watchlist.py pharma --watch 礼来,诺和诺德,信达生物 -o watchlist.html
```
变化记录为 Event 而非覆盖旧事实；目标是 **Change Detection，而不是 News Aggregation**。

---

## Evidence Layer

```bash
python3 scripts/evidence-audit.py pharma --audit-dir 05-证据审计   # pharma（V2）
python3 scripts/evidence-audit.py demo                            # demo（V1）
```

当前打标（2026-08-27）：pharma 36 VERIFIED / 11 SUPPORTED / 0 UNKNOWN；demo 26 SUPPORTED / 4 VERIFIED / 0 UNKNOWN。

长期设计区分 `source_quality ≠ evidence_strength`（Reuters 是高质量来源，但"据悉可能获批"对"已经获批"的支撑强度仍然很低）。

---

## Evaluation

### Eval v1 — Is what we stored correct?
Relation Precision / Evidence quality / Entity Resolution / Temporal Validity / Abstention。方法就绪，50 条 gold set 抽样待跑；当前证据打标 UNKNOWN=0。

### Eval v2 — Is the system useful?
| Metric | Question | 当前值 |
|--------|----------|--------|
| Relation Recall | 应该知道的关系覆盖了多少？ | 待测 |
| Event Recall | 重要事件抓到了多少？（2024-2026 医药 12 项基准） | **7/12 = 58%** |
| Detection Latency | 事件发生多久后系统知道？ | live 待 cron 运行数据 |
| False Alert Rate | 推送中有多少没有商业意义？ | 待运行数据 |
| Evidence Coverage | 多少 claim 能追溯到来源？ | pharma 100%（0 UNKNOWN） |

诚实结论：**precision 较高，coverage 有限；live latency 与 false-alert 仍待证明。**

---

## Example Intelligence Domains

- `pharma/`：V2 intelligence model（Company/Drug/Target/Event/Capacity），聚焦先进制药赛道：GLP-1 减重（司美格鲁肽/替尔泊肽/玛仕度肽）、PD-1 免疫治疗（国产四大）、CAR-T 细胞治疗（西达基奥仑赛/阿基仑赛）、ADC（德曲妥珠单抗）。52 节点 / 0 断裂。
- `demo/`：Company-centric v1 图谱（A股/港股 10 家药企 + 产品 + 投资人 + 交易 + 产业链）。32 节点 / 0 断裂。

数据来源：ClinicalTrials.gov v2 API 真实查询（NCT 编号为证据）、FDA/NMPA 批准记录、药企官网/年报、公开报道。

---

## Repository

```text
demo/            v1 医药图谱（公司/产品/投资人/交易/产业链）
pharma/          V2 先进制药图谱（实体/产品/靶点/事件/产能）
scripts/         ingest · ask · panorama · cross-entity-scan · watchlist · evidence-audit · import-helper
docs/            architecture · search methods · schema · eval v1 · eval v2 · user/commercial validation
templates/       HTML 看板模板
samples/         示例输出（HTML+PNG）
```

## Documentation

- `docs/02-企业情报数据库-架构与Proposal.md` — architecture
- `docs/04-search-methods.md` — data sources & retrieval methodology（ClinicalTrials.gov v2 API 用法）
- `docs/06-eval-report.md` — Eval v1
- `docs/07-schema-v2.md` — intelligence schema（医药版对象模型）
- `docs/08-eval-v2.md` — recall / latency / false-alert evaluation
- `docs/09-user-validation.md` — user validation
- `docs/10-commercial-validation.md` — commercial roadmap

---

## Design Principle

> 只保存会改变我们对药物、公司、靶点、管线或事件判断的信息，并让每个判断可以被验证、比较和更新。

```text
Search finds information.
A database stores information.
Intelligence connects information, tracks how it changes,
tests whether it is reliable, and determines why the change matters.
```

---

## Status

**Current stage: sellable / testable intelligence MVP, not yet a validated commercial intelligence platform.**

已证明：structured intelligence can be built / evidence provenance can be preserved（0 UNKNOWN）/ cross-entity relationships can be discovered / events can be represented and surfaced / system quality can be evaluated

尚待证明：high recall / low detection latency / low false-alert rate / impact propagation quality / repeated real-user usage / willingness to pay
