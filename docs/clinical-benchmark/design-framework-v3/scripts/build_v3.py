#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
SVG_DIR = ROOT / "svg"
PNG_DIR = ROOT / "output" / "png"
DOCS_DIR = ROOT / "docs"
for d in (SVG_DIR, PNG_DIR, DOCS_DIR):
    d.mkdir(parents=True, exist_ok=True)

FONT = "Microsoft YaHei, Noto Sans CJK SC, sans-serif"
C = {
    "ink": "#17324D", "text": "#243746", "muted": "#687481", "line": "#8091A0",
    "blue": "#2C6E9F", "blue_bg": "#DCEAF7", "green": "#2E7D5B", "green_bg": "#E1F1E8",
    "purple": "#6B52A3", "purple_bg": "#ECE4F7", "orange": "#B76820", "orange_bg": "#FBE9D7",
    "red": "#A74444", "red_bg": "#F8DEDE", "teal": "#237B75", "teal_bg": "#DDF2F0",
    "yellow": "#9A7212", "yellow_bg": "#FFF3C9", "gray_bg": "#F4F6F8", "white": "#FFFFFF",
}

class SVG:
    def __init__(self, width: int, height: int, title: str, subtitle: str = ""):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<defs>',
            '<marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#687481"/></marker>',
            '<marker id="arrowRed" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#A74444"/></marker>',
            '</defs>',
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        ]
        self.text(60, 62, title, 34, C["ink"], 700)
        if subtitle:
            self.text(60, 98, subtitle, 18, C["muted"], 400)

    def rect(self, x, y, w, h, fill, stroke=None, sw=2, rx=16):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}/>')

    def line(self, x1, y1, x2, y2, color=None, sw=3, arrow=True, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or C["muted"]}" stroke-width="{sw}"{extra}{marker}/>')

    def path(self, d, color=None, sw=3, arrow=True, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color or C["muted"]}" stroke-width="{sw}"{extra}{marker}/>')

    def text(self, x, y, content, size=18, color=None, weight=400, anchor="start"):
        self.parts.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color or C["text"]}">{escape(str(content))}</text>'
        )

    def multiline(self, x, y, lines, size=17, color=None, weight=400, leading=1.35, anchor="start"):
        spans = []
        for i, line in enumerate(lines):
            dy = "0" if i == 0 else f"{size*leading:.1f}"
            spans.append(f'<tspan x="{x}" dy="{dy}">{escape(str(line))}</tspan>')
        self.parts.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color or C["text"]}">' + "".join(spans) + '</text>'
        )

    def pill(self, x, y, w, label, fill, text_color=C["white"]):
        self.rect(x, y, w, 38, fill, None, rx=19)
        self.text(x+w/2, y+26, label, 17, text_color, 700, "middle")

    def card(self, x, y, w, h, title, lines, fill, stroke, title_size=21, body_size=16):
        self.rect(x, y, w, h, fill, stroke)
        self.text(x+18, y+34, title, title_size, C["ink"], 700)
        self.multiline(x+18, y+66, lines, body_size, C["text"], 400)

    def save(self, name):
        self.parts.append('</svg>')
        path = SVG_DIR / name
        path.write_text("\n".join(self.parts) + "\n", encoding="utf-8")
        return path


def overview():
    s = SVG(1800, 1080, "V3 总框架：从临床世界到可部署能力边界", "一张图只保留六个一级模块；每个复杂模块在后续子图展开")
    s.rect(60, 125, 1680, 70, C["yellow_bg"], C["yellow"], 2, 14)
    s.text(900, 168, "核心对象不是一道题，而是：一个可证伪 Claim 经过实验、测量、复现与攻防后形成的证据包", 22, C["ink"], 700, "middle")
    cards = [
        ("1 临床世界", ["患者旅程 + 决策链", "定义真实要解决的问题"], C["blue_bg"], C["blue"]),
        ("2 实验网络", ["Hypothesis + Estimand", "C0–C4 + 6 axes × L0–L4"], C["green_bg"], C["green"]),
        ("3 测量仪器", ["Oracle + Rubric", "Checker + Judge"], C["purple_bg"], C["purple"]),
        ("4 执行与复现", ["FSM + Episode", "seed ⊂ instance ⊂ family"], C["teal_bg"], C["teal"]),
        ("5 对抗验证", ["Red → Blue → Purple", "CAUGHT / SURVIVED / VOID"], C["red_bg"], C["red"]),
        ("6 边界输出", ["Failure Profile", "Capability → Deployment"], C["orange_bg"], C["orange"]),
    ]
    x0, y, w, h, gap = 60, 270, 250, 190, 34
    for i,(title,lines,fill,stroke) in enumerate(cards):
        x=x0+i*(w+gap)
        s.card(x,y,w,h,title,lines,fill,stroke,20,17)
        if i < len(cards)-1:
            s.line(x+w,y+h/2,x+w+gap-8,y+h/2)
    s.pill(60, 520, 300, "横向合同：全链可追溯", C["ink"])
    gov = [
        ("Claim Contract", "允许说什么"), ("Version Binding", "版本与 hash"),
        ("Clinical Governance", "gold / 隐私 / 地区"), ("Release Gate", "工程≠科学≠准入"),
    ]
    for i,(a,b) in enumerate(gov):
        x=60+i*420
        s.card(x,585,375,125,a,[b],C["gray_bg"],C["line"],20,17)
    s.rect(60, 770, 1680, 190, C["gray_bg"], C["ink"], 2, 18)
    s.text(90, 810, "总框架的唯一主线", 23, C["ink"], 700)
    s.multiline(90, 855, [
        "临床问题决定要测什么；实验网络决定怎样排除替代解释；测量仪器决定怎样裁决；",
        "执行与复现决定结果是否稳定；对抗验证决定高分是否来自捷径；最后才允许输出能力与部署边界。",
        "任一前门失败，后门不得用总分补偿。",
    ], 20, C["text"], 400, 1.45)
    s.text(900, 1020, "展开图：题量｜临床过程｜因果实验｜测量仪器｜攻防｜准入", 19, C["muted"], 700, "middle")
    return s.save("00-高度概括总图.svg")


def quantity():
    s = SVG(1800, 1460, "V3 题量：完整网络是稀疏张量，72 只是一条 Pilot 切片", "按非空错误类型总数 N 计算；不存在的 stage × mechanism 组合不造题")
    s.pill(60,125,300,"A 先定义稀疏错误网络",C["blue"])
    s.card(60,185,500,155,"6 个 Process Stages",["S1 信息提取 → S6 复核输出","每个错误必须绑定一个 stage"],C["blue_bg"],C["blue"],21,17)
    s.line(560,262,625,262)
    s.card(650,185,500,155,"3 个 Attribution Layers",["Decision / Algorithm / Engineering","不是每个 stage 都必须三类齐全"],C["purple_bg"],C["purple"],21,17)
    s.line(1150,262,1215,262)
    s.card(1240,185,500,155,"n(s,m) 个 Error Types",["每个非空格可有多个具体错误","N = Σ n(s,m)"],C["orange_bg"],C["orange"],21,17)
    s.text(900,385,"只有 18 个格全部非空且每格同为 n 个错误时，才可写成 N = 6 × 3 × n。",21,C["red"],700,"middle")

    s.pill(60,430,350,"B 每个错误类型的实验槽位",C["green"])
    s.card(60,490,500,170,"Control Block",["5 个成组对照：C0–C4","用于干预 / 特异性 / 检出 / 救援"],C["green_bg"],C["green"],22,18)
    s.text(610,580,"+",34,C["ink"],700,"middle")
    s.card(650,490,500,170,"Pressure Block",["6 个独立 pressure axes","每轴 L0–L4 共 5 个梯度"],C["teal_bg"],C["teal"],22,18)
    s.text(1200,580,"=",34,C["ink"],700,"middle")
    s.card(1240,490,500,170,"35 Planned Slots",["5 + 6 × 5 = 35","压力与对照在设计矩阵中分列"],C["yellow_bg"],C["yellow"],22,18)
    s.text(900,705,"若六轴共享同一个 L0 基线：独特题面 = 5 + 6 × (5−1) = 29；重复 L0 属运行槽位，不虚增题库。",20,C["ink"],700,"middle")

    s.pill(60,755,310,"C 乘 clinical instances",C["purple"])
    s.rect(60,815,1680,150,C["purple_bg"],C["purple"])
    s.text(900,865,"完整题库：Q_slots = 35 × I × N    ｜    Q_unique = 29 × I × N",29,C["ink"],700,"middle")
    s.text(900,915,"推荐 I = 3 个 genuine sibling instances：Q_slots = 105N；Q_unique = 87N",23,C["text"],700,"middle")

    scenarios=[
        ("稠密下界 n=1",["N=18","1890 slots / 1566 unique","5670 episodes/模型（3 runs）"]),
        ("稠密 n=2",["N=36","3780 slots / 3132 unique","11340 episodes/模型（3 runs）"]),
        ("稠密 n=3",["N=54","5670 slots / 4698 unique","17010 episodes/模型（3 runs）"]),
    ]
    for i,(a,b) in enumerate(scenarios):
        x=60+i*560
        s.card(x,1025,510,195,a,b,[C["gray_bg"],C["yellow_bg"],C["orange_bg"]][i],[C["line"],C["yellow"],C["orange"]][i],22,18)

    s.pill(60,1275,280,"D 72 的正确定位",C["red"])
    s.rect(60,1335,1680,80,C["red_bg"],C["red"])
    s.text(900,1385,"72 = 旧版 H1–H3 最小 Pilot 切片；不是完整 stage × mechanism × error-type 网络总题量。",21,C["red"],700,"middle")
    return s.save("01-题量计算与单位.svg")


def clinical():
    s=SVG(1800,1300,"V3 临床世界：旅程提供场景，决策链提供可定位的失效环节","疾病名不是出题骨架；每个 Failure Hypothesis 必须绑定一个 canonical stage")
    s.pill(60,125,280,"A 第一版三段患者旅程",C["blue"])
    journeys=[
        ("J01 首次咨询",["信息不足 → 关键追问","风险升级 / 是否立即就医"]),
        ("J02 二次核验",["已有判断 / 检查结果","来源权重 / 冲突处理"]),
        ("J03 治疗后变化",["恶化 / 再就医","纵向状态 / 新证据更新"]),
    ]
    for i,(a,b) in enumerate(journeys):
        x=60+i*560
        s.card(x,185,510,150,a,b,C["blue_bg"],C["blue"],23,18)
        if i<2:s.line(x+510,260,x+545,260)
    s.pill(60,390,280,"B 可观察决策过程链",C["green"])
    stages=[
        ("S1","事实提取","读全了吗"),("S2","问题分解","拆对了吗"),("S3","证据处理","算对了吗"),
        ("S4","决策选择","选对了吗"),("S5","工具执行","做对了吗"),("S6","复核输出","说对了吗"),
    ]
    for i,(sid,name,q) in enumerate(stages):
        x=60+i*280
        s.card(x,450,240,135,f"{sid} {name}",[q],C["green_bg"],C["green"],20,17)
        if i<5:s.line(x+240,518,x+265,518)
    s.pill(60,650,310,"C Failure Hypothesis 生成",C["orange"])
    s.card(60,710,500,180,"一个 hypothesis 必填",["目标 journey + canonical stage","可观察错误 + 目标压力","竞争解释 + 预期方向"],C["orange_bg"],C["orange"],22,18)
    s.card(650,710,500,180,"允许归因",["决策：看见但选错行动","算法：信息处理/更新错误","工程：状态/工具执行偏离"],C["purple_bg"],C["purple"],22,18)
    s.card(1240,710,500,180,"禁止偷换",["输出错误 ≠ 读到内部思维","无法排除上游传播时","状态必须是 UNRESOLVED"],C["red_bg"],C["red"],22,18)
    s.pill(60,955,350,"D 当前脑卒中 reference family",C["teal"])
    hs=[
        ("H1 风险升级",["短暂改善 / 锚定 / 阻力","不应推迟 120 路径"]),
        ("H2 时间状态",["发病时间 vs 最后正常时间","跨轮不得丢失或补造"]),
        ("H3 来源权重",["相同 claim 改来源标签","结论强度应有可解释变化"]),
    ]
    for i,(a,b) in enumerate(hs):
        x=60+i*560
        s.card(x,1015,510,165,a,b,C["teal_bg"],C["teal"],22,18)
    s.text(900,1245,"三条是假设，不是已证实模型规律；当前只有 H1 的一个 clinical instance 已实例化。",19,C["red"],700,"middle")
    return s.save("02-临床旅程与失败假设.svg")


def causal():
    s=SVG(1800,1540,"V3 因果实验网络：从 Claim 到可升级结论","Estimand 决定测什么；C0–C4 排除替代解释；G0–G7 决定最多能说到哪一步")
    s.pill(60,125,300,"A 实验族输入合同",C["orange"])
    s.card(60,185,520,170,"Failure Hypothesis",["目标阶段 + 目标压力","预期错误方向 + 替代解释"],C["orange_bg"],C["orange"],22,18)
    s.line(580,270,630,270)
    s.card(650,185,520,170,"Estimand Contract",["单位 / treatment / outcome","contrast / missingness / decision rule"],C["yellow_bg"],C["yellow"],22,18)
    s.line(1170,270,1220,270)
    s.card(1240,185,500,170,"冻结不变量",["truth / 必要信息 / 评分机会","模型配置 / 数据边界 / 版本"],C["gray_bg"],C["line"],22,18)

    s.pill(60,410,270,"B C0–C4 实验臂",C["green"])
    controls=[("C0","基线 / P0"),("C1","目标干预 P1–P3"),("C2","阴性对照"),("C3","阳性对照"),("C4","救援/反转")]
    for i,(a,b) in enumerate(controls):
        x=60+i*330
        s.card(x,470,290,120,a,[b],C["green_bg"],C["green"],22,17)
    s.text(900,635,"actual_diff_paths 必须机械证明：除预注册目标字段外，其余语义不变量没有漂移。",19,C["red"],700,"middle")

    s.pill(60,680,330,"C 压力轴与嵌套复现",C["teal"])
    s.card(60,740,520,160,"Pressure",["6 个 axes，各自 L0 → L4","axis interaction 另开 factorial 实验"],C["teal_bg"],C["teal"],22,18)
    s.card(640,740,520,160,"Calibration",["每条轴在 development pilot 校准","冻结后 held-out 不得按结果回调"],C["teal_bg"],C["teal"],22,18)
    s.card(1220,740,520,160,"Replication",["run/seed ⊂ variant ⊂ instance","⊂ family；seed 不是独立题"],C["teal_bg"],C["teal"],22,18)

    s.pill(60,955,290,"D G0–G7 串行门",C["purple"])
    gates=[("G0","测量有效"),("G1","干预效应"),("G2","特异性"),("G3","检出能力"),("G4","救援恢复"),("G5","压力响应"),("G6","多层复现"),("G7","反作弊")]
    for i,(a,b) in enumerate(gates):
        row=i//4; col=i%4; x=60+col*420; y=1015+row*150
        s.card(x,y,380,115,f"{a} {b}",["PASS / FAIL / UNRESOLVED"],C["purple_bg"] if i<6 else C["red_bg"],C["purple"] if i<6 else C["red"],20,15)
        if col<3:s.line(x+380,y+58,x+405,y+58)
    s.rect(60,1345,1680,120,C["gray_bg"],C["ink"])
    s.text(900,1392,"结论阶梯：观察 → 关联 → 机制支持 → 压力曲线 → 稳定模式 → 能力边界",25,C["ink"],700,"middle")
    s.text(900,1432,"前一门失败，后一门结果不得补偿；NOT_TESTED 不能写成 PASS。",19,C["red"],700,"middle")
    return s.save("03-因果实验网络.svg")


def measurement():
    s=SVG(1800,1390,"V3 测量仪器：Oracle、Rubric、Verifier 各自只做一件事","评分系统不是 clinical gold；工程 PASS 不能冒充科学或临床批准")
    s.pill(60,125,330,"A Clinical World Contract",C["blue"])
    s.card(60,185,520,190,"病例真值 + FSM",["当前可见 / 未知 / 未来事实","披露路径 / deadline / 节点状态"],C["blue_bg"],C["blue"],22,18)
    s.card(640,185,520,190,"适用范围",["地区 / 语言 / 人群 / 资源假设","病例性质 / 隐私 / 数据流向"],C["blue_bg"],C["blue"],22,18)
    s.card(1220,185,520,190,"临床依据",["current guideline / evidence version","独立审核 / 分歧仲裁 / 置信度"],C["blue_bg"],C["blue"],22,18)

    s.pill(60,430,270,"B 三层测量架构",C["purple"])
    s.card(60,490,500,185,"Oracle：允许什么",["可接受处置集合","必须 / 禁止 / 时序 / 条件"],C["purple_bg"],C["purple"],23,18)
    s.line(560,582,625,582)
    s.card(650,490,500,185,"Rubric：看哪些维度",["证据来源 / 权重 / 更新","风险升级 / 行动匹配 / 边界"],C["purple_bg"],C["purple"],23,18)
    s.line(1150,582,1215,582)
    s.card(1240,490,500,185,"Verifier：怎样裁决",["Deterministic first","受约束 Judge 只做语义窄判"],C["purple_bg"],C["purple"],23,18)

    s.pill(60,730,330,"C 两层结果，不做总分遮蔽",C["red"])
    s.card(60,790,800,190,"Safety Gate",["延误 / 禁忌 / 未来信息 / 明确危险行动","任何 Critical 事件单列；不能被平均分抵消"],C["red_bg"],C["red"],23,18)
    s.card(940,790,800,190,"Capability Profile",["决策环节 × failure type × pressure","同时报告 usefulness，防全急诊 / 全弃权"],C["green_bg"],C["green"],23,18)

    s.pill(60,1035,310,"D 全链版本与证据绑定",C["ink"])
    s.rect(60,1095,1680,180,C["gray_bg"],C["line"])
    s.multiline(90,1140,[
        "case / truth / FSM / pressure generator / Oracle / Rubric / Checker / Judge prompt",
        "subject model / system prompt / decoding / RAG snapshot / tools / runner / code commit / environment manifest",
        "每个 Failure Report 必须能回到原始 trajectory、裁决依据和版本 hash。",
    ],19,C["text"],400,1.45)
    s.text(900,1340,"临床审核者签 clinical approval；模型、runner、Judge 和 verifier 都无权自我批准。",20,C["red"],700,"middle")
    return s.save("04-测量仪器与临床治理.svg")


def adversarial():
    s=SVG(1800,1510,"V3 极限测试：红队打穿，蓝队封堵，紫队固化为回归门","只攻击自有 benchmark sandbox；目标是发现“表面高分 ≠ 目标能力”的路径")
    s.pill(60,125,270,"A Red Team 攻击面",C["red"])
    attacks=[
        ("策略投机",["全急诊 / 全弃权","超长万金油"]),
        ("Judge Gaming",["指令注入 / rubric 模仿","事后编漂亮 reasoning"]),
        ("Proxy / 污染",["metadata / 文件名 / class prior","sentinel 识别 / canary 命中"]),
        ("Verifier 绕过",["空 checker / 非法状态","NaN / 重复 / 缺失 / 阈值"]),
        ("运行污染",["跨 run 缓存 / 重试计数","旧版本 / 工具伪造 / 状态串病例"]),
    ]
    for i,(a,b) in enumerate(attacks):
        x=60+i*330
        s.card(x,185,290,155,a,b,C["red_bg"],C["red"],20,15)

    s.pill(60,395,280,"B Blue Team 五层防线",C["blue"])
    defenses=[
        ("L1 隔离","separate verifier"),("L2 信息边界","FSM + held-out"),("L3 评分完整性","blocker + coverage"),
        ("L4 构念效度","反事实 + proxy probe"),("L5 测量质量","mutation + false reject"),
    ]
    for i,(a,b) in enumerate(defenses):
        x=60+i*330
        s.card(x,455,290,125,a,[b],C["blue_bg"],C["blue"],20,16)

    s.pill(60,635,300,"C Purple Team 证据闭环",C["purple"])
    flow=[("REGISTER","登记攻击与目标属性"),("LAND","证明 mutation/攻击落地"),("RUN","保存 receipt 与原始输出"),("CLASSIFY","CAUGHT / SURVIVED / VOID"),("FIX + REPLAY","修复后同攻击重放")]
    for i,(a,b) in enumerate(flow):
        x=60+i*330
        s.card(x,695,290,135,a,[b],C["purple_bg"],C["purple"],19,15)
        if i<4:s.line(x+290,763,x+315,763)

    s.pill(60,890,390,"D Verifier 五基线攻击矩阵",C["green"])
    matrix=[("Oracle","PASS"), ("独立科学正确实现","PASS"), ("Naive baseline","FAIL"), ("合理但方法错误","FAIL"), ("Cheat agent","FAIL")]
    for i,(a,b) in enumerate(matrix):
        x=60+i*330
        fill=C["green_bg"] if b=="PASS" else C["red_bg"]
        stroke=C["green"] if b=="PASS" else C["red"]
        s.card(x,950,290,125,a,[b],fill,stroke,19,19)

    s.pill(60,1130,300,"E 极限测试 Release Gate",C["ink"])
    s.rect(60,1190,1680,205,C["gray_bg"],C["ink"])
    s.multiline(90,1235,[
        "所有 Critical 攻击已实际落地且被抓；所有未落地攻击标 VOID，不得计作防御成功；",
        "独立正确实现不被误杀；每条防线有阳性和阴性对照；修复后可重放；",
        "运行隔离、版本、provenance 与恢复 hash 完整；任何 Critical SURVIVED 均阻断发布。",
    ],20,C["text"],400,1.5)
    s.text(900,1460,"Sentinel = 科学哨兵；Canary = 污染探针。二者不能混用，也不能只测误报而不测有效题召回。",19,C["red"],700,"middle")
    return s.save("05-红蓝紫攻防与极限测试.svg")


def release():
    s=SVG(1800,1360,"V3 准入：工程可跑、科学可信、临床可用是三件不同的事","每道门有独立 owner、artifact 和阻断条件")
    s.pill(60,125,310,"A 三道不可替代的准入门",C["ink"])
    gates=[
        ("Gate A 工程有效",["schema / closure / deterministic run","artifact + receipt + version 可复现"],C["blue_bg"],C["blue"]),
        ("Gate B 测量与科学有效",["estimand / controls / pressure / replication","G0–G7 + False Accept/Reject"],C["purple_bg"],C["purple"]),
        ("Gate C 临床与部署准入",["独立 clinical review / 风险预算","适用范围 / human oversight / 责任链"],C["green_bg"],C["green"]),
    ]
    for i,(a,b,fill,stroke) in enumerate(gates):
        x=60+i*560
        s.card(x,185,510,190,a,b,fill,stroke,23,18)
        if i<2:s.line(x+510,280,x+545,280)
    s.text(900,420,"A PASS ≠ B PASS；A+B PASS 也不自动等于 C PASS。",22,C["red"],700,"middle")

    s.pill(60,470,280,"B M0–M5 路线重排",C["orange"])
    phases=[
        ("M0","35 slots / error","单错误类型测量闭环"),("M1","盘点 N","冻结稀疏错误网络"),
        ("M2","105N slots","3 sibling instances / error"),("M3","冻结","合同 / 分区 / 版本"),
        ("M4","完整 Pilot","35 × I × N；不把 run 当题"),("M5","独立复测","held-out / 外部验证"),
    ]
    for i,(a,b,c) in enumerate(phases):
        row=i//3; col=i%3; x=60+col*560; y=530+row*190
        s.card(x,y,510,150,f"{a}  {b}",[c],C["orange_bg"],C["orange"],22,18)

    s.pill(60,950,310,"C 最终不是总分，而是边界包",C["teal"])
    outputs=[
        ("Failure Profile",["哪一环 / 什么错误 / 哪个压力"]),
        ("Capability Boundary",["在哪些条件下仍可靠"]),
        ("Deployment Boundary",["允许自主 / 必须复核 / 禁止"]),
    ]
    for i,(a,b) in enumerate(outputs):
        x=60+i*560
        s.card(x,1010,510,155,a,b,C["teal_bg"],C["teal"],22,18)
        if i<2:s.line(x+510,1088,x+545,1088)
    s.rect(60,1220,1680,80,C["yellow_bg"],C["yellow"])
    s.text(900,1270,"Pilot 输出必须写：研究结果，不构成临床批准；clinical_approval=false 直到真人临床审核者签署。",20,C["ink"],700,"middle")
    return s.save("06-准入门与边界输出.svg")


def docs():
    count_md = """# GroundSignal 出题网络题量计算 V3.1

> 团队内部讨论稿。题量是设计合同，不是已完成数量，也不是统计功效结论。

## 1. 纠正后的总公式

完整出题网络不是固定三个 hypothesis，而是一个稀疏张量：

```text
N = Σ n(s,m)
```

- `s`：6 个 process stages；
- `m`：Decision / Algorithm / Engineering 三个归因层；
- `n(s,m)`：某个 stage × mechanism 格子中实际存在的错误类型数量；
- 不存在的组合记 0，不为凑全笛卡尔积而造题。

只有 18 个格全部非空且每格恰有相同的 `n` 个错误类型时，才可简写：

```text
N = 6 × 3 × n
```

## 2. 每个错误类型的实验槽位

对照与压力分开：

```text
5 个成组对照 + 6 个 pressure axes × 5 个 levels = 35 个计划实验槽位
```

这里的五级压力记为 `L0–L4`。axis interaction 是额外 factorial 实验，不把它叫作第五梯度。

如果六条压力轴共享同一个完全相同的 L0 基线，则不重复的题面为：

```text
5 + 6 × (5−1) = 29 个独特题面
```

因此同时报告两种口径：

- `planned slots`：35，表示预注册实验矩阵的槽位；
- `unique prompts`：29，表示共享 L0 后去重的实际题面。

## 3. 乘 clinical instances

设每个错误类型使用 `I` 个 genuine sibling clinical instances：

```text
Q_slots  = 35 × I × N
Q_unique = 29 × I × N
```

推荐 `I=3` 时：

```text
Q_slots  = 105N
Q_unique = 87N
```

只要总错误类型 `N≥10`，计划槽位就超过 1000；`N≥12` 时，即使共享 L0 去重，独特题面也超过 1000。

## 4. 稠密网络示例

假设 6×3 的所有格子都非空：

- 每格 `n=1`：`N=18`；1890 planned slots；1566 unique prompts；3 runs 为 5670 episodes/模型。
- 每格 `n=2`：`N=36`；3780 planned slots；3132 unique prompts；3 runs 为 11340 episodes/模型。
- 每格 `n=3`：`N=54`；5670 planned slots；4698 unique prompts；3 runs 为 17010 episodes/模型。

## 5. 为什么仍不能直接报一个固定总数

用户指出的“几千道题”在完整网络和 3 个 sibling instances 下是正确量级，但精确总数仍取决于错误类型清单：

```text
先冻结 6×3 稀疏矩阵中的 n(s,m)
→ 得到 N
→ 再计算 105N planned slots / 87N unique prompts
```

`n` 不能凭直觉统一填入；每个错误类型必须满足：可观察、可证伪、可构造对照、可被 verifier 裁决、与相邻错误类型可区分。

## 6. 72 的正确定位

旧版 `3 hypotheses × 3 instances × 8 variants = 72` 只是 H1–H3 的最小 Pilot 切片，不是完整出题网络总量。它可用于先校准测量仪器，但不能代表整个 stage × mechanism × error-type 空间。

## 7. run 不算新题

一次 query 的不同 seed、对话 turn、checker judgment、Judge 重评都属于运行与测量，不增加独立题数。运行预算另算：

```text
episodes / model = Q_slots × repeated runs
```
"""
    (DOCS_DIR/"题量计算-V3.md").write_text(count_md,encoding="utf-8")
    note = """# 出题网络设计框架 V3.1

V3.1 根据完整出题网络纠正题量：一张高度概括总图，六个复杂模块分别拆图。

## 图册

1. `00-高度概括总图.svg`：六模块总框架。
2. `01-题量计算与单位.svg`：稀疏错误网络与千题级计算。
3. `02-临床旅程与失败假设.svg`：旅程、决策链、H1–H3 示例。
4. `03-因果实验网络.svg`：Estimand、C0–C4、6 压力轴×L0–L4、G0–G7。
5. `04-测量仪器与临床治理.svg`：Oracle、Rubric、Verifier 与治理。
6. `05-红蓝紫攻防与极限测试.svg`：攻击面、防御层、紫队闭环。
7. `06-准入门与边界输出.svg`：工程、科学、临床准入分离。

## 题量边界

- 完整题量使用 `N = Σ n(s,m)`，不存在的 stage × mechanism 格子记 0。
- 每个错误类型有 35 个 planned slots；共享六轴 L0 后为 29 个 unique prompts。
- 三个 sibling instances 时为 `105N slots / 87N unique`。
- 72 仅是旧版 H1–H3 Pilot 切片，不是完整网络总题量。
- clinical approval 只能由真人临床审核者签署。
- 本图册不含 author truth、Oracle 明细、Rubric 阈值或隐藏病例答案，可作为公开白名单候选。
"""
    (DOCS_DIR/"设计说明.md").write_text(note,encoding="utf-8")


def html_index(files):
    cards=[]
    for f in files:
        title=f.stem
        cards.append(f'''<article><h2>{escape(title)}</h2><object data="svg/{escape(f.name)}" type="image/svg+xml"></object><p><a href="svg/{escape(f.name)}">单独打开可编辑 SVG</a></p></article>''')
    html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GroundSignal 出题网络设计框架 V3</title><style>body{{font-family:Microsoft YaHei,Noto Sans CJK SC,sans-serif;margin:0;background:#eef2f5;color:#17324D}}header{{padding:32px 5vw;background:#17324D;color:white}}main{{max-width:1500px;margin:28px auto;padding:0 24px}}article{{background:white;border-radius:16px;padding:20px;margin:24px 0;box-shadow:0 4px 18px #0001}}object{{width:100%;height:760px;border:1px solid #d8e0e6;background:white}}a{{color:#2C6E9F}}.lead{{font-size:20px;line-height:1.7}}</style></head><body><header><h1>GroundSignal 出题网络设计框架 V3</h1><p>总图高度概括，复杂模块分图展开。完整题量按稀疏错误网络计算；72 仅是旧版 Pilot 切片。</p></header><main><p class="lead">推荐阅读顺序：总图 → 题量 → 临床过程 → 因果实验 → 测量仪器 → 攻防 → 准入。</p>{''.join(cards)}</main></body></html>'''
    (ROOT/"出题网络-设计框架-V3.html").write_text(html,encoding="utf-8")


def main():
    docs()
    files=[overview(),quantity(),clinical(),causal(),measurement(),adversarial(),release()]
    html_index(files)
    print(f"generated {len(files)} SVG files in {SVG_DIR}")

if __name__ == "__main__":
    main()
