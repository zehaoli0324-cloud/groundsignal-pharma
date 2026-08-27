# Schema V2 — 医药版对象模型

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
