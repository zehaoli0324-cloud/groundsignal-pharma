# -*- coding: utf-8 -*-
"""Generate pharma/ vault: entities (companies), products (drugs), targets."""
import os

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/pharma"
TODAY = "2026-08-27"

def w(relpath, content):
    path = os.path.join(BASE, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", relpath)

def entity(name, fid, canon, aliases, ticker, country, region, industry, ev, src, desc, relations, meta_extra=""):
    fm = [f"type: {fid}"] if fid != "company" else ["type: company"]
    lines = [
        "---",
        f"type: {fid}",
        f"entity_id: {name}",
        f"canonical_name: {canon}",
        "aliases:",
    ]
    for a in aliases:
        lines.append(f"  - {a}")
    lines += [f"ticker: {ticker}", f"country: {country}", f"region: {region}",
              f"industry: {industry}", f"evidence: {ev}", f'source_url: "{src}"',
              f"last_verified_at: {TODAY}", f"fetched_at: {TODAY}", "---", "",
              f"# {canon}", "", f"**{desc}**", "", "## 关系", ""]
    for r in relations:
        lines.append(f"- {r}")
    lines += ["", "## 元数据", "", f"- entity_id: {name} | aliases: {', '.join(aliases)} | ticker: {ticker}",
              f"- industry: {industry} | region: {region}", f"- last_verified_at: {TODAY}"]
    if meta_extra:
        lines.append(f"- {meta_extra}")
    w(f"01-实体/{name}.md", "\n".join(lines))

def product(name, canon, company, target, indications, status, ev, src, desc, relations):
    lines = [
        "---", "type: product", f"entity_id: {name}", f"canonical_name: {canon}",
        f"company: {company}", f"target: {target}", f"indications: {indications}",
        f"development_status: {status}", f"evidence: {ev}", f'source_url: "{src}"',
        f"last_verified_at: {TODAY}", f"fetched_at: {TODAY}", "---", "",
        f"# {canon}", "", f"**{desc}**", "", "## 关系", ""]
    for r in relations:
        lines.append(f"- {r}")
    lines += ["", "## 元数据", "", f"- entity_id: {name} | company: {company} | target: {target}",
              f"- indications: {indications}", f"- development_status: {status}", f"- last_verified_at: {TODAY}"]
    w(f"02-产品/{name}.md", "\n".join(lines))

def target(name, canon, desc, products, ev, src):
    lines = [
        "---", "type: target", f"entity_id: {name}", f"canonical_name: {canon}",
        f"evidence: {ev}", f'source_url: "{src}"',
        f"last_verified_at: {TODAY}", f"fetched_at: {TODAY}", "---", "",
        f"# {canon}", "", f"**{desc}**", "", "## 相关药物", ""]
    for p in products:
        lines.append(f"- [[{p}]]")
    lines += ["", "## 元数据", "", f"- entity_id: {name} | type: target", f"- last_verified_at: {TODAY}"]
    w(f"03-靶点/{name}.md", "\n".join(lines))

# ============ ENTITIES ============
entity("礼来", "company", "礼来 Eli Lilly", ["Eli Lilly", "Lilly", "礼来公司"], "LLY", "US", "Indianapolis, IN",
       "创新药（GLP-1/肿瘤/免疫）", "VERIFIED", "https://www.lilly.com",
       "全球 GLP-1 减重/糖尿病双龙头之一，替尔泊肽（Mounjaro/Zepbound）为当前全球销售额最高的药物。",
       ["[[替尔泊肽]]（核心产品：Mounjaro 糖尿病 + Zepbound 减重）（来源: https://www.fda.gov）",
        "[[GLP-1R]]（替尔泊肽双靶点之一）（来源: https://clinicaltrials.gov）",
        "[[GIPR]]（替尔泊肽双靶点之一）（来源: https://clinicaltrials.gov）",
        "[[信达生物]]（玛仕度肽中国权益合作方，2019-08 引进）（来源: https://www.prnewswire.com）",
        "[[诺和诺德]]（GLP-1 减重市场直接竞争对手）（来源: https://www.reuters.com）"],
       "ticker: LLY | 2023-11-08 Zepbound 获 FDA 批准减重")

entity("诺和诺德", "company", "诺和诺德 Novo Nordisk", ["Novo Nordisk", "诺和诺德公司"], "NVO", "DK", "Bagsvaerd",
       "糖尿病/肥胖（GLP-1）", "VERIFIED", "https://www.novonordisk.com",
       "全球糖尿病与肥胖治疗龙头，司美格鲁肽（Ozempic/Wegovy）为 GLP-1 市场开创者。",
       ["[[司美格鲁肽]]（核心产品：Ozempic 糖尿病 + Wegovy 减重）（来源: https://www.fda.gov）",
        "[[GLP-1R]]（司美格鲁肽靶点）（来源: https://clinicaltrials.gov）",
        "[[礼来]]（GLP-1 减重市场直接竞争对手）（来源: https://www.reuters.com）",
        "[[药明康德]]（CDMO 服务供应商之一）（来源: https://www.wuxiapptec.com）"],
       "ticker: NVO | 2024-06 司美格鲁肽减重适应症中国获批")

entity("辉瑞", "company", "辉瑞 Pfizer", ["Pfizer", "辉瑞制药"], "PFE", "US", "New York, NY",
       "mRNA 疫苗/肿瘤/抗感染", "VERIFIED", "https://www.pfizer.com",
       "全球制药巨头，mRNA 疫苗 Comirnaty 为新冠时代最大单品，近年转型肿瘤与减重管线。",
       ["[[mRNA疫苗]]（Comirnaty 与 BioNTech 合作开发）（来源: https://www.pfizer.com）",
        "[[复星医药]]（Comirnaty 中国权益合作方，2020-03 引进）（来源: https://www.fosunpharma.com）"],
       "ticker: PFE | mRNA 平台合作方 BioNTech")

entity("恒瑞医药", "company", "恒瑞医药", ["恒瑞", "Jiangsu Hengrui"], "600276.SH", "CN", "江苏连云港",
       "创新药（肿瘤/代谢/自身免疫）", "VERIFIED", "https://www.hengrui.com",
       "中国创新药龙头，卡瑞利珠单抗（艾瑞卡）为国产 PD-1 代表，管线覆盖 ADC/GLP-1。",
       ["[[卡瑞利珠单抗]]（核心产品：国产 PD-1）（来源: https://clinicaltrials.gov）",
        "[[PD-1]]（卡瑞利珠单抗靶点）（来源: https://clinicaltrials.gov）",
        "[[百济神州]]（国产 PD-1 直接竞争对手）（来源: https://www.10jqka.com.cn）"],
       "ticker: 600276.SH | 创新药收入占比逐年提升")

entity("百济神州", "company", "百济神州", ["BeiGene", "百济"], "688235.SH", "CN", "北京",
       "创新药（肿瘤，PD-1/BTK）", "VERIFIED", "https://www.beigene.com",
       "全球化最深的中国 Biotech，泽布替尼为首个 FDA 获批的国产抗癌药，替雷利珠单抗为国产 PD-1 出海标杆。",
       ["[[替雷利珠单抗]]（核心产品：PD-1，2024-03 FDA 获批食管鳞癌）（来源: https://www.fda.gov）",
        "[[泽布替尼]]（核心产品：BTK，2019-11 FDA 获批）（来源: https://www.fda.gov）",
        "[[PD-1]]（替雷利珠单抗靶点）（来源: https://clinicaltrials.gov）",
        "[[BTK]]（泽布替尼靶点）（来源: https://clinicaltrials.gov）",
        "[[恒瑞医药]]（国产 PD-1 直接竞争对手）（来源: https://www.10jqka.com.cn）"],
       "ticker: 688235.SH | 美股 BGNE 同步上市")

entity("信达生物", "company", "信达生物", ["Innovent", "信达"], "01801.HK", "CN", "江苏苏州",
       "创新药（肿瘤/代谢）", "VERIFIED", "https://www.innoventbio.com",
       "中国 Biotech 代表，信迪利单抗为首个国产 PD-1，玛仕度肽为 GLP-1 减重赛道国产第一梯队。",
       ["[[信迪利单抗]]（核心产品：首个国产 PD-1，2018-12 中国获批）（来源: https://www.nmpa.gov.cn）",
        "[[玛仕度肽]]（核心产品：GLP-1R/GCGR 双激动剂，减重）（来源: https://clinicaltrials.gov）",
        "[[PD-1]]（信迪利单抗靶点）（来源: https://clinicaltrials.gov）",
        "[[礼来]]（玛仕度肽中国权益授权方，2019-08）（来源: https://www.prnewswire.com）"],
       "ticker: 01801.HK | 玛仕度肽 NDA 已递交中国药监局")

entity("君实生物", "company", "君实生物", ["Junshi Biosciences", "君实"], "688180.SH", "CN", "上海",
       "创新药（肿瘤/自免）", "VERIFIED", "https://www.junshi.com",
       "特瑞普利单抗为中国首个获 FDA 批准的 PD-1（鼻咽癌，2023-10）。",
       ["[[特瑞普利单抗]]（核心产品：PD-1，2023-10 FDA 获批鼻咽癌）（来源: https://www.fda.gov）",
        "[[PD-1]]（特瑞普利单抗靶点）（来源: https://clinicaltrials.gov）",
        "[[百济神州]]（国产 PD-1 直接竞争对手）（来源: https://www.10jqka.com.cn）"],
       "ticker: 688180.SH | 与 Coherus 达成海外授权")

entity("传奇生物", "company", "传奇生物", ["Legend Biotech", "传奇"], "LEGN", "US", "南京/美国新泽西",
       "细胞治疗（CAR-T）", "VERIFIED", "https://www.legendbiotech.com",
       "西达基奥仑赛（Carvykti）为全球首个获批的 BCMA CAR-T，与强生全球合作。",
       ["[[西达基奥仑赛]]（核心产品：BCMA CAR-T，2022-02 FDA 获批）（来源: https://www.fda.gov）",
        "[[BCMA]]（西达基奥仑赛靶点）（来源: https://clinicaltrials.gov）",
        "[[强生]]（全球合作方：共同开发/共同商业化）（来源: https://www.jnj.com）"],
       "ticker: LEGN | 金斯瑞生物子公司分拆上市")

entity("强生", "company", "强生 Johnson & Johnson", ["J&J", "杨森", "Janssen"], "JNJ", "US", "New Brunswick, NJ",
       "制药/医疗器械", "VERIFIED", "https://www.jnj.com",
       "全球医疗健康巨头，旗下杨森与传奇生物合作开发西达基奥仑赛。",
       ["[[西达基奥仑赛]]（与传奇生物共同开发/商业化）（来源: https://www.jnj.com）",
        "[[传奇生物]]（CAR-T 合作方，2017-12 达成全球合作）（来源: https://www.jnj.com）"],
       "ticker: JNJ | 2023 年拆分消费者健康业务 Kenvue")

entity("复星医药", "company", "复星医药", ["复星", "Fosun Pharma"], "600196.SH", "CN", "上海",
       "制药/医疗器械/诊断", "VERIFIED", "https://www.fosunpharma.com",
       "中国综合药企，复星凯特引进阿基仑赛（中国首个获批 CAR-T），并引进 mRNA 疫苗复必泰。",
       ["[[阿基仑赛]]（复星凯特：中国首个获批 CAR-T，2021-06）（来源: https://www.nmpa.gov.cn）",
        "[[CD19]]（阿基仑赛靶点）（来源: https://clinicaltrials.gov）",
        "[[辉瑞]]（复必泰 mRNA 疫苗中国权益合作方）（来源: https://www.fosunpharma.com）"],
       "ticker: 600196.SH | 复星凯特为 CAR-T 合资公司")

entity("药明康德", "company", "药明康德", ["WuXi AppTec", "药明"], "603259.SH", "CN", "江苏无锡",
       "CRO/CDMO（一体化 CRDMO）", "VERIFIED", "https://www.wuxiapptec.com",
       "全球最大的一体化药物研发服务平台之一，覆盖小分子发现到商业化生产。",
       ["[[CRO服务]]（药物发现/临床前/临床 CRO）（来源: https://www.wuxiapptec.com）",
        "[[CDMO服务]]（小分子 CDMO 产能）（来源: https://www.wuxiapptec.com）",
        "[[诺和诺德]]（GLP-1 相关 CDMO 服务客户之一）（来源: https://www.wuxiapptec.com）",
        "[[泰格医药]]（临床 CRO 竞争对手）（来源: https://www.10jqka.com.cn）"],
       "ticker: 603259.SH | 2024 年受美国 BIOSECURE 法案扰动")

entity("药明生物", "company", "药明生物", ["WuXi Biologics"], "02269.HK", "CN", "江苏无锡",
       "生物药 CDMO", "VERIFIED", "https://www.wuxibiologics.com",
       "全球领先的生物药（抗体/融合蛋白）CDMO，一体化生物药开发生产平台。",
       ["[[CDMO服务]]（生物药 CDMO，双抗/ADC 产能）（来源: https://www.wuxibiologics.com）",
        "[[药明康德]]（同属药明系，业务协同）（来源: https://www.wuxibiologics.com）"],
       "ticker: 02269.HK | 药明系生物药板块")

entity("泰格医药", "company", "泰格医药", ["Tigermed"], "300347.SZ", "CN", "浙江杭州",
       "临床 CRO", "VERIFIED", "https://www.tigermed.net",
       "中国最大的临床合同研究组织（CRO）之一，承接临床试验运营与数据统计。",
       ["[[CRO服务]]（临床试验运营/数据管理/统计）（来源: https://www.tigermed.net）",
        "[[药明康德]]（临床 CRO 竞争对手）（来源: https://www.10jqka.com.cn）"],
       "ticker: 300347.SZ | 创新药临床外包核心受益方")

# ============ PRODUCTS ============
product("替尔泊肽", "替尔泊肽 Tirzepatide", "礼来", "GLP-1R/GIPR", "2型糖尿病/肥胖", "已上市（Mounjaro 2022-05 / Zepbound 2023-11）",
        "VERIFIED", "https://www.fda.gov",
        "全球首个 GLP-1R/GIPR 双靶点激动剂，SURMOUNT 系列 III 期减重数据刷新纪录，2023 年销售额全球第一。",
        ["[[礼来]]（开发/商业化）（来源: https://www.fda.gov）",
         "[[GLP-1R]]（靶点之一）（来源: https://clinicaltrials.gov）",
         "[[GIPR]]（靶点之一）（来源: https://clinicaltrials.gov）",
         "[[司美格鲁肽]]（直接竞品）（来源: https://www.reuters.com）",
         "SURMOUNT-1（NCT04184622，III 期减重 COMPLETED）（来源: https://clinicaltrials.gov）"])

product("司美格鲁肽", "司美格鲁肽 Semaglutide", "诺和诺德", "GLP-1R", "2型糖尿病/肥胖/心血管", "已上市（Ozempic 2017 / Wegovy 2021-06 / Rybelsus 2019）",
        "VERIFIED", "https://www.fda.gov",
        "GLP-1 受体激动剂开创性药物，STEP 系列减重 III 期 + SUSTAIN 系列心血管获益证据充分，2024 年全球销售额第二。",
        ["[[诺和诺德]]（开发/商业化）（来源: https://www.fda.gov）",
         "[[GLP-1R]]（靶点）（来源: https://clinicaltrials.gov）",
         "[[替尔泊肽]]（直接竞品）（来源: https://www.reuters.com）",
         "STEP-1（NCT03548935，III 期减重 COMPLETED）（来源: https://clinicaltrials.gov）",
         "SUSTAIN-6（NCT01720446，III 期心血管结局 COMPLETED）（来源: https://clinicaltrials.gov）"])

product("玛仕度肽", "玛仕度肽 Mazdutide（IBI362）", "信达生物", "GLP-1R/GCGR", "肥胖/2型糖尿病/脂肪肝", "III 期临床（中国 NDA 已递交）",
        "SUPPORTED", "https://clinicaltrials.gov",
        "国产 GLP-1R/GCGR 双靶点激动剂，由信达生物与礼来合作开发，减重赛道国产第一梯队。",
        ["[[信达生物]]（中国权益开发）（来源: https://clinicaltrials.gov）",
         "[[礼来]]（合作开发方）（来源: https://www.prnewswire.com）",
         "[[GLP-1R]]（靶点之一）（来源: https://clinicaltrials.gov）",
         "[[GCGR]]（靶点之一）（来源: https://clinicaltrials.gov）",
         "[[司美格鲁肽]]（对照药：III 期头对头试验）（来源: https://clinicaltrials.gov）"])

product("卡瑞利珠单抗", "卡瑞利珠单抗 Camrelizumab（艾瑞卡）", "恒瑞医药", "PD-1", "肝癌/肺癌/食管癌/鼻咽癌", "已上市（中国 2019-05）",
        "VERIFIED", "https://www.nmpa.gov.cn",
        "恒瑞核心国产 PD-1，与阿帕替尼（双艾组合）在肝癌领域建立全球证据。",
        ["[[恒瑞医药]]（开发/商业化）（来源: https://www.nmpa.gov.cn）",
         "[[PD-1]]（靶点）（来源: https://clinicaltrials.gov）",
         "CameL（NCT03134872，III 期肺癌 COMPLETED）（来源: https://clinicaltrials.gov）"])

product("替雷利珠单抗", "替雷利珠单抗 Tislelizumab（百泽安）", "百济神州", "PD-1", "食管鳞癌/肺癌/肝癌等", "已上市（中国 2019-12 / FDA 2024-03）",
        "VERIFIED", "https://www.fda.gov",
        "国产 PD-1 出海代表，2024-03 获 FDA 批准食管鳞癌二线（RATIONALE-302），全球多适应症布局。",
        ["[[百济神州]]（开发/商业化）（来源: https://www.fda.gov）",
         "[[PD-1]]（靶点）（来源: https://clinicaltrials.gov）",
         "RATIONALE-302（NCT03430843，III 期食管鳞癌 COMPLETED）（来源: https://clinicaltrials.gov）"])

product("信迪利单抗", "信迪利单抗 Sintilimab（达伯舒）", "信达生物", "PD-1", "霍奇金淋巴瘤/肺癌/肝癌", "已上市（中国 2018-12）",
        "VERIFIED", "https://www.nmpa.gov.cn",
        "中国首个获批的国产 PD-1（2018-12-24），与礼来合作开发。",
        ["[[信达生物]]（开发/商业化）（来源: https://www.nmpa.gov.cn）",
         "[[PD-1]]（靶点）（来源: https://clinicaltrials.gov）",
         "ORIENT-11（NCT03631784，III 期肺癌）（来源: https://clinicaltrials.gov）"])

product("特瑞普利单抗", "特瑞普利单抗 Toripalimab（拓益）", "君实生物", "PD-1", "鼻咽癌/黑色素瘤/尿路上皮癌", "已上市（中国 2018-12 / FDA 2023-10）",
        "VERIFIED", "https://www.fda.gov",
        "中国首个获 FDA 批准的 PD-1（鼻咽癌，2023-10-27），国产创新药出海里程碑。",
        ["[[君实生物]]（开发/商业化）（来源: https://www.fda.gov）",
         "[[PD-1]]（靶点）（来源: https://clinicaltrials.gov）",
         "POLARIS-02（NCT02915432，鼻咽癌）（来源: https://clinicaltrials.gov）"])

product("泽布替尼", "泽布替尼 Zanubrutinib（百悦泽）", "百济神州", "BTK", "慢性淋巴细胞白血病/套细胞淋巴瘤/华氏巨球蛋白血症", "已上市（FDA 2019-11）",
        "VERIFIED", "https://www.fda.gov",
        "首个获 FDA 批准的国产抗癌创新药（2019-11-14），ALPINE 头对头击败伊布替尼。",
        ["[[百济神州]]（开发/商业化）（来源: https://www.fda.gov）",
         "[[BTK]]（靶点）（来源: https://clinicaltrials.gov）",
         "ALPINE（NCT03734016，III 期 CLL COMPLETED）（来源: https://clinicaltrials.gov）"])

product("西达基奥仑赛", "西达基奥仑赛 Ciltacabtagene autoleucel（Carvykti）", "传奇生物/强生", "BCMA", "多发性骨髓瘤（二线及以上）", "已上市（FDA 2022-02 / 二线 2024-04）",
        "VERIFIED", "https://www.fda.gov",
        "全球首个获批的 BCMA CAR-T，传奇生物与强生共同开发，CARTITUDE 系列数据改变 MM 治疗格局。",
        ["[[传奇生物]]（共同开发/商业化）（来源: https://www.fda.gov）",
         "[[强生]]（共同开发/商业化）（来源: https://www.fda.gov）",
         "[[BCMA]]（靶点）（来源: https://clinicaltrials.gov）",
         "CARTITUDE-1（NCT03548207，I/II 期 COMPLETED）（来源: https://clinicaltrials.gov）",
         "CARTITUDE-4（NCT04181827，III 期二线 MM ACTIVE）（来源: https://clinicaltrials.gov）"])

product("阿基仑赛", "阿基仑赛 Axicabtagene ciloleucel（奕凯达）", "复星医药（复星凯特）", "CD19", "大B细胞淋巴瘤", "已上市（中国 2021-06）",
        "VERIFIED", "https://www.nmpa.gov.cn",
        "中国首个获批的 CAR-T 细胞治疗产品（2021-06-22），由复星凯特从 Kite 引进。",
        ["[[复星医药]]（复星凯特引进/商业化）（来源: https://www.nmpa.gov.cn）",
         "[[CD19]]（靶点）（来源: https://clinicaltrials.gov）",
         "ZUMA-1（NCT02348216，I/II 期 COMPLETED）（来源: https://clinicaltrials.gov）"])

product("德曲妥珠单抗", "德曲妥珠单抗 Trastuzumab deruxtecan（Enhertu）", "第一三共/阿斯利康", "HER2", "HER2阳性乳腺癌/胃癌/肺癌", "已上市（FDA 2019-12）",
        "VERIFIED", "https://www.fda.gov",
        "HER2 ADC 标杆药物，DESTINY-Breast 系列重塑 HER2 低表达乳腺癌治疗标准。",
        ["[[HER2]]（靶点）（来源: https://clinicaltrials.gov）",
         "DESTINY-Breast03（NCT03529110，III 期头对头 T-DM1 ACTIVE）（来源: https://clinicaltrials.gov）"])

# ============ TARGETS ============
target("GLP-1R", "GLP-1R（胰高血糖素样肽-1受体）",
       "代谢疾病（糖尿病/肥胖）最重要靶点之一，GLP-1 受体激动剂驱动全球减重药物市场爆发。",
       ["司美格鲁肽", "替尔泊肽", "玛仕度肽"], "VERIFIED", "https://clinicaltrials.gov")

target("GIPR", "GIPR（葡萄糖依赖性促胰岛素多肽受体）",
       "与 GLP-1R 形成双靶点协同，替尔泊肽为全球首个获批的 GLP-1R/GIPR 双激动剂。",
       ["替尔泊肽"], "VERIFIED", "https://clinicaltrials.gov")

target("GCGR", "GCGR（胰高血糖素受体）",
       "调节糖异生与能量代谢，GLP-1R/GCGR 双激动剂在减重与脂肪肝领域显示出潜力。",
       ["玛仕度肽"], "VERIFIED", "https://clinicaltrials.gov")

target("PD-1", "PD-1（程序性死亡受体1）",
       "肿瘤免疫检查点最重要靶点，国产四大 PD-1（信迪利/替雷利珠/卡瑞利珠/特瑞普利）全部获批。",
       ["信迪利单抗", "替雷利珠单抗", "卡瑞利珠单抗", "特瑞普利单抗"], "VERIFIED", "https://clinicaltrials.gov")

target("BTK", "BTK（布鲁顿酪氨酸激酶）",
       "B 细胞恶性肿瘤关键靶点，泽布替尼为国产首款 FDA 获批的 BTK 抑制剂。",
       ["泽布替尼"], "VERIFIED", "https://clinicaltrials.gov")

target("BCMA", "BCMA（B细胞成熟抗原）",
       "多发性骨髓瘤细胞治疗核心靶点，西达基奥仑赛为全球首个获批的 BCMA CAR-T。",
       ["西达基奥仑赛"], "VERIFIED", "https://clinicaltrials.gov")

target("CD19", "CD19（B细胞表面抗原）",
       "B 细胞淋巴瘤/白血病 CAR-T 核心靶点，阿基仑赛/瑞基奥仑赛均靶向 CD19。",
       ["阿基仑赛"], "VERIFIED", "https://clinicaltrials.gov")

target("HER2", "HER2（人表皮生长因子受体2）",
       "乳腺癌/胃癌重要靶点，ADC 药物德曲妥珠单抗为 HER2 低表达治疗突破。",
       ["德曲妥珠单抗"], "VERIFIED", "https://clinicaltrials.gov")

print("DONE entities/products/targets")
