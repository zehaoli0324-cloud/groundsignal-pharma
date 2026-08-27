# Schema V2 — 医药版对象模型（升级版）

## 核心对象（11 类）

| 对象 | 医药版含义 | 示例 | 当前实现状态 |
|------|-----------|------|-------------|
| COMPANY | 药企 / Biotech / CXO / 监管机构 | [[礼来]] · [[百济神州]] · [[药明康德]] | ✅ 01-实体/ |
| ASSET | 药物资产（管线） | [[替尔泊肽]] · [[西达基奥仑赛]] | ✅ 02-产品/ |
| TARGET | 分子靶点 / 通路 | [[GLP-1R]] · [[PD-1]] · [[BCMA]] | ✅ 03-靶点/ |
| INDICATION | 疾病 / 临床适应症 | obesity · type 2 diabetes · NSCLC | ⏳ frontmatter 字段；独立节点待建 |
| TRIAL | 注册临床试验 | SURMOUNT-1（NCT04184622） | ⏳ NCT 编号关系行；独立节点待建 |
| BIOMARKER | 分子/临床选择特征 | EGFR mutation · PD-L1 status | ⏳ 未实现（设计预留） |
| MODALITY | 治疗技术类别 | peptide · mAb · ADC · CAR-T · mRNA | ✅ 产品 frontmatter modality 字段 |
| REGULATORY_EVENT | 获批 / 申报 / CRL / 临床暂停 / 标签更新 | Zepbound 获批（2023-11-08） | ✅ 04-事件/（event_type） |
| SAFETY_SIGNAL | 标签警告 / 试验安全观察 / 监管沟通 | 黑框警告更新 | ⏳ 事件类型已注册；节点待建 |
| CLAIM | 带范围和状态的主张 | "替尔泊肽获批用于肥胖"（VERIFIED） | ⏳ 关系行 + evidence 状态 |
| EVIDENCE | 为什么相信 | clinicaltrials.gov / fda.gov / 年报 | ✅ source_url + evidence 等级 |

**诚实声明：TRIAL / INDICATION / BIOMARKER / SAFETY_SIGNAL 当前为 frontmatter 字段或关系行形式，独立 first-class 节点是 Schema V2.1 升级方向**（升级后可支持 trial-state diff、indication-level landscape 等分析）。

## 关系类型

### Observed（可观察关系）

- `DEVELOPS`（礼来 → 替尔泊肽）
- `TARGETS`（替尔泊肽 → GLP-1R）
- `TREATS_OR_STUDIES`（药物 → 适应症）
- `TESTED_IN` / `SPONSORED_BY`（药物 ↔ 试验）
- `USES_BIOMARKER`
- `HAS_MODALITY`
- `COMBINATION_WITH`（联合用药）
- `LICENSED_TO / LICENSED_FROM`（信达 ← 礼来 玛仕度肽）
- `ACQUIRED_BY`（M&A）
- `APPROVED_FOR`（获批适应症）
- `REGULATED_BY`

### Derived / analytical（派生关系，≠ 事实）

- `DIRECT_COMPETITOR`（同靶点 + 同适应症 + 同阶段定位）
- `SHARED_TARGET`（共享靶点，**不等于直接竞争**）
- `SHARED_INDICATION`
- `SHARED_MODALITY`
- `TRIAL_OVERLAP`（共享关键注册试验设计）
- `MECHANISTIC_NEIGHBOR`（机制邻近）
- `REGULATORY_ANALOG`（监管类比：同类资产获批 → 风险/机会传导）
- `SAFETY_ANALOG`（安全信号传导：A 资产黑框警告 → B 同类资产风险重估）

**核心纪律：shared target ≠ direct competitor。** 直接竞争需要靶点 + 适应症 + 模式 + 阶段 + 定位叠加判断（cross-entity-scan.py pharma 模式实现）。

## 字段（值钱字段优先）

### ASSET（02-产品/）

```yaml
type: product
entity_id:
canonical_name:
company:
target:
modality:        # peptide / monoclonal antibody / small molecule / ADC / CAR-T / mRNA
indications:
development_status:
evidence:
source_url:
```

### TRIAL（升级后）

```yaml
type: trial
registry_id:     # NCT 编号（ClinicalTrials.gov 一手）
status:          # RECRUITING / COMPLETED / ACTIVE_NOT_RECRUITING / UNKNOWN
phase:
sponsor:
interventions:
conditions:
primary_endpoints:
enrollment:
start_date:
primary_completion_date:
last_update_posted:
```

### EVENT（04-事件/）

```yaml
type: event
event_id:
event_type:      # FDA_APPROVAL / PHASE_TRANSITION / CLINICAL_HOLD / CRL / SAFETY_SIGNAL / ...
entity:
event_date:
confidence:
impact:
evidence:
source_url:
```

## 禁止清单

- 不采企业简介/新闻摘要/官网宣传文案（不改变判断的信息）
- 不写没有来源的关系
- 不把"预计/可能"写成事实（标待核实）
- 靶点节点必须有真实药物关联（不建孤立靶点）
- **不把共享靶点写成直接竞争**（需叠加适应症/模式/阶段）
- **不把 III 期阳性写成获批**（见 docs/11-clinical-safety-boundaries.md）

## 与半导体版的关系

同一套 claim-evidence-event 引擎。领域适配点：对象从 company/product/supplier 扩展为 asset/target/indication/trial/modality；事件类型从产能/客户变化扩展为获批/临床阶段/安全信号/授权；竞争判定从 shared customer/supplier 扩展为 shared target/indication/modality。
