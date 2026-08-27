#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
panorama.py — 双实体全景关系看板（富瀚微 × 全志科技 及其上下游）

从 Obsidian 情报 vault 提取两个中心实体的全部关联，生成一张
双中心网络图 HTML（SVG 手绘布局，无需 JS 库）+ 可选 PNG。

用法:
    python3 panorama.py <vault> <实体A> <实体B> -o 全景看板.html [--png 输出.png]

布局:
    左中心 = 实体A，右中心 = 实体B
    中间列 = 两者共享的邻居（供应链重叠/共同生态）
    左右两列 = 各自独有邻居
    富瀚微 ↔ 全志 = 红色粗线（竞争）
"""

import argparse
import html
import math
import os
import re
import sys

TYPE_LABELS = {
    'company': '公司', 'person': '人物', 'product': '产品',
    'investor': '投资人', 'deal': '交易事件', 'analysis': '分析',
    'changelog': '变更日志', 'index': '索引',
}
TYPE_COLORS = {
    'company': '#3b82f6', 'person': '#f59e0b', 'product': '#10b981',
    'investor': '#8b5cf6', 'deal': '#ef4444', 'analysis': '#64748b',
    'changelog': '#94a3b8', 'index': '#0ea5e9',
}
TYPE_FILL = {
    'company': 'rgba(59,130,246,.14)', 'person': 'rgba(245,158,11,.14)',
    'product': 'rgba(16,185,129,.14)', 'investor': 'rgba(139,92,246,.14)',
    'deal': 'rgba(239,68,68,.14)', 'analysis': 'rgba(100,116,139,.14)',
}


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
            base = os.path.splitext(f)[0]
            fm, body, links = parse_note(os.path.join(root, f))
            notes[base] = {
                'fm': fm, 'body': body,
                'links': {os.path.basename(t) for t in links},
                'backlinks': set(),
            }
    for base, note in notes.items():
        for t in note['links']:
            if t in notes:
                notes[t]['backlinks'].add(base)
    return notes


def neighbors(note, notes, exclude_types=('index', 'changelog')):
    out = set()
    for t in note['links'] | note['backlinks']:
        if t not in notes or t == note:
            continue
        if notes[t]['fm'].get('type', '') in exclude_types:
            continue
        out.add(t)
    return out


def build_svg(c1_name, c2_name, only1, only2, shared, notes, height):
    """双中心布局：左中心 c1，右中心 c2，共享列居中"""
    W = 1200
    cx1, cx2 = 250, 950
    cy = height // 2
    parts = []

    def node_xy(name, col, idx, n):
        if col == 'left':
            return 130, 60 + idx * 52
        if col == 'right':
            return 1070, 60 + idx * 52
        return 600, 60 + idx * 52

    def edge(x1, y1, x2, y2, color, width=1.2, dash=''):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" opacity="0.55"{d}/>')

    def node(name, x, y, big=False):
        t = notes[name]['fm'].get('type', 'company')
        color = TYPE_COLORS.get(t, '#64748b')
        fill = TYPE_FILL.get(t, 'rgba(100,116,139,.14)')
        r = 40 if big else 20
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{color}" stroke-width="2"/>')
        label = name[:9] + ('…' if len(name) > 9 else '')
        parts.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" font-size="{12 if big else 10}" fill="#1e293b" font-weight="{"700" if big else "400"}">{html.escape(label)}</text>')
        parts.append(f'<title>{html.escape(name)}（{TYPE_LABELS.get(t, t)}）</title>')

    # 中心
    node(c1_name, cx1, cy, big=True)
    node(c2_name, cx2, cy, big=True)
    # 中心之间：不默认画"竞争"红粗线——关系类型由 cross-entity-scan 判定，这里用灰实线
    # （NVIDIA×SK海力士 等非竞争组合不应被默认标红）
    edge(cx1, cy, cx2, cy, '#94a3b8', width=2.5)

    # 共享列
    n_shared = len(shared)
    for i, name in enumerate(sorted(shared)):
        x, y = node_xy(name, 'mid', i, n_shared)
        node(name, x, y)
        edge(cx1, cy, x, y, '#94a3b8')
        edge(cx2, cy, x, y, '#94a3b8')

    # 左列（only1）
    for i, name in enumerate(sorted(only1)):
        x, y = node_xy(name, 'left', i, len(only1))
        node(name, x, y)
        edge(cx1, cy, x, y, '#3b82f6')

    # 右列（only2）
    for i, name in enumerate(sorted(only2)):
        x, y = node_xy(name, 'right', i, len(only2))
        node(name, x, y)
        edge(cx2, cy, x, y, '#10b981')

    return f'<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;background:#f8fafc;border-radius:12px;">' + ''.join(parts) + '</svg>'


def render(vault, c1, c2, out, png_path=None):
    notes = scan_vault(vault)
    if c1 not in notes:
        print(f'❌ 实体不存在: {c1}', file=sys.stderr)
        sys.exit(1)
    if c2 not in notes:
        print(f'❌ 实体不存在: {c2}', file=sys.stderr)
        sys.exit(1)

    n1 = neighbors(notes[c1], notes)
    n2 = neighbors(notes[c2], notes)
    shared = n1 & n2
    only1 = n1 - n2
    only2 = n2 - n1

    max_col = max(len(only1), len(only2), len(shared), 6)
    height = max(420, max_col * 52 + 80)

    svg = build_svg(c1, c2, only1, only2, shared, notes, height)

    def chip_list(items, note_map):
        if not items:
            return '<span style="color:#94a3b8">（无）</span>'
        return ' · '.join(
            f'<span style="color:{TYPE_COLORS.get(note_map[i]["fm"].get("type",""), "#64748b")}">{html.escape(i)}</span>'
            for i in sorted(items)
        )

    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(c1)} × {html.escape(c2)} · 关系全景看板</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; background:#eef2f7; color:#1e293b; padding:24px; }}
  .wrap {{ max-width:1240px; margin:0 auto; }}
  .hero {{ background:linear-gradient(135deg,#1e293b,#334155); color:#fff; border-radius:16px; padding:24px 32px; margin-bottom:20px; }}
  .hero h1 {{ font-size:24px; }}
  .hero .sub {{ opacity:.85; font-size:13px; margin-top:6px; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:16px; background:#fff; border-radius:12px; padding:14px 20px; margin-bottom:20px; font-size:12px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .legend .item {{ display:flex; align-items:center; gap:6px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
  .line-demo {{ width:26px; height:0; border-top:2px solid; display:inline-block; }}
  .card {{ background:#fff; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,.08); margin-top:20px; }}
  .card h2 {{ font-size:15px; margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid #e2e8f0; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  @media (max-width:900px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  .stat {{ font-size:14px; line-height:2; }}
  .stat b {{ font-size:22px; }}
  .foot {{ text-align:center; color:#94a3b8; font-size:12px; margin-top:20px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>{html.escape(c1)} × {html.escape(c2)} · 关系全景</h1>
    <div class="sub">全上下游/投资/竞争网络 · 数据来自 Obsidian 情报库（共 {len(notes)} 节点）</div>
  </div>
  <div class="legend">
    <span class="item"><span class="dot" style="background:#3b82f6"></span>公司</span>
    <span class="item"><span class="dot" style="background:#f59e0b"></span>人物</span>
    <span class="item"><span class="dot" style="background:#10b981"></span>产品</span>
    <span class="item"><span class="dot" style="background:#8b5cf6"></span>投资人</span>
    <span class="item"><span class="dot" style="background:#ef4444"></span>事件</span>
    <span class="item"><span class="dot" style="background:#64748b"></span>分析</span>
    <span class="item"><span class="line-demo" style="border-color:#ef4444"></span>竞争关系（cross-entity-scan 判定后可选标注）</span>
    <span class="item"><span class="line-demo" style="border-color:#94a3b8"></span>中心关联（类型见 cross-entity-scan）</span>
    <span class="item"><span class="line-demo" style="border-color:#3b82f6"></span>{html.escape(c1)} 关联</span>
    <span class="item"><span class="line-demo" style="border-color:#10b981"></span>{html.escape(c2)} 关联</span>
    <span class="item"><span class="line-demo" style="border-color:#94a3b8"></span>共享关联</span>
  </div>
  {svg}
  <div class="grid2">
    <div class="card">
      <h2>统计</h2>
      <div class="stat">
        {html.escape(c1)} 直接关联：<b>{len(n1)}</b><br>
        {html.escape(c2)} 直接关联：<b>{len(n2)}</b><br>
        <span style="color:#ef4444">双方共享节点（重叠/间接竞争点）：<b>{len(shared)}</b></span><br>
        {html.escape(c1)} 独有：{len(only1)} ｜ {html.escape(c2)} 独有：{len(only2)}
      </div>
    </div>
    <div class="card">
      <h2>共享节点（供应链重叠 / 共同生态 / 共同竞品）</h2>
      <div style="font-size:13px;line-height:2">{chip_list(shared, notes)}</div>
    </div>
  </div>
  <div class="grid2">
    <div class="card">
      <h2>{html.escape(c1)} 独有关联</h2>
      <div style="font-size:13px;line-height:2">{chip_list(only1, notes)}</div>
    </div>
    <div class="card">
      <h2>{html.escape(c2)} 独有关联</h2>
      <div style="font-size:13px;line-height:2">{chip_list(only2, notes)}</div>
    </div>
  </div>
  <div class="foot">由 panorama.py 生成 · 数据采集自公开渠道（详见各节点来源）</div>
</div>
</body>
</html>'''

    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'✅ 全景看板已生成: {out}')
    print(f'   {c1} 关联 {len(n1)} | {c2} 关联 {len(n2)} | 共享 {len(shared)} | 画布 {1200}x{height}')

    if png_path:
        print(f'   PNG 输出: {png_path}')


def main():
    ap = argparse.ArgumentParser(description='双实体全景关系看板')
    ap.add_argument('vault', help='Obsidian vault 路径')
    ap.add_argument('entity_a', help='中心实体 A')
    ap.add_argument('entity_b', help='中心实体 B')
    ap.add_argument('-o', '--output', default='全景看板.html', help='输出 HTML 路径')
    ap.add_argument('--png', default=None, help='输出 PNG 路径（需外部渲染）')
    args = ap.parse_args()
    render(args.vault, args.entity_a, args.entity_b, args.output, args.png)


if __name__ == '__main__':
    main()
