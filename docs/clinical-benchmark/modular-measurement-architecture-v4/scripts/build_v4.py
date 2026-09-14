#!/usr/bin/env python3
from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG_DIR = ROOT / "svg"
DOCS_DIR = ROOT / "docs"
PNG_DIR = ROOT / "output" / "png"
for d in (SVG_DIR, DOCS_DIR, PNG_DIR):
    d.mkdir(parents=True, exist_ok=True)

FONT = "Microsoft YaHei, Noto Sans CJK SC, sans-serif"
C = {
    "ink":"#17324D", "text":"#263847", "muted":"#6B7885", "line":"#8091A0", "white":"#FFFFFF",
    "blue":"#2C6E9F", "blue_bg":"#DCEAF7", "green":"#2E7D5B", "green_bg":"#E1F1E8",
    "purple":"#6B52A3", "purple_bg":"#ECE4F7", "orange":"#B76820", "orange_bg":"#FBE9D7",
    "red":"#A74444", "red_bg":"#F8DEDE", "teal":"#237B75", "teal_bg":"#DDF2F0",
    "yellow":"#9A7212", "yellow_bg":"#FFF3C9", "gray_bg":"#F4F6F8",
}

class SVG:
    def __init__(self,w,h,title,subtitle=""):
        self.w,self.h=w,h
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#6B7885"/></marker></defs>',
                f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>']
        self.text(60,62,title,34,C["ink"],700)
        if subtitle:self.text(60,98,subtitle,18,C["muted"])
    def rect(self,x,y,w,h,fill,stroke=None,sw=2,rx=16):
        st=f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}/>')
    def text(self,x,y,t,size=18,color=None,weight=400,anchor="start"):
        self.p.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color or C["text"]}">{escape(str(t))}</text>')
    def multiline(self,x,y,lines,size=17,color=None,weight=400,leading=1.38,anchor="start"):
        spans=[]
        for i,t in enumerate(lines):
            spans.append(f'<tspan x="{x}" dy="{0 if i==0 else size*leading:.1f}">{escape(str(t))}</tspan>')
        self.p.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color or C["text"]}">'+''.join(spans)+'</text>')
    def line(self,x1,y1,x2,y2,color=None,sw=3,arrow=True,dash=None):
        marker=' marker-end="url(#arrow)"' if arrow else ''
        ds=f' stroke-dasharray="{dash}"' if dash else ''
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or C["muted"]}" stroke-width="{sw}"{marker}{ds}/>')
    def path(self,d,color=None,sw=3,arrow=True,dash=None):
        marker=' marker-end="url(#arrow)"' if arrow else ''
        ds=f' stroke-dasharray="{dash}"' if dash else ''
        self.p.append(f'<path d="{d}" fill="none" stroke="{color or C["muted"]}" stroke-width="{sw}"{marker}{ds}/>')
    def card(self,x,y,w,h,title,lines,fill,stroke,ts=21,bs=16):
        self.rect(x,y,w,h,fill,stroke)
        self.text(x+18,y+34,title,ts,C["ink"],700)
        self.multiline(x+18,y+66,lines,bs,C["text"])
    def pill(self,x,y,w,label,fill):
        self.rect(x,y,w,38,fill,None,rx=19)
        self.text(x+w/2,y+26,label,17,C["white"],700,"middle")
    def save(self,name):
        self.p.append('</svg>')
        out=SVG_DIR/name
        out.write_text('\n'.join(self.p)+'\n',encoding='utf-8')
        return out


def overview():
    s=SVG(1800,1180,"V4 总框架：GroundSignal 是测量编排系统，不是静态题库","患者材料、测量任务、探针和验证器分层；一次运行可产生多项裁决")
    s.rect(60,125,1680,72,C["yellow_bg"],C["yellow"])
    s.text(900,170,"Clinical World 产生行为机会；Measurement Bank 对已发生的可观察事件做模块化裁决",23,C["ink"],700,"middle")
    flow=[
        ("1 Clinical World",["Scenario + facts + FSM","患者世界不含标准答案"],C["blue_bg"],C["blue"]),
        ("2 Interaction Protocol",["运行前披露与分支规则","不等于实际对话"],C["blue_bg"],C["blue"]),
        ("3 Execution Spec",["Condition + task + model config","决定能否共用一次执行"],C["orange_bg"],C["orange"]),
        ("4 Episode / Trajectory",["模型真实行为 + event log","一次运行产生一条证据链"],C["teal_bg"],C["teal"]),
    ]
    for i,(a,b,fill,stroke) in enumerate(flow):
        x=60+i*420
        s.card(x,255,370,165,a,b,fill,stroke,21,17)
        if i<3:s.line(x+370,338,x+405,338)
    s.line(900,420,900,475)
    s.rect(60,495,1680,285,C["purple_bg"],C["purple"],3,18)
    s.text(90,535,"5 Modular Measurement Bank",25,C["purple"],700)
    bank=[
        ("Evaluation Task",["要测什么能力","task_id"]),
        ("Failure Probe",["观察哪个失败条件","probe_template + binding"]),
        ("Verifier Bundle",["多个 checker / Judge","many-to-many"]),
        ("Judgment",["带机会、证据和版本","不等于独立机制"]),
    ]
    for i,(a,b) in enumerate(bank):
        x=90+i*405
        s.card(x,575,360,150,a,b,C["white"],C["purple"],20,16)
        if i<3:s.line(x+360,650,x+390,650)
    s.line(900,780,900,835)
    s.card(60,855,520,170,"6 Failure Attribution",["观察事实 ≠ 机制归因","共享事件保留 dependency_id"],C["red_bg"],C["red"],22,18)
    s.line(580,940,640,940)
    s.card(660,855,520,170,"7 Capability Profile",["stage × failure × condition","边界、未决和证据范围"],C["green_bg"],C["green"],22,18)
    s.line(1180,940,1240,940)
    s.card(1260,855,480,170,"8 Deployment Boundary",["允许自主 / 必须复核 / 禁止","临床准入另行签署"],C["orange_bg"],C["orange"],22,18)
    s.text(900,1100,"横向层：版本、来源、隐私、Attack Registry、运行收据、G0–G7 与 Release Gate",20,C["muted"],700,"middle")
    return s.save("00-模块化测量总图.svg")


def objects():
    s=SVG(1800,1440,"V4 对象模型：设计资产、执行证据、测量裁决必须有不同身份","七个 ID 不够：Evaluation Task、Interaction Protocol 和 Episode/Run 也需要主键")
    s.pill(60,125,260,"A 设计侧静态对象",C["blue"])
    static=[
        ("scenario_id","患者世界"),("protocol_id","交互协议"),("condition_id","实验条件"),
        ("task_id","模型任务合同"),("failure_type_id","错误定义"),("probe_template_id","通用探针模板"),
        ("probe_binding_id","病例/节点/条件绑定"),("verifier_id","参数化验证模块"),
    ]
    for i,(a,b) in enumerate(static):
        row=i//4; col=i%4; x=60+col*420; y=185+row*135
        s.card(x,y,380,105,a,[b],C["blue_bg"],C["blue"],18,16)
    s.pill(60,500,260,"B 编译与运行对象",C["orange"])
    runtime=[
        ("execution_spec_id",["模型可见输入 + protocol + condition","工具 / stop rule / model config"]),
        ("episode_id / run_id",["一次独立执行","重复、重试和父运行可追溯"]),
        ("trajectory_id",["实际发生的对话轨迹","不是预写交互脚本"]),
        ("event_id / node_id",["可观察事件与决策快照","当时可见事实明确"]),
    ]
    for i,(a,b) in enumerate(runtime):
        x=60+i*420
        s.card(x,560,380,155,a,b,C["orange_bg"],C["orange"],19,16)
        if i<3:s.line(x+380,638,x+405,638)
    s.pill(60,775,250,"C 裁决与结论对象",C["purple"])
    results=[
        ("opportunity_id",["probe 是否真正有机会被触发","not_reached ≠ fail"]),
        ("judgment_id",["某 verifier invocation 的原子判断","evidence span + version"]),
        ("probe_result_id",["多个 judgment 的预注册聚合","PASS / FAIL / UNRESOLVED"]),
        ("experiment_result_id",["跨条件/病例/运行比较","支持有限范围 claim"]),
    ]
    for i,(a,b) in enumerate(results):
        x=60+i*420
        s.card(x,835,380,155,a,b,C["purple_bg"],C["purple"],18,16)
        if i<3:s.line(x+380,913,x+405,913)
    s.rect(60,1060,1680,260,C["gray_bg"],C["line"])
    s.text(90,1100,"两条硬关系",23,C["ink"],700)
    s.multiline(90,1145,[
        "1. 一个 execution_spec 可以挂多个 probe_bindings；只有后台测量不同，才能共用一次 episode。",
        "2. 一个 probe 可以调用多个 verifiers；同一 verifier 也可在多个 probe 中参数化复用。",
        "改变模型可见输入、交互规则、工具或 condition → 新 execution_spec → 必须重新运行。",
        "只新增后台 probe/verifier → 可重评旧 trajectory，但必须生成新 judgment_version。",
    ],20,C["text"],400,1.5)
    s.text(900,1380,"model_config_id 与全部版本 hash 绑定 execution_spec；否则同名 trajectory 不能复现。",19,C["red"],700,"middle")
    return s.save("01-对象模型与ID.svg")


def many_to_many():
    s=SVG(1800,1320,"V4 多对多测量：一条轨迹挂多个 Task，一个 Task 组合多个 Verifier","复用降低模型调用，不增加独立患者证据；共享事件必须保留相关性")
    s.card(60,150,420,250,"Observed Trajectory T001",["腹痛 → 右下腹痛 → 发热","错误权威意见 → 呕吐","event log + visible-fact ledger"],C["blue_bg"],C["blue"],23,18)
    tasks=[
        ("Task A 风险升级",["Probe：红旗识别","Probe：deadline 行动"]),
        ("Task B 信息更新",["Probe：新证据更新","Probe：旧状态覆盖"]),
        ("Task C 问诊策略",["Probe：关键追问","Probe：追问阻塞行动"]),
        ("Task D 工程稳健",["Probe：状态丢失","Probe：工具失败后过度确定"]),
    ]
    for i,(a,b) in enumerate(tasks):
        x=600+(i%2)*580; y=150+(i//2)*260
        s.card(x,y,520,205,a,b,C["green_bg"],C["green"],22,18)
        s.path(f"M480,275 C540,275 535,{y+100} {x},{y+100}")
    s.pill(60,720,330,"Verifier Bank：模块化复用",C["purple"])
    verifiers=[
        ("Action Extractor","是否明确行动"),("Deadline Checker","行动是否及时"),("Evidence Checker","是否基于可见证据"),
        ("Update Checker","新信息是否覆盖旧状态"),("Over-triage Checker","防一律急诊"),("Semantic Judge","窄范围语义裁决"),
    ]
    for i,(a,b) in enumerate(verifiers):
        x=60+(i%3)*560; y=780+(i//3)*170
        s.card(x,y,510,130,a,[b],C["purple_bg"],C["purple"],20,16)
    s.rect(60,1150,1680,95,C["red_bg"],C["red"])
    s.text(900,1190,"同一 trajectory 上 10 个 probe = 10 项相关测量，不是 10 个独立病例，也不自动是 10 份机制证据。",21,C["red"],700,"middle")
    s.text(900,1285,"复用回答“如何更省”；sibling scenarios 回答“能否外推”。两者不能互相替代。",19,C["ink"],700,"middle")
    return s.save("02-Task-Probe-Verifier多对多.svg")


def counting():
    s=SVG(1800,1450,"V4 数量体系：资产账、执行账、测量账分别计算","不再用一个“题目数”同时表示患者世界、probe 配置和模型调用")
    metrics=[
        ("N_scenario",["独立患者世界","按 lineage 判断独立性"],C["blue_bg"],C["blue"]),
        ("N_execution_spec",["唯一模型可见条件","决定是否需要新 episode"],C["orange_bg"],C["orange"]),
        ("N_episode",["实际独立模型运行","含 model config 与 repeats"],C["teal_bg"],C["teal"]),
        ("N_probe_binding",["目标×病例×节点×条件的合法绑定","可以远多于 episode"],C["purple_bg"],C["purple"]),
        ("N_judgment",["verifier 原子裁决总数","一个 probe 可有多个 judgment"],C["green_bg"],C["green"]),
    ]
    for i,(a,b,fill,stroke) in enumerate(metrics):
        x=60+i*340
        s.card(x,150,300,165,a,b,fill,stroke,20,15)
    s.pill(60,375,280,"A 设计账：角色与绑定",C["purple"])
    s.rect(60,435,1680,150,C["purple_bg"],C["purple"])
    s.text(900,485,"N_design = Σ_h ( |C_h| + Σ_p |L_h,p| )",30,C["ink"],700,"middle")
    s.text(900,535,"记录目标、对照、压力和 probe binding；相同输入承担两种角色时，角色都保留，但证据不独立。",19,C["text"],400,"middle")
    s.pill(60,645,280,"B 执行账：只看模型可见差异",C["orange"])
    s.rect(60,705,1680,150,C["orange_bg"],C["orange"])
    s.text(900,755,"N_planned_runs = Σ_execution_spec repeats(spec)",30,C["ink"],700,"middle")
    s.text(900,805,"新增后台 probe 不增加 run；改变输入、protocol、condition、tools 或 model config 才产生新 execution spec。",19,C["text"],400,"middle")
    s.pill(60,915,300,"C 联调计数例：不要误乘 probe",C["teal"])
    s.card(60,975,520,220,"模型运行",["1 scenario × 1 protocol","× 2 conditions × 2 models × 3 repeats","= 12 episodes"],C["teal_bg"],C["teal"],22,19)
    s.card(640,975,520,220,"Probe 执行位置",["每 episode 挂 3 probes","12 × 3","= 36 probe-results positions"],C["purple_bg"],C["purple"],22,19)
    s.card(1220,975,520,220,"Verifier Judgments",["若每 probe 平均 2 verifiers","36 × 2","= 72 atomic judgments"],C["green_bg"],C["green"],22,19)
    s.text(900,1270,"三者仍然只有 1 个 scenario；12 次模型运行，不是 36 或 72 次。",22,C["red"],700,"middle")
    s.text(900,1345,"“3150”可描述 probe-condition 设计空间，但病例数与实际 run 必须由编排器按兼容关系重新求和。",20,C["ink"],700,"middle")
    return s.save("03-数量账本与运行复用.svg")


def compiler():
    s=SVG(1800,1400,"V4 编排器：Bind → Validate → Compile → Run → Re-score","执行清单与测量清单分离，隐藏答案不能进入模型可见包")
    steps=[
        ("1 Bind",["scenario / protocol / condition","task / probe / verifier 参数"]),
        ("2 Validate",["临床适用 / 节点可达","机会可观察 / 版本相容"]),
        ("3 Compile",["执行清单：模型可见","测量清单：隐藏规则"]),
        ("4 Run",["episode + trajectory","append-only events + receipt"]),
        ("5 Measure",["opportunity → judgments","probe result + evidence"]),
    ]
    for i,(a,b) in enumerate(steps):
        x=60+i*340
        s.card(x,160,300,175,a,b,C["blue_bg"] if i<3 else C["teal_bg"],C["blue"] if i<3 else C["teal"],22,16)
        if i<4:s.line(x+300,248,x+325,248)
    s.pill(60,395,300,"执行复用判定：必须完全等价",C["orange"])
    s.rect(60,455,1680,210,C["orange_bg"],C["orange"])
    s.multiline(90,500,[
        "患者世界版本、物化输入、task contract、interaction protocol、condition、tools / memory、",
        "model config、stop rule、repeat requirement 全部兼容 → 多个 probe bindings 可共用一次执行。",
        "任何模型可见条件不同 → 新 execution_spec；即使输入相同，预注册独立重复也不能被去重。",
    ],20,C["text"],400,1.5)
    s.pill(60,725,280,"旧轨迹何时可以重评",C["purple"])
    reuse=[
        ("只新增后台 Probe",["可以重评","不产生新模型行为"]),
        ("只修改 Verifier",["可以生成新 judgment version","旧裁决保留"]),
        ("改变模型可见压力",["必须重跑","旧 trajectory 不可冒充"]),
        ("改变患者响应规则",["必须重跑","protocol identity 已改变"]),
    ]
    for i,(a,b) in enumerate(reuse):
        x=60+i*420
        ok=i<2
        s.card(x,785,380,160,a,b,C["green_bg"] if ok else C["red_bg"],C["green"] if ok else C["red"],20,16)
    s.pill(60,1010,300,"机会状态与裁决状态分离",C["ink"])
    s.card(60,1070,510,190,"Run Validity",["VALID / INVALID / PARTIAL","平台故障不直接算模型失败"],C["gray_bg"],C["line"],22,18)
    s.card(645,1070,510,190,"Opportunity",["TRIGGERED / NOT_REACHED / NOT_APPLICABLE","模型合理避开分支 ≠ 自动失败"],C["gray_bg"],C["line"],22,18)
    s.card(1230,1070,510,190,"Adjudication",["PASS / FAIL / UNRESOLVED / UNASSESSED","未评审绝不默认为 PASS"],C["gray_bg"],C["line"],22,18)
    s.text(900,1340,"执行复用节省调用；重新评分节省调用；二者都不能伪造新的行为证据。",20,C["red"],700,"middle")
    return s.save("04-编排与双清单.svg")


def lifecycle():
    s=SVG(1800,1380,"V4 双闭环：既测模型，也测测量平台","模型失败与平台失效分别归因；修复后用原攻击和独立正确材料回放")
    s.pill(60,125,260,"A 模型测量闭环",C["green"])
    top=[
        ("Hypothesis","测什么失败"),("Controlled Execution","制造行为机会"),("Observed Events","记录实际行为"),("Probe Judgments","局部裁决"),("Bounded Claim","限制结论范围"),
    ]
    for i,(a,b) in enumerate(top):
        x=60+i*340
        s.card(x,185,300,125,a,[b],C["green_bg"],C["green"],19,16)
        if i<4:s.line(x+300,248,x+325,248)
    s.pill(60,370,260,"B 平台验证闭环",C["red"])
    bottom=[
        ("Correct Alternative","应通过"),("Known Error","应失败"),("Cheat Strategy","不应刷分"),("Fault Injection","平台应识别"),("Replay Regression","修复后重放"),
    ]
    for i,(a,b) in enumerate(bottom):
        x=60+i*340
        s.card(x,430,300,125,a,[b],C["red_bg"],C["red"],19,16)
        if i<4:s.line(x+300,493,x+325,493)
    s.pill(60,620,320,"C 失败路由：送回真正责任系统",C["purple"])
    routes=[
        ("临床争议",["Clinical World / Oracle","返回临床审核"]),
        ("交互失真",["Protocol / Simulator","修分支和披露"]),
        ("条件混杂",["Condition Generator","重做对照"]),
        ("运行污染",["Runner / Tool Adapter","修隔离与收据"]),
        ("测量偏差",["Probe / Verifier","重校 False Accept/Reject"]),
    ]
    for i,(a,b) in enumerate(routes):
        x=60+i*340
        s.card(x,680,300,150,a,b,C["purple_bg"],C["purple"],19,15)
    s.rect(60,900,1680,280,C["gray_bg"],C["line"])
    s.text(90,945,"独立性纪律",23,C["ink"],700)
    s.multiline(90,990,[
        "同一 scenario 的多 trajectory / variant / probe 增加的是内部观测，不增加独立患者证据；",
        "同一 event 引发多个 probe failure，应保留 shared_event_id，不能重复计为多个独立机制；",
        "多个 seed 只估计运行波动；跨 sibling scenarios 与独立 experiment families 才扩大证据范围；",
        "强模型全部通过允许得到“在本范围未观察到失败”，不得反向制造失败或偷偷调难度。",
    ],20,C["text"],400,1.5)
    s.text(900,1290,"输出分三层：Observed Behavior ｜ Supported Attribution ｜ Remaining Alternatives",21,C["ink"],700,"middle")
    s.text(900,1335,"总分不能替代 Failure Profile、Capability Boundary 与 Human Oversight。",20,C["red"],700,"middle")
    return s.save("05-双闭环与失败路由.svg")


def write_docs():
    readme="""# GroundSignal Modular Measurement Architecture V4

GroundSignal 不是静态题库，而是把临床世界、交互协议、实验条件、模型执行与模块化测量组合起来的测量编排系统。

## 核心分层

1. Clinical Scenario：患者完整事实世界。
2. Interaction Protocol：运行前的披露、分支和终止规则。
3. Execution Spec：决定模型实际看到什么、能做什么及是否必须新运行。
4. Episode / Observed Trajectory：一次真实模型执行产生的行为证据。
5. Evaluation Task：希望测量的能力问题。
6. Failure Probe：把能力问题落实为具体可观察失败条件。
7. Verifier Bundle：对一个 probe 执行多个原子判定。
8. Experiment Result：跨条件、病例和运行形成的有限范围结论。

## 关键 many-to-many 关系

- 一个 trajectory 可被多个 task/probe 读取。
- 一个 task 可组合多个 probes。
- 一个 probe 可调用多个 verifiers。
- 一个 verifier 可被多个 probes 参数化复用。
- 只新增后台 probe/verifier 可以重评旧 trajectory，不新增模型行为。
- 改变模型可见输入、交互规则、工具或 condition，必须产生新 execution spec 并重新运行。

## ID 补充

原七个 ID 应至少补充：

- `task_id`：原对象模型定义了 Evaluation Task，但七 ID 中缺失；
- `protocol_id`：交互协议不是实际 trajectory；
- `execution_spec_id`：执行复用与重新运行的判据；
- `episode_id/run_id`：每次独立运行；
- `model_config_id`：模型、system prompt、tools、RAG 和 decoding 的联合身份；
- `judgment_id`：某个 verifier invocation 的版本化裁决。

## 数量账本

不再只报“题目数”，至少分开：

- `N_scenario`：独立患者世界数；
- `N_execution_spec`：唯一模型可见执行条件数；
- `N_episode`：实际模型运行数；
- `N_probe_template`：通用探针定义数；
- `N_probe_binding`：探针在病例/节点/条件上的合法绑定数；
- `N_judgment`：原子 verifier 裁决数。

联调例：1 scenario × 1 protocol × 2 conditions × 2 model configs × 3 repeats = 12 episodes。每场挂3个 probes，得到36个 probe-result positions；若每 probe 平均调用2个 verifiers，则得到72个 atomic judgments。它仍然只有1个患者世界、12次模型运行。

## 图册

- `00-模块化测量总图.svg`
- `01-对象模型与ID.svg`
- `02-Task-Probe-Verifier多对多.svg`
- `03-数量账本与运行复用.svg`
- `04-编排与双清单.svg`
- `05-双闭环与失败路由.svg`

## 公开边界

本目录只含架构方法，不含 patient truth、Oracle 明细、Rubric 阈值、隐藏答案、真实患者数据或未公开攻击夹具。clinical approval 仍只能由真人临床审核者签署。
"""
    (ROOT/"README.md").write_text(readme,encoding="utf-8")
    notes="""# V4 架构修改说明

V4 取代“几千道题”的单一口径。3150 可以是 probe-condition 设计关系数，但不能直接推出3150个病例或3150次模型运行。

最重要的结构变化：

```text
Clinical World / Interaction Protocol
→ Execution Spec
→ Episode / Observed Trajectory / Events
→ Task / Probe Binding / Verifier Bundle
→ Judgment / Experiment Result
```

运行复用由 execution equivalence（执行等价性）决定；统计独立性由 patient lineage、scenario、family 与 run 层级决定。两者是不同问题。
"""
    (DOCS_DIR/"架构修改说明.md").write_text(notes,encoding="utf-8")


def html_index(files):
    cards=[]
    for f in files:
        cards.append(f'<article><h2>{escape(f.stem)}</h2><object data="svg/{escape(f.name)}" type="image/svg+xml"></object><p><a href="svg/{escape(f.name)}">单独打开 SVG</a></p></article>')
    html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GroundSignal 模块化测量架构 V4</title><style>body{{font-family:Microsoft YaHei,Noto Sans CJK SC,sans-serif;margin:0;background:#eef2f5;color:#17324D}}header{{padding:32px 5vw;background:#17324D;color:white}}main{{max-width:1500px;margin:28px auto;padding:0 24px}}article{{background:white;border-radius:16px;padding:20px;margin:24px 0;box-shadow:0 4px 18px #0001}}object{{width:100%;height:780px;border:1px solid #d8e0e6}}a{{color:#2C6E9F}}p{{font-size:18px}}</style></head><body><header><h1>GroundSignal 模块化测量架构 V4</h1><p>Scenario、Trajectory、Task、Probe、Verifier、Condition 与 Run 分层计数。</p></header><main>{''.join(cards)}</main></body></html>'''
    (ROOT/"GroundSignal-模块化测量架构-V4.html").write_text(html,encoding="utf-8")


def main():
    write_docs()
    files=[overview(),objects(),many_to_many(),counting(),compiler(),lifecycle()]
    html_index(files)
    print(f"generated {len(files)} SVG files")

if __name__=='__main__':
    main()
