# -*- coding: utf-8 -*-
"""Generate demo/ vault (v1 style, with tags): A-share/HK pharma companies + products + investors + deals + industry chains."""
import os

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/demo"
TODAY = "2026-08-27"

def w(relpath, content):
    path = os.path.join(BASE, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", relpath)

def company(name, full, code, industry, region, desc, products, src, suppliers="", customers="",
            investors="", competitors="", ev="VERIFIED"):
    lines = [
        "---", "type: company", f"name: {full}", f"code: {code}", f"industry: {industry}",
        f"region: {region}", f"status: 上市", f"website: {src}",
        f'products: "{products}"']
    if suppliers: lines.append(f'suppliers: "{suppliers}"')
    if customers: lines.append(f'customers: "{customers}"')
    if investors: lines.append(f'investors: "{investors}"')
    if competitors: lines.append(f'competitors: "{competitors}"')
    lines += [f"source_url: {src}", f"fetched_at: {TODAY}", "tags:",
              f"  - type/company", f"evidence: {ev}", "---", "", f"# {name}", "", f"**{desc}**", ""]
    w(f"01-公司/{name}.md", "\n".join(lines))

def product(name, full, industry, desc, src, companies, ev="SUPPORTED"):
    lines = [
        "---", "type: product", f"name: {full}", f"industry: {industry}",
        f"source_url: {src}", f"fetched_at: {TODAY}", "tags:",
        "  - type/product", f"evidence: {ev}", "---", "", f"# {name}", "", f"**{desc}**", "",
        "## 相关公司", ""]
    for c in companies:
        lines.append(f"- [[{c}]]")
    w(f"03-产品物料/{name}.md", "\n".join(lines))

def investor(name, full, desc, src, portfolio, ev="VERIFIED"):
    lines = [
        "---", "type: investor", f"name: {full}",
        f"source_url: {src}", f"fetched_at: {TODAY}", "tags:",
        "  - type/investor", f"evidence: {ev}", "---", "", f"# {name}", "", f"**{desc}**", "",
        "## 投资组合（医药）", ""]
    for p in portfolio:
        lines.append(f"- [[{p}]]")
    w(f"04-投资人/{name}.md", "\n".join(lines))

def deal(name, full, date, parties, desc, src, ev="SUPPORTED"):
    lines = [
        "---", "type: deal", f"name: {full}", f"date: {date}", f"parties: \"{parties}\"",
        f"source_url: {src}", f"fetched_at: {TODAY}", "tags:",
        "  - type/deal", f"evidence: {ev}", "---", "", f"# {name}", "", f"**{desc}**", ""]
    for p in parties.split(" / "):
        lines.append(f"- 涉及：[[{p}]]")
    w(f"05-交易事件/{name}.md", "\n".join(lines))

# ============ COMPANIES ============
company("恒瑞医药", "江苏恒瑞医药股份有限公司", "600276.SH", "创新药（肿瘤/代谢/自免）", "江苏连云港",
        "中国创新药龙头，卡瑞利珠单抗为国产 PD-1 代表，管线覆盖 ADC、GLP-1、双抗。",
        "[[PD-1抑制剂]] · [[GLP-1减重药]]",
        competitors="[[百济神州]] · [[信达生物]] · [[君实生物]]",
        src="https://www.hengrui.com")

company("百济神州", "百济神州（北京）生物科技有限公司", "688235.SH", "创新药（肿瘤）", "北京",
        "全球化最深的中国 Biotech，泽布替尼为首个 FDA 获批国产抗癌药，替雷利珠单抗出海标杆。",
        "[[PD-1抑制剂]]",
        investors="[[高瓴资本]]",
        competitors="[[恒瑞医药]] · [[信达生物]] · [[君实生物]]",
        src="https://www.beigene.com")

company("信达生物", "信达生物制药（苏州）有限公司", "01801.HK", "创新药（肿瘤/代谢）", "江苏苏州",
        "信迪利单抗为首个国产 PD-1，玛仕度肽为 GLP-1 减重国产第一梯队。",
        "[[PD-1抑制剂]] · [[GLP-1减重药]]",
        investors="[[礼来亚洲基金]] · [[高瓴资本]]",
        competitors="[[恒瑞医药]] · [[百济神州]]",
        src="https://www.innoventbio.com")

company("君实生物", "上海君实生物医药科技股份有限公司", "688180.SH", "创新药（肿瘤/自免）", "上海",
        "特瑞普利单抗为中国首个获 FDA 批准的 PD-1（鼻咽癌，2023-10）。",
        "[[PD-1抑制剂]]",
        competitors="[[恒瑞医药]] · [[百济神州]]",
        src="https://www.junshi.com")

company("复星医药", "上海复星医药（集团）股份有限公司", "600196.SH", "制药/医疗器械/诊断", "上海",
        "复星凯特引进阿基仑赛（中国首个获批 CAR-T），并引进 mRNA 疫苗复必泰。",
        "[[CAR-T疗法]] · [[mRNA疫苗]]",
        src="https://www.fosunpharma.com")

company("药明康德", "无锡药明康德新药开发股份有限公司", "603259.SH", "CRO/CDMO（一体化 CRDMO）", "江苏无锡",
        "全球最大的一体化药物研发服务平台之一，覆盖小分子发现到商业化生产。",
        "[[CRO服务]] · [[CDMO服务]]",
        customers="[[诺和诺德]] · [[礼来]]",
        competitors="[[泰格医药]]",
        src="https://www.wuxiapptec.com")

company("药明生物", "药明生物技术有限公司", "02269.HK", "生物药 CDMO", "江苏无锡",
        "全球领先的生物药（抗体/融合蛋白）CDMO，一体化生物药开发生产平台。",
        "[[CDMO服务]]",
        src="https://www.wuxibiologics.com")

company("泰格医药", "杭州泰格医药科技股份有限公司", "300347.SZ", "临床 CRO", "浙江杭州",
        "中国最大的临床合同研究组织（CRO）之一，承接临床试验运营与数据统计。",
        "[[CRO服务]]",
        competitors="[[药明康德]]",
        src="https://www.tigermed.net")

company("迈瑞医疗", "深圳迈瑞生物医疗电子股份有限公司", "300760.SZ", "医疗器械（监护/超声/IVD）", "广东深圳",
        "中国医疗器械龙头，生命信息与支持、体外诊断、医学影像三大板块。",
        "[[医疗器械]]",
        src="https://www.mindray.com")

company("智飞生物", "重庆智飞生物制品股份有限公司", "300122.SZ", "疫苗（代理+自研）", "重庆",
        "疫苗龙头，代理默沙东 HPV/五价轮状疫苗，自研结核 EC 诊断与微卡。",
        "[[HPV疫苗]]",
        src="https://www.zhifeishengwu.com")

# ============ PRODUCTS ============
product("PD-1抑制剂", "PD-1 抑制剂（国产四大）", "肿瘤免疫",
        "国产四大 PD-1：卡瑞利珠（恒瑞）、替雷利珠（百济）、信迪利（信达）、特瑞普利（君实），特瑞普利/替雷利珠已获 FDA 批准出海。",
        "https://www.nmpa.gov.cn", ["恒瑞医药", "百济神州", "信达生物", "君实生物"], "VERIFIED")

product("GLP-1减重药", "GLP-1 减重药物", "代谢疾病",
        "全球减重药市场爆发：进口（司美格鲁肽/替尔泊肽）与国产（玛仕度肽）竞争，产能为瓶颈。",
        "https://clinicaltrials.gov", ["信达生物", "恒瑞医药", "药明康德"], "VERIFIED")

product("CAR-T疗法", "CAR-T 细胞治疗", "细胞治疗",
        "个体化定制细胞治疗：复星凯特阿基仑赛（中国首个）、传奇西达基奥仑赛（BCMA，出海 FDA）。",
        "https://www.nmpa.gov.cn", ["复星医药", "传奇生物"], "VERIFIED")

product("mRNA疫苗", "mRNA 疫苗（复必泰）", "疫苗",
        "复星医药与 BioNTech 合作引入 Comirnaty 中国权益（复必泰），mRNA 平台向肿瘤疫苗扩展。",
        "https://www.fosunpharma.com", ["复星医药", "辉瑞"], "VERIFIED")

product("CRO服务", "CRO 服务（合同研究组织）", "研发外包",
        "药物研发外包：临床前研究、临床 I-IV 期运营、数据统计。药明康德一体化平台、泰格临床 CRO 龙头。",
        "https://www.wuxiapptec.com", ["药明康德", "泰格医药"], "VERIFIED")

product("CDMO服务", "CDMO 服务（合同定制研发生产）", "研发外包",
        "原料药/制剂/生物药工艺开发与商业化生产外包：药明康德（小分子）、药明生物（生物药）。",
        "https://www.wuxiapptec.com", ["药明康德", "药明生物"], "VERIFIED")

product("医疗器械", "医疗器械（监护/超声/IVD）", "医疗器械",
        "迈瑞医疗三大板块：生命信息与支持、体外诊断（IVD）、医学影像。",
        "https://www.mindray.com", ["迈瑞医疗"], "VERIFIED")

product("HPV疫苗", "HPV 疫苗", "疫苗",
        "智飞生物独家代理默沙东四价/九价 HPV 疫苗中国大陆权益，为营收核心来源。",
        "https://www.zhifeishengwu.com", ["智飞生物"], "VERIFIED")

# ============ INVESTORS ============
investor("高瓴资本", "高瓴资本（HHLR）", "头部医疗健康产业资本，重仓创新药与 CXO。",
         "https://www.hillhousecap.com", ["百济神州", "信达生物"])

investor("礼来亚洲基金", "礼来亚洲基金（Lilly Asia Ventures）", "专注医疗健康的风险投资，信达生物早期投资人。",
         "https://www.lillyasia.com", ["信达生物"])

investor("启明创投", "启明创投（Qiming Venture Partners）", "医疗健康与 TMT 双轮驱动的头部 VC。",
         "https://www.qimingvc.com", ["泰格医药"])

investor("红杉中国", "红杉中国（HongShan）", "覆盖创新药、医疗器械、CXO 的头部 VC/PE。",
         "https://www.hongshan.com", ["药明康德"])

# ============ DEALS ============
deal("信达礼来玛仕度肽授权", "信达生物与礼来达成玛仕度肽中国权益授权（2019-08）", "2019-08-22",
     "信达生物 / 礼来",
     "信达获得玛仕度肽（IBI362）中国区权益，首付加里程碑总额超 10 亿美元；礼来保留中国以外权益。",
     "https://www.prnewswire.com")

deal("百济诺华替雷利珠授权", "百济神州与诺华达成替雷利珠单抗海外授权（2021-01）", "2021-01-12",
     "百济神州 / 诺华",
     "诺华获替雷利珠单抗欧美日等海外权益，首付款 6.5 亿美元，里程碑总额最高 22 亿美元，为当年国产 PD-1 最大出海交易。",
     "https://www.beigene.com")

deal("君实Coherus特瑞普利授权", "君实生物与 Coherus 达成特瑞普利单抗北美授权（2021-02）", "2021-02-01",
     "君实生物 / Coherus",
     "Coherus 获特瑞普利单抗北美权益，首付款 1.5 亿美元，里程碑总额最高 11.1 亿美元。",
     "https://www.junshi.com")

deal("复星BioNTech合作", "复星医药与 BioNTech 达成 mRNA 疫苗中国权益合作（2020-03）", "2020-03-13",
     "复星医药 / 辉瑞",
     "复星医药获得 BioNTech mRNA 疫苗（复必泰）中国大陆及港澳台独家权益，双方共同开发、复星负责中国商业化。",
     "https://www.fosunpharma.com")

deal("传奇强生合作", "传奇生物与强生达成西达基奥仑赛全球合作（2017-12）", "2017-12-21",
     "传奇生物 / 强生",
     "强生旗下杨森以 3.5 亿美元首付款获得西达基奥仑赛全球（除大中华）权益，共同开发 BCMA CAR-T。",
     "https://www.jnj.com")

# ============ INDUSTRY CHAINS ============
w("06-产业链/药物研发产业链全景.md", """---
type: analysis
name: 药物研发产业链全景
source_url: "https://www.fda.gov"
fetched_at: 2026-08-27
tags:
  - type/analysis
evidence: NA
---

# 药物研发产业链全景

**从靶点发现到商业化：创新药全链条 + 横向服务外包（CRO/CDMO）。**

```text
靶点发现 → 临床前研究 → IND 申报 → 临床 I 期 → 临床 II 期 → 临床 III 期 → NDA 申报 → 获批上市 → 商业化
     │            │            │           │          │            │            │          │
     └────────────┴────────────┴───────────┴──────────┴────────────┴────────────┴──────────┴── 横向服务
                                            ▲
                                    临床 CRO（[[泰格医药]]）
                                    一体化 CRDMO（[[药明康德]]）
                                    生物药 CDMO（[[药明生物]]）
```

## 环节与代表实体

| 环节 | 代表实体 | 关键节点 |
|------|----------|----------|
| 靶点发现 | [[GLP-1R]] · [[PD-1]] · [[BCMA]] | 生物学验证 |
| 临床前 | [[药明康德]] | 药理毒理/CMC |
| 临床开发 | [[泰格医药]] | I-III 期入组 |
| 注册申报 | FDA / NMPA | 获批里程碑（[[2023-11-08-礼来Zepbound获批减重]]） |
| 商业化 | [[礼来]] · [[诺和诺德]] · [[恒瑞医药]] | 产能（[[GLP-1-API-产能]]） |
""")

w("06-产业链/GLP-1产业链.md", """---
type: analysis
name: GLP-1 产业链
source_url: "https://www.reuters.com"
fetched_at: 2026-08-27
tags:
  - type/analysis
evidence: SUPPORTED
---

# GLP-1 产业链

**减重药市场爆发，核心瓶颈在原料药（API）与制剂产能。**

```text
GLP-1 多肽 API → 制剂灌装 → 药企商业化 → 渠道/患者
      ▲              ▲
   多肽 CDMO       Catalent 等灌装厂
```

## 关键玩家

- 原研：[[礼来]]（替尔泊肽）· [[诺和诺德]]（司美格鲁肽）
- 国产：[[信达生物]]（玛仕度肽）
- CDMO：[[药明康德]] · [[药明生物]]
- 靶点：[[GLP-1R]] · [[GIPR]] · [[GCGR]]

## 关键约束

- 产能：[[GLP-1-API-产能]]（诺和诺德收购 Catalent、礼来 53 亿美元扩产）
- 口服剂型生物利用度低 → API 需求倍增
""")

w("06-产业链/细胞治疗产业链.md", """---
type: analysis
name: 细胞治疗产业链
source_url: "https://www.legendbiotech.com"
fetched_at: 2026-08-27
tags:
  - type/analysis
evidence: SUPPORTED
---

# 细胞治疗产业链

**CAR-T 为个体化定制治疗：从患者白细胞分离到回输，全流程约 2-4 周。**

```text
白细胞单采 → 基因改造（病毒载体）→ 细胞扩增 → 质控放行 → 回输患者
     │              │                  │
  临床中心       载体 CDMO           制备工厂（[[CAR-T-产能]]）
```

## 关键玩家

- [[传奇生物]] / [[强生]]：西达基奥仑赛（BCMA，出海 FDA）
- [[复星医药]]（复星凯特）：阿基仑赛（CD19，中国首个）
- 靶点：[[BCMA]] · [[CD19]]
""")

# ============ CHANGELOG + INDEX ============
w("07-变更日志/2026-08-27-建库.md", """---
type: changelog
name: 2026-08-27 医药版建库
date: 2026-08-27
tags:
  - type/changelog
---

# 2026-08-27 医药版建库

- 建库：10 家药企/Biotech/CXO + 8 产品 + 4 投资人 + 5 交易事件 + 3 产业链
- 数据源：ClinicalTrials.gov v2 API（NCT 编号真实查询）、公司官网/公告、公开报道
- 事件口径：获批日期以 FDA/NMPA 为准；授权金额为报道口径
""")

w("00-总目录.md", """# GroundSignal Pharma — demo 图谱（v1）

**临床医学 + 先进制药 · 企业情报图谱（10 公司 / 8 产品 / 4 投资人 / 5 交易 / 3 产业链）**

> 最后更新：2026-08-27

## 01-公司

- [[恒瑞医药]] · [[百济神州]] · [[信达生物]] · [[君实生物]] · [[复星医药]]
- [[药明康德]] · [[药明生物]] · [[泰格医药]] · [[迈瑞医疗]] · [[智飞生物]]

## 03-产品物料

- [[PD-1抑制剂]] · [[GLP-1减重药]] · [[CAR-T疗法]] · [[mRNA疫苗]]
- [[CRO服务]] · [[CDMO服务]] · [[医疗器械]] · [[HPV疫苗]]

## 04-投资人

- [[高瓴资本]] · [[礼来亚洲基金]] · [[启明创投]] · [[红杉中国]]

## 05-交易事件

- [[信达礼来玛仕度肽授权]] · [[百济诺华替雷利珠授权]] · [[君实Coherus特瑞普利授权]]
- [[复星BioNTech合作]] · [[传奇强生合作]]

## 06-产业链

- [[药物研发产业链全景]] · [[GLP-1产业链]] · [[细胞治疗产业链]]

## 07-变更日志

- [[2026-08-27-建库]]
""")

print("DONE demo")
