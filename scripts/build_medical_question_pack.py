"""Build a readable, standalone source distribution. No credentials or run logs."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')

def card_md(c,sources):
    lines=[f"# {c['scenario_id']} · {c['title']}",'','合成开发题，待临床复核。此文件给操作者/运行器与评审者阅读，不整份发给被测GPT。','', '## 第一条发给GPT的内容','',c['prefix'][0]['content'],'','## 被追问时的固定回复','']
    for f in c['facts']:lines += [f"- {f['id']} {f['topic']}：{f['answer']}"]
    lines += ['','## 条件触发事件','']
    for e in c['events']:lines += [f"- {e['id']}：已经披露 {', '.join(e['requires'])}，且收到至少{e['min_assistant_turns']}次自然回答后，在下一用户回合优先发送一次：",e['answer']]
    if not c['events']:lines+=['无额外事件。']
    lines+=['','## 评分参考','']
    for r in c['criteria']:lines += [f"- {r['id']} / {r['dimension']}：{r['description']}",f"  触发条件：{', '.join(r['requires']) or '从首轮起'}。失败例：{r['fail_example']}"]
    lines += ['','## 自然阶段结束后可选的解释探查','',c['probe'],'','仅单独评价探查表现，不反向补自然阶段分数。','', '## 参考来源','']
    ids={x for r in c['criteria'] for x in r['source_ids']}
    lines += [f"- {x['title']}：{x['url']}（核对日期{x['accessed']}）" for x in sources if x['id'] in ids]
    return '\n'.join(lines)+'\n'

def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    data=ROOT/'benchmark/medical-dialogue-v1';suite=json.loads((data/'suite.json').read_text());policies=json.loads((data/'oracle-policy.json').read_text());cards=suite['scenarios']
    engine=out/'工程';engine.mkdir()
    for name in ['medical_dialogue_bench','patient_eval']:
        for f in (ROOT/'scripts'/name).glob('*.py'):write(engine/'scripts'/name/f.name,f.read_text())
    for f in (ROOT/'scripts/patient_eval/app_pilot_assets').glob('*.html'):write(engine/'scripts/patient_eval/app_pilot_assets'/f.name,f.read_text())
    write(engine/'scripts/__init__.py','');write(engine/'tests/__init__.py','')
    for f in (ROOT/'tests/medical_dialogue_bench').glob('*.py'):write(engine/'tests/medical_dialogue_bench'/f.name,f.read_text())
    for f in data.iterdir():
        if f.is_file():write(engine/'benchmark/medical-dialogue-v1'/f.name,f.read_text())
    write(engine/'start_offline.py','''from pathlib import Path
import datetime, subprocess, sys
root=Path(__file__).resolve().parent
out=root/'medical/patient-eval/local'/('oracle-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
for args in [['validate'],['run','--backend','oracle','--out',str(out)],['verify','--run',str(out),'--out',str(out.parent/(out.name+'-report.json'))]]:
    subprocess.run([sys.executable,'-m','scripts.medical_dialogue_bench',*args],cwd=root,check=True)
print('完成：这是脚本参考解法演练，不是真实GPT成绩。结果在：',out)
''')
    write(engine/'双击运行参考解法.bat','@echo off\r\ncd /d "%~dp0"\r\npy -3 start_offline.py\r\npause\r\n')
    oracle_lines=['# 作者参考解法','', '这些路径用于工程演练，不是唯一正确回答，也不是独立临床金标准。被测GPT不能看到这份文件。','']
    body=[];nav=[]
    for c in cards:
        cid=c['scenario_id'];text=card_md(c,suite['sources']);write(out/'题卡'/f'{cid}.md',text);write(out/'题卡'/f'{cid}.json',json.dumps(c,ensure_ascii=False,indent=2)+'\n')
        nav.append(f'<a href="#{cid}">{cid} {html.escape(c["title"])}</a>')
        facts=''.join(f'<tr><td>{html.escape(f["topic"])}</td><td>{html.escape(f["answer"])}</td></tr>' for f in c['facts'])
        events=''.join(f'<p>已披露 {html.escape(", ".join(e["requires"]))} 且至少收到{e["min_assistant_turns"]}次回答后：<strong>{html.escape(e["answer"])}</strong></p>' for e in c['events']) or '<p>本题没有额外事件。</p>'
        criteria=''.join(f'<li>{html.escape(r["description"])} <small>触发：{html.escape(", ".join(r["requires"]) or "首轮起")}；失败例：{html.escape(r["fail_example"])}</small></li>' for r in c['criteria'])
        body.append(f'<section id="{cid}"><h2>{cid} · {html.escape(c["title"])}</h2><p class="label">第一轮只发送下面这句话</p><textarea readonly>{html.escape(c["prefix"][0]["content"])}</textarea><p><a href="题卡/{cid}.md">完整文字题卡</a> · <a href="题卡/{cid}.json">机器可读题卡</a></p><details><summary>操作者查看：被追问时的回复</summary><table><tr><th>被问到什么</th><th>固定回复</th></tr>{facts}</table>{events}</details><details><summary>评审者查看：评分点</summary><ul>{criteria}</ul></details><a href="#top">回到目录</a></section>')
    for family,policy in policies.items():oracle_lines += [f'## {family}','',*[f'{i+1}. {q}' for i,q in enumerate(policy['questions'])],'','参考结论：'+policy['answer'],'']
    write(out/'参考与评分/ORACLE参考解法.md','\n'.join(oracle_lines))
    write(out/'参考与评分/RUBRIC评分细则.md',(data/'RUBRIC.md').read_text())
    write(out/'参考与评分/来源记录.json',json.dumps(suite['sources'],ensure_ascii=False,indent=2))
    write(out/'参考与评分/人工记录模板.txt','''模型名称与模式：
日期：
题卡编号：
是否新建独立会话：
每轮依次记录：用户发送原文 / GPT完整回答 / 实际披露事实编号 / 自然或探查阶段。
结束原因：
疑似问题、对应回答原句：

此文本用于人工记录，可交回项目维护者整理。不要冒充自动运行日志；未评分保持未评。
''')
    write(out/'README_先读我.txt','''GroundSignal 医学问答题包 v1.1

1. 先解压整个文件夹，再双击 START_HERE.html。这个页面可直接阅读全部14张题卡，不需要安装Python。
2. 手动测试：每题新建GPT会话，只复制首问。GPT追问后，再按固定事实回复；未知内容不编造。完整记录每轮内容。不要把整个ZIP、评分标准或参考解法发给被测GPT。
3. 自动演练：安装Python 3.10或以上。Windows在“工程”目录双击“运行参考解法”批处理文件；或进入该目录运行 python start_offline.py。该命令只跑脚本参考解法，不调用真实模型、不产生API费用。
4. 真正调用GPT：在“工程”目录配置OPENAI_API_KEY环境变量，按该目录benchmark/medical-dialogue-v1/README.md填写实际模型标识并运行。自然阶段最多84次模型调用；启用解释探查最多98次。每題结束自动换题。
5. 保存结果：自动运行结果在“工程/medical/patient-eval/local”。可以把某次run目录及对应评审文件压缩后交回分析，原始记录不要公开发布。

题目：AP01—AP06为原有12张卡；AP07基础版与干扰版为新增腹痛分诊候选题。共14张卡，只有7个独立情境家族。全部为合成开发题；新增医学处置标准待临床复核，尚无真实GPT成绩。

包内：可读题卡、机器可读题卡、披露规则、参考解法、评分细则、来源记录、Python运行器、校验器、Dockerfile和测试。
''')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GroundSignal 医学题卡 v1.1</title><style>body{font:17px/1.7 system-ui,sans-serif;color:#20334a;background:#f2f5f8;margin:0}main{max-width:1000px;margin:auto;padding:32px 20px}h1{font-size:32px}nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:8px}a{color:#17637f}section{background:white;border-radius:14px;padding:24px;margin:24px 0}textarea{width:100%;box-sizing:border-box;min-height:100px;font:18px/1.7 system-ui;padding:12px;background:#edf7f8;border:1px solid #b8d2dc}summary{cursor:pointer;font-weight:600;padding:12px 0}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #dde5eb;text-align:left}small{display:block;color:#5d6d7e}li{margin:12px 0}.label{color:#17637f;font-weight:bold}.notice{border-left:4px solid #db9e36;padding:12px;background:#fff9ec}</style><main id="top"><h1>医学多轮问答 · 14张题卡</h1><p>7个情境家族，各有基础版与无关文本干扰版。先选一张题，新建GPT会话，复制首问；后续按实际追问披露信息。</p><p class="notice">这是给操作者看的题包。不要将整包或评分答案交给被测GPT。全部题目是合成开发情境，医学标准待临床复核。</p><p><a href="README_先读我.txt">先读使用说明</a> · <a href="参考与评分/RUBRIC评分细则.md">评分细则</a> · <a href="工程/benchmark/medical-dialogue-v1/README.md">自动运行说明</a></p><nav>'''+''.join(nav)+'</nav>'+''.join(body)+'</main></html>'
    write(out/'START_HERE.html',page)
    hashes={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.rglob('*')) if f.is_file()}
    write(out/'PACK_MANIFEST.json',json.dumps(dict(version='1.1',cards=14,families=7,files=hashes),ensure_ascii=False,indent=2))
    return out

def archive(out):
    path=Path(str(out)+'.zip')
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob('*')):
            if f.is_file():z.write(f,arcname=str(Path(out.name)/f.relative_to(out)))
    return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();print(archive(build(a.out)))
