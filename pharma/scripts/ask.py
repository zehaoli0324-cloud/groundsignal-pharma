#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问询功能：从 Obsidian 企业情报 vault 生成 HTML 看板

用法:
    python3 ask.py <vault_path> <查询词> [-o 输出.html]

示例:
    python3 ask.py demo 富瀚微 -o 富瀚微看板.html
    python3 ask.py <vault路径> "富瀚微的客户是谁" -o out.html

说明:
- 查询词支持实体名（公司/人物/产品/投资人）或问题句式（取第一个匹配的实体）
- 输出为自包含 HTML（内嵌 CSS），无外部依赖，浏览器直接打开
- 关系图用纯 SVG 渲染，无需 JS 库
"""

import argparse
import datetime
import html
import math
import os
import re
import sys

TYPE_LABELS = {
    'company': '公司', 'person': '人物', 'product': '产品',
    'investor': '投资人', 'deal': '交易事件', 'analysis': '分析',
    'changelog': '变更日志', 'index': '索引',
    'facility': '设施', 'event': '事件', 'capacity': '产能追踪',
    'target': '靶点',
}
TYPE_COLORS = {
    'company': '#3b82f6', 'person': '#f59e0b', 'product': '#10b981',
    'investor': '#8b5cf6', 'deal': '#ef4444', 'analysis': '#64748b',
    'changelog': '#94a3b8', 'index': '#0ea5e9',
    'facility': '#0d9488', 'event': '#e11d48', 'capacity': '#7c3aed',
    'target': '#a855f7',
}
TYPE_FILL = {
    'facility': 'rgba(13,148,136,.14)', 'event': 'rgba(225,29,72,.14)', 'capacity': 'rgba(124,58,237,.14)',
}
EVIDENCE_STYLE = {
    'VERIFIED': ('一手官方', '#10b981'),
    'SUPPORTED': ('权威媒体', '#3b82f6'),
    'INFERRED': ('自媒体', '#f59e0b'),
    'UNKNOWN': ('待核实', '#ef4444'),
    'NA': ('非实体', '#94a3b8'),
}


def evidence_badge_html(level):
    label, color = EVIDENCE_STYLE.get(level, ('未知', '#94a3b8'))
    return f'<span class="tag" style="background:{color}">证据:{label}</span>'
RELATION_KEYWORDS = {
    '投资': '#8b5cf6', '股东': '#8b5cf6', '持股': '#8b5cf6',
    '供货': '#3b82f6', '客户': '#3b82f6', '采购': '#3b82f6', '供应': '#3b82f6',
    '竞争': '#ef4444', '对手': '#ef4444', '竞逐': '#ef4444',
    '代工': '#10b981', '上游': '#10b981',
    '授权': '#8b5cf6', '许可': '#8b5cf6', '引进': '#8b5cf6',
    '临床': '#10b981', '试验': '#10b981', '获批': '#10b981', '上市': '#10b981',
    '研发': '#3b82f6', '开发': '#3b82f6', '合作': '#64748b', '联合': '#64748b',
    '关联': '#64748b', '生态': '#64748b',
}

# 内置兜底模板（templates/board.html 缺失时使用，结构与外部模板一致）
TEMPLATE_FALLBACK = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; background:#eef2f7; color:#1e293b; padding:24px; }
  .wrap { max-width:960px; margin:0 auto; }
  .hero { background:linear-gradient(135deg,{{HERO_COLOR}},#1e293b); color:#fff; border-radius:16px; padding:28px 32px; margin-bottom:20px; }
  .hero h1 { font-size:26px; margin-bottom:6px; }
  .hero .sub { opacity:.85; font-size:14px; }
  .tag { display:inline-block; background:rgba(255,255,255,.2); border-radius:20px; padding:2px 12px; font-size:12px; margin-right:6px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  @media (max-width:720px) { .grid { grid-template-columns:1fr; } }
  .card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .card h2 { font-size:16px; margin-bottom:14px; padding-bottom:8px; border-bottom:2px solid #e2e8f0; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td { padding:6px 8px; border-bottom:1px solid #f1f5f9; vertical-align:top; }
  td.k { width:90px; color:#64748b; font-weight:600; }
  .rel-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; }
  .rel-card { display:block; text-decoration:none; color:inherit; border:1px solid #e2e8f0; border-left:4px solid var(--c,#94a3b8); border-radius:8px; padding:10px; transition:.15s; }
  .rel-card:hover { box-shadow:0 2px 8px rgba(0,0,0,.12); transform:translateY(-1px); }
  .rel-name { font-size:14px; font-weight:600; margin-bottom:2px; }
  .rel-desc { font-size:11px; color:#64748b; line-height:1.4; }
  .rel-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px; }
  .empty { color:#94a3b8; font-size:13px; }
  .src { font-size:12px; color:#64748b; word-break:break-all; }
  .body-snip { font-size:13px; line-height:1.7; color:#475569; background:#f8fafc; border-radius:8px; padding:12px; }
  form.q { margin-bottom:20px; display:flex; gap:10px; }
  form.q input { flex:1; padding:12px 16px; border-radius:10px; border:1px solid #cbd5e1; font-size:14px; }
  form.q button { padding:12px 24px; background:#1e293b; color:#fff; border:none; border-radius:10px; cursor:pointer; font-size:14px; }
  .foot { text-align:center; color:#94a3b8; font-size:12px; margin-top:24px; }
</style>
</head>
<body>
<div class="wrap">
  <form class="q" method="get" action="">
    <input id="q" name="q" value="" placeholder="换个实体再查：输入公司/人物/产品/投资人名…">
    <button type="submit">查询</button>
  </form>
  <div class="hero">
    <h1>{{NAME}}</h1>
    <div class="sub">
      <span class="tag">{{TYPE_LABEL}}</span>
      {{EVIDENCE}}
      <span class="tag">采集于 {{FETCHED}}</span>
      <span class="tag">{{NEIGHBOR_COUNT}} 个直接关联</span>
    </div>
  </div>
  <div class="grid">
    <div class="card"><h2>基本信息</h2><table>{{FM_ROWS}}</table></div>
    <div class="card"><h2>关系网络</h2>{{SVG}}</div>
  </div>
  <div class="card" style="margin-top:20px;"><h2>直接关联（{{NEIGHBOR_COUNT}}）</h2><div class="rel-grid">{{REL_CARDS}}</div></div>
  <div class="card" style="margin-top:20px;"><h2>笔记内容摘要</h2><div class="body-snip">{{BODY_SNIP}}</div></div>
  <div class="card" style="margin-top:20px;"><h2>来源</h2><div class="src">{{SRC}}</div></div>
  <div class="foot">由 ask.py 生成 · {{DATE}}</div>
</div>
</body>
</html>"""


def parse_note(path):
    content = open(path, encoding='utf-8').read()
    fm = {}
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    body = content
    if m:
        body = content[m.end():]
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
    links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
    return fm, body, links


def scan_vault(vault):
    notes = {}
    for root, dirs, files in os.walk(vault):
        if '.obsidian' in root:
            continue
        for f in files:
            if not f.endswith('.md'):
                continue
            fp = os.path.join(root, f)
            base = os.path.splitext(f)[0]
            fm, body, links = parse_note(fp)
            notes[base] = {
                'path': fp, 'fm': fm, 'body': body, 'links': set(links),
                'backlinks': set(),
            }
    for base, note in notes.items():
        for t in note['links']:
            if t in notes:
                notes[t]['backlinks'].add(base)
    return notes


def find_target(notes, query):
    """实体匹配：完全匹配（文件名/frontmatter name）优先于子串匹配"""
    best, best_score = None, 0
    for base, note in notes.items():
        name = note['fm'].get('name', base)
        score = 0
        if query == base or query == name:
            score = 100          # 完全匹配，压倒性优先
        elif query in base:
            score = 10           # 文件名子串
        elif query in name:
            score = 10           # frontmatter name 子串
        if query in note['body']:
            score += 1
        if score > best_score:
            best, best_score = (base, note), score
    return best


def find_by_substring(notes, query):
    """问题句式回退：找 query 中出现的实体名（最长优先）
    e.g. "富瀚微的客户是谁" -> 富瀚微
    """
    hits = []
    for base, note in notes.items():
        name = note['fm'].get('name', base)
        for candidate in {base, name}:
            if candidate and len(candidate) >= 2 and candidate in query:
                hits.append((len(candidate), candidate, base, note))
    if not hits:
        return None
    hits.sort(key=lambda x: -x[0])
    return hits[0][2], hits[0][3]


def relation_color(desc):
    for kw, color in RELATION_KEYWORDS.items():
        if kw in desc:
            return color
    return '#94a3b8'


def extract_context(body, target):
    ctx = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if f'[[{target}]]' in line or f'[[{target}|' in line:
            clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', line)
            if clean not in ctx:
                ctx.append(clean)
    return ctx[:6]


def build_svg(center, neighbors):
    """中心辐射 SVG 关系图"""
    n = len(neighbors)
    cx, cy, R = 360, 210, 150
    svg = [f'<svg viewBox="0 0 720 420" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;background:#f8fafc;border-radius:12px;">']
    for i, (name, color) in enumerate(neighbors):
        ang = 2 * math.pi * i / n - math.pi / 2
        x = cx + R * math.cos(ang)
        y = cy + R * math.sin(ang)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="{color}" stroke-width="2" stroke-dasharray="4,3" opacity="0.7"/>')
        svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="26" fill="{color}" opacity="0.15" stroke="{color}" stroke-width="2"/>')
        svg.append(f'<text x="{x:.0f}" y="{y+4:.0f}" text-anchor="middle" font-size="12" fill="#1e293b">{html.escape(name[:10])}</text>')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="#1e293b"/>')
    svg.append(f'<text x="{cx}" y="{cy-2}" text-anchor="middle" font-size="13" fill="#fff" font-weight="600">{html.escape(center[:8])}</text>')
    svg.append(f'<text x="{cx}" y="{cy+16}" text-anchor="middle" font-size="10" fill="#cbd5e1">{len(neighbors)} 个关联</text>')
    svg.append('</svg>')
    return ''.join(svg)


def render(target_base, note, notes, template_path=None):
    fm, body, links = note['fm'], note['body'], note['links']
    ntype = fm.get('type', 'index')
    name = fm.get('name', target_base)
    type_label = TYPE_LABELS.get(ntype, ntype)
    color = TYPE_COLORS.get(ntype, '#64748b')

    # 一度关联（出去 + 进来），过滤索引/日志类非实体节点
    neighbors = []
    for t in sorted(links | note['backlinks']):
        if t not in notes or t == target_base:
            continue
        tn = notes[t]
        ttype = tn['fm'].get('type', '')
        if ttype in ('index', 'changelog'):
            continue
        tcolor = TYPE_COLORS.get(ttype, '#64748b')
        # 关系描述：本笔记指向它（本笔记正文）+ 它指向本笔记（对方正文）
        desc = extract_context(body, t)
        if not desc:
            desc = extract_context(tn['body'], target_base)
        d = desc[0] if desc else ttype
        neighbors.append((t, tcolor, d))
    # 全部显示；SVG 图只画前 16 个（防图太密）

    # 基本信息表
    field_order = ['name', 'code', 'industry', 'region', 'founded', 'status', 'website',
                   'investor_type', 'deal_type', 'amount', 'date', 'role', 'company',
                   'fetched_at']
    fm_rows = []
    for k in field_order:
        if k in fm and fm[k]:
            label = {'name': '名称', 'code': '代码', 'industry': '行业', 'region': '地区',
                     'founded': '成立', 'status': '状态', 'website': '官网',
                     'investor_type': '类型', 'deal_type': '事件类型', 'amount': '金额',
                     'date': '日期', 'role': '角色', 'company': '所属公司',
                     'fetched_at': '采集时间'}.get(k, k)
            fm_rows.append(f'<tr><td class="k">{label}</td><td>{html.escape(str(fm[k]))}</td></tr>')
    if not fm_rows:
        fm_rows = '<tr><td class="k">说明</td><td>（无结构化字段）</td></tr>'
    else:
        fm_rows = ''.join(fm_rows)

    # 关系卡片
    rel_cards = []
    for name_i, c, d in neighbors:
        rel_cards.append(f'''
        <a class="rel-card" href="#" style="--c:{c}" onclick="document.getElementById('q').value='{html.escape(name_i)}';this.form.submit();">
          <div class="rel-dot" style="background:{c}"></div>
          <div class="rel-name">{html.escape(name_i)}</div>
          <div class="rel-desc">{html.escape(d[:60])}</div>
        </a>''')
    rel_html = ''.join(rel_cards) if rel_cards else '<p class="empty">暂无关联节点</p>'

    # 正文摘要（去掉 frontmatter 和 wikilink 语法）
    body_clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', body)
    body_clean = re.sub(r'```mermaid.*?```', '[关系图]', body_clean, flags=re.S)
    body_snip = html.escape(body_clean.strip()[:1500]).replace('\n', '<br>')

    src = fm.get('source_url', '')
    src_html = f'<a href="{html.escape(src)}" target="_blank">{html.escape(src[:80])}</a>' if src else '无来源记录'

    values = {
        'TITLE': html.escape(f'{name} · 企业情报看板'),
        'NAME': html.escape(name),
        'TYPE_LABEL': type_label,
        'EVIDENCE': evidence_badge_html(fm.get('evidence', '')),
        'FETCHED': fm.get('fetched_at', '-'),
        'NEIGHBOR_COUNT': str(len(neighbors)),
        'HERO_COLOR': color,
        'FM_ROWS': fm_rows,
        'SVG': build_svg(name[:8], [(n, c) for n, c, _ in neighbors[:16]]),
        'REL_CARDS': rel_html,
        'BODY_SNIP': body_snip,
        'SRC': src_html,
        'DATE': datetime.date.today().isoformat(),
    }
    tpl = TEMPLATE_FALLBACK
    if template_path and os.path.exists(template_path):
        tpl = open(template_path, encoding='utf-8').read()
    for k, v in values.items():
        tpl = tpl.replace('{{' + k + '}}', v)
    return tpl


def main():
    ap = argparse.ArgumentParser(description='Obsidian 企业情报 vault 问询 → HTML 看板')
    ap.add_argument('vault', help='vault 路径')
    ap.add_argument('query', help='查询词（实体名或问题）')
    ap.add_argument('-o', '--output', default=None, help='输出 HTML 路径')
    ap.add_argument('-t', '--template', default=None,
                    help='看板模板路径（默认: 脚本同级 templates/board.html）')
    args = ap.parse_args()

    # 默认模板位置：<script_dir>/../templates/board.html
    template_path = args.template
    if not template_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, '..', 'templates', 'board.html')
        if os.path.exists(candidate):
            template_path = candidate

    if not os.path.isdir(args.vault):
        print(f'❌ vault 路径不存在: {args.vault}', file=sys.stderr)
        sys.exit(1)

    notes = scan_vault(args.vault)
    # 问题句式：先尝试精确匹配，再尝试实体名子串匹配
    query = args.query
    target = find_target(notes, query)
    if not target:
        target = find_by_substring(notes, query)
        if target:
            base, note = target
            query = base
    if not target:
        print(f'❌ 在 vault 中未找到与「{args.query}」匹配的实体', file=sys.stderr)
        sys.exit(1)

    base, note = target
    page = render(base, note, notes, template_path=template_path)
    out = args.output or f'看板-{base}.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'✅ 看板已生成: {out}')
    print(f'   实体: {base} | 关联节点: {len(note["links"] | note["backlinks"]) - 1}')


if __name__ == '__main__':
    main()
