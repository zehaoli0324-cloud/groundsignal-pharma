# -*- coding: utf-8 -*-
"""Generate pharma/ vault part 2: events, capacity tracking, templates, index."""
import os

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/pharma"
TODAY = "2026-08-27"

def w(relpath, content):
    path = os.path.join(BASE, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", relpath)

def event(fname, eid, etype, entity, date, conf, impact, ev, src, title, content, note=""):
    lines = [
        "---", "type: event", f"event_id: {eid}", f"event_type: {etype}",
        f"entity: \"[[{entity}]]\"", f"event_date: {date}", f"confidence: {conf}",
        f"impact: {impact}", f"evidence: {ev}", f'source_url: "{src}"',
        f"last_verified_at: {TODAY}", f"fetched_at: {TODAY}", "---", "",
        f"# {fname}", "", f"**事件类型：{etype} · 主体：[[{entity}]]**", "",
        f"- 时间：{date} | 置信度：{conf}", f"- 内容：{content}", f"- 影响：{impact}", f"- 来源：{src}"]
    if note:
        lines.append(f"- 备注：{note}")
    w(f"04-事件/{fname}.md", "\n".join(lines))

def template(fname, content):
    w(f"_模板/{fname}", content)

# ============ EVENTS ============
event("2023-11-08-礼来Zepbound获批减重", "evt_2023_lilly_zepbound",
      "FDA_APPROVAL", "礼来", "2023-11-08", 0.95,
      "替尔泊肽成为全球首个获批减重适应症的 GLP-1/GIP 双靶点药物，直接挑战司美格鲁肽 Wegovy",
      "VERIFIED", "https://www.fda.gov/news-events/press-announcements/fda-approves-new-medication-chronic-weight-management",
      "FDA 批准礼来 Zepbound（替尔泊肽 2.5mg-15mg）用于肥胖或超重合并至少一种体重相关合并症的慢性体重管理。",
      "FDA 批准 Zepbound 上市，SURMOUNT 系列 III 期数据显示平均减重可达 20% 以上。",
      "SURMOUNT-1 NCT04184622 为关键注册试验")

event("2022-05-13-礼来Mounjaro获批糖尿病", "evt_2022_lilly_mounjaro",
      "FDA_APPROVAL", "礼来", "2022-05-13", 0.95,
      "替尔泊肽首个适应症获批（2 型糖尿病），SURPASS 系列头对头击败司美格鲁肽",
      "VERIFIED", "https://www.fda.gov/news-events/press-announcements/fda-approves-novel-dual-targeted-treatment-type-2-diabetes",
      "FDA 批准 Mounjaro（替尔泊肽）用于改善 2 型糖尿病成人血糖控制。",
      "Mounjaro 获批上市，SURPASS-2 显示 HbA1c 降幅优于司美格鲁肽 1mg。",
      "SURPASS-2 NCT03987919 为关键注册试验")

event("2024-06-司美格鲁肽减重中国获批", "evt_2024_novo_wegovy_cn",
      "FDA_APPROVAL", "诺和诺德", "2024-06", 0.85,
      "GLP-1 减重适应症首次进入中国，国产 GLP-1 减重管线竞争加剧",
      "SUPPORTED", "https://www.nmpa.gov.cn",
      "诺和诺德司美格鲁肽 2.4mg（Wegovy）减重适应症获中国国家药监局批准，用于肥胖或超重成人。",
      "Wegovy 中国获批减重，玛仕度肽等国产 GLP-1 管线面临进口药上市竞争。",
      "获批日期以 NMPA 公告为准，报道口径")

event("2024-04-05-Carvykti获批二线骨髓瘤", "evt_2024_legend_carvykti_2l",
      "FDA_APPROVAL", "传奇生物", "2024-04-05", 0.9,
      "BCMA CAR-T 从末线推向二线治疗，多发性骨髓瘤治疗格局改变",
      "VERIFIED", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-ciltacabtagene-autoleucel-relapsed-or-refractory-multiple-myeloma",
      "FDA 批准强生/传奇西达基奥仑赛（Carvykti）用于既往接受过至少一线治疗的复发难治多发性骨髓瘤成人。",
      "CARTITUDE-4（NCT04181827）III 期数据支持二线获批，显著改善无进展生存期。",
      "CARTITUDE-1（NCT03548207）支撑 2022-02-28 末线获批")

event("2022-02-28-Carvykti获批末线骨髓瘤", "evt_2022_legend_carvykti",
      "FDA_APPROVAL", "传奇生物", "2022-02-28", 0.95,
      "全球首个 BCMA CAR-T 获批上市，传奇生物完成从 Biotech 到商业化公司跨越",
      "VERIFIED", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-ciltacabtagene-autoleucel-relapsed-or-refractory-multiple-myeloma",
      "FDA 批准 Carvykti 用于四线及以上复发难治多发性骨髓瘤。",
      "Carvykti 获批基于 CARTITUDE-1 单臂试验，总缓解率 97%。",
      "传奇生物美股 LEGN 为金斯瑞子公司")

event("2024-03-13-替雷利珠单抗FDA获批", "evt_2024_beigene_tislelizumab_fda",
      "FDA_APPROVAL", "百济神州", "2024-03-13", 0.9,
      "替雷利珠单抗成为第二个获 FDA 批准的国产 PD-1",
      "VERIFIED", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-tislelizumab-esophageal-squamous-cell-carcinoma",
      "FDA 批准百济神州替雷利珠单抗（百泽安）单药用于既往系统治疗后的不可切除或转移性食管鳞状细胞癌。",
      "RATIONALE-302（NCT03430843）III 期显示总生存显著优于化疗。",
      "为国产 PD-1 出海里程碑事件")

event("2023-10-27-特瑞普利单抗FDA获批", "evt_2023_junshi_toripalimab_fda",
      "FDA_APPROVAL", "君实生物", "2023-10-27", 0.9,
      "特瑞普利单抗成为中国首个获 FDA 批准的 PD-1，国产创新药出海标志事件",
      "VERIFIED", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-toripalimab-tpcs-nasopharyngeal-carcinoma",
      "FDA 批准君实生物特瑞普利单抗（拓益）联合化疗用于复发或转移性鼻咽癌一线治疗。",
      "基于 JUPITER-02 研究，鼻咽癌适应症为中国优势瘤种。",
      "国产 PD-1 出海第一单")

event("2019-11-14-泽布替尼FDA获批", "evt_2019_beigene_zanubrutinib_fda",
      "FDA_APPROVAL", "百济神州", "2019-11-14", 0.95,
      "泽布替尼成为中国首个获 FDA 批准的国产抗癌创新药",
      "VERIFIED", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-zanubrutinib-cll-sll",
      "FDA 批准百济神州泽布替尼（百悦泽）用于套细胞淋巴瘤（2019-11-14），后扩展至 CLL/SLL 等适应症。",
      "ALPINE（NCT03734016）III 期头对头优于伊布替尼，确立 CLL 标准治疗地位。",
      "国产创新药出海里程碑")

event("2021-06-22-奕凯达中国获批", "evt_2021_fosun_yikaida",
      "FDA_APPROVAL", "复星医药", "2021-06-22", 0.9,
      "阿基仑赛成为中国首个获批的 CAR-T 细胞治疗产品",
      "VERIFIED", "https://www.nmpa.gov.cn",
      "复星凯特奕凯达（阿基仑赛注射液）获中国国家药监局附条件批准，用于复发难治大B细胞淋巴瘤。",
      "基于 ZUMA-1（NCT02348216）桥接数据，开启中国细胞治疗商业化元年。",
      "由 Kite（吉利德）Yescarta 引进中国")

event("2019-08-22-信达礼来玛仕度肽授权", "evt_2019_innovent_lilly_mazdutide",
      "LICENSING_DEAL", "信达生物", "2019-08-22", 0.85,
      "玛仕度肽中国权益交易：总额超 10 亿美元，国产 GLP-1 减重管线起步",
      "SUPPORTED", "https://www.prnewswire.com/news-releases/innovent-and-elililly",
      "信达生物与礼来达成协议，获得玛仕度肽（IBI362，原 LY3305677）中国区权益，首付款加里程碑总额超 10 亿美元。",
      "礼来保留中国以外权益；信达负责中国临床开发与商业化。",
      "交易金额为报道口径")

# ============ CAPACITY ============
w("06-产能追踪/GLP-1-API-产能.md", """---
type: capacity
entity_id: cap_glp1_api
entity: "[[GLP-1R]]"
metric: GLP-1 原料药（API）/制剂产能
last_verified_at: 2026-08-27
---

# GLP-1 API 产能追踪

**GLP-1 类药物供不应求，产能是全球减重药市场的核心瓶颈。**

## 关键产能事实

- 诺和诺德：2024-02 宣布以 110 亿美元收购 Catalent 三座灌装工厂，用于司美格鲁肽产能扩张（来源: https://www.reuters.com）
- 礼来：2024-05 追加 53 亿美元投资印第安纳州工厂，扩大替尔泊肽 API 与制剂产能（来源: https://www.lilly.com）
- 礼来北卡罗来纳州 Concord 工厂（2022 建成）为替尔泊肽关键生产节点
- 司美格鲁肽/替尔泊肽口服剂型（Rybelsus/口服替尔泊肽）对 API 用量需求更大（生物利用度低）

## 变化记录

| 日期 | 变化 | 来源 |
|------|------|------|
| 2024-02 | 诺和诺德收购 Catalent 灌装厂（110 亿美元） | Reuters |
| 2024-05 | 礼来追加 53 亿美元扩产 | lilly.com |
""")

w("06-产能追踪/CAR-T-产能.md", """---
type: capacity
entity_id: cap_cart
entity: "[[传奇生物]]"
metric: CAR-T 商业化产能
last_verified_at: 2026-08-27
---

# CAR-T 商业化产能追踪

**CAR-T 为个体化定制治疗，产能（病毒载体 + 细胞制备 + 质检）决定可及性。**

## 关键产能事实

- 传奇生物：美国新泽西 Raritan 工厂 2022-05 投产，为 Carvykti 商业化生产核心基地（来源: https://www.legendbiotech.com）
- 传奇生物 2024-05 宣布新增比利时工厂，扩大欧洲产能（来源: https://www.legendbiotech.com）
- 复星凯特（复星医药）：上海张江产业化基地为阿基仑赛生产中心（来源: https://www.fosunpharma.com）

## 变化记录

| 日期 | 变化 | 来源 |
|------|------|------|
| 2022-05 | 传奇生物新泽西工厂投产 | legendbiotech.com |
| 2024-05 | 传奇生物宣布比利时新工厂 | legendbiotech.com |
""")

# ============ TEMPLATES ============
template("entity.md", """---
type: company
entity_id:
canonical_name:
aliases:
  -
ticker:
country:
region:
industry:
evidence: UNKNOWN
source_url:
last_verified_at:
fetched_at:
---

# {{canonical_name}}

**{{一句话描述}}**

## 关系

- [[产品]]（关系，年份）（来源: URL）
- [[公司]]（关系）（来源: URL）

## 元数据

- entity_id: | aliases: | ticker:
- industry: | region:
- last_verified_at:
""")

template("product.md", """---
type: product
entity_id:
canonical_name:
company:
target:
indications:
development_status:
evidence: UNKNOWN
source_url:
last_verified_at:
---

# {{canonical_name}}

**{{一句话描述}}**

## 关系

- [[公司]]（开发/商业化）（来源: URL）
- [[靶点]]（靶点）（来源: URL）
- 关键注册试验（NCT ID）（来源: https://clinicaltrials.gov）

## 元数据

- entity_id: | company: | target:
- indications:
- development_status:
""")

template("target.md", """---
type: target
entity_id:
canonical_name:
evidence: UNKNOWN
source_url:
last_verified_at:
---

# {{canonical_name}}

**{{靶点生物学与治疗价值描述}}**

## 相关药物

- [[药物1]]
- [[药物2]]

## 元数据

- entity_id: | type: target
""")

template("event.md", """---
type: event
event_id:
event_type:
entity:
event_date:
confidence:
impact:
evidence: UNKNOWN
source_url:
last_verified_at:
---

# {{title}}

**事件类型： · 主体：**

- 时间： | 置信度：
- 内容：
- 影响：
- 来源：
""")

# ============ INDEX ============
w("00-总目录.md", """# GroundSignal Pharma — 情报库总目录

**临床医学 + 先进制药情报图谱（Evidence-Grounded Biopharma Intelligence）**

> 实体 = 一个 .md 文件 | 关系 = [[wikilink]] | 证据 = source_url + evidence 等级
> 最后更新：2026-08-27

## 01-实体（药企/Biotech/服务商）

- [[礼来]] · [[诺和诺德]] · [[辉瑞]] · [[恒瑞医药]] · [[百济神州]] · [[信达生物]] · [[君实生物]]
- [[传奇生物]] · [[强生]] · [[复星医药]] · [[药明康德]] · [[药明生物]] · [[泰格医药]]

## 02-产品（药物管线）

- GLP-1：[[司美格鲁肽]] · [[替尔泊肽]] · [[玛仕度肽]]
- PD-1：[[信迪利单抗]] · [[替雷利珠单抗]] · [[卡瑞利珠单抗]] · [[特瑞普利单抗]]
- 细胞治疗：[[西达基奥仑赛]] · [[阿基仑赛]]
- 其他：[[泽布替尼]] · [[德曲妥珠单抗]]

## 03-靶点

- 代谢：[[GLP-1R]] · [[GIPR]] · [[GCGR]]
- 肿瘤免疫：[[PD-1]] · [[BTK]]
- 细胞治疗：[[BCMA]] · [[CD19]]
- ADC：[[HER2]]

## 04-事件（获批/临床/交易）

- FDA 获批：[[2023-11-08-礼来Zepbound获批减重]] · [[2022-05-13-礼来Mounjaro获批糖尿病]] · [[2024-04-05-Carvykti获批二线骨髓瘤]] · [[2022-02-28-Carvykti获批末线骨髓瘤]] · [[2024-03-13-替雷利珠单抗FDA获批]] · [[2023-10-27-特瑞普利单抗FDA获批]] · [[2019-11-14-泽布替尼FDA获批]]
- 中国获批：[[2024-06-司美格鲁肽减重中国获批]] · [[2021-06-22-奕凯达中国获批]]
- 授权交易：[[2019-08-22-信达礼来玛仕度肽授权]]

## 06-产能追踪

- [[GLP-1-API-产能]] · [[CAR-T-产能]]

## 05-证据审计

- 见 `05-证据审计/evidence-audit.md`（evidence-audit.py 生成）
- `05-证据审计/v2-metrics.md`（Schema V2 度量）
""")

print("DONE events/capacity/templates/index")
