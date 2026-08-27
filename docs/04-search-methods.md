# 医药版数据源与检索方法论

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
